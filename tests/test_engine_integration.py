"""
엔진 통합 테스트 — SwarmSimulator + Voronoi 공역 분할

검증 항목:
  1. SwarmSimulator.run() 완주 + SimulationResult 반환
  2. SimulationResult.summary_table() 출력 형식
  3. AirspaceController Voronoi 활성화 (_check_voronoi_conflict)
  4. main.py cmd_simulate 엔드투엔드 (argparse → SwarmSimulator)
"""
from __future__ import annotations

import sys
import os
import types

import numpy as np
import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


# ── 1. SwarmSimulator 짧은 실행 ──────────────────────────────

class TestSwarmSimulatorRun:
    def test_run_returns_simulation_result(self):
        from simulation.simulator import SwarmSimulator
        from simulation.analytics import SimulationResult

        sim = SwarmSimulator(seed=0, scenario_cfg={"drones": {"default_count": 5}})
        result = sim.run(duration_s=10.0)
        assert isinstance(result, SimulationResult)

    def test_result_fields_nonnegative(self):
        from simulation.simulator import SwarmSimulator

        sim = SwarmSimulator(seed=1, scenario_cfg={"drones": {"default_count": 5}})
        r = sim.run(duration_s=10.0)
        assert r.collision_count >= 0
        assert r.near_miss_count >= 0
        assert r.conflicts_total >= 0
        assert r.advisories_issued >= 0
        assert 0.0 <= r.conflict_resolution_rate_pct <= 100.0

    def test_result_summary_table_format(self):
        from simulation.simulator import SwarmSimulator

        sim = SwarmSimulator(seed=2, scenario_cfg={"drones": {"default_count": 3}})
        r = sim.run(duration_s=5.0)
        table = r.summary_table()
        assert "KPI" in table
        assert "충돌 수" in table
        assert "┌" in table and "┘" in table


# ── 2. SimulationResult.summary_table() ──────────────────────

class TestSimulationResultSummaryTable:
    def test_summary_table_contains_all_kpis(self):
        from simulation.analytics import SimulationResult

        r = SimulationResult(
            collision_count=0,
            near_miss_count=2,
            conflicts_total=5,
            advisories_issued=5,
            conflict_resolution_rate_pct=100.0,
            route_efficiency_mean=1.05,
            route_efficiency_max=1.12,
            total_flight_time_s=3600.0,
            total_distance_km=120.5,
            clearances_approved=50,
            clearances_denied=0,
            advisory_latency_p50=0.45,
            advisory_latency_p99=1.82,
            seed=42,
            scenario="default",
            duration_s=600.0,
            n_drones=100,
        )
        table = r.summary_table()
        assert "100.0 %" in table
        assert "1.050" in table
        assert "120.5 km" in table
        assert "0.45" in table

    def test_check_acceptance_passes_good_result(self):
        from simulation.analytics import SimulationResult

        r = SimulationResult(
            collision_count=0,
            conflict_resolution_rate_pct=99.8,
            route_efficiency_mean=1.10,
        )
        thresholds = {
            "conflict_resolution_rate_pct": 99.5,
            "route_efficiency_max": 1.15,
        }
        checks = r.check_acceptance(thresholds)
        assert checks["no_collision"] is True
        assert checks["conflict_res_rate"] is True
        assert checks["route_efficiency"] is True

    def test_check_acceptance_fails_collision(self):
        from simulation.analytics import SimulationResult

        r = SimulationResult(collision_count=1)
        checks = r.check_acceptance({})
        assert checks["no_collision"] is False


# ── 3. Voronoi 충돌 감지 ─────────────────────────────────────

