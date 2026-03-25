"""SimulationMetrics 테스트"""
import numpy as np
import pytest
from simulation.metrics import SimulationMetrics, check_sla


class TestSimulationMetrics:
    def test_default_values(self):
        m = SimulationMetrics()
        assert m.collision_count == 0
        assert m.near_miss_count == 0
        assert m.conflict_resolution_rate == 1.0

    def test_record_collision(self):
        m = SimulationMetrics()
        m.record_event(1.0, "collision", drone_a="D1", drone_b="D2")
        assert m.collision_count == 1

    def test_record_near_miss(self):
        m = SimulationMetrics()
        m.record_event(1.0, "near_miss", drone_a="D1", drone_b="D2")
        assert m.near_miss_count == 1

    def test_conflict_resolution_rate(self):
        m = SimulationMetrics()
        m.record_event(1.0, "conflict_detected")
        m.record_event(1.0, "conflict_detected")
        m.record_event(2.0, "conflict_resolved")
        assert m.conflict_resolution_rate == pytest.approx(0.5)

    def test_route_efficiency(self):
        m = SimulationMetrics()
        m.total_planned_distance_m = 1000.0
        m.total_actual_distance_m = 1200.0
        assert m.route_efficiency == pytest.approx(1.2)

    def test_route_efficiency_no_plan(self):
        m = SimulationMetrics()
        assert m.route_efficiency == 1.0

    def test_emergency_response_percentiles(self):
        m = SimulationMetrics()
        m.emergency_response_times_s = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert m.emergency_response_p50_s == pytest.approx(3.0)
        assert m.emergency_response_p99_s > 4.0

    def test_summary_dict(self):
        m = SimulationMetrics()
        d = m.summary_dict()
        assert "collision_count" in d
        assert "route_efficiency" in d

    def test_summary_table(self):
        m = SimulationMetrics()
        table = m.summary_table()
        assert "collision_count" in table
        assert "│" in table

    def test_record_trajectory(self):
        m = SimulationMetrics()
        m.record_trajectory(1.0, "D1", np.zeros(3), np.ones(3), 90.0, "ENROUTE")
        assert len(m.trajectory_log) == 1
        assert m.trajectory_log[0]["drone_id"] == "D1"


class TestCheckSla:
    def test_pass_all(self):
        m = SimulationMetrics()
        m.conflict_detected = 10
        m.conflict_resolved = 10
        thresholds = {
            "collision_rate_per_1000h": 0,
            "conflict_resolution_rate_pct": 99.0,
            "route_efficiency_max": 1.5,
        }
        results = check_sla(m, thresholds)
        assert results["zero_collision"] is True
        assert results["conflict_resolution"] is True
        assert results["route_efficiency"] is True

    def test_fail_collision(self):
        m = SimulationMetrics()
        m.collision_count = 1
        results = check_sla(m, {"collision_rate_per_1000h": 0})
        assert results["zero_collision"] is False
