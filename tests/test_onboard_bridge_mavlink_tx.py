"""Tests for the MAVLink TX additions (P1-A feat/mavlink-tx).

Covers:
- TelemetrySnapshot ATTITUDE fields default to NaN and roundtrip via to_json.
- MavlinkAdapter.poll_telemetry consumes ATTITUDE messages.
- send_position_target_local_ned wires SET_POSITION_TARGET_LOCAL_NED.
- set_mode_message uses dedicated SET_MODE path (not COMMAND_LONG).
- LostLinkStateMachine 3-phase transitions (NORMAL → HOLDING → RTL → LANDING).
- heartbeat_age_s monotonically tracks staleness.
"""
from __future__ import annotations

import asyncio
import json
import math
import time
from typing import Any

import pytest

from src.hardware.onboard_bridge import (
    LostLinkConfig,
    LostLinkPhase,
    LostLinkStateMachine,
    MavlinkAdapter,
    TelemetrySnapshot,
)


# --- Helpers ---


def _base_snapshot(**overrides: Any) -> TelemetrySnapshot:
    defaults = dict(
        drone_id=7,
        timestamp_ns=1,
        lat_deg=37.5,
        lon_deg=127.0,
        alt_msl_m=120.0,
        alt_rel_m=30.0,
        vx_mps=1.0,
        vy_mps=0.0,
        vz_mps=-0.1,
        heading_deg=90.0,
        battery_pct=88.0,
        mode="GUIDED",
        armed=True,
        gps_fix_type=3,
    )
    defaults.update(overrides)
    return TelemetrySnapshot(**defaults)


class _ScriptedMsg:
    def __init__(self, mtype: str, **fields: Any) -> None:
        self._mtype = mtype
        for k, v in fields.items():
            setattr(self, k, v)

    def get_type(self) -> str:
        return self._mtype


class _ScriptedConnection:
    """Replays a queue of pre-canned messages through recv_match."""

    def __init__(self, msgs: list[_ScriptedMsg]) -> None:
        self._queue = list(msgs)
        self.sent_position_targets: list[tuple] = []
        self.sent_set_modes: list[tuple] = []
        self.target_system = 1
        self.target_component = 1

        class _Mav:
            def __init__(self, outer: "_ScriptedConnection") -> None:
                self._outer = outer

            def set_position_target_local_ned_send(self, *args: Any) -> None:
                self._outer.sent_position_targets.append(args)

            def set_mode_send(self, *args: Any) -> None:
                self._outer.sent_set_modes.append(args)

        self.mav = _Mav(self)

    def recv_match(self, type=None, blocking=False, **_kw):  # noqa: A002
        types = type if isinstance(type, list) else [type] if type else None
        for i, m in enumerate(self._queue):
            if types is None or m.get_type() in types:
                return self._queue.pop(i)
        return None

    def close(self) -> None:  # pragma: no cover - close is trivial
        self._queue.clear()


# --- Tests ---


def test_telemetry_snapshot_attitude_default_nan():
    snap = _base_snapshot()
    assert math.isnan(snap.roll_rad)
    assert math.isnan(snap.pitch_rad)
    assert math.isnan(snap.yaw_rad)
    assert snap.attitude_ts_ns == 0


def test_telemetry_snapshot_to_json_omits_attitude_when_absent():
    snap = _base_snapshot()
    payload = json.loads(snap.to_json())
    assert "att" not in payload


def test_telemetry_snapshot_to_json_includes_attitude_when_present():
    snap = _base_snapshot(
        roll_rad=0.1, pitch_rad=-0.2, yaw_rad=1.57, attitude_ts_ns=42
    )
    payload = json.loads(snap.to_json())
    assert payload["att"] == {
        "roll": 0.1,
        "pitch": -0.2,
        "yaw": 1.57,
        "t_ns": 42,
    }


@pytest.mark.asyncio
async def test_poll_telemetry_consumes_attitude_message():
    pytest.importorskip("pymavlink")
    adapter = MavlinkAdapter("udp:0.0.0.0:14550")
    adapter._connection = _ScriptedConnection(
        [
            _ScriptedMsg("ATTITUDE", roll=0.05, pitch=-0.02, yaw=1.0),
            _ScriptedMsg("HEARTBEAT", base_mode=0x80, custom_mode=0),
            _ScriptedMsg(
                "GLOBAL_POSITION_INT",
                lat=int(37.5 * 1e7),
                lon=int(127.0 * 1e7),
                alt=120_000,
                relative_alt=30_000,
                vx=100,
                vy=0,
                vz=-10,
                hdg=9000,
            ),
        ]
    )
    snap = await adapter.poll_telemetry(drone_id=7)
    assert snap is not None
    assert pytest.approx(snap.roll_rad) == 0.05
    assert pytest.approx(snap.pitch_rad) == -0.02
    assert pytest.approx(snap.yaw_rad) == 1.0
    assert snap.attitude_ts_ns > 0


@pytest.mark.asyncio
async def test_send_position_target_local_ned_writes_to_wire():
    pytest.importorskip("pymavlink")
    adapter = MavlinkAdapter("udp:0.0.0.0:14550")
    conn = _ScriptedConnection([])
    adapter._connection = conn
    ok = await adapter.send_position_target_local_ned(
        north_m=10.0, east_m=-5.0, down_m=-2.0, yaw_rad=1.57
    )
    assert ok is True
    assert len(conn.sent_position_targets) == 1
    args = conn.sent_position_targets[0]
    # args = (time_boot_ms, target_sys, target_comp, frame, type_mask,
    #         n,e,d, vx,vy,vz, afx,afy,afz, yaw, yaw_rate)
    assert args[1] == 1  # target_system
    assert args[5] == 10.0  # north
    assert args[6] == -5.0  # east
    assert args[7] == -2.0  # down
    assert args[14] == 1.57  # yaw


