"""
Phase 92-107 테스트
- 리더 선출, 공역 예측, 임무 체인, 장애 전파, 고도 관리,
  비행 로그, 충전 최적화, 드론 페어링, 비행 계획 검증,
  대시보드, 배치 시뮬, 공역 이력, 성능 프로필, 임무 평가,
  접근 제어, 시스템 건강
"""
import pytest
import numpy as np


# ── Phase 92: 리더 선출 ──
class TestLeaderElection:
    def _make(self):
        from simulation.leader_election import LeaderElection
        return LeaderElection()

    def test_elect(self):
        le = self._make()
        le.add_candidate("d1", score=0.9)
        le.add_candidate("d2", score=0.5)
        assert le.elect() == "d1"

    def test_failover(self):
        le = self._make()
        le.add_candidate("d1", score=0.9)
        le.add_candidate("d2", score=0.7)
        le.elect()
        leader = le.failover()
        assert leader == "d2"

    def test_battery_weight(self):
        le = self._make()
        le.add_candidate("d1", score=0.9, battery_pct=10)
        le.add_candidate("d2", score=0.7, battery_pct=90)
        assert le.elect() == "d2"

    def test_is_leader(self):
        le = self._make()
        le.add_candidate("d1", score=0.9)
        le.elect()
        assert le.is_leader("d1")
        assert not le.is_leader("d2")

    def test_summary(self):
        le = self._make()
        le.add_candidate("d1", score=0.5)
        le.elect()
        s = le.summary()
        assert s["current_leader"] == "d1"


# ── Phase 93: 공역 예측 ──
class TestAirspacePredictor:
    def _make(self):
        from simulation.airspace_predictor import AirspacePredictor
        return AirspacePredictor(sectors=4)

    def test_record_predict(self):
        ap = self._make()
        for i in range(10):
            ap.record(0, 5 + i, float(i))
        pred = ap.predict(0)
        assert pred.predicted_density > 10

    def test_trend_increasing(self):
        ap = self._make()
        for i in range(10):
            ap.record(0, i * 3, float(i))
        pred = ap.predict(0)
        assert pred.trend == "INCREASING"

    def test_congested_sectors(self):
        ap = self._make()
        for i in range(10):
            ap.record(0, 20, float(i))
        assert 0 in ap.congested_sectors()

    def test_summary(self):
        ap = self._make()
        ap.record(0, 5, 1.0)
        s = ap.summary()
        assert s["sectors"] == 4


# ── Phase 94: 임무 체인 ──
class TestMissionChain:
    def _make(self):
        from simulation.mission_chain import MissionChain
        return MissionChain()

    def test_add_and_start(self):
        mc = self._make()
        mc.add_task("A", drone="d1")
        assert mc.start("A") is True

    def test_dependency(self):
        mc = self._make()
        mc.add_task("A")
        mc.add_task("B", depends_on=["A"])
        assert mc.start("B") is False  # A not completed
        mc.start("A")
        mc.complete("A")
        assert mc.start("B") is True

    def test_progress(self):
        mc = self._make()
        mc.add_task("A")
        mc.add_task("B")
        mc.start("A")
        mc.complete("A")
        assert mc.progress_pct() == 50.0

    def test_critical_path(self):
        mc = self._make()
        mc.add_task("A")
        mc.add_task("B", depends_on=["A"])
        mc.add_task("C", depends_on=["B"])
        path = mc.critical_path()
        assert len(path) == 3

    def test_summary(self):
        mc = self._make()
        mc.add_task("A")
        s = mc.summary()
        assert s["total_tasks"] == 1


# ── Phase 95: 장애 전파 ──
class TestFailurePropagation:
    def _make(self):
        from simulation.failure_propagation import FailurePropagation
        return FailurePropagation()

    def test_propagate(self):
        fp = self._make()
        fp.add_dependency("d1", "d2")
        fp.add_dependency("d2", "d3")
        result = fp.propagate("d1")
        assert "d2" in result.affected_nodes
        assert "d3" in result.affected_nodes

    def test_isolation(self):
        fp = self._make()
        fp.add_dependency("d1", "d2")
        fp.add_dependency("d1", "d3")
        result = fp.propagate("d1")
        assert len(result.isolation_candidates) == 2

    def test_no_propagation(self):
        fp = self._make()
        fp.add_node("d1")
        fp.add_node("d2")
        result = fp.propagate("d1")
        assert len(result.affected_nodes) == 0

    def test_summary(self):
        fp = self._make()
        fp.add_dependency("a", "b")
        s = fp.summary()
        assert s["nodes"] == 2