class TestVoronoiConflictDetection:
    def _make_controller(self):
        """최소 의존성 AirspaceController 인스턴스 생성"""
        import simpy
        from src.airspace_control.comms.communication_bus import CommunicationBus
        from src.airspace_control.controller.priority_queue import FlightPriorityQueue
        from src.airspace_control.planning.flight_path_planner import FlightPathPlanner
        from src.airspace_control.avoidance.resolution_advisory import AdvisoryGenerator
        from src.airspace_control.controller.airspace_controller import AirspaceController

        env  = simpy.Environment()
        rng  = np.random.default_rng(0)
        bus  = CommunicationBus(env, rng)
        pq   = FlightPriorityQueue()
        bounds = {"x": [-5000, 5000], "y": [-5000, 5000], "z": [0, 200]}
        plan = FlightPathPlanner(airspace_bounds=bounds, no_fly_zones=[])
        adv  = AdvisoryGenerator()
        cfg  = {
            "separation_standards": {
                "lateral_min_m": 50.0,
                "vertical_min_m": 15.0,
                "near_miss_lateral_m": 10.0,
                "conflict_lookahead_s": 90.0,
            },
            "controller": {"max_concurrent_clearances": 10},
        }
        return AirspaceController(env, bus, plan, adv, pq, cfg)

    def test_no_cells_returns_empty(self):
        ctrl = self._make_controller()
        # _voronoi_cells 비어있을 때 → 충돌 없음
        dest = np.array([100.0, 100.0, 50.0])
        result = ctrl._check_voronoi_conflict("drone_A", dest)
        assert result == ""

    def test_point_inside_polygon_detected(self):
        from src.airspace_control.controller.airspace_controller import _point_in_polygon

        # 단위 정사각형 (0,0)-(1,1)
        square = [(0, 0), (1, 0), (1, 1), (0, 1)]
        assert _point_in_polygon(np.array([0.5, 0.5]), square) is True
        assert _point_in_polygon(np.array([1.5, 0.5]), square) is False
        assert _point_in_polygon(np.array([0.1, 0.9]), square) is True

    def test_voronoi_conflict_detected(self):
        ctrl = self._make_controller()

        # 가짜 Voronoi 셀: drone_B가 (0,0)-(200,0)-(200,200)-(0,200) 사각형 소유
        class FakeCell:
            vertices = [(0, 0), (200, 0), (200, 200), (0, 200)]

        ctrl._voronoi_cells = {"drone_B": FakeCell()}

        # drone_A가 drone_B 셀 내부 목적지로 요청
        dest = np.array([100.0, 100.0, 50.0])
        conflict = ctrl._check_voronoi_conflict("drone_A", dest)
        assert conflict == "drone_B"

    def test_own_cell_not_conflict(self):
        ctrl = self._make_controller()

        class FakeCell:
            vertices = [(0, 0), (200, 0), (200, 200), (0, 200)]

        ctrl._voronoi_cells = {"drone_A": FakeCell()}

        # 자신의 셀 내부 → 충돌 없음
        dest = np.array([100.0, 100.0, 50.0])
        conflict = ctrl._check_voronoi_conflict("drone_A", dest)
        assert conflict == ""


# ── 4. main.py cmd_simulate 연기 테스트 ──────────────────────

class TestMainCmdSimulate:
    def test_cmd_simulate_calls_swarm_simulator(self, monkeypatch):
        """cmd_simulate가 SwarmSimulator를 사용하는지 확인"""
        from simulation.analytics import SimulationResult

        called_with = {}

        class MockSim:
            def __init__(self, seed, scenario_cfg):
                called_with["seed"] = seed
                called_with["cfg"] = scenario_cfg

            def run(self, duration_s):
                called_with["duration"] = duration_s
                r = SimulationResult()
                return r

        import simulation.simulator as sim_mod
        monkeypatch.setattr(sim_mod, "SwarmSimulator", MockSim)

        import main as main_mod
        import types

        args = types.SimpleNamespace(
            duration=10.0,
            seed=99,
            drones=5,
            log_level="WARNING",
        )
        main_mod.cmd_simulate(args)

        assert called_with["seed"] == 99
        assert called_with["duration"] == 10.0
        assert called_with["cfg"]["drones"]["default_count"] == 5
