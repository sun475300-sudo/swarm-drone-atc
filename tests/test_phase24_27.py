"""
Phase 24-27 테스트
==================
- Phase 24: MetricsCollector 실시간 메트릭 수집
- Phase 25: ResultStore 비교 차트 / HTML 리포트 / 민감도 분석
- Phase 26: FormationController 편대 비행 (V_SHAPE, LINE, CIRCLE, GRID)
- Phase 27: MeshNetwork 메쉬 통신 (라우팅, 파티션, 큐잉)
"""
import math
import os
import tempfile
from pathlib import Path

import numpy as np
import pytest


# ─── Phase 24: MetricsCollector ──────────────────────────────
class TestMetricsCollector:
    """MetricsCollector 시계열 수집 테스트"""

    def _make_collector(self):
        from visualization.metrics_stream import MetricsCollector
        return MetricsCollector(max_history=100)

    def _make_fake_drone(self, battery=80.0, phase_name="ENROUTE", active=True):
        """간이 드론 mock"""
        from src.airspace_control.agents.drone_state import DroneState, FlightPhase
        d = DroneState(
            drone_id="DR000",
            position=np.array([0.0, 0.0, 60.0]),
            velocity=np.array([10.0, 0.0, 0.0]),
            profile_name="COMMERCIAL_DELIVERY",
            flight_phase=FlightPhase[phase_name],
            battery_pct=battery,
        )
        return d

    def test_initial_empty(self):
        mc = self._make_collector()
        assert mc.latest is None
        assert mc.history_len() == 0

    def test_record_creates_snapshot(self):
        mc = self._make_collector()
        drones = [self._make_fake_drone(battery=75.0)]
        mc.record(t=1.0, drones=drones, conflicts=0, collisions=0,
                  near_misses=0, advisories=0)
        assert mc.history_len() == 1
        snap = mc.latest
        assert snap is not None
        assert snap.t == 1.0
        assert snap.avg_battery_pct == 75.0

    def test_battery_histogram(self):
        mc = self._make_collector()
        drones = [
            self._make_fake_drone(battery=5.0),
            self._make_fake_drone(battery=55.0),
            self._make_fake_drone(battery=95.0),
        ]
        mc.record(t=1.0, drones=drones, conflicts=0, collisions=0,
                  near_misses=0, advisories=0)
        hist = mc.battery_distribution()
        assert len(hist) == 10
        assert hist[0] == 1   # 0-10%
        assert hist[5] == 1   # 50-60%
        assert hist[9] == 1   # 90-100%

    def test_time_series(self):
        mc = self._make_collector()
        for i in range(5):
            drones = [self._make_fake_drone(battery=100.0 - i * 10)]
            mc.record(t=float(i), drones=drones, conflicts=i,
                      collisions=0, near_misses=0, advisories=0)
        ts, vals = mc.time_series("conflicts_cumulative")
        assert len(ts) == 5
        assert vals == [0, 1, 2, 3, 4]

    def test_energy_accumulates(self):
        mc = self._make_collector()
        drones = [self._make_fake_drone()]
        mc.record(t=1.0, drones=drones, conflicts=0, collisions=0,
                  near_misses=0, advisories=0, dt=0.1)
        mc.record(t=2.0, drones=drones, conflicts=0, collisions=0,
                  near_misses=0, advisories=0, dt=0.1)
        snap = mc.latest
        assert snap.total_energy_wh > 0

    def test_conflict_resolution_rate(self):
        mc = self._make_collector()
        drones = [self._make_fake_drone()]
        mc.record(t=1.0, drones=drones, conflicts=10, collisions=2,
                  near_misses=0, advisories=0)
        snap = mc.latest
        expected = (1.0 - 2 / 12) * 100
        assert abs(snap.conflict_resolution_rate - expected) < 0.01

    def test_max_history_limit(self):
        mc = self._make_collector()
        mc.max_history = 5
        mc._history = __import__("collections").deque(maxlen=5)
        drones = [self._make_fake_drone()]
        for i in range(10):
            mc.record(t=float(i), drones=drones, conflicts=0,
                      collisions=0, near_misses=0, advisories=0)
        assert mc.history_len() == 5

    def test_reset_clears(self):
        mc = self._make_collector()
        drones = [self._make_fake_drone()]
        mc.record(t=1.0, drones=drones, conflicts=0, collisions=0,
                  near_misses=0, advisories=0)
        mc.reset()
        assert mc.history_len() == 0
        assert mc.latest is None


