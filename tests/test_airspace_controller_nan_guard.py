"""Phase 7 — airspace_controller _update_drone_state NaN/None 가드 회귀.

defense in depth: ws_bridge·SITL·외부 텔레메트리 통합 시 NaN/None position/velocity 가
내부 CommBus 직접 호출 경로(`_on_message` → `_update_drone_state`)로 흘러도 silent NaN
전파를 차단해야 한다. fastapi WS 진입 검증(_normalize_live_telemetry)은 별도 경로.
"""

from __future__ import annotations

import dataclasses
import math
from unittest.mock import MagicMock

import numpy as np
import pytest

from src.airspace_control.comms.communication_bus import CommunicationBus
from src.airspace_control.comms.message_types import TelemetryMessage
from src.airspace_control.controller.airspace_controller import AirspaceController


def _make_controller() -> AirspaceController:
    """최소 controller (실제 SimPy/CommBus 미사용)."""
    env = MagicMock()
    env.now = 0.0
    bus = MagicMock(spec=CommunicationBus)
    bus.subscribe = MagicMock()
    ctrl = AirspaceController(env=env, comm_bus=bus, control_period_s=1.0)
    return ctrl


def _tm(drone_id: str, position, velocity, timestamp: float = 0.5) -> TelemetryMessage:
    return TelemetryMessage(
        drone_id=drone_id,
        timestamp_s=timestamp,
        position=position,
        velocity=velocity,
        battery_pct=80.0,
        flight_phase="ENROUTE",
    )


class TestUpdateDroneStateNaNGuard:
    """_update_drone_state NaN/None 가드 회귀."""

    def test_valid_telemetry_accepted(self) -> None:
        """정상 텔레메트리는 등록되어야 함 (기준선)."""
        ctrl = _make_controller()
        ctrl._update_drone_state(
            _tm("D001", [100.0, 200.0, 50.0], [5.0, 0.0, 0.0])
        )
        assert "D001" in ctrl._active_drones

    def test_none_position_dropped(self) -> None:
        ctrl = _make_controller()
        ctrl._update_drone_state(_tm("D002", None, [5.0, 0.0, 0.0]))
        assert "D002" not in ctrl._active_drones

    def test_none_velocity_dropped(self) -> None:
        ctrl = _make_controller()
        ctrl._update_drone_state(_tm("D003", [100.0, 200.0, 50.0], None))
        assert "D003" not in ctrl._active_drones

    def test_nan_position_dropped(self) -> None:
        ctrl = _make_controller()
        ctrl._update_drone_state(
            _tm("D004", [math.nan, 200.0, 50.0], [5.0, 0.0, 0.0])
        )
        assert "D004" not in ctrl._active_drones

    def test_nan_velocity_dropped(self) -> None:
        ctrl = _make_controller()
        ctrl._update_drone_state(
            _tm("D005", [100.0, 200.0, 50.0], [math.nan, 0.0, 0.0])
        )
        assert "D005" not in ctrl._active_drones

    def test_inf_position_dropped(self) -> None:
        ctrl = _make_controller()
        ctrl._update_drone_state(
            _tm("D006", [math.inf, 200.0, 50.0], [5.0, 0.0, 0.0])
        )
        assert "D006" not in ctrl._active_drones

    def test_short_position_dropped(self) -> None:
        """2D position (3차원 미만)은 거부."""
        ctrl = _make_controller()
        ctrl._update_drone_state(
            _tm("D007", [100.0, 200.0], [5.0, 0.0, 0.0])
        )
        assert "D007" not in ctrl._active_drones

    def test_update_existing_drone_with_nan_ignored(self) -> None:
        """기존 등록 드론에 NaN 텔레메트리 와도 기존 position 보존."""
        ctrl = _make_controller()
        # 1st: 정상 등록
        ctrl._update_drone_state(
            _tm("D008", [100.0, 200.0, 50.0], [5.0, 0.0, 0.0], timestamp=0.5)
        )
        orig_pos = ctrl._active_drones["D008"].position.copy()
        # 2nd: NaN 도착 → 무시
        ctrl._update_drone_state(
            _tm("D008", [math.nan, math.nan, math.nan], [0.0, 0.0, 0.0], timestamp=1.5)
        )
        # 원래 position 보존
        np.testing.assert_array_equal(ctrl._active_drones["D008"].position, orig_pos)

    def test_partial_nan_velocity_dropped(self) -> None:
        """velocity 한 성분만 NaN 이어도 거부 (np.all 가드)."""
        ctrl = _make_controller()
        ctrl._update_drone_state(
            _tm("D009", [100.0, 200.0, 50.0], [5.0, math.nan, 0.0])
        )
        assert "D009" not in ctrl._active_drones
