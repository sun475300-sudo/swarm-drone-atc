"""SimulationAnalyticsHook 테스트"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.analytics.simulation_hook import SimulationAnalyticsHook

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_drone(speed: float = 5.0, battery: float = 80.0) -> MagicMock:
    d = MagicMock()
    d.velocity = np.array([speed, 0.0, 0.0])
    d.battery_pct = battery
    return d


def _make_mock_controller() -> MagicMock:
    c = MagicMock()
    c.get_active_advisories = MagicMock(return_value=[])
    c.get_pending_requests = MagicMock(return_value=[])
    return c


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def hook() -> SimulationAnalyticsHook:
    return SimulationAnalyticsHook()


@pytest.fixture
def hook_with_sim() -> SimulationAnalyticsHook:
    sim = MagicMock()
    sim.completed_missions = 10
    return SimulationAnalyticsHook(simulator=sim)


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------

class TestInit:
    def test_starts_empty(self, hook):
        assert hook.events == []
        assert hook.metrics_history == []
        assert hook.conflict_events == []
        assert hook.collision_events == []

    def test_simulator_stored(self):
        sim = MagicMock()
        h = SimulationAnalyticsHook(simulator=sim)
        assert h.simulator is sim

    def test_no_simulator_defaults_none(self, hook):
        assert hook.simulator is None


# ---------------------------------------------------------------------------
# on_tick
# ---------------------------------------------------------------------------

class TestOnTick:
    def test_records_tick_event(self, hook):
        drones = [_make_mock_drone()]
        controller = _make_mock_controller()
        with patch.object(hook.collector, "collect_drone_metrics", return_value={}), \
             patch.object(hook.collector, "collect_airspace_metrics", return_value={}):
            hook.on_tick(1.0, drones, controller)
        assert len(hook.events) == 1
        assert hook.events[0]["event_type"] == "TICK"
        assert hook.events[0]["sim_time"] == 1.0

    def test_records_metrics_history(self, hook):
        drones = []
        controller = _make_mock_controller()
        with patch.object(hook.collector, "collect_drone_metrics", return_value={"speed": 5.0}), \
             patch.object(hook.collector, "collect_airspace_metrics", return_value={}):
            hook.on_tick(2.0, drones, controller)
        assert len(hook.metrics_history) == 1
        assert hook.metrics_history[0]["sim_time"] == 2.0

    def test_sets_start_time_on_first_tick(self, hook):
        drones = []
        controller = _make_mock_controller()
        with patch.object(hook.collector, "collect_drone_metrics", return_value={}), \
             patch.object(hook.collector, "collect_airspace_metrics", return_value={}):
            hook.on_tick(3.0, drones, controller)
        assert hook._start_time == 3.0

    def test_start_time_not_overwritten(self, hook):
        drones = []
        controller = _make_mock_controller()
        with patch.object(hook.collector, "collect_drone_metrics", return_value={}), \
             patch.object(hook.collector, "collect_airspace_metrics", return_value={}):
            hook.on_tick(1.0, drones, controller)
            hook.on_tick(2.0, drones, controller)
        assert hook._start_time == 1.0

    def test_handles_drone_metrics_exception(self, hook):
        drones = []
        controller = _make_mock_controller()
        with patch.object(hook.collector, "collect_drone_metrics", side_effect=RuntimeError("oops")), \
             patch.object(hook.collector, "collect_airspace_metrics", return_value={}):
            hook.on_tick(5.0, drones, controller)
        assert len(hook.events) == 1

    def test_handles_airspace_metrics_exception(self, hook):
        drones = []
        controller = _make_mock_controller()
        with patch.object(hook.collector, "collect_drone_metrics", return_value={}), \
             patch.object(hook.collector, "collect_airspace_metrics", side_effect=RuntimeError("fail")):
            hook.on_tick(6.0, drones, controller)
        assert len(hook.events) == 1
        assert hook.events[0]["sim_time"] == 6.0

    def test_drone_count_in_event(self, hook):
        drones = [_make_mock_drone(), _make_mock_drone()]
        controller = _make_mock_controller()
        with patch.object(hook.collector, "collect_drone_metrics", return_value={}), \
             patch.object(hook.collector, "collect_airspace_metrics", return_value={}):
            hook.on_tick(0.0, drones, controller)
        assert hook.events[0]["drone_count"] == 2


# ---------------------------------------------------------------------------
# on_conflict
# ---------------------------------------------------------------------------

class TestOnConflict:
    def test_records_conflict_event(self, hook):
        data = {
            "sim_time": 10.0,
            "drone_a": "D1",
            "drone_b": "D2",
            "separation_distance_m": 30.0,
            "time_to_closest_approach_s": 5.0,
        }
        hook.on_conflict(data)
        assert len(hook.conflict_events) == 1
        assert len(hook.events) == 1
        assert hook.events[0]["event_type"] == "CONFLICT"

    def test_conflict_fields(self, hook):
        data = {"sim_time": 1.0, "drone_a": "A", "drone_b": "B",
                "separation_distance_m": 20.0, "time_to_closest_approach_s": 2.0}
        hook.on_conflict(data)
        ev = hook.events[0]
        assert ev["drone_a"] == "A"
        assert ev["drone_b"] == "B"
        assert ev["separation_distance_m"] == 20.0

    def test_multiple_conflicts(self, hook):
        for i in range(3):
            hook.on_conflict({"sim_time": float(i), "drone_a": f"D{i}", "drone_b": "D0",
                              "separation_distance_m": 25.0})
        assert len(hook.conflict_events) == 3


# ---------------------------------------------------------------------------
# on_collision
# ---------------------------------------------------------------------------

class TestOnCollision:
    def test_records_collision_event(self, hook):
        data = {
            "sim_time": 15.0,
            "drone_a": "D1",
            "drone_b": "D2",
            "position": np.array([10.0, 20.0, 30.0]),
            "relative_velocity_ms": 8.5,
        }
        hook.on_collision(data)
        assert len(hook.collision_events) == 1
        assert hook.events[0]["event_type"] == "COLLISION"

    def test_position_converted_to_list(self, hook):
        data = {"sim_time": 1.0, "drone_a": "A", "drone_b": "B",
                "position": np.array([1.0, 2.0, 3.0])}
        hook.on_collision(data)
        assert isinstance(hook.events[0]["position"], list)

    def test_position_none_when_not_ndarray(self, hook):
        data = {"sim_time": 1.0, "drone_a": "A", "drone_b": "B",
                "position": None}
        hook.on_collision(data)
        assert hook.events[0]["position"] is None

    def test_collision_without_position_key(self, hook):
        data = {"sim_time": 1.0, "drone_a": "A", "drone_b": "B"}
        hook.on_collision(data)
        assert hook.events[0]["position"] is None


# ---------------------------------------------------------------------------
# on_simulation_end
# ---------------------------------------------------------------------------

class TestOnSimulationEnd:
    def test_returns_dict_with_required_keys(self, hook_with_sim):
        result = hook_with_sim.on_simulation_end(60.0)
        required = ["duration_s", "total_events", "conflicts_detected",
                    "collisions_occurred", "collision_resolution_rate",
                    "throughput_missions_per_min"]
        for key in required:
            assert key in result

    def test_duration_set_correctly(self, hook):
        result = hook.on_simulation_end(120.0)
        assert result["duration_s"] == 120.0

    def test_no_conflicts_full_resolution(self, hook):
        result = hook.on_simulation_end(10.0)
        assert result["collision_resolution_rate"] == pytest.approx(1.0)

    def test_conflict_and_collision_counted(self, hook):
        hook.on_conflict({"sim_time": 1.0, "drone_a": "A", "drone_b": "B",
                          "separation_distance_m": 20.0})
        hook.on_collision({"sim_time": 2.0, "drone_a": "A", "drone_b": "B"})
        result = hook.on_simulation_end(30.0)
        assert result["conflicts_detected"] == 1
        assert result["collisions_occurred"] == 1

    def test_sets_end_time(self, hook):
        hook.on_simulation_end(45.0)
        assert hook._end_time == 45.0

    def test_simulator_completed_missions(self, hook_with_sim):
        result = hook_with_sim.on_simulation_end(60.0)
        assert result["throughput_missions_per_min"] == pytest.approx(10.0)

    def test_safety_metrics_present(self, hook):
        result = hook.on_simulation_end(10.0)
        assert "safety_metrics" in result


# ---------------------------------------------------------------------------
# get_live_dashboard_data
# ---------------------------------------------------------------------------

class TestGetLiveDashboardData:
    def test_empty_returns_no_data_message(self, hook):
        data = hook.get_live_dashboard_data()
        assert data["total_events"] == 0
        assert "message" in data

    def test_after_tick_returns_data(self, hook):
        drones = []
        controller = _make_mock_controller()
        with patch.object(hook.collector, "collect_drone_metrics", return_value={}), \
             patch.object(hook.collector, "collect_airspace_metrics", return_value={}):
            hook.on_tick(5.0, drones, controller)
        data = hook.get_live_dashboard_data()
        assert data["current_time"] == 5.0

    def test_recent_events_capped_at_10(self, hook):
        drones = []
        controller = _make_mock_controller()
        with patch.object(hook.collector, "collect_drone_metrics", return_value={}), \
             patch.object(hook.collector, "collect_airspace_metrics", return_value={}):
            for t in range(15):
                hook.on_tick(float(t), drones, controller)
        data = hook.get_live_dashboard_data()
        assert len(data["recent_events"]) == 10

    def test_conflicts_collisions_counts(self, hook):
        drones = []
        controller = _make_mock_controller()
        with patch.object(hook.collector, "collect_drone_metrics", return_value={}), \
             patch.object(hook.collector, "collect_airspace_metrics", return_value={}):
            hook.on_tick(1.0, drones, controller)
        hook.on_conflict({"sim_time": 2.0, "drone_a": "A", "drone_b": "B"})
        data = hook.get_live_dashboard_data()
        assert data["conflicts_count"] == 1
        assert data["collisions_count"] == 0

    def test_resolution_rate_present(self, hook):
        drones = []
        controller = _make_mock_controller()
        with patch.object(hook.collector, "collect_drone_metrics", return_value={}), \
             patch.object(hook.collector, "collect_airspace_metrics", return_value={}):
            hook.on_tick(1.0, drones, controller)
        data = hook.get_live_dashboard_data()
        assert "collision_resolution_rate" in data


# ---------------------------------------------------------------------------
# export_to_json
# ---------------------------------------------------------------------------

class TestExportToJson:
    def test_creates_json_file(self, hook, tmp_path):
        output = str(tmp_path / "analytics.json")
        hook.export_to_json(output)
        with open(output, encoding="utf-8") as f:
            data = json.load(f)
        assert "events" in data
        assert "summary" in data

    def test_duration_in_export(self, hook, tmp_path):
        hook._start_time = 5.0
        hook._end_time = 35.0
        output = str(tmp_path / "out.json")
        hook.export_to_json(output)
        with open(output, encoding="utf-8") as f:
            data = json.load(f)
        assert data["simulation_info"]["duration_s"] == pytest.approx(30.0)  # 35.0 - 5.0

    def test_bad_path_does_not_raise(self, hook):
        hook.export_to_json("/nonexistent_dir/bad.json")


# ---------------------------------------------------------------------------
# get_conflict_log / get_collision_log
# ---------------------------------------------------------------------------

class TestLogs:
    def test_conflict_log_returns_copy(self, hook):
        hook.on_conflict({"sim_time": 1.0, "drone_a": "A", "drone_b": "B"})
        log = hook.get_conflict_log()
        log.clear()
        assert len(hook.conflict_events) == 1

    def test_collision_log_returns_copy(self, hook):
        hook.on_collision({"sim_time": 1.0, "drone_a": "A", "drone_b": "B"})
        log = hook.get_collision_log()
        log.clear()
        assert len(hook.collision_events) == 1


# ---------------------------------------------------------------------------
# get_metrics_summary
# ---------------------------------------------------------------------------

class TestGetMetricsSummary:
    def test_empty_returns_empty_dict(self, hook):
        assert hook.get_metrics_summary() == {}

    def test_filters_by_time_range(self, hook):
        hook.metrics_history = [
            {"sim_time": 1.0, "drone_metrics": {"speed_mean_ms": 5.0, "battery_mean_pct": 90.0}},
            {"sim_time": 10.0, "drone_metrics": {"speed_mean_ms": 7.0, "battery_mean_pct": 70.0}},
        ]
        summary = hook.get_metrics_summary(start_time=5.0, end_time=15.0)
        assert summary["samples"] == 1
        assert summary["avg_drone_speed_ms"] == pytest.approx(7.0)

    def test_no_data_in_range_returns_empty(self, hook):
        hook.metrics_history = [
            {"sim_time": 1.0, "drone_metrics": {}, "airspace_metrics": {}},
        ]
        assert hook.get_metrics_summary(start_time=50.0, end_time=100.0) == {}

    def test_full_range_includes_all(self, hook):
        hook.metrics_history = [
            {"sim_time": 1.0, "drone_metrics": {"speed_mean_ms": 4.0, "battery_mean_pct": 80.0}},
            {"sim_time": 2.0, "drone_metrics": {"speed_mean_ms": 6.0, "battery_mean_pct": 60.0}},
        ]
        summary = hook.get_metrics_summary()
        assert summary["samples"] == 2
        assert summary["avg_drone_speed_ms"] == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# _get_min_separation
# ---------------------------------------------------------------------------

class TestGetMinSeparation:
    def test_no_conflicts_returns_inf(self, hook):
        assert hook._get_min_separation() == float("inf")

    def test_returns_minimum(self, hook):
        hook.conflict_events = [
            {"separation_distance_m": 30.0},
            {"separation_distance_m": 15.0},
            {"separation_distance_m": 50.0},
        ]
        assert hook._get_min_separation() == pytest.approx(15.0)

    def test_missing_separation_key_uses_inf(self, hook):
        hook.conflict_events = [{"no_sep": True}]
        assert hook._get_min_separation() == float("inf")


# ---------------------------------------------------------------------------
# reset
# ---------------------------------------------------------------------------

class TestReset:
    def test_clears_all_data(self, hook):
        drones = []
        controller = _make_mock_controller()
        with patch.object(hook.collector, "collect_drone_metrics", return_value={}), \
             patch.object(hook.collector, "collect_airspace_metrics", return_value={}):
            hook.on_tick(1.0, drones, controller)
        hook.on_conflict({"sim_time": 1.0, "drone_a": "A", "drone_b": "B"})
        hook.on_collision({"sim_time": 1.5, "drone_a": "A", "drone_b": "B"})
        hook.reset()
        assert hook.events == []
        assert hook.metrics_history == []
        assert hook.conflict_events == []
        assert hook.collision_events == []
        assert hook._start_time is None
        assert hook._end_time is None

    def test_counters_reset(self, hook):
        hook._last_collision_count = 5
        hook._last_conflict_count = 3
        hook.reset()
        assert hook._last_collision_count == 0
        assert hook._last_conflict_count == 0
