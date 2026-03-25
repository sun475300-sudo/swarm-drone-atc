"""
SimulationMetrics 및 check_sla 포괄적 단위 테스트
모든 KPI 프로퍼티 및 SLA 판정 분기 커버
"""
from __future__ import annotations

import numpy as np
import pytest

from simulation.metrics import SimulationMetrics, check_sla


class TestSimulationMetricsExtended:
    def test_conflict_resolution_no_conflict(self):
        m = SimulationMetrics()
        assert m.conflict_resolution_rate == 1.0

    def test_conflict_resolution_partial(self):
        m = SimulationMetrics(conflict_detected=10, conflict_resolved=7)
        assert m.conflict_resolution_rate == pytest.approx(0.7)

    def test_conflict_resolution_all_resolved(self):
        m = SimulationMetrics(conflict_detected=10, conflict_resolved=10)
        assert m.conflict_resolution_rate == pytest.approx(1.0)

    def test_route_efficiency_no_plan(self):
        m = SimulationMetrics(total_planned_distance_m=0.0, total_actual_distance_m=0.0)
        assert m.route_efficiency == 1.0

    def test_route_efficiency_overshoot(self):
        """실제 거리가 계획보다 긴 경우"""
        m = SimulationMetrics(total_planned_distance_m=100.0, total_actual_distance_m=120.0)
        assert m.route_efficiency == pytest.approx(1.2)

    def test_emergency_response_p50_empty(self):
        m = SimulationMetrics()
        assert m.emergency_response_p50_s == 0.0

    def test_emergency_response_p99_empty(self):
        m = SimulationMetrics()
        assert m.emergency_response_p99_s == 0.0

    def test_emergency_response_p50(self):
        m = SimulationMetrics(emergency_response_times_s=[1.0, 2.0, 3.0, 4.0, 5.0])
        assert m.emergency_response_p50_s == pytest.approx(3.0)

    def test_emergency_response_p99(self):
        m = SimulationMetrics(emergency_response_times_s=list(range(1, 101)))
        assert m.emergency_response_p99_s > 95.0

    def test_record_event_collision(self):
        m = SimulationMetrics()
        m.record_event(1.0, "collision")
        assert m.collision_count == 1
        assert len(m.event_log) == 1

    def test_record_event_near_miss(self):
        m = SimulationMetrics()
        m.record_event(1.0, "near_miss")
        assert m.near_miss_count == 1

    def test_record_event_conflict_detected(self):
        m = SimulationMetrics()
        m.record_event(1.0, "conflict_detected")
        assert m.conflict_detected == 1

    def test_record_event_conflict_resolved(self):
        m = SimulationMetrics()
        m.record_event(1.0, "conflict_resolved")
        assert m.conflict_resolved == 1

    def test_record_event_unknown_type(self):
        """알 수 없는 이벤트 유형도 로그에 기록"""
        m = SimulationMetrics()
        m.record_event(1.0, "custom_event", detail="test")
        assert len(m.event_log) == 1
        assert m.event_log[0]["type"] == "custom_event"

    def test_record_trajectory(self):
        m = SimulationMetrics()
        m.record_trajectory(1.0, "D0", np.array([10, 20, 30]),
                           np.array([1, 2, 3]), 95.0, "ENROUTE")
        assert len(m.trajectory_log) == 1
        assert m.trajectory_log[0]["drone_id"] == "D0"
        assert m.trajectory_log[0]["x"] == 10.0

    def test_summary_dict_keys(self):
        m = SimulationMetrics()
        sd = m.summary_dict()
        expected_keys = {"collision_count", "near_miss_count", "conflict_resolution_rate",
                         "route_efficiency", "routes_completed", "battery_depleted",
                         "avg_battery_remaining", "emergency_p50_s", "emergency_p99_s"}
        assert expected_keys == set(sd.keys())

    def test_summary_table_format(self):
        m = SimulationMetrics()
        table = m.summary_table()
        assert "┌" in table
        assert "└" in table
        assert "collision_count" in table


class TestCheckSlaExtended:
    def test_pass_all(self):
        m = SimulationMetrics(collision_count=0, conflict_detected=10,
                              conflict_resolved=10, total_planned_distance_m=100,
                              total_actual_distance_m=105)
        thresholds = {
            "collision_rate_per_1000h": 0,
            "conflict_resolution_rate_pct": 95.0,
            "route_efficiency_max": 1.2,
            "emergency_response_p50_s": 1.0,
        }
        results = check_sla(m, thresholds)
        assert all(results.values())

    def test_fail_collision(self):
        m = SimulationMetrics(collision_count=1)
        results = check_sla(m, {"collision_rate_per_1000h": 0})
        assert results["zero_collision"] is False

    def test_fail_conflict_resolution(self):
        m = SimulationMetrics(conflict_detected=10, conflict_resolved=5)
        results = check_sla(m, {"conflict_resolution_rate_pct": 80.0})
        assert results["conflict_resolution"] is False

    def test_fail_route_efficiency(self):
        m = SimulationMetrics(total_planned_distance_m=100, total_actual_distance_m=200)
        results = check_sla(m, {"route_efficiency_max": 1.5})
        assert results["route_efficiency"] is False

    def test_pass_emergency_response(self):
        m = SimulationMetrics(emergency_response_times_s=[0.5, 0.6, 0.7])
        results = check_sla(m, {"emergency_response_p50_s": 1.0})
        assert results["emergency_p50"] is True

    def test_empty_thresholds(self):
        m = SimulationMetrics()
        results = check_sla(m, {})
        assert results == {}
