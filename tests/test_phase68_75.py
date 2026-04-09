"""
Phase 68-75 테스트
- 교통 흐름 분석기 (TrafficFlowAnalyzer)
- 부하 분산기 (LoadBalancer)
- 웨이포인트 최적화 (WaypointOptimizer)
- 비상 대안 경로 (ContingencyPlanner)
- 감시 추적기 (SurveillanceTracker)
- 충전 인프라 (PowerGrid)
- 규제 보고서 (RegulatoryReporter)
- 시나리오 생성기 (ScenarioGenerator)
"""
import pytest
import numpy as np


# ──────────────────────────────────────────────
# Phase 68: 교통 흐름 분석기
# ──────────────────────────────────────────────
class TestTrafficFlowAnalyzer:
    def _make(self):
        from simulation.traffic_flow import TrafficFlowAnalyzer
        return TrafficFlowAnalyzer(bounds=(0, 0, 1000, 1000), grid=(5, 5))

    def test_basic_update(self):
        tf = self._make()
        tf.update({"d1": (100, 100, 50), "d2": (100, 150, 50)})
        dm = tf.density_map()
        assert dm.sum() == 2

    def test_empty_no_bottleneck(self):
        tf = self._make()
        tf.update({})
        assert tf.detect_bottlenecks() == []

    def test_bottleneck_detection(self):
        tf = self._make()
        positions = {f"d{i}": (100, 100, 50) for i in range(15)}
        tf.update(positions)
        bns = tf.detect_bottlenecks()
        assert len(bns) >= 1
        assert bns[0].density >= 10

    def test_flow_map_shape(self):
        tf = self._make()
        fm = tf.flow_map()
        assert fm.shape == (5, 5)

    def test_density_map_shape(self):
        tf = self._make()
        dm = tf.density_map()
        assert dm.shape == (5, 5)

    def test_overall_congestion_zero_empty(self):
        tf = self._make()
        tf.update({})
        assert tf.overall_congestion() == 0.0

    def test_with_velocities(self):
        tf = self._make()
        pos = {"d1": (500, 500, 50)}
        vel = {"d1": (5, 0, 0)}
        tf.update(pos, vel)
        assert tf.overall_congestion() >= 0

    def test_summary(self):
        tf = self._make()
        tf.update({"d1": (500, 500, 50)})
        s = tf.summary()
        assert "total_cells" in s
        assert s["total_cells"] == 25

    def test_boundary_positions(self):
        tf = self._make()
        tf.update({"d1": (0, 0, 50), "d2": (999, 999, 50)})
        dm = tf.density_map()
        assert dm.sum() == 2


# ──────────────────────────────────────────────
# Phase 69: 부하 분산기
# ──────────────────────────────────────────────
class TestLoadBalancer:
    def _make(self):
        from simulation.load_balancer import LoadBalancer
        return LoadBalancer(bounds=(0, 0, 900, 900), sectors=(3, 3))

    def test_update(self):
        lb = self._make()
        lb.update({"d1": (100, 100, 50), "d2": (500, 500, 50)})
        s = lb.summary()
        assert s["total_drones"] == 2

    def test_balanced_no_hotspots(self):
        lb = self._make()
        positions = {}
        idx = 0
        for r in range(3):
            for c in range(3):
                x = 150 + c * 300
                y = 150 + r * 300
                positions[f"d{idx}"] = (x, y, 50)
                idx += 1
        lb.update(positions)
        assert len(lb.hotspots()) == 0

    def test_imbalanced_detects_hotspot(self):
        lb = self._make()
        positions = {f"d{i}": (100, 100, 50) for i in range(20)}
        lb.update(positions)
        assert len(lb.hotspots()) >= 1
        assert lb.imbalance_score() > 0.5

    def test_rebalance_generates_actions(self):
        lb = self._make()
        positions = {f"d{i}": (100, 100, 50) for i in range(20)}
        lb.update(positions)
        actions = lb.rebalance()
        assert len(actions) >= 1
        assert actions[0].from_sector != actions[0].to_sector

    def test_coldspots(self):
        lb = self._make()
        positions = {f"d{i}": (100, 100, 50) for i in range(20)}
        lb.update(positions)
        assert len(lb.coldspots()) >= 1

    def test_empty_zero_imbalance(self):
        lb = self._make()
        lb.update({})
        assert lb.imbalance_score() == 0.0

    def test_rebalance_max_moves(self):
        lb = self._make()
        positions = {f"d{i}": (100, 100, 50) for i in range(30)}
        lb.update(positions)
        actions = lb.rebalance(max_moves=2)
        assert len(actions) <= 2

    def test_summary_keys(self):
        lb = self._make()
        lb.update({})
        s = lb.summary()
        assert "imbalance" in s
        assert "sector_counts" in s


