"""
SimulationAnalytics / SimulationResult 단위 테스트
"""
from __future__ import annotations

import numpy as np
import pytest

from simulation.analytics import SimulationAnalytics, SimulationResult


@pytest.fixture
def analytics():
    cfg = {"logging": {"save_trajectory": True}}
    return SimulationAnalytics(cfg)


class TestSimulationResult:
    def test_to_dict_excludes_config_params(self):
        r = SimulationResult(seed=1, scenario="test", config_params={"a": 1})
        d = r.to_dict()
        assert "config_params" not in d
        assert d["seed"] == 1

    def test_check_acceptance_no_collision(self):
        r = SimulationResult(collision_count=0, conflict_resolution_rate_pct=99.9,
                             route_efficiency_mean=1.05)
        checks = r.check_acceptance({
            "conflict_resolution_rate_pct": 99.5,
            "route_efficiency_max": 1.15,
        })
        assert checks["no_collision"] is True
        assert checks["conflict_res_rate"] is True
        assert checks["route_efficiency"] is True

    def test_check_acceptance_collision_fail(self):
        r = SimulationResult(collision_count=1)
        checks = r.check_acceptance({})
        assert checks["no_collision"] is False

    def test_check_acceptance_efficiency_fail(self):
        r = SimulationResult(collision_count=0, route_efficiency_mean=1.20)
        checks = r.check_acceptance({"route_efficiency_max": 1.15})
        assert checks["route_efficiency"] is False


class TestSimulationAnalytics:
    def test_record_collision(self, analytics):
        analytics.record_event("COLLISION", 5.0, drone_a="A", drone_b="B")
        result = analytics.finalize(seed=0, scenario="test", duration_s=10.0, n_drones=2)
        assert result.collision_count == 1

    def test_record_near_miss(self, analytics):
        analytics.record_event("NEAR_MISS", 3.0)
        result = analytics.finalize()
        assert result.near_miss_count == 1

    def test_record_conflict_and_advisory(self, analytics):
        analytics.record_event("CONFLICT", 1.0)
        analytics.record_event("ADVISORY_ISSUED", 1.0)
        result = analytics.finalize()
        assert result.conflicts_total == 1
        assert result.advisories_issued == 1

    def test_clearance_counts(self, analytics):
        analytics.record_event("CLEARANCE_APPROVED", 1.0)
        analytics.record_event("CLEARANCE_APPROVED", 2.0)
        analytics.record_event("CLEARANCE_DENIED", 3.0)
        result = analytics.finalize()
        assert result.clearances_approved == 2
        assert result.clearances_denied == 1

    def test_advisory_latency_percentiles(self, analytics):
        for lat in [0.1, 0.2, 0.3, 0.5, 1.0, 2.0, 5.0, 8.0, 9.0, 10.0]:
            analytics.record_advisory_latency(lat)
        result = analytics.finalize()
        assert result.advisory_latency_p50 > 0.0
        assert result.advisory_latency_p99 >= result.advisory_latency_p50

    def test_route_efficiency_calculation(self, analytics):
        analytics.record_planned_distance("D1", 1000.0)
        analytics._dist_actual["D1"] = 1100.0
        analytics._flight_time["D1"] = 120.0
        result = analytics.finalize(n_drones=1)
        assert result.route_efficiency_mean == pytest.approx(1.1, rel=1e-3)

    def test_conflict_resolution_rate_no_collision(self, analytics):
        analytics.record_event("CONFLICT", 1.0)
        analytics.record_event("CONFLICT", 2.0)
        # 충돌 없음
        result = analytics.finalize()
        assert result.conflict_resolution_rate_pct == pytest.approx(100.0)

    def test_conflict_resolution_rate_with_collision(self, analytics):
        analytics.record_event("CONFLICT", 1.0)
        analytics.record_event("CONFLICT", 2.0)
        analytics.record_event("COLLISION", 2.5)
        result = analytics.finalize()
        # 공식: 1 - collisions/(conflicts + collisions) = 1 - 1/3 ≈ 66.7%
        assert result.conflict_resolution_rate_pct == pytest.approx(66.667, abs=0.1)

    def test_max_events_cap(self, analytics):
        for i in range(SimulationAnalytics.MAX_EVENTS + 100):
            analytics.record_event("NEAR_MISS", float(i))
        assert len(analytics.events) == SimulationAnalytics.MAX_EVENTS

    def test_snapshot_recording(self, analytics):
        from src.airspace_control.agents.drone_state import DroneState, FlightPhase
        d = DroneState("D1", np.array([0.0, 0.0, 60.0]), np.zeros(3))
        d.flight_phase = FlightPhase.ENROUTE
        analytics.record_snapshot({"D1": d}, t=1.0)
        assert len(analytics.snapshots) == 1
        assert analytics.snapshots[0]["id"] == "D1"