# ── Phase 96: 고도 관리 ──
class TestAltitudeManager:
    def _make(self):
        from simulation.altitude_manager import AltitudeManager
        return AltitudeManager()

    def test_assign_altitude(self):
        am = self._make()
        a = am.assign_altitude("d1", heading_deg=90)
        assert 30 <= a.altitude_m <= 120
        assert a.heading_band == "E"

    def test_direction_separation(self):
        am = self._make()
        a1 = am.assign_altitude("d1", heading_deg=0)   # N
        a2 = am.assign_altitude("d2", heading_deg=180)  # S
        assert a1.altitude_m != a2.altitude_m

    def test_vertical_separation(self):
        am = self._make()
        am.assign_altitude("d1", heading_deg=0, priority=1)
        am.assign_altitude("d2", heading_deg=0, priority=2)
        assert am.vertical_separation_ok("d1", "d2")

    def test_release(self):
        am = self._make()
        am.assign_altitude("d1", heading_deg=0)
        assert am.release("d1") is True

    def test_summary(self):
        am = self._make()
        am.assign_altitude("d1", heading_deg=45)
        s = am.summary()
        assert s["total_assigned"] == 1


# ── Phase 97: 비행 로그 ──
class TestFlightLogAnalyzer:
    def _make(self):
        from simulation.flight_log_analyzer import FlightLogAnalyzer
        return FlightLogAnalyzer()

    def test_add_and_stats(self):
        fla = self._make()
        fla.add_entry("d1", duration_s=300, distance_m=2000, energy_wh=20)
        stats = fla.drone_stats("d1")
        assert stats.total_flights == 1
        assert stats.total_distance_m == 2000

    def test_fleet_kpi(self):
        fla = self._make()
        fla.add_entry("d1", 300, 2000, 20)
        fla.add_entry("d2", 600, 4000, 40)
        kpi = fla.fleet_kpi()
        assert kpi["total_flights"] == 2

    def test_anomaly_detection(self):
        fla = self._make()
        for i in range(10):
            fla.add_entry(f"d{i}", 300, 2000, 20)
        fla.add_entry("d_bad", 300, 100, 200)  # very inefficient
        anomalies = fla.detect_anomalies()
        assert len(anomalies) >= 1

    def test_summary(self):
        fla = self._make()
        fla.add_entry("d1", 300, 2000, 20)
        s = fla.summary()
        assert s["unique_drones"] == 1


# ── Phase 98: 충전 최적화 ──
class TestChargeOptimizer:
    def _make(self):
        from simulation.charge_optimizer import ChargeOptimizer
        return ChargeOptimizer()

    def test_optimize(self):
        co = self._make()
        co.add_station("CS1", (0, 0), capacity=4)
        co.add_station("CS2", (1000, 1000), capacity=4)
        plan = co.optimize_charge("d1", (100, 100, 50), battery_pct=15)
        assert plan is not None
        assert plan.station_id == "CS1"  # closer

    def test_empty_stations(self):
        co = self._make()
        assert co.optimize_charge("d1", (100, 100, 50)) is None

    def test_batch_optimize(self):
        co = self._make()
        co.add_station("CS1", (0, 0), capacity=2)
        drones = {"d1": ((100, 100, 50), 10.0), "d2": ((200, 200, 50), 15.0)}
        plans = co.batch_optimize(drones)
        assert len(plans) == 2

    def test_summary(self):
        co = self._make()
        co.add_station("CS1", (0, 0))
        s = co.summary()
        assert s["stations"] == 1


# ── Phase 99: 드론 페어링 ──
class TestDronePairing:
    def _make(self):
        from simulation.drone_pairing import DronePairing
        return DronePairing()

    def test_pair_and_partner(self):
        dp = self._make()
        dp.pair("d1", "d2", mode="ESCORT")
        assert dp.get_partner("d1") == "d2"
        assert dp.get_partner("d2") == "d1"

    def test_unpair(self):
        dp = self._make()
        info = dp.pair("d1", "d2")
        dp.unpair(info.pair_id)
        assert dp.get_partner("d1") is None

    def test_distance_warning(self):
        from simulation.drone_pairing import DronePairing
        dp = DronePairing(max_pair_distance=100)
        dp.pair("d1", "d2")
        warnings = dp.update_positions({"d1": (0, 0, 50), "d2": (500, 500, 50)})
        assert len(warnings) >= 1

    def test_suggest_pair(self):
        dp = self._make()
        positions = {"d1": (0, 0, 50), "d2": (10, 10, 50), "d3": (1000, 1000, 50)}
        pair = dp.suggest_pair(positions)
        assert pair == ("d1", "d2")

    def test_summary(self):
        dp = self._make()
        dp.pair("d1", "d2")
        s = dp.summary()
        assert s["active_pairs"] == 1