# ──────────────────────────────────────────────
# Phase 70: 웨이포인트 최적화
# ──────────────────────────────────────────────
class TestWaypointOptimizer:
    def _make(self):
        from simulation.waypoint_optimizer import WaypointOptimizer
        return WaypointOptimizer()

    def test_simplify_straight_line(self):
        opt = self._make()
        wps = [(0, 0, 50), (50, 0, 50), (100, 0, 50), (150, 0, 50)]
        result = opt.simplify(wps, epsilon=1.0)
        assert len(result) == 2  # start + end only

    def test_simplify_keeps_corners(self):
        opt = self._make()
        wps = [(0, 0, 50), (100, 0, 50), (100, 100, 50), (200, 100, 50)]
        result = opt.simplify(wps, epsilon=1.0)
        assert len(result) >= 3

    def test_simplify_short_path(self):
        opt = self._make()
        wps = [(0, 0, 50), (100, 100, 50)]
        result = opt.simplify(wps)
        assert len(result) == 2

    def test_smooth_output(self):
        opt = self._make()
        wps = [(0, 0, 50), (50, 30, 50), (100, 0, 50), (150, 30, 50)]
        result = opt.smooth(wps, resolution=10)
        assert len(result) > len(wps)

    def test_optimize_result(self):
        opt = self._make()
        wps = [(0, 0, 50), (50, 0, 50), (100, 0, 50), (150, 0, 50)]
        r = opt.optimize(wps, epsilon=1.0)
        assert r.original_count == 4
        assert r.optimized_count <= 4
        assert r.reduction_pct >= 0

    def test_remove_collinear(self):
        opt = self._make()
        wps = [(0, 0, 50), (50, 0.1, 50), (100, 0, 50)]
        result = opt.remove_collinear(wps, angle_threshold_deg=5.0)
        assert len(result) <= 3

    def test_summary(self):
        opt = self._make()
        wps = [(0, 0, 50), (50, 0, 50), (100, 0, 50)]
        s = opt.summary(wps)
        assert "original" in s
        assert "optimized" in s

    def test_empty_waypoints(self):
        opt = self._make()
        assert opt.simplify([]) == []
        assert opt.smooth([(0, 0, 0)]) == [(0, 0, 0)]


# ──────────────────────────────────────────────
# Phase 71: 비상 대안 경로
# ──────────────────────────────────────────────
class TestContingencyPlanner:
    def _make(self):
        from simulation.contingency_planner import ContingencyPlanner
        return ContingencyPlanner()

    def test_set_primary_and_alternatives(self):
        cp = self._make()
        wps = [(0, 0, 50), (100, 100, 50), (200, 200, 50)]
        cp.set_primary_path("d1", wps)
        alts = cp.compute_alternatives("d1")
        assert len(alts) == 3

    def test_alternative_has_waypoints(self):
        cp = self._make()
        wps = [(0, 0, 50), (100, 100, 50), (200, 200, 50)]
        cp.set_primary_path("d1", wps)
        alts = cp.compute_alternatives("d1")
        for a in alts:
            assert len(a.waypoints) >= 2

    def test_alternatives_with_blocked_zones(self):
        cp = self._make()
        wps = [(0, 0, 50), (100, 100, 50), (200, 200, 50)]
        cp.set_primary_path("d1", wps)
        alts = cp.compute_alternatives("d1", blocked_zones=[(100, 100, 50)])
        assert len(alts) > 0

    def test_get_best_alternative(self):
        cp = self._make()
        wps = [(0, 0, 50), (100, 100, 50), (200, 200, 50)]
        cp.set_primary_path("d1", wps)
        cp.compute_alternatives("d1")
        best = cp.get_best_alternative("d1")
        assert best is not None
        assert best.total_distance_m > 0

    def test_switch_to_alternative(self):
        cp = self._make()
        wps = [(0, 0, 50), (100, 100, 50), (200, 200, 50)]
        cp.set_primary_path("d1", wps)
        alts = cp.compute_alternatives("d1")
        ok = cp.switch_to_alternative("d1", alts[0].route_id)
        assert ok is True

    def test_switch_invalid_route(self):
        cp = self._make()
        cp.set_primary_path("d1", [(0, 0, 50), (100, 100, 50)])
        assert cp.switch_to_alternative("d1", "nonexistent") is False

    def test_no_primary_no_alternatives(self):
        cp = self._make()
        assert cp.compute_alternatives("d1") == []

    def test_summary(self):
        cp = self._make()
        cp.set_primary_path("d1", [(0, 0, 50), (100, 100, 50), (200, 200, 50)])
        cp.compute_alternatives("d1")
        s = cp.summary()
        assert s["primary_routes"] == 1
        assert s["alternatives_computed"] == 3


