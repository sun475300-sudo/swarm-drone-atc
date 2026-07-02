"""TRANSCENDENCE Phase 241-243 — 다중 관제사 세션·명령 검증·충돌 해결 회귀."""

from __future__ import annotations

import pytest

from simulation.atc_multiuser_session import (
    SESSION_TTL_S,
    AtcCommand,
    ControllerRole,
    SessionRegistry,
    resolve_conflict,
    validate_command,
)


class _FakeClock:
    def __init__(self, t: float = 0.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t


def _cmd(cid: str, role: ControllerRole, drone: str = "D1", command: str = "HOLD",
         ts: float = 10.0, seq: int = 1) -> AtcCommand:
    return AtcCommand(controller_id=cid, role=role, drone_id=drone,
                      command=command, timestamp_s=ts, seq=seq)


# ── Phase 242: SessionRegistry ─────────────────────────────────────────────

class TestSessionRegistry:
    def test_register_and_get(self) -> None:
        clock = _FakeClock(100.0)
        reg = SessionRegistry(clock=clock)
        sess = reg.register("alice", ControllerRole.OPERATOR)
        assert sess.controller_id == "alice"
        assert reg.get("alice") is not None
        assert reg.active_count == 1

    def test_register_rejects_bad_id(self) -> None:
        reg = SessionRegistry(clock=_FakeClock())
        with pytest.raises(ValueError):
            reg.register("", ControllerRole.ADMIN)
        with pytest.raises(ValueError):
            reg.register("x" * 65, ControllerRole.ADMIN)

    def test_heartbeat_extends_session(self) -> None:
        clock = _FakeClock(0.0)
        reg = SessionRegistry(clock=clock)
        reg.register("bob", ControllerRole.ADMIN)
        clock.t = SESSION_TTL_S - 1  # 만료 직전 하트비트
        assert reg.heartbeat("bob") is True
        clock.t = SESSION_TTL_S + 10  # 원래라면 만료 시점이지만 하트비트로 연장됨
        assert reg.sweep_expired() == []
        assert reg.active_count == 1

    def test_sweep_removes_expired_deterministic_order(self) -> None:
        clock = _FakeClock(0.0)
        reg = SessionRegistry(clock=clock)
        reg.register("zed", ControllerRole.OPERATOR)
        reg.register("amy", ControllerRole.OPERATOR)
        clock.t = SESSION_TTL_S + 1
        assert reg.sweep_expired() == ["amy", "zed"]  # 정렬 — 결정적
        assert reg.active_count == 0

    def test_heartbeat_unknown_controller(self) -> None:
        reg = SessionRegistry(clock=_FakeClock())
        assert reg.heartbeat("ghost") is False


# ── Phase 241: validate_command ────────────────────────────────────────────

class TestValidateCommand:
    def _session(self, role: ControllerRole = ControllerRole.OPERATOR):
        reg = SessionRegistry(clock=_FakeClock(0.0))
        return reg.register("op1", role)

    def test_valid_command_accepted(self) -> None:
        v = validate_command(_cmd("op1", ControllerRole.OPERATOR), self._session(), now_s=1.0)
        assert v.accepted and v.reason == "OK"

    def test_no_session_rejected(self) -> None:
        v = validate_command(_cmd("op1", ControllerRole.OPERATOR), None, now_s=1.0)
        assert not v.accepted and "NO_SESSION" in v.reason

    def test_expired_session_rejected(self) -> None:
        v = validate_command(
            _cmd("op1", ControllerRole.OPERATOR), self._session(), now_s=SESSION_TTL_S + 1
        )
        assert not v.accepted and "SESSION_EXPIRED" in v.reason

    def test_viewer_forbidden(self) -> None:
        v = validate_command(
            _cmd("op1", ControllerRole.VIEWER), self._session(ControllerRole.VIEWER), now_s=1.0
        )
        assert not v.accepted and "FORBIDDEN" in v.reason

    def test_unsupported_command_rejected(self) -> None:
        v = validate_command(
            _cmd("op1", ControllerRole.ADMIN, command="SELF_DESTRUCT"),
            self._session(ControllerRole.ADMIN), now_s=1.0,
        )
        assert not v.accepted and "UNSUPPORTED_COMMAND" in v.reason

    def test_invalid_drone_id_rejected(self) -> None:
        for bad in ("", "  ", "d" * 65):
            v = validate_command(
                _cmd("op1", ControllerRole.ADMIN, drone=bad), self._session(ControllerRole.ADMIN), now_s=1.0
            )
            assert not v.accepted and "INVALID_DRONE_ID" in v.reason


# ── Phase 243: resolve_conflict 결정성 ─────────────────────────────────────

class TestResolveConflict:
    def test_higher_role_wins(self) -> None:
        a = _cmd("admin1", ControllerRole.ADMIN, ts=20.0)   # 늦었지만 admin
        b = _cmd("op1", ControllerRole.OPERATOR, ts=10.0)   # 빨랐지만 operator
        winners = resolve_conflict([a, b])
        assert winners["D1"].controller_id == "admin1"

    def test_same_role_earlier_timestamp_wins(self) -> None:
        a = _cmd("op-late", ControllerRole.OPERATOR, ts=20.0)
        b = _cmd("op-early", ControllerRole.OPERATOR, ts=10.0)
        assert resolve_conflict([a, b])["D1"].controller_id == "op-early"

    def test_full_tie_sha_tiebreak_is_input_order_independent(self) -> None:
        a = _cmd("alpha", ControllerRole.OPERATOR, ts=10.0)
        b = _cmd("bravo", ControllerRole.OPERATOR, ts=10.0)
        w1 = resolve_conflict([a, b])["D1"].controller_id
        w2 = resolve_conflict([b, a])["D1"].controller_id
        assert w1 == w2  # 입력 순서 무관 — 결정성

    def test_per_drone_independent_winners(self) -> None:
        cmds = [
            _cmd("op1", ControllerRole.OPERATOR, drone="D1", ts=10.0),
            _cmd("admin1", ControllerRole.ADMIN, drone="D2", ts=10.0),
        ]
        winners = resolve_conflict(cmds)
        assert winners["D1"].controller_id == "op1"
        assert winners["D2"].controller_id == "admin1"

    def test_empty_input(self) -> None:
        assert resolve_conflict([]) == {}


# ── Phase 241: 라우터 팩토리 (fastapi 옵트인) ──────────────────────────────

class TestRouterFactory:
    def test_create_router_requires_fastapi(self) -> None:
        pytest.importorskip("fastapi")
        from simulation.atc_multiuser_session import create_atc_router

        router = create_atc_router()
        paths = [r.path for r in router.routes]
        assert "/ws/atc" in paths