# ── Phase 100: 비행 계획 검증 ──
class TestFlightPlanValidator:
    def _make(self):
        from simulation.flight_plan_validator import FlightPlanValidator
        return FlightPlanValidator()

    def test_valid_plan(self):
        fpv = self._make()
        wps = [(100, 100, 50), (200, 200, 50), (300, 300, 50)]
        result = fpv.validate(wps)
        assert result.valid is True

    def test_altitude_violation(self):
        fpv = self._make()
        wps = [(100, 100, 200)]  # too high
        result = fpv.validate(wps)
        assert not result.valid
        assert any(i.issue_type == "ALTITUDE" for i in result.issues)

    def test_nfz_violation(self):
        fpv = self._make()
        fpv.add_nfz("NFZ1", (500, 500), 100)
        wps = [(500, 500, 50)]
        result = fpv.validate(wps)
        assert not result.valid

    def test_quick_check(self):
        fpv = self._make()
        assert fpv.quick_check([(100, 100, 50)]) is True

    def test_summary(self):
        fpv = self._make()
        fpv.add_nfz("N1", (0, 0), 50)
        s = fpv.summary()
        assert s["nfz_count"] == 1


# ── Phase 101: 대시보드 데이터 ──
class TestDashboardData:
    def _make(self):
        from simulation.dashboard_data import DashboardData
        return DashboardData()

    def test_update_kpi(self):
        dd = self._make()
        dd.update_kpi("collision_rate", 0.02, t=1.0)
        snap = dd.snapshot()
        assert snap["kpis"]["collision_rate"] == 0.02

    def test_alerts(self):
        dd = self._make()
        dd.add_alert("CRITICAL", "충돌 감지", t=5.0)
        alerts = dd.recent_alerts()
        assert len(alerts) == 1
        assert alerts[0].level == "CRITICAL"

    def test_kpi_trend(self):
        dd = self._make()
        for i in range(5):
            dd.update_kpi("speed", float(i), t=float(i))
        trend = dd.kpi_trend("speed")
        assert len(trend) == 5

    def test_summary(self):
        dd = self._make()
        dd.set_counts(drones=50, missions=10)
        s = dd.summary()
        assert s["drone_count"] == 50


# ── Phase 102: 배치 시뮬레이터 ──
class TestBatchSimulator:
    def _make(self):
        from simulation.batch_simulator import BatchSimulator
        return BatchSimulator()

    def test_run_all(self):
        bs = self._make()
        bs.add_scenario("sc1", {"n": 10})
        bs.add_scenario("sc2", {"n": 20})
        results = bs.run_all(lambda p: {"score": p.get("n", 0) * 10})
        assert len(results) == 2
        assert results["sc1"].metrics["score"] == 100

    def test_compare(self):
        bs = self._make()
        bs.add_scenario("a", {"n": 5})
        bs.add_scenario("b", {"n": 10})
        bs.run_all(lambda p: {"val": p["n"]})
        comp = bs.compare("val")
        assert comp["a"] == 5
        assert comp["b"] == 10

    def test_statistics(self):
        bs = self._make()
        bs.add_scenario("a", {"n": 5})
        bs.add_scenario("b", {"n": 15})
        bs.run_all(lambda p: {"val": float(p["n"])})
        stats = bs.statistics("val")
        assert stats["mean"] == 10.0

    def test_summary(self):
        bs = self._make()
        bs.add_scenario("a", {})
        s = bs.summary()
        assert s["scenarios"] == 1


# ── Phase 103: 공역 이력 ──
class TestAirspaceHistory:
    def _make(self):
        from simulation.airspace_history import AirspaceHistory
        return AirspaceHistory()

    def test_record_query(self):
        ah = self._make()
        ah.record(t=1.0, drone_count=50)
        ah.record(t=2.0, drone_count=55)
        result = ah.query(t_start=1.5)
        assert len(result) == 1

    def test_trend(self):
        ah = self._make()
        for i in range(10):
            ah.record(t=float(i), drone_count=10 + i * 5)
        assert ah.trend("drone_count") == "INCREASING"

    def test_collision_rate(self):
        ah = self._make()
        ah.record(t=1.0, conflicts=10, collisions=1)
        rate = ah.collision_rate()
        assert rate > 0

    def test_summary(self):
        ah = self._make()
        ah.record(t=1.0)
        s = ah.summary()
        assert s["total_records"] == 1


