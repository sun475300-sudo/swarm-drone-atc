"""TRANSCENDENCE Phase 241-243 — 다중 관제사 WebSocket 관제 세션 코어.

Phase 241 (WS 관제 서버): FastAPI 라우터 팩토리 `create_atc_router()` 로
``/ws/atc`` 관제 명령 채널을 제공한다. fastapi 미설치 환경에서도 코어 로직
(세션 레지스트리·명령 검증·충돌 해결)은 순수 파이썬으로 동작한다.

Phase 242 (JWT 다중 관제사 세션): `SessionRegistry` 가 관제사 세션을
role(RBAC) 과 함께 등록·만료 관리한다. 토큰 검증 자체는 `api.auth` 에 위임
(중복 구현 없음).

Phase 243 (동시 편집 충돌 해결 검증): 동일 드론에 대한 동시 명령을
**결정적** 3단 타이브레이크로 해결한다:
  1) role rank 높은 쪽 (admin > operator > viewer)
  2) 동률이면 timestamp 이른 쪽 (선점)
  3) 그래도 동률이면 sha256(controller_id) 사전순 — 무작위성 0

설계 원칙 (기존 코드 게이트 모듈과 정합):
- frozen dataclass·부수효과 최소·무작위성 0
- 기존 `api/fastapi_server.py` 무수정 — 라우터는 옵트인 include
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any

__all__ = [
    "AtcCommand",
    "CommandVerdict",
    "ControllerRole",
    "ControllerSession",
    "SessionRegistry",
    "create_atc_router",
    "resolve_conflict",
    "validate_command",
]

# 세션 하트비트 없이 유지되는 최대 시간 (초)
SESSION_TTL_S = 120.0

# 지원 관제 명령 셋 — 시뮬레이터 `_sdacs.atcCommand()` 와 정렬
SUPPORTED_COMMANDS = frozenset(
    {"HOLD", "RESUME", "RTL", "LAND", "CLIMB", "DESCEND", "REROUTE", "PRIORITY"}
)


class ControllerRole(str, Enum):
    """관제사 RBAC 역할 — api.auth 의 Role 과 값 정렬 (문자열 호환)."""

    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


_ROLE_RANK: dict[ControllerRole, int] = {
    ControllerRole.ADMIN: 3,
    ControllerRole.OPERATOR: 2,
    ControllerRole.VIEWER: 1,
}


@dataclass(frozen=True)
class ControllerSession:
    """관제사 1인의 활성 세션 (Phase 242)."""

    controller_id: str
    role: ControllerRole
    connected_at_s: float
    last_heartbeat_s: float

    def is_expired(self, now_s: float, ttl_s: float = SESSION_TTL_S) -> bool:
        return (now_s - self.last_heartbeat_s) > ttl_s


@dataclass(frozen=True)
class AtcCommand:
    """관제 명령 1건 — 결정적 충돌 해결의 단위 (Phase 243)."""

    controller_id: str
    role: ControllerRole
    drone_id: str
    command: str
    timestamp_s: float
    seq: int  # 관제사별 단조 증가 시퀀스 (재전송/순서 뒤틀림 감지)
    params: tuple = ()  # 해시 가능해야 frozen 유지 — dict 대신 튜플 쌍


@dataclass(frozen=True)
class CommandVerdict:
    """명령 검증 결과."""

    accepted: bool
    reason: str


def validate_command(cmd: AtcCommand, session: ControllerSession | None, now_s: float) -> CommandVerdict:
    """명령 1건을 결정적으로 검증한다 (Phase 241 게이트).

    거부 우선순위: 세션 없음 > 세션 만료 > viewer 권한 > 미지원 명령 > 빈 드론 id.
    """
    if session is None:
        return CommandVerdict(False, "NO_SESSION: 등록되지 않은 관제사")
    if session.is_expired(now_s):
        return CommandVerdict(False, "SESSION_EXPIRED: 하트비트 TTL 초과")
    if _ROLE_RANK[cmd.role] < _ROLE_RANK[ControllerRole.OPERATOR]:
        return CommandVerdict(False, "FORBIDDEN: viewer 는 관제 명령 불가")
    if cmd.command not in SUPPORTED_COMMANDS:
        return CommandVerdict(
            False, f"UNSUPPORTED_COMMAND: {cmd.command!r} (지원: {sorted(SUPPORTED_COMMANDS)})"
        )
    if not cmd.drone_id or not cmd.drone_id.strip() or len(cmd.drone_id) > 64:
        return CommandVerdict(False, "INVALID_DRONE_ID: 빈 값 또는 64자 초과")
    return CommandVerdict(True, "OK")


def _tiebreak_key(cmd: AtcCommand) -> tuple:
    """결정적 3단 타이브레이크 키 (작을수록 우선).

    role rank 는 내림차순(높을수록 우선)이라 부호 반전, timestamp 는 이른 쪽,
    마지막은 sha256(controller_id) 사전순 — 어떤 입력 순서든 같은 승자.
    """
    return (
        -_ROLE_RANK[cmd.role],
        cmd.timestamp_s,
        hashlib.sha256(cmd.controller_id.encode()).hexdigest(),
    )


def resolve_conflict(commands: list[AtcCommand]) -> dict[str, AtcCommand]:
    """동일 드론 동시 명령을 드론별 승자 1건으로 결정적 해결 (Phase 243).

    반환: {drone_id: 승자 명령}. 입력 순서와 무관하게 동일 결과 (결정성).
    """
    winners: dict[str, AtcCommand] = {}
    for cmd in sorted(commands, key=_tiebreak_key):
        if cmd.drone_id not in winners:
            winners[cmd.drone_id] = cmd
    return winners


class SessionRegistry:
    """관제사 세션 레지스트리 (Phase 242) — 등록·하트비트·만료 스윕.

    시계는 주입식(clock 콜러블) — 테스트 결정성 보장.
    """

    def __init__(self, clock: Callable[[], float] = time.monotonic, ttl_s: float = SESSION_TTL_S) -> None:
        self._clock = clock
        self._ttl_s = ttl_s
        self._sessions: dict[str, ControllerSession] = {}

    def register(self, controller_id: str, role: ControllerRole) -> ControllerSession:
        if not controller_id or len(controller_id) > 64:
            raise ValueError("controller_id 는 1~64자")
        now = self._clock()
        sess = ControllerSession(
            controller_id=controller_id, role=role, connected_at_s=now, last_heartbeat_s=now
        )
        self._sessions[controller_id] = sess
        return sess

    def heartbeat(self, controller_id: str) -> bool:
        sess = self._sessions.get(controller_id)
        if sess is None:
            return False
        self._sessions[controller_id] = replace(sess, last_heartbeat_s=self._clock())
        return True

    def get(self, controller_id: str) -> ControllerSession | None:
        return self._sessions.get(controller_id)

    def remove(self, controller_id: str) -> None:
        self._sessions.pop(controller_id, None)

    def sweep_expired(self) -> list[str]:
        """만료 세션 제거 후 제거된 id 목록 반환 (결정적 — 정렬)."""
        now = self._clock()
        expired = sorted(
            cid for cid, s in self._sessions.items() if s.is_expired(now, self._ttl_s)
        )
        for cid in expired:
            del self._sessions[cid]
        return expired

    @property
    def active_count(self) -> int:
        return len(self._sessions)

    def active_controllers(self) -> list[str]:
        return sorted(self._sessions)


def create_atc_router(registry: SessionRegistry | None = None) -> Any:
    """Phase 241 — `/ws/atc` FastAPI 라우터 팩토리 (fastapi 옵트인).

    사용 (api/fastapi_server.py 에 1줄):
        app.include_router(create_atc_router())

    프로토콜 (JSON text frame):
      → {"type":"register","controller_id":"...","token":"<JWT>"}
      ← {"type":"registered","role":"operator","active_controllers":[...]}
      → {"type":"command","drone_id":"D1","command":"HOLD","seq":1}
      ← {"type":"ack","accepted":true,"reason":"OK"}   (거부 시 accepted=false)
      → {"type":"heartbeat"}
      명령은 검증 통과 시 다른 접속 관제사 전원에게 브로드캐스트.
    """
    from fastapi import APIRouter, WebSocket, WebSocketDisconnect  # 지역 import — 옵트인

    from api.auth import verify_token  # JWT 검증 위임 (중복 구현 금지)

    reg = registry if registry is not None else SessionRegistry(clock=time.time)
    router = APIRouter()
    peers: dict[str, WebSocket] = {}
    seq_state: dict[str, int] = {}

    async def _broadcast(event: dict, exclude: str | None = None) -> None:
        dead = []
        for cid, sock in peers.items():
            if cid == exclude:
                continue
            try:
                await sock.send_text(json.dumps(event))
            except Exception:  # noqa: BLE001 — 끊긴 소켓은 정리
                dead.append(cid)
        for cid in dead:
            peers.pop(cid, None)
            reg.remove(cid)

    @router.websocket("/ws/atc")
    async def ws_atc(ws: WebSocket) -> None:  # pragma: no cover — E2E 로 검증
        await ws.accept()
        cid: str | None = None
        try:
            while True:
                raw = await ws.receive_text()
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    await ws.send_text(json.dumps({"type": "error", "error": "BAD_JSON"}))
                    continue
                mtype = msg.get("type")

                if mtype == "register":
                    try:
                        payload = verify_token(str(msg.get("token", "")))
                    except Exception:  # HTTPException 포함 — 소켓 프로토콜로 변환
                        await ws.send_text(json.dumps({"type": "error", "error": "AUTH_FAILED"}))
                        continue
                    cid = str(msg.get("controller_id") or payload.get("sub") or "")
                    try:
                        role = ControllerRole(str(payload.get("role", "viewer")))
                    except ValueError:
                        role = ControllerRole.VIEWER
                    reg.register(cid, role)
                    peers[cid] = ws
                    seq_state[cid] = 0
                    await ws.send_text(json.dumps({
                        "type": "registered", "role": role.value,
                        "active_controllers": reg.active_controllers(),
                    }))

                elif mtype == "heartbeat" and cid:
                    reg.heartbeat(cid)

                elif mtype == "command":
                    sess = reg.get(cid) if cid else None
                    seq = int(msg.get("seq", 0))
                    cmd = AtcCommand(
                        controller_id=cid or "",
                        role=sess.role if sess else ControllerRole.VIEWER,
                        drone_id=str(msg.get("drone_id", "")),
                        command=str(msg.get("command", "")),
                        timestamp_s=time.time(),
                        seq=seq,
                    )
                    # seq 단조성 — 재전송·역전 프레임 거부
                    if cid is not None and seq <= seq_state.get(cid, 0):
                        await ws.send_text(json.dumps(
                            {"type": "ack", "accepted": False, "reason": "STALE_SEQ"}))
                        continue
                    verdict = validate_command(cmd, sess, time.time())
                    await ws.send_text(json.dumps(
                        {"type": "ack", "accepted": verdict.accepted, "reason": verdict.reason}))
                    if verdict.accepted and cid is not None:
                        seq_state[cid] = seq
                        await _broadcast({
                            "type": "atc_command", "controller_id": cid,
                            "drone_id": cmd.drone_id, "command": cmd.command, "seq": seq,
                        }, exclude=cid)
                else:
                    await ws.send_text(json.dumps({"type": "error", "error": "UNKNOWN_TYPE"}))
        except WebSocketDisconnect:
            pass
        finally:
            if cid is not None:
                peers.pop(cid, None)
                reg.remove(cid)

    return router
