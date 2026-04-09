"""
시나리오 실행기 단위 테스트
"""
from __future__ import annotations

import pytest

from simulation.scenario_runner import (
    list_scenarios,
    _translate_scenario,
    run_scenario,
)


class TestListScenarios:
    def test_returns_list(self):
        scenarios = list_scenarios()
        assert isinstance(scenarios, list)
        assert len(scenarios) >= 7

    def test_includes_known_scenarios(self):
        scenarios = list_scenarios()
        for name in ["high_density", "weather_disturbance", "comms_loss",
                     "emergency_failure", "adversarial_intrusion"]:
            assert name in scenarios, f"{name} not found"


class TestTranslateScenario:
    def test_drone_count_from_base_traffic(self):
        raw = {"base_traffic": {"drone_count": 50}}
        cfg = _translate_scenario(raw)
        assert cfg["drones"]["default_count"] == 50

    def test_drone_count_direct(self):
        raw = {"drone_count": 100}
        cfg = _translate_scenario(raw)
        assert cfg["drones"]["default_count"] == 100

    def test_drone_count_base_drone_count(self):
        raw = {"base_drone_count": 80}
        cfg = _translate_scenario(raw)
        assert cfg["drones"]["default_count"] == 80

    def test_duration_seconds(self):
        raw = {"simulation_duration_s": 300}
        cfg = _translate_scenario(raw)
        assert cfg["_duration_s"] == 300.0

    def test_duration_minutes(self):
        raw = {"simulation_duration_min": 10}
        cfg = _translate_scenario(raw)
        assert cfg["_duration_s"] == 600.0

    def test_weather_passthrough(self):
        raw = {"weather": {"wind_models": [{"type": "constant"}]}}
        cfg = _translate_scenario(raw)
        assert "weather" in cfg
        assert cfg["weather"]["wind_models"][0]["type"] == "constant"

    def test_intrusion(self):
        raw = {"intrusion": {"count": 3}}
        cfg = _translate_scenario(raw)
        assert cfg["scenario"]["drones"]["n_rogue"] == 3

    def test_comms_loss(self):
        raw = {"comms_loss": {"trigger_time_range": [30, 300]}}
        cfg = _translate_scenario(raw)
        assert cfg["failure_injection"]["comms_loss_rate"] == 0.05

    def test_failure_injection(self):
        raw = {"failure_injection": {"failure_rate_pct": 5.0}}
        cfg = _translate_scenario(raw)
        assert cfg["failure_injection"]["drone_failure_rate"] == pytest.approx(0.05)

    def test_lost_link_protocol(self):
        raw = {"lost_link_protocol": {"hold_s": 30, "climb_alt_m": 80}}
        cfg = _translate_scenario(raw)
        assert cfg["lost_link_protocol"]["hold_s"] == 30

    def test_empty_returns_empty(self):
        cfg = _translate_scenario({})
        assert cfg == {}


class TestRunScenario:
    def test_run_high_density_single(self):
        results = run_scenario("high_density", n_runs=1, seed=42, verbose=False)
        assert len(results) == 1
        assert "collision_count" in results[0]
        assert results[0]["scenario"] == "high_density"

    def test_run_nonexistent_raises(self):
        with pytest.raises(FileNotFoundError):
            run_scenario("nonexistent_scenario_xyz", n_runs=1, verbose=False)

    def test_run_multiple(self):
        results = run_scenario("route_conflict", n_runs=2, seed=42, verbose=False)
        assert len(results) == 2
        # 다른 시드로 실행되므로 결과가 다를 수 있음
        assert all("collision_count" in r for r in results)