# ── Phase 104: 성능 프로필 ──
class TestPerformanceProfile:
    def _make(self):
        from simulation.performance_profile import PerformanceProfile
        return PerformanceProfile()

    def test_add_profile(self):
        pp = self._make()
        p = pp.add_profile("d1", "COMMERCIAL", max_speed=15)
        assert p.max_speed_ms == 15

    def test_degradation(self):
        pp = self._make()
        pp.add_profile("d1", max_speed=15)
        for i in range(10):
            pp.record_performance("d1", speed=10, vibration=5)
        deg = pp.degradation("d1")
        assert deg > 0

    def test_compare(self):
        pp = self._make()
        pp.add_profile("d1", max_speed=15, battery=80)
        pp.add_profile("d2", max_speed=20, battery=100)
        comp = pp.compare("d1", "d2")
        assert comp["speed_ratio"] < 1

    def test_summary(self):
        pp = self._make()
        pp.add_profile("d1")
        s = pp.summary()
        assert s["total_profiles"] == 1


# ── Phase 105: 임무 평가 ──
class TestMissionEvaluator:
    def _make(self):
        from simulation.mission_evaluator import MissionEvaluator
        return MissionEvaluator()

    def test_evaluate_success(self):
        me = self._make()
        me.record_mission("m1", success=True, duration_s=300, distance_m=2000)
        result = me.evaluate("m1")
        assert result.grade == "A"
        assert result.score >= 90

    def test_evaluate_failure(self):
        me = self._make()
        me.record_mission("m1", success=False, duration_s=300, distance_m=2000)
        result = me.evaluate("m1")
        assert result.score < 70

    def test_success_rate(self):
        me = self._make()
        me.record_mission("m1", success=True, duration_s=100, distance_m=500)
        me.record_mission("m2", success=False, duration_s=100, distance_m=500)
        assert me.success_rate() == 50.0

    def test_summary(self):
        me = self._make()
        me.record_mission("m1", success=True, duration_s=100, distance_m=500)
        s = me.summary()
        assert s["total_missions"] == 1


# ── Phase 106: 접근 제어 ──
class TestAccessControl:
    def _make(self):
        from simulation.access_control import AccessControl
        return AccessControl()

    def test_role_check(self):
        ac = self._make()
        ac.add_role("PILOT", ["FLY", "LAND"])
        ac.assign_role("u1", "PILOT")
        assert ac.check("u1", "FLY") is True
        assert ac.check("u1", "ADMIN") is False

    def test_unassigned_denied(self):
        ac = self._make()
        assert ac.check("unknown", "FLY") is False

    def test_revoke(self):
        ac = self._make()
        ac.add_role("PILOT", ["FLY"])
        ac.assign_role("u1", "PILOT")
        ac.revoke_role("u1")
        assert ac.check("u1", "FLY") is False

    def test_audit_log(self):
        ac = self._make()
        ac.add_role("PILOT", ["FLY"])
        ac.assign_role("u1", "PILOT")
        ac.check("u1", "FLY")
        ac.check("u1", "ADMIN")
        log = ac.audit_log("u1")
        assert len(log) == 2

    def test_summary(self):
        ac = self._make()
        ac.add_role("ADMIN", ["ALL"])
        s = ac.summary()
        assert s["roles"] == 1


# ── Phase 107: 시스템 건강 ──
class TestSystemHealth:
    def _make(self):
        from simulation.system_health import SystemHealth
        return SystemHealth()

    def test_healthy(self):
        sh = self._make()
        sh.update("cpu_usage", 30)
        sh.update("memory_pct", 40)
        assert sh.is_healthy()

    def test_warning(self):
        sh = self._make()
        sh.update("cpu_usage", 80)
        assert sh.overall_status() == "WARNING"

    def test_critical(self):
        sh = self._make()
        sh.update("cpu_usage", 95)
        assert sh.overall_status() == "CRITICAL"

    def test_battery_reverse(self):
        sh = self._make()
        sh.update("battery_min_pct", 5)
        check = sh.check("battery_min_pct")
        assert check.status == "CRITICAL"

    def test_diagnose(self):
        sh = self._make()
        sh.update("cpu_usage", 50)
        sh.update("memory_pct", 85)
        checks = sh.diagnose()
        assert len(checks) == 2

    def test_summary(self):
        sh = self._make()
        sh.update("cpu_usage", 30)
        s = sh.summary()
        assert s["overall"] == "OK"
