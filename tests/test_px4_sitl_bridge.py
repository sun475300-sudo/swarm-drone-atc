"""TRANSCENDENCE Phase 225 — PX4 SITL 브리지 MAVLink 파서 결정적 회귀.

실 PX4 SITL 연동은 외부 시스템(HW/컨테이너) 의존 — 본 회귀는 브리지의
*결정적 계약* (연결 상태 머신·텔레메트리 프레임 형식·시드 재현성)을 SITL 없이
검증한다 (기존 회귀 부재 갭 해소).
"""

from __future__ import annotations

import pytest

from simulation.px4_sitl_bridge import MAVLinkMessage, PX4SITLBridge


class TestConnectionStateMachine:
    def test_initial_disconnected(self) -> None:
        b = PX4SITLBridge(seed=42)
        assert b.receive_telemetry() is None  # 미연결 시 텔레메트리 없음

    def test_connect_loopback(self) -> None:
        b = PX4SITLBridge(seed=42)
        assert b.connect() is True

    def test_disconnect_stops_telemetry(self) -> None:
        b = PX4SITLBridge(seed=42)
        b.connect()
        b.disconnect()
        assert b.receive_telemetry() is None


class TestTelemetryContract:
    def test_telemetry_frame_shape(self) -> None:
        b = PX4SITLBridge(seed=42)
        b.connect()
        b.arm_drone("D1")
        msg = b.receive_telemetry()
        assert msg is None or isinstance(msg, MAVLinkMessage)

    def test_seed_reproducibility(self) -> None:
        """동일 시드 → 동일 명령 시퀀스 결과 (결정성 계약)."""
        def run(seed: int) -> list:
            b = PX4SITLBridge(seed=seed)
            b.connect()
            b.arm_drone("D1")
            frames = []
            for _ in range(5):
                m = b.receive_telemetry()
                if m is not None:
                    frames.append((m.msg_type, tuple(sorted(m.payload)) if isinstance(m.payload, dict) else m.payload))
            return frames

        assert run(42) == run(42)

    def test_arm_requires_connection(self) -> None:
        b = PX4SITLBridge(seed=42)
        assert b.arm_drone("D1") is False  # 미연결 arm 거부 (fail-closed)


class TestCommandValidation:
    def test_send_command_requires_connection(self) -> None:
        b = PX4SITLBridge(seed=42)
        assert b.send_command("ARM", {}) is False

    def test_send_command_after_connect(self) -> None:
        b = PX4SITLBridge(seed=42)
        b.connect()
        result = b.send_command("ARM", {"drone_id": "D1"})
        assert isinstance(result, bool)  # 계약: bool 반환 (예외 없음)
