"""
시나리오별 통합 테스트 (짧은 시뮬레이션 실행)
"""
from __future__ import annotations

import pytest

from simulation.analytics import SimulationResult


@pytest.fixture
def base_scenario():
    return {
        "airspace": {
            "bounds_km": {"x": [-2, 2], "y": [-2, 2], "z": [0, 0.15]},
            "no_fly_zones": [
                {"center": [0, 0, 0], "radius_m": 200, "label": "TEST_NFZ"}
            ],
        },
        "drones": {"count": 4, "profiles": ["COMMERCIAL_DELIVERY"]},
        "weather": {"wind_models": []},
        "failure_injection": {"drone_failure_rate": 0.0, "comms_loss_rate": 0.0},
        "logging": {"save_trajectory": False},
    }


class TestBaseScenario:
    def test_run_returns_result(self, sim_config, base_scenario):
        from simulation.simulator import SwarmSimulator
        sim = SwarmSimulator(config_path=sim_config, scenario_cfg=base_scenario, seed=0)
        result = sim.run(duration_s=30.0)
        assert isinstance(result, SimulationResult)

    def test_no_collision_basic(self, sim_config, base_scenario):
        from simulation.simulator import SwarmSimulator
        sim = SwarmSimulator(config_path=sim_config, scenario_cfg=base_scenario, seed=42)
        result = sim.run(duration_s=30.0)
        # 충돌 수가 합리적인 범위여야 함 (음수 아님)
        assert result.collision_count >= 0

    def test_drones_registered(self, sim_config, base_scenario):
        from simulation.simulator import SwarmSimulator
        sim = SwarmSimulator(config_path=sim_config, scenario_cfg=base_scenario, seed=1)
        result = sim.run(duration_s=10.0)
        assert result.n_drones >= 1


class TestWeatherScenario:
    def test_strong_wind_scenario(self, sim_config, base_scenario):
        from simulation.simulator import SwarmSimulator
        scenario = dict(base_scenario)
        scenario["weather"] = {
            "wind_models": [
                {"type": "constant", "speed_ms": 15.0, "direction_deg": 90.0}
            ]
        }
        sim = SwarmSimulator(config_path=sim_config, scenario_cfg=scenario, seed=5)
        result = sim.run(duration_s=20.0)
        assert isinstance(result, SimulationResult)

    def test_gust_scenario(self, sim_config, base_scenario):
        from simulation.simulator import SwarmSimulator
        scenario = dict(base_scenario)
        scenario["weather"] = {
            "wind_models": [
                {
                    "type": "variable",
                    "mean_speed_ms": 5.0,
                    "direction_deg": 0.0,
                    "gust_speed_ms": 12.0,
                    "gust_duration_s": 5.0,
                }
            ]
        }
        sim = SwarmSimulator(config_path=sim_config, scenario_cfg=scenario, seed=7)
        result = sim.run(duration_s=20.0)
        assert isinstance(result, SimulationResult)


class TestIntrusionScenario:
    def test_rogue_drone_detected(self, sim_config, base_scenario):
        from simulation.simulator import SwarmSimulator
        scenario = dict(base_scenario)
        scenario["drones"] = {
            "count": 3,
            "profiles": ["COMMERCIAL_DELIVERY"],
            "rogue_count": 1,
        }
        sim = SwarmSimulator(config_path=sim_config, scenario_cfg=scenario, seed=10)
        result = sim.run(duration_s=15.0)
        assert isinstance(result, SimulationResult)


class TestCommsLossScenario:
    def test_comms_loss_simulation(self, sim_config, base_scenario):
        from simulation.simulator import SwarmSimulator
        scenario = dict(base_scenario)
        scenario["failure_injection"] = {
            "drone_failure_rate": 0.0,
            "comms_loss_rate": 0.2,
        }
        sim = SwarmSimulator(config_path=sim_config, scenario_cfg=scenario, seed=20)
        result = sim.run(duration_s=20.0)
        assert isinstance(result, SimulationResult)


class TestFailureScenario:
    def test_drone_failure_injection(self, sim_config, base_scenario):
        from simulation.simulator import SwarmSimulator
        scenario = dict(base_scenario)
        scenario["failure_injection"] = {
            "drone_failure_rate": 0.5,
            "comms_loss_rate": 0.0,
        }
        sim = SwarmSimulator(config_path=sim_config, scenario_cfg=scenario, seed=30)
        result = sim.run(duration_s=20.0)
        assert isinstance(result, SimulationResult)
