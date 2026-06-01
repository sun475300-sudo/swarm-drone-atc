"""Tests for src/failsafe.py — P695 Failsafe Logic."""

from __future__ import annotations

import numpy as np
import pytest

from src.failsafe import (
    FailsafeAction,
    FailsafeConfig,
    FailsafeMonitor,
    GeofenceZone,
    SwarmFailsafe,
)


# ---------------------------------------------------------------------------
# GeofenceZone
# ---------------------------------------------------------------------------


class TestGeofenceZone:
    def _zone(self, radius=100.0, keep_in=True):
        return GeofenceZone(center_xy=(0.0, 0.0), radius_m=radius, keep_in=keep_in)

    def test_contains_inside(self):
        zone = self._zone()
        assert zone.contains(np.array([50.0, 0.0, 50.0])) is True

    def test_contains_outside(self):
        zone = self._zone()
        assert zone.contains(np.array([200.0, 0.0, 50.0])) is False

    def test_contains_on_boundary(self):
        zone = self._zone(radius=100.0)
        assert zone.contains(np.array([100.0, 0.0, 50.0])) is True

    def test_contains_below_floor(self):
        zone = GeofenceZone(center_xy=(0.0, 0.0), radius_m=100.0, min_alt_m=10.0)
        assert zone.contains(np.array([50.0, 0.0, 5.0])) is False

    def test_contains_above_ceiling(self):
        zone = GeofenceZone(center_xy=(0.0, 0.0), radius_m=100.0, max_alt_m=200.0)
        assert zone.contains(np.array([50.0, 0.0, 300.0])) is False

    def test_is_violated_keep_in_outside(self):
        zone = self._zone(keep_in=True)
        assert zone.is_violated(np.array([200.0, 0.0, 50.0])) is True

    def test_is_violated_keep_in_inside(self):
        zone = self._zone(keep_in=True)
        assert zone.is_violated(np.array([50.0, 0.0, 50.0])) is False

    def test_is_violated_keep_out_inside(self):
        zone = self._zone(keep_in=False)
        assert zone.is_violated(np.array([50.0, 0.0, 50.0])) is True

    def test_is_violated_keep_out_outside(self):
        zone = self._zone(keep_in=False)
        assert zone.is_violated(np.array([200.0, 0.0, 50.0])) is False

    def test_2d_position_defaults_alt_zero(self):
        zone = GeofenceZone(center_xy=(0.0, 0.0), radius_m=100.0, min_alt_m=0.0)
        assert zone.contains(np.array([50.0, 0.0])) is True


# ---------------------------------------------------------------------------
# FailsafeMonitor — comm loss
# ---------------------------------------------------------------------------


class TestFailsafeMonitorCommLoss:
    def _monitor(self, timeout=5.0):
        cfg = FailsafeConfig(comm_timeout_s=timeout, geofence_zones=[])
        return FailsafeMonitor(drone_id=1, config=cfg)

    def _pos(self):
        return np.array([0.0, 0.0, 50.0])

    def test_nominal_after_heartbeat(self):
        m = self._monitor()
        m.update_comm(timestamp=0.0)
        status = m.evaluate(current_time=4.9, position=self._pos())
        assert status.action == FailsafeAction.NONE

    def test_rtl_after_timeout(self):
        m = self._monitor(timeout=5.0)
        m.update_comm(timestamp=0.0)
        status = m.evaluate(current_time=6.0, position=self._pos())
        assert status.action == FailsafeAction.RTL

    def test_rtl_when_no_comm_ever(self):
        m = self._monitor(timeout=5.0)
        # Current time 10.0, no heartbeat ever received
        status = m.evaluate(current_time=10.0, position=self._pos())
        assert status.action == FailsafeAction.RTL

    def test_exactly_at_timeout_triggers(self):
        m = self._monitor(timeout=5.0)
        m.update_comm(timestamp=0.0)
        status = m.evaluate(current_time=5.01, position=self._pos())
        assert status.action == FailsafeAction.RTL

    def test_status_contains_drone_id(self):
        m = self._monitor()
        m.update_comm(0.0)
        status = m.evaluate(current_time=0.1, position=self._pos())
        assert status.drone_id == 1

    def test_reset_clears_active_action(self):
        m = self._monitor(timeout=5.0)
        m.update_comm(0.0)
        m.evaluate(current_time=10.0, position=self._pos())
        m.reset()
        assert m.active_action == FailsafeAction.NONE

    def test_disable_comm_failsafe(self):
        cfg = FailsafeConfig(comm_timeout_s=5.0, enable_comm_failsafe=False)
        m = FailsafeMonitor(drone_id=1, config=cfg)
        status = m.evaluate(current_time=100.0, position=self._pos())
        assert status.action == FailsafeAction.NONE