@pytest.mark.asyncio
async def test_send_position_target_raises_when_not_connected():
    adapter = MavlinkAdapter("udp:0.0.0.0:14550")
    with pytest.raises(RuntimeError):
        await adapter.send_position_target_local_ned(0, 0, 0)


@pytest.mark.asyncio
async def test_set_mode_message_observes_heartbeat_echo():
    pytest.importorskip("pymavlink")
    adapter = MavlinkAdapter("udp:0.0.0.0:14550")
    # Queue a HEARTBEAT that reflects custom_mode=6 (RTL) so set_mode_message
    # observes the ACK echo and returns True immediately.
    adapter._connection = _ScriptedConnection(
        [_ScriptedMsg("HEARTBEAT", base_mode=0x80, custom_mode=6)]
    )
    ok = await adapter.set_mode_message(custom_mode=6)
    assert ok is True
    assert len(adapter._connection.sent_set_modes) == 1


def test_heartbeat_age_s_infinite_before_any_heartbeat():
    adapter = MavlinkAdapter("udp:0.0.0.0:14550")
    assert math.isinf(adapter.heartbeat_age_s())


def test_heartbeat_age_s_grows_with_time():
    adapter = MavlinkAdapter("udp:0.0.0.0:14550")
    adapter._last_heartbeat_monotonic_s = 100.0
    assert adapter.heartbeat_age_s(now_monotonic_s=103.5) == pytest.approx(3.5)


# --- Lost-Link state machine ---


def test_lost_link_normal_when_link_alive():
    sm = LostLinkStateMachine()
    assert sm.update(heartbeat_age_s=0.5, snapshot=None) is None
    assert sm.phase == LostLinkPhase.NORMAL


def test_lost_link_transitions_to_holding_after_hold_timeout():
    sm = LostLinkStateMachine(LostLinkConfig(hold_timeout_s=3.0))
    transition = sm.update(heartbeat_age_s=5.0, snapshot=None, now_s=100.0)
    assert transition == LostLinkPhase.HOLDING
    assert sm.phase == LostLinkPhase.HOLDING


def test_lost_link_transitions_to_rtl_after_30s():
    sm = LostLinkStateMachine(LostLinkConfig(hold_timeout_s=3.0, rtl_after_s=30.0))
    # Establish HOLDING at t=10s with 5s silence (started at t=5s).
    sm.update(heartbeat_age_s=5.0, snapshot=None, now_s=10.0)
    assert sm.phase == LostLinkPhase.HOLDING
    # Advance to t=40s; silence has lasted 35s ≥ rtl_after_s.
    transition = sm.update(heartbeat_age_s=35.0, snapshot=None, now_s=40.0)
    assert transition == LostLinkPhase.RTL
    assert sm.phase == LostLinkPhase.RTL


def test_lost_link_transitions_to_landing_within_home_radius():
    sm = LostLinkStateMachine(
        LostLinkConfig(hold_timeout_s=3.0, rtl_after_s=30.0, land_radius_m=50.0),
        home_position=(37.5, 127.0, 100.0),
    )
    # Drive to RTL first.
    sm.update(heartbeat_age_s=5.0, snapshot=None, now_s=10.0)
    sm.update(heartbeat_age_s=35.0, snapshot=None, now_s=40.0)
    assert sm.phase == LostLinkPhase.RTL
    # Snapshot near home (well within 50 m).
    near_home = _base_snapshot(lat_deg=37.5, lon_deg=127.0, alt_msl_m=110.0)
    transition = sm.update(heartbeat_age_s=40.0, snapshot=near_home, now_s=45.0)
    assert transition == LostLinkPhase.LANDING
    assert sm.phase == LostLinkPhase.LANDING


def test_lost_link_recovers_to_normal_when_link_restored():
    sm = LostLinkStateMachine(LostLinkConfig(hold_timeout_s=3.0))
    sm.update(heartbeat_age_s=10.0, snapshot=None, now_s=10.0)
    assert sm.phase == LostLinkPhase.HOLDING
    transition = sm.update(heartbeat_age_s=0.5, snapshot=None, now_s=11.0)
    assert transition == LostLinkPhase.NORMAL
    assert sm.phase == LostLinkPhase.NORMAL


def test_lost_link_set_home_then_distance():
    sm = LostLinkStateMachine()
    sm.set_home(37.5, 127.0, 100.0)
    snap = _base_snapshot(lat_deg=37.5001, lon_deg=127.0001, alt_msl_m=100.0)
    # Should be ~13 m diagonally — definitely under default 50 m radius.
    d = sm._distance_to_home_m(snap)
    assert 5.0 < d < 30.0


def test_lost_link_mode_for_phase_returns_ardupilot_modes():
    assert LostLinkStateMachine.mode_for_phase(LostLinkPhase.HOLDING) == 5
    assert LostLinkStateMachine.mode_for_phase(LostLinkPhase.RTL) == 6
    assert LostLinkStateMachine.mode_for_phase(LostLinkPhase.LANDING) == 9
    assert LostLinkStateMachine.mode_for_phase(LostLinkPhase.NORMAL) is None