# ─── Phase 25: ResultStore Enhanced ──────────────────────────
class TestResultStoreEnhanced:
    """ResultStore 비교 차트, HTML 리포트, 민감도 분석"""

    def _make_result(self, **overrides):
        from simulation.analytics import SimulationResult
        defaults = dict(
            collision_count=5,
            near_miss_count=10,
            conflict_resolution_rate_pct=95.0,
            route_efficiency_mean=1.05,
            energy_efficiency_wh_per_km=12.5,
            seed=42,
        )
        defaults.update(overrides)
        return SimulationResult(**defaults)

    def test_compare_chart_returns_path(self):
        from simulation.result_store import ResultStore
        with tempfile.TemporaryDirectory() as td:
            store = ResultStore(td)
            r1 = self._make_result(collision_count=3)
            r2 = self._make_result(collision_count=8)
            store.save(r1, tag="v1")
            store.save(r2, tag="v2")
            path = store.compare_chart(["v1", "v2"])
            if path is not None:  # matplotlib may not be available
                assert path.exists()

    def test_compare_chart_no_results(self):
        from simulation.result_store import ResultStore
        with tempfile.TemporaryDirectory() as td:
            store = ResultStore(td)
            path = store.compare_chart(["nonexistent"])
            assert path is None

    def test_sensitivity_analysis(self):
        from simulation.result_store import ResultStore
        with tempfile.TemporaryDirectory() as td:
            store = ResultStore(td)
            for n in [50, 100, 200]:
                r = self._make_result(collision_count=n // 10)
                r.n_drones = n
                store.save(r, tag=f"sens_{n}")
            params, vals = store.sensitivity_analysis(
                "collision_count", "near_miss_count")
            assert len(params) == len(vals)

    def test_sensitivity_analysis_empty(self):
        from simulation.result_store import ResultStore
        with tempfile.TemporaryDirectory() as td:
            store = ResultStore(td)
            params, vals = store.sensitivity_analysis("nonexistent")
            assert params == [] and vals == []

    def test_html_report_creation(self):
        from simulation.result_store import ResultStore
        with tempfile.TemporaryDirectory() as td:
            store = ResultStore(td)
            r1 = self._make_result(collision_count=2)
            store.save(r1, tag="report_test")
            path = store.export_html_report(["report_test"])
            assert path.exists()
            content = path.read_text(encoding="utf-8")
            assert "SDACS" in content
            assert "report_test" in content

    def test_html_report_contains_metrics(self):
        from simulation.result_store import ResultStore
        with tempfile.TemporaryDirectory() as td:
            store = ResultStore(td)
            r1 = self._make_result(collision_count=7)
            store.save(r1, tag="metrics_html")
            path = store.export_html_report(["metrics_html"])
            content = path.read_text(encoding="utf-8")
            assert "collision_count" in content


# ─── Phase 26: FormationController ───────────────────────────
class TestFormationController:
    """편대 비행 알고리즘 테스트"""

    def test_v_shape_offsets(self):
        from simulation.formation import FormationController
        fc = FormationController(pattern="V_SHAPE", spacing=80.0)
        offsets = fc.compute_offsets(4)
        assert len(offsets) == 4
        # V자: 뒤쪽으로 가야 함 (x_off < 0)
        for off in offsets:
            assert off[0] < 0

    def test_line_offsets(self):
        from simulation.formation import FormationController
        fc = FormationController(pattern="LINE", spacing=50.0)
        offsets = fc.compute_offsets(3)
        assert len(offsets) == 3
        # 일렬: y=0, x는 점점 뒤로
        for off in offsets:
            assert off[1] == 0.0
            assert off[0] < 0

    def test_circle_offsets(self):
        from simulation.formation import FormationController
        fc = FormationController(pattern="CIRCLE", spacing=100.0)
        offsets = fc.compute_offsets(4)
        assert len(offsets) == 4
        # 원형: 모든 오프셋은 spacing 거리
        for off in offsets:
            dist = float(np.linalg.norm(off[:2]))
            assert abs(dist - 100.0) < 1.0

    def test_grid_offsets(self):
        from simulation.formation import FormationController
        fc = FormationController(pattern="GRID", spacing=60.0)
        offsets = fc.compute_offsets(6)
        assert len(offsets) == 6

    def test_zero_followers(self):
        from simulation.formation import FormationController
        fc = FormationController(pattern="V_SHAPE")
        offsets = fc.compute_offsets(0)
        assert offsets == []

    def test_follower_targets_world_coords(self):
        from simulation.formation import FormationController
        fc = FormationController(pattern="LINE", spacing=50.0)
        leader_pos = np.array([1000.0, 2000.0, 60.0])
        targets = fc.follower_targets(leader_pos, 0.0, 2)
        assert len(targets) == 2
        # 방향 0 (동쪽) → 뒤쪽은 서쪽
        for t in targets:
            assert t[0] < leader_pos[0]

    def test_follower_targets_heading_rotation(self):
        from simulation.formation import FormationController
        fc = FormationController(pattern="LINE", spacing=100.0)
        leader_pos = np.array([0.0, 0.0, 60.0])
        # 북쪽 향할 때 (pi/2)
        targets = fc.follower_targets(leader_pos, math.pi / 2, 1)
        # 뒤쪽은 남쪽 → y < 0
        assert targets[0][1] < -50

    def test_change_pattern(self):
        from simulation.formation import FormationController, FormationPattern
        fc = FormationController(pattern="V_SHAPE")
        assert fc.pattern == FormationPattern.V_SHAPE
        fc.change_pattern("CIRCLE")
        assert fc.pattern == FormationPattern.CIRCLE

    def test_compute_follow_velocity(self):
        from simulation.formation import FormationController
        fc = FormationController()
        pos = np.array([0.0, 0.0, 60.0])
        target = np.array([100.0, 0.0, 60.0])
        vel = fc.compute_follow_velocity(pos, target, max_speed=15.0)
        assert vel[0] > 0  # 동쪽으로 이동
        assert float(np.linalg.norm(vel)) <= 15.0 + 0.01

    def test_follow_velocity_at_target(self):
        from simulation.formation import FormationController
        fc = FormationController()
        pos = np.array([100.0, 0.0, 60.0])
        target = np.array([100.0, 0.0, 60.0])
        vel = fc.compute_follow_velocity(pos, target)
        assert float(np.linalg.norm(vel)) < 0.01

    def test_should_break_formation(self):
        from simulation.formation import FormationController
        fc = FormationController()
        pos = np.array([100.0, 100.0, 60.0])
        target = np.array([100.0, 100.0, 60.0])
        obstacle = np.array([120.0, 100.0, 60.0])
        assert fc.should_break_formation(pos, target, 50.0, [obstacle]) is True
        assert fc.should_break_formation(pos, target, 50.0, []) is False

    def test_break_formation_distant_obstacle(self):
        from simulation.formation import FormationController
        fc = FormationController()
        pos = np.array([0.0, 0.0, 60.0])
        target = np.array([0.0, 0.0, 60.0])
        obstacle = np.array([1000.0, 1000.0, 60.0])
        assert fc.should_break_formation(pos, target, 50.0, [obstacle]) is False


# ─── Phase 27: MeshNetwork ───────────────────────────────────
class TestMeshNetwork:
    """메쉬 네트워크 토폴로지 테스트"""

    def _make_mesh(self, comm_range=500.0):
        from simulation.mesh_network import MeshNetwork
        return MeshNetwork(comm_range=comm_range)

    def test_two_nodes_in_range(self):
        mesh = self._make_mesh(500.0)
        mesh.update_positions({
            "A": np.array([0.0, 0.0, 60.0]),
            "B": np.array([300.0, 0.0, 60.0]),
        })
        assert "B" in mesh.neighbors("A")
        assert "A" in mesh.neighbors("B")

    def test_two_nodes_out_of_range(self):
        mesh = self._make_mesh(200.0)
        mesh.update_positions({
            "A": np.array([0.0, 0.0, 60.0]),
            "B": np.array([500.0, 0.0, 60.0]),
        })
        assert "B" not in mesh.neighbors("A")

    def test_find_route_direct(self):
        mesh = self._make_mesh(500.0)
        mesh.update_positions({
            "A": np.array([0.0, 0.0, 60.0]),
            "B": np.array([300.0, 0.0, 60.0]),
        })
        route = mesh.find_route("A", "B")
        assert route == ["A", "B"]

    def test_find_route_multihop(self):
        mesh = self._make_mesh(300.0)
        mesh.update_positions({
            "A": np.array([0.0, 0.0, 60.0]),
            "B": np.array([200.0, 0.0, 60.0]),
            "C": np.array([400.0, 0.0, 60.0]),
        })
        route = mesh.find_route("A", "C")
        assert route is not None
        assert route[0] == "A" and route[-1] == "C"
        assert len(route) == 3  # A -> B -> C

    def test_find_route_unreachable(self):
        mesh = self._make_mesh(100.0)
        mesh.update_positions({
            "A": np.array([0.0, 0.0, 60.0]),
            "B": np.array([500.0, 0.0, 60.0]),
        })
        route = mesh.find_route("A", "B")
        assert route is None

    def test_find_route_self(self):
        mesh = self._make_mesh(500.0)
        mesh.update_positions({"A": np.array([0.0, 0.0, 60.0])})
        route = mesh.find_route("A", "A")
        assert route == ["A"]

    def test_detect_single_partition(self):
        mesh = self._make_mesh(500.0)
        mesh.update_positions({
            "A": np.array([0.0, 0.0, 60.0]),
            "B": np.array([200.0, 0.0, 60.0]),
            "C": np.array([400.0, 0.0, 60.0]),
        })
        parts = mesh.detect_partitions()
        assert len(parts) == 1
        assert mesh.is_connected()

    def test_detect_two_partitions(self):
        mesh = self._make_mesh(200.0)
        mesh.update_positions({
            "A": np.array([0.0, 0.0, 60.0]),
            "B": np.array([100.0, 0.0, 60.0]),
            "C": np.array([2000.0, 0.0, 60.0]),
            "D": np.array([2100.0, 0.0, 60.0]),
        })
        parts = mesh.detect_partitions()
        assert len(parts) == 2
        assert not mesh.is_connected()

    def test_send_message_success(self):
        mesh = self._make_mesh(500.0)
        mesh.update_positions({
            "A": np.array([0.0, 0.0, 60.0]),
            "B": np.array([300.0, 0.0, 60.0]),
        })
        assert mesh.send_message("A", "B") is True
        assert mesh.messages_routed == 1

    def test_send_message_no_route(self):
        mesh = self._make_mesh(100.0)
        mesh.update_positions({
            "A": np.array([0.0, 0.0, 60.0]),
            "B": np.array([500.0, 0.0, 60.0]),
        })
        assert mesh.send_message("A", "B") is False
        assert mesh.messages_dropped == 1

    def test_network_stats(self):
        mesh = self._make_mesh(500.0)
        mesh.update_positions({
            "A": np.array([0.0, 0.0, 60.0]),
            "B": np.array([200.0, 0.0, 60.0]),
            "C": np.array([400.0, 0.0, 60.0]),
        })
        stats = mesh.network_stats()
        assert stats["nodes"] == 3
        assert stats["connected"] is True
        assert stats["partitions"] == 1

    def test_suggest_relay_connected(self):
        mesh = self._make_mesh(500.0)
        mesh.update_positions({
            "A": np.array([0.0, 0.0, 60.0]),
            "B": np.array([200.0, 0.0, 60.0]),
        })
        relays = mesh.suggest_relay_positions()
        assert len(relays) == 0  # already connected

    def test_suggest_relay_partitioned(self):
        mesh = self._make_mesh(200.0)
        mesh.update_positions({
            "A": np.array([0.0, 0.0, 60.0]),
            "B": np.array([2000.0, 0.0, 60.0]),
        })
        relays = mesh.suggest_relay_positions()
        assert len(relays) >= 1
        # 중점 근처여야 함
        midpoint = np.array([1000.0, 0.0, 60.0])
        assert float(np.linalg.norm(relays[0] - midpoint)) < 100

    def test_empty_network(self):
        mesh = self._make_mesh()
        mesh.update_positions({})
        assert mesh.is_connected()  # 빈 네트워크는 연결
        assert mesh.detect_partitions() == []