# ---------------------------------------------------------------------------
# FailsafeMonitor — geofence
# ---------------------------------------------------------------------------


class TestFailsafeMonitorGeofence:
    def _monitor(self, zone=None):
        zones = [zone] if zone else [
            GeofenceZone(center_xy=(0.0, 0.0), radius_m=100.0, keep_in=True)
        ]
        cfg = FailsafeConfig(geofence_zones=zones, enable_comm_failsafe=False)
        m = FailsafeMonitor(drone_id=2, config=cfg)
        m.update_comm(0.0)
        return m

    def test_geofence_rtl_when_outside_keep_in_zone(self):
        m = self._monitor()
        status = m.evaluate(current_time=1.0, position=np.array([150.0, 0.0, 50.0]))
        assert status.action == FailsafeAction.GEOFENCE_RTL

    def test_no_action_when_inside_keep_in_zone(self):
        m = self._monitor()
        status = m.evaluate(current_time=1.0, position=np.array([50.0, 0.0, 50.0]))
        assert status.action == FailsafeAction.NONE

    def test_geofence_rtl_for_keep_out_zone_entry(self):
        zone = GeofenceZone(center_xy=(500.0, 500.0), radius_m=50.0, keep_in=False)
        m = self._monitor(zone=zone)
        status = m.evaluate(current_time=1.0, position=np.array([500.0, 500.0, 50.0]))
        assert status.action == FailsafeAction.GEOFENCE_RTL

    def test_disable_geofence(self):
        cfg = FailsafeConfig(
            geofence_zones=[GeofenceZone(center_xy=(0.0, 0.0), radius_m=100.0)],
            enable_geofence=False,
            enable_comm_failsafe=False,
        )
        m = FailsafeMonitor(drone_id=3, config=cfg)
        m.update_comm(0.0)
        status = m.evaluate(current_time=1.0, position=np.array([200.0, 0.0, 50.0]))
        assert status.action == FailsafeAction.NONE

    def test_reason_mentions_zone_type(self):
        m = self._monitor()
        status = m.evaluate(current_time=1.0, position=np.array([200.0, 0.0, 50.0]))
        assert "keep-in" in status.reason


# ---------------------------------------------------------------------------
# FailsafeMonitor — battery
# ---------------------------------------------------------------------------


class TestFailsafeMonitorBattery:
    def _monitor(self, low_pct=15.0):
        cfg = FailsafeConfig(
            low_battery_pct=low_pct,
            enable_comm_failsafe=False,
            geofence_zones=[],
        )
        m = FailsafeMonitor(drone_id=4, config=cfg)
        m.update_comm(0.0)
        return m

    def test_land_when_battery_low(self):
        m = self._monitor()
        status = m.evaluate(current_time=1.0, position=np.array([0.0, 0.0, 50.0]), battery_pct=10.0)
        assert status.action == FailsafeAction.LAND

    def test_no_action_when_battery_ok(self):
        m = self._monitor()
        status = m.evaluate(current_time=1.0, position=np.array([0.0, 0.0, 50.0]), battery_pct=50.0)
        assert status.action == FailsafeAction.NONE

    def test_land_at_exact_threshold(self):
        m = self._monitor(low_pct=15.0)
        status = m.evaluate(current_time=1.0, position=np.array([0.0, 0.0, 50.0]), battery_pct=15.0)
        assert status.action == FailsafeAction.LAND

    def test_battery_takes_priority_over_geofence(self):
        zone = GeofenceZone(center_xy=(0.0, 0.0), radius_m=100.0, keep_in=True)
        cfg = FailsafeConfig(
            low_battery_pct=15.0,
            geofence_zones=[zone],
            enable_comm_failsafe=False,
        )
        m = FailsafeMonitor(drone_id=5, config=cfg)
        m.update_comm(0.0)
        # Both battery low and outside geofence
        status = m.evaluate(current_time=1.0, position=np.array([200.0, 0.0, 50.0]), battery_pct=10.0)
        assert status.action == FailsafeAction.LAND

    def test_disable_battery_failsafe(self):
        cfg = FailsafeConfig(enable_battery=False, enable_comm_failsafe=False)
        m = FailsafeMonitor(drone_id=6, config=cfg)
        m.update_comm(0.0)
        status = m.evaluate(current_time=1.0, position=np.array([0.0, 0.0, 50.0]), battery_pct=0.0)
        assert status.action == FailsafeAction.NONE


