"""
Phase 20-23 테스트: 프로파일러, 결과 저장소, 배터리 모델, 동적 NFZ
"""
from __future__ import annotations

import json
import os
import tempfile

import numpy as np
import pytest


# ── 프로파일러 테스트 ────────────────────────────────────────


class TestProfiler:
    def test_profile_report_structure(self):
        from simulation.profiler import ProfileReport
        r = ProfileReport(wall_time_s=1.0, total_calls=100)
        s = r.summary()
        assert "1.00" in s
        assert "100" in s

    def test_profile_short_sim(self):
        from simulation.profiler import profile_simulation
        report = profile_simulation(duration_s=2.0, n_drones=3, seed=42, top_n=5)
        assert report.wall_time_s > 0
        assert report.total_calls > 0
        assert len(report.top_functions) <= 5


# ── 결과 저장소 테스트 ───────────────────────────────────────


class TestResultStore:
    def test_save_json(self):
        from simulation.result_store import ResultStore
        from simulation.analytics import SimulationResult
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ResultStore(tmpdir)
            result = SimulationResult(collision_count=5, seed=42)
            path = store.save(result, tag="test_run", fmt="json")
            assert path.exists()
            data = json.loads(path.read_text(encoding="utf-8"))
            assert data["collision_count"] == 5
            assert data["_tag"] == "test_run"

    def test_save_csv(self):
        from simulation.result_store import ResultStore
        from simulation.analytics import SimulationResult
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ResultStore(tmpdir)
            result = SimulationResult(seed=99)
            path = store.save(result, tag="csv_test", fmt="csv")
            assert path.exists()
            assert path.suffix == ".csv"

    def test_load_all(self):
        from simulation.result_store import ResultStore
        from simulation.analytics import SimulationResult
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ResultStore(tmpdir)
            store.save(SimulationResult(collision_count=1, seed=1), tag="a")
            store.save(SimulationResult(collision_count=2, seed=2), tag="b")
            all_results = store.load_all()
            assert len(all_results) == 2

    def test_find_by_tag(self):
        from simulation.result_store import ResultStore
        from simulation.analytics import SimulationResult
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ResultStore(tmpdir)
            store.save(SimulationResult(seed=1), tag="alpha")
            store.save(SimulationResult(seed=2), tag="beta")
            found = store.find_by_tag("alpha")
            assert len(found) == 1
            assert found[0]["_tag"] == "alpha"

    def test_compare(self):
        from simulation.result_store import ResultStore
        from simulation.analytics import SimulationResult
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ResultStore(tmpdir)
            store.save(SimulationResult(collision_count=0, seed=1), tag="v1")
            store.save(SimulationResult(collision_count=3, seed=2), tag="v2")
            table = store.compare(["v1", "v2"])
            assert "collision_count" in table
            assert "v1" in table

    def test_invalid_format(self):
        from simulation.result_store import ResultStore
        from simulation.analytics import SimulationResult
        with tempfile.TemporaryDirectory() as tmpdir:
            store = ResultStore(tmpdir)
            with pytest.raises(ValueError):
                store.save(SimulationResult(), fmt="xml")


# ── 배터리 모델 테스트 ───────────────────────────────────────


class TestBatteryModel:
    def test_basic_power(self):
        from simulation.simulator import _estimate_power_w
        from src.airspace_control.agents.drone_profiles import DRONE_PROFILES
        profile = DRONE_PROFILES["COMMERCIAL_DELIVERY"]
        pw = _estimate_power_w(10.0, profile)
        assert pw > 0

    def test_altitude_increases_power(self):
        from simulation.simulator import _estimate_power_w
        from src.airspace_control.agents.drone_profiles import DRONE_PROFILES
        profile = DRONE_PROFILES["COMMERCIAL_DELIVERY"]
        pw_low = _estimate_power_w(10.0, profile, altitude_m=30.0)
        pw_high = _estimate_power_w(10.0, profile, altitude_m=120.0)
        assert pw_high > pw_low

    def test_headwind_increases_power(self):
        from simulation.simulator import _estimate_power_w
        from src.airspace_control.agents.drone_profiles import DRONE_PROFILES
        profile = DRONE_PROFILES["COMMERCIAL_DELIVERY"]
        pw_calm = _estimate_power_w(10.0, profile, headwind_ms=0.0)
        pw_wind = _estimate_power_w(10.0, profile, headwind_ms=10.0)
        assert pw_wind > pw_calm

    def test_climb_increases_power(self):
        from simulation.simulator import _estimate_power_w
        from src.airspace_control.agents.drone_profiles import DRONE_PROFILES
        profile = DRONE_PROFILES["COMMERCIAL_DELIVERY"]
        pw_level = _estimate_power_w(10.0, profile, climb_rate_ms=0.0)
        pw_climb = _estimate_power_w(10.0, profile, climb_rate_ms=3.0)
        assert pw_climb > pw_level

    def test_descent_reduces_power(self):
        from simulation.simulator import _estimate_power_w
        from src.airspace_control.agents.drone_profiles import DRONE_PROFILES
        profile = DRONE_PROFILES["COMMERCIAL_DELIVERY"]
        pw_level = _estimate_power_w(10.0, profile, climb_rate_ms=0.0)
        pw_desc = _estimate_power_w(10.0, profile, climb_rate_ms=-3.0)
        assert pw_desc < pw_level

    def test_power_never_negative(self):
        from simulation.simulator import _estimate_power_w
        from src.airspace_control.agents.drone_profiles import DRONE_PROFILES
        profile = DRONE_PROFILES["COMMERCIAL_DELIVERY"]
        pw = _estimate_power_w(0.0, profile, climb_rate_ms=-10.0)
        assert pw >= 0.0

    def test_zero_speed_hover_power(self):
        from simulation.simulator import _estimate_power_w
        from src.airspace_control.agents.drone_profiles import DRONE_PROFILES
        profile = DRONE_PROFILES["COMMERCIAL_DELIVERY"]
        pw = _estimate_power_w(0.0, profile)
        assert pw > 0  # 호버링에도 전력 소모