# ──────────────────────────────────────────────
# Phase 72: 감시 추적기
# ──────────────────────────────────────────────
class TestSurveillanceTracker:
    def _make(self):
        from simulation.surveillance_tracker import SurveillanceTracker
        return SurveillanceTracker()

    def test_track_and_predict(self):
        st = self._make()
        for i in range(10):
            st.track("t1", (100 + i * 10, 200, 50), t=float(i))
        pred = st.predict("t1", horizon_s=30)
        assert pred is not None
        assert len(pred.predicted_positions) == 10
        assert pred.speed_estimate > 0

    def test_predict_insufficient_data(self):
        st = self._make()
        st.track("t1", (100, 200, 50), t=0.0)
        assert st.predict("t1") is None

    def test_intercept_point(self):
        st = self._make()
        for i in range(10):
            st.track("t1", (100 + i * 10, 200, 50), t=float(i))
        ip = st.intercept_point("t1", (0, 200, 50), interceptor_speed=20)
        assert ip is not None

    def test_active_tracks(self):
        st = self._make()
        st.track("t1", (100, 200, 50), t=0.0)
        st.track("t2", (300, 400, 50), t=0.0)
        assert set(st.active_tracks()) == {"t1", "t2"}

    def test_last_position(self):
        st = self._make()
        st.track("t1", (100, 200, 50), t=0.0)
        st.track("t1", (110, 200, 50), t=1.0)
        assert st.last_position("t1") == (110, 200, 50)

    def test_last_position_none(self):
        st = self._make()
        assert st.last_position("no_target") is None

    def test_remove_track(self):
        st = self._make()
        st.track("t1", (100, 200, 50), t=0.0)
        st.remove_track("t1")
        assert "t1" not in st.active_tracks()

    def test_max_history(self):
        st = self._make()
        for i in range(300):
            st.track("t1", (i, 0, 50), t=float(i))
        assert st.summary()["total_records"] <= 200

    def test_summary(self):
        st = self._make()
        st.track("t1", (100, 200, 50), t=0.0)
        s = st.summary()
        assert s["active_tracks"] == 1


# ──────────────────────────────────────────────
# Phase 73: 충전 인프라
# ──────────────────────────────────────────────
class TestPowerGrid:
    def _make(self):
        from simulation.power_grid import PowerGrid
        return PowerGrid()

    def test_add_station(self):
        pg = self._make()
        cs = pg.add_station("CS1", (0, 0), capacity=4)
        assert cs.station_id == "CS1"
        assert cs.capacity == 4

    def test_recommend_station(self):
        pg = self._make()
        pg.add_station("CS1", (0, 0))
        pg.add_station("CS2", (1000, 1000))
        best = pg.recommend_station("d1", (100, 100, 50))
        assert best == "CS1"

    def test_recommend_station_empty(self):
        pg = self._make()
        assert pg.recommend_station("d1", (100, 100, 50)) is None

    def test_request_charge(self):
        pg = self._make()
        pg.add_station("CS1", (0, 0), capacity=2)
        assert pg.request_charge("d1", "CS1") is True
        assert pg.total_occupied() == 1

    def test_request_charge_queue(self):
        pg = self._make()
        pg.add_station("CS1", (0, 0), capacity=1)
        pg.request_charge("d1", "CS1")
        pg.request_charge("d2", "CS1")  # goes to queue
        assert pg.total_occupied() == 1

    def test_complete_charge(self):
        pg = self._make()
        pg.add_station("CS1", (0, 0), capacity=2)
        pg.request_charge("d1", "CS1")
        ok = pg.complete_charge("d1", "CS1")
        assert ok is True
        assert pg.total_occupied() == 0

    def test_complete_promotes_from_queue(self):
        pg = self._make()
        pg.add_station("CS1", (0, 0), capacity=1)
        pg.request_charge("d1", "CS1")
        pg.request_charge("d2", "CS1")
        pg.complete_charge("d1", "CS1")
        assert pg.total_occupied() == 1  # d2 promoted

    def test_charge_time_estimate(self):
        pg = self._make()
        pg.add_station("CS1", (0, 0), capacity=2, charge_rate=2.0)
        t = pg.charge_time_estimate("CS1", current_pct=20, target_pct=90)
        assert t > 0  # (90-20)/2 = 35 min

    def test_station_utilization(self):
        pg = self._make()
        pg.add_station("CS1", (0, 0), capacity=4)
        pg.request_charge("d1", "CS1")
        pg.request_charge("d2", "CS1")
        assert pg.station_utilization("CS1") == 0.5

    def test_summary(self):
        pg = self._make()
        pg.add_station("CS1", (0, 0))
        s = pg.summary()
        assert s["total_stations"] == 1