# ---------------------------------------------------------------------------
# SwarmFailsafe
# ---------------------------------------------------------------------------


class TestSwarmFailsafe:
    def _swarm(self):
        cfg = FailsafeConfig(
            comm_timeout_s=5.0,
            geofence_zones=[GeofenceZone(center_xy=(0.0, 0.0), radius_m=200.0)],
        )
        return SwarmFailsafe(config=cfg)

    def _states(self, positions: dict[int, list]) -> dict[int, tuple[np.ndarray, float]]:
        return {
            drone_id: (np.array(pos, dtype=float), 80.0)
            for drone_id, pos in positions.items()
        }

    def test_creates_monitor_on_demand(self):
        sf = self._swarm()
        monitor = sf.get_monitor(42)
        assert monitor.drone_id == 42

    def test_evaluate_all_returns_sorted_by_drone_id(self):
        sf = self._swarm()
        for drone_id in [3, 1, 2]:
            sf.update_comm(drone_id, 0.0)
        states = self._states({3: [0, 0, 50], 1: [0, 0, 50], 2: [0, 0, 50]})
        results = sf.evaluate_all(current_time=1.0, drone_states=states)
        assert [s.drone_id for s in results] == [1, 2, 3]

    def test_active_alerts_filters_none_actions(self):
        sf = self._swarm()
        sf.update_comm(1, 0.0)
        sf.update_comm(2, 0.0)
        # Drone 1 inside, drone 2 outside geofence
        states = self._states({1: [0, 0, 50], 2: [300, 0, 50]})
        alerts = sf.active_alerts(current_time=1.0, drone_states=states)
        drone_ids = [a.drone_id for a in alerts]
        assert 2 in drone_ids
        assert 1 not in drone_ids

    def test_update_comm_prevents_rtl(self):
        sf = self._swarm()
        sf.update_comm(1, 0.0)
        sf.update_comm(1, 3.0)  # Fresh heartbeat at t=3
        states = self._states({1: [0, 0, 50]})
        alerts = sf.active_alerts(current_time=5.0, drone_states=states)
        # 5.0 - 3.0 = 2s < 5s timeout → no RTL
        assert not any(a.drone_id == 1 and a.action == FailsafeAction.RTL for a in alerts)

    def test_reset_all_clears_monitors(self):
        sf = self._swarm()
        sf.update_comm(1, 0.0)
        states = self._states({1: [0, 0, 50]})
        sf.evaluate_all(current_time=10.0, drone_states=states)
        sf.reset()
        assert sf.get_monitor(1).active_action == FailsafeAction.NONE

    def test_reset_single_drone(self):
        sf = self._swarm()
        sf.update_comm(1, 0.0)
        sf.update_comm(2, 0.0)
        states = self._states({1: [300, 0, 50], 2: [300, 0, 50]})
        sf.evaluate_all(current_time=10.0, drone_states=states)
        sf.reset(drone_id=1)
        assert sf.get_monitor(1).active_action == FailsafeAction.NONE
        # Drone 2 should still have active action from geofence
        assert sf.get_monitor(2).active_action != FailsafeAction.NONE

    def test_empty_drone_states_returns_empty_list(self):
        sf = self._swarm()
        results = sf.evaluate_all(current_time=0.0, drone_states={})
        assert results == []
