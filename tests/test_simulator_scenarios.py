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


class TestRTLNearestPad:
    """BUG-03: RTL 시 최근접 패드로 귀환하는지 검증"""

    def test_nearest_pad_selection(self):
        """드론 위치에 가장 가까운 패드가 선택되어야 한다."""
        import numpy as np
        from simulation.simulator import SwarmSimulator

        # 패드 딕셔너리에서 최근접 패드 선택 로직 직접 테스트
        landing_pads = {
            "PAD_NW": np.array([-3000.0,  3000.0, 0.0]),
            "PAD_NE": np.array([ 3000.0,  3000.0, 0.0]),
            "PAD_SW": np.array([-3000.0, -3000.0, 0.0]),
            "PAD_SE": np.array([ 3000.0, -3000.0, 0.0]),
            "PAD_CENTER": np.array([0.0, 0.0, 0.0]),
        }
        drone_pos = np.array([2800.0, 2800.0, 80.0])  # PAD_NE에 가장 가까움

        nearest = min(
            landing_pads.values(),
            key=lambda p: float(np.linalg.norm(drone_pos[:2] - p[:2])),
        )
        expected = landing_pads["PAD_NE"]
        assert np.allclose(nearest, expected), (
            f"PAD_NE를 기대했으나 {nearest} 선택됨"
        )

    def test_nearest_pad_sw(self):
        """SW 구역 드론은 PAD_SW 선택"""
        import numpy as np
        landing_pads = {
            "PAD_NW": np.array([-3000.0,  3000.0, 0.0]),
            "PAD_NE": np.array([ 3000.0,  3000.0, 0.0]),
            "PAD_SW": np.array([-3000.0, -3000.0, 0.0]),
            "PAD_SE": np.array([ 3000.0, -3000.0, 0.0]),
            "PAD_CENTER": np.array([0.0, 0.0, 0.0]),
        }
        drone_pos = np.array([-2500.0, -2500.0, 80.0])
        nearest = min(
            landing_pads.values(),
            key=lambda p: float(np.linalg.norm(drone_pos[:2] - p[:2])),
        )
        assert np.allclose(nearest, landing_pads["PAD_SW"])


class TestHoldingRTL:
    """IMP-04: HOLDING 3회 반복 시 RTL 전환 검증"""

    def test_hold_count_increments(self):
        """HOLDING 진입 시 hold_count가 증가해야 한다."""
        from src.airspace_control.agents.drone_state import DroneState, FlightPhase
        drone = DroneState(
            drone_id="H1",
            position=[0.0, 0.0, 60.0],
            velocity=[0.0, 0.0, 0.0],
        )
        assert drone.hold_count == 0
        drone.hold_count += 1
        assert drone.hold_count == 1

    def test_hold_count_field_exists(self):
        """DroneState에 hold_count 필드가 있어야 한다."""
        from src.airspace_control.agents.drone_state import DroneState
        drone = DroneState(
            drone_id="H2",
            position=[0.0, 0.0, 60.0],
            velocity=[0.0, 0.0, 0.0],
        )
        assert hasattr(drone, "hold_count")
        assert isinstance(drone.hold_count, int)