# ──────────────────────────────────────────────
# Phase 74: 규제 보고서
# ──────────────────────────────────────────────
class TestRegulatoryReporter:
    def _make(self):
        from simulation.regulatory_reporter import RegulatoryReporter
        return RegulatoryReporter()

    def test_log_event(self):
        rr = self._make()
        rr.log_event("d1", "TAKEOFF", t=1.0)
        assert rr.summary()["total_events"] == 1

    def test_log_violation(self):
        rr = self._make()
        rr.log_event("d1", "NFZ_VIOLATION", t=5.0, compliant=False)
        assert rr.summary()["total_violations"] == 1

    def test_compliance_rate_perfect(self):
        rr = self._make()
        rr.log_event("d1", "TAKEOFF", t=1.0)
        rr.log_event("d1", "LAND", t=10.0)
        assert rr.compliance_rate() == 100.0

    def test_compliance_rate_with_violations(self):
        rr = self._make()
        rr.log_event("d1", "TAKEOFF", t=1.0)
        rr.log_event("d1", "NFZ_VIOLATION", t=5.0, compliant=False)
        assert rr.compliance_rate() == 50.0

    def test_compliance_rate_empty(self):
        rr = self._make()
        assert rr.compliance_rate() == 100.0

    def test_violations_by_drone(self):
        rr = self._make()
        rr.log_event("d1", "V1", t=1.0, compliant=False)
        rr.log_event("d1", "V2", t=2.0, compliant=False)
        rr.log_event("d2", "V1", t=3.0, compliant=False)
        by_drone = rr.violations_by_drone()
        assert by_drone["d1"] == 2
        assert by_drone["d2"] == 1

    def test_generate_compliance_report(self):
        rr = self._make()
        rr.log_event("d1", "TAKEOFF", t=1.0)
        rr.log_event("d1", "NFZ_VIOLATION", t=5.0, compliant=False, regulation="K-UTM-003")
        report = rr.generate_compliance_report()
        assert "준수율" in report
        assert "위반" in report

    def test_audit_trail(self):
        rr = self._make()
        rr.log_event("d1", "TAKEOFF", t=1.0)
        rr.log_event("d2", "TAKEOFF", t=2.0)
        trail = rr.audit_trail(drone_id="d1")
        assert len(trail) == 1

    def test_audit_trail_all(self):
        rr = self._make()
        for i in range(10):
            rr.log_event(f"d{i}", "E", t=float(i))
        trail = rr.audit_trail()
        assert len(trail) == 10

    def test_clear(self):
        rr = self._make()
        rr.log_event("d1", "E", t=1.0, compliant=False)
        rr.clear()
        assert rr.summary()["total_events"] == 0
        assert rr.summary()["total_violations"] == 0


# ──────────────────────────────────────────────
# Phase 75: 시나리오 생성기
# ──────────────────────────────────────────────
class TestScenarioGenerator:
    def _make(self):
        from simulation.scenario_generator import ScenarioGenerator
        return ScenarioGenerator(seed=42)

    def test_generate_random(self):
        sg = self._make()
        sc = sg.generate_random()
        assert sc.drone_count >= 10
        assert sc.duration_s >= 30
        assert sc.difficulty in ("EASY", "MEDIUM", "HARD", "EXTREME")

    def test_random_reproducible(self):
        from simulation.scenario_generator import ScenarioGenerator
        sg1 = ScenarioGenerator(seed=99)
        sg2 = ScenarioGenerator(seed=99)
        s1 = sg1.generate_random()
        s2 = sg2.generate_random()
        assert s1.drone_count == s2.drone_count
        assert s1.wind_speed_range == s2.wind_speed_range

    def test_generate_stress_test(self):
        sg = self._make()
        sc = sg.generate_stress_test(drones=300)
        assert sc.drone_count == 300
        assert sc.difficulty == "EXTREME"

    def test_generate_weather_extreme(self):
        sg = self._make()
        sc = sg.generate_weather_extreme()
        assert sc.wind_speed_range[1] >= 20.0
        assert "microburst" in sc.params

    def test_generate_batch(self):
        sg = self._make()
        batch = sg.generate_batch(n=5)
        assert len(batch) == 5
        names = [s.name for s in batch]
        assert len(set(names)) == 5

    def test_generate_progressive(self):
        sg = self._make()
        prog = sg.generate_progressive(levels=5)
        assert len(prog) == 5
        assert prog[0].drone_count < prog[-1].drone_count
        assert prog[0].difficulty == "EASY"
        assert prog[-1].difficulty == "EXTREME"

    def test_summary_counter(self):
        sg = self._make()
        sg.generate_random()
        sg.generate_random()
        s = sg.summary()
        assert s["scenarios_generated"] == 2

    def test_difficulty_estimation(self):
        sg = self._make()
        # Low difficulty
        d = sg._estimate_difficulty(10, 2.0, 0.0, 0)
        assert d in ("EASY", "MEDIUM")
        # High difficulty
        d = sg._estimate_difficulty(200, 20.0, 0.1, 5)
        assert d == "EXTREME"
