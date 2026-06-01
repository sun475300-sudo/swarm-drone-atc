"""P712 — API 감사 로그 (Audit Log).

모든 인증/인가/상태 변경 이벤트를 구조화된 JSONL 파일에 기록한다.
P714에서 TimescaleDB로 마이그레이션 예정.

사용법:
    from api.audit_log import audit

    await audit("admin", "scenario.run", {"scenario_id": "01_corridor_crossing"})
    await audit("pilot_demo", "auth.login", {}, success=True)
    await audit("attacker", "auth.login", {"reason": "bad password"}, success=False)

파일 위치: logs/audit.jsonl  (SDACS_AUDIT_LOG_PATH 환경 변수로 재정의 가능)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from pathlib import Path

LOGGER = logging.getLogger("sdacs.audit")

_LOG_PATH: Path = Path(os.environ.get("SDACS_AUDIT_LOG_PATH", "logs/audit.jsonl"))
_write_lock: asyncio.Lock | None = None  # 초기화는 첫 사용 시 (event loop 의존)


def _get_lock() -> asyncio.Lock:
    global _write_lock
    if _write_lock is None:
        _write_lock = asyncio.Lock()
    return _write_lock


async def audit(
    actor: str,
    action: str,
    details: dict | None = None,
    success: bool = True,
    request_id: str | None = None,
) -> None:
    """감사 이벤트를 비동기로 기록한다.

    Args:
        actor:      사용자명 또는 시스템 식별자 (예: "admin", "system")
        action:     이벤트 코드 (예: "auth.login", "scenario.run", "user.create")
        details:    추가 컨텍스트 (직렬화 가능한 dict)
        success:    작업 성공 여부
        request_id: 추적용 요청 ID (HTTP X-Request-ID 헤더 등)
    """
    entry = {
        "ts": time.time(),
        "actor": actor,
        "action": action,
        "success": success,
        "details": details or {},
    }
    if request_id:
        entry["request_id"] = request_id

    line = json.dumps(entry, ensure_ascii=False)

    try:
        async with _get_lock():
            await asyncio.to_thread(_write_line, line)
    except Exception as exc:
        LOGGER.error("audit write failed: %s | entry=%s", exc, line)


def _write_line(line: str) -> None:
    """로그 파일에 한 줄을 동기 방식으로 쓴다."""
    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def read_audit_log(limit: int = 100, offset: int = 0) -> list[dict]:
    """감사 로그를 최근 순으로 읽는다 (동기).

    Args:
        limit:  반환할 최대 항목 수
        offset: 건너뛸 항목 수 (페이지네이션)
    """
    if not _LOG_PATH.exists():
        return []
    try:
        lines = _LOG_PATH.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []

    parsed: list[dict] = []
    for raw in reversed(lines):
        raw = raw.strip()
        if not raw:
            continue
        try:
            parsed.append(json.loads(raw))
        except json.JSONDecodeError:
            continue

    return parsed[offset : offset + limit]


__all__ = ["audit", "read_audit_log"]