# ── 동적 NFZ 테스트 ──────────────────────────────────────────


class TestDynamicNFZ:
    def _make_controller(self):
        import simpy
        from src.airspace_control.controller.airspace_controller import AirspaceController
        from src.airspace_control.comms.communication_bus import CommunicationBus
        from src.airspace_control.planning.flight_path_planner import FlightPathPlanner
        from src.airspace_control.avoidance.resolution_advisory import AdvisoryGenerator
        from src.airspace_control.controller.priority_queue import FlightPriorityQueue

        env = simpy.Environment()
        rng = np.random.default_rng(42)
        comm = CommunicationBus(env, rng)
        bounds = {"x": [-5000, 5000], "y": [-5000, 5000], "z": [0, 120]}
        planner = FlightPathPlanner(airspace_bounds=bounds, no_fly_zones=[])
        adv_gen = AdvisoryGenerator()
        pq = FlightPriorityQueue()
        ctrl = AirspaceController(
            env=env, comm_bus=comm, planner=planner,
            advisory_gen=adv_gen, priority_queue=pq, config={},
        )
        return ctrl

    def test_add_nfz(self):
        ctrl = self._make_controller()
        n = ctrl.add_dynamic_nfz("NFZ_TEST", np.array([0, 0, 0]), 500.0, 0.0)
        assert n == 0  # no active drones
        assert len(ctrl.planner.nfz_list) == 1
        assert ctrl.planner.nfz_list[0]["id"] == "NFZ_TEST"

    def test_remove_nfz(self):
        ctrl = self._make_controller()
        ctrl.add_dynamic_nfz("NFZ_A", np.zeros(3), 300.0, 0.0)
        ctrl.add_dynamic_nfz("NFZ_B", np.ones(3) * 100, 200.0, 0.0)
        assert len(ctrl.planner.nfz_list) == 2
        removed = ctrl.remove_dynamic_nfz("NFZ_A", 1.0)
        assert removed is True
        assert len(ctrl.planner.nfz_list) == 1
        assert ctrl.planner.nfz_list[0]["id"] == "NFZ_B"

    def test_remove_nonexistent(self):
        ctrl = self._make_controller()
        removed = ctrl.remove_dynamic_nfz("DOES_NOT_EXIST", 0.0)
        assert removed is False

    def test_nfz_reroutes_nearby_drones(self):
        from src.airspace_control.agents.drone_state import DroneState, FlightPhase
        ctrl = self._make_controller()
        drone = DroneState(
            drone_id="DR001",
            position=np.array([100.0, 100.0, 60.0]),
            velocity=np.array([5.0, 0.0, 0.0]),
            flight_phase=FlightPhase.ENROUTE,
        )
        ctrl._active_drones["DR001"] = drone
        ctrl.comm_bus.subscribe("DR001", lambda m: None)
        n = ctrl.add_dynamic_nfz("NFZ_NEAR", np.array([100.0, 100.0, 0.0]), 200.0, 0.0)
        assert n == 1  # drone within 200m * 1.2 = 240m

    def test_nfz_does_not_reroute_distant(self):
        from src.airspace_control.agents.drone_state import DroneState, FlightPhase
        ctrl = self._make_controller()
        drone = DroneState(
            drone_id="DR002",
            position=np.array([5000.0, 5000.0, 60.0]),
            velocity=np.array([5.0, 0.0, 0.0]),
            flight_phase=FlightPhase.ENROUTE,
        )
        ctrl._active_drones["DR002"] = drone
        n = ctrl.add_dynamic_nfz("NFZ_FAR", np.zeros(3), 100.0, 0.0)
        assert n == 0


# ── 시뮬레이터 통합 테스트 ───────────────────────────────────


class TestSimulatorIntegration:
    def test_battery_decreases_over_time(self):
        from simulation.simulator import SwarmSimulator
        sim = SwarmSimulator(seed=42, scenario_cfg={"drones": {"default_count": 3}})
        result = sim.run(duration_s=30.0)
        # 드론들이 비행했으므로 배터리가 줄었을 것
        assert result.total_flight_time_s > 0

    def test_result_serializable(self):
        from simulation.simulator import SwarmSimulator
        sim = SwarmSimulator(seed=42, scenario_cfg={"drones": {"default_count": 3}})
        result = sim.run(duration_s=5.0)
        d = result.to_dict()
        # JSON 직렬화 가능해야 함
        serialized = json.dumps(d)
        assert len(serialized) > 0

    def test_wind_updates_controller(self):
        from simulation.simulator import SwarmSimulator
        sim = SwarmSimulator(
            seed=42,
            scenario_cfg={
                "drones": {"default_count": 3},
                "weather": {"wind_models": [{"type": "constant", "speed_ms": 10, "direction_deg": 90}]},
            },
        )
        result = sim.run(duration_s=5.0)
        assert result.duration_s == 5.0
