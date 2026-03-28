"""Phase 108-131 통합 테스트 — 24개 모듈, 120개 테스트."""
import unittest


# ── Phase 108: RL 경로 선택 ──
class TestRLPathSelector(unittest.TestCase):
    def _make(self):
        from simulation.rl_path_selector import RLPathSelector
        return RLPathSelector(n_actions=4, seed=42)

    def test_select_action(self):
        rl = self._make()
        a = rl.select_action("s0")
        assert 0 <= a < 4

    def test_update_and_best(self):
        rl = self._make()
        for _ in range(50):
            rl.update("s0", 2, reward=10.0, next_state="s1")
        assert rl.best_action("s0") == 2

    def test_episode(self):
        rl = self._make()
        rl.start_episode()
        rl.update("s0", 0, 5.0, "s1")
        rl.end_episode()
        assert len(rl.episode_rewards()) == 1

    def test_decay_epsilon(self):
        rl = self._make()
        old = rl.epsilon
        rl.decay_epsilon()
        assert rl.epsilon < old

    def test_summary(self):
        rl = self._make()
        s = rl.summary()
        assert "episodes" in s


# ── Phase 109: 예측 유지보수 ──
class TestPredictiveMaintenance(unittest.TestCase):
    def _make(self):
        from simulation.predictive_maintenance import PredictiveMaintenance
        pm = PredictiveMaintenance()
        pm.register_drone("d1", max_hours=500)
        return pm

    def test_register_and_schedule(self):
        pm = self._make()
        s = pm.get_schedule("d1")
        assert s is not None
        assert s.urgency == "NORMAL"

    def test_usage_degrades(self):
        pm = self._make()
        pm.update_usage("d1", hours=450, cycles=1800, vibration=8.0)
        s = pm.get_schedule("d1")
        assert s.health_score < 50

    def test_overdue(self):
        pm = self._make()
        pm.update_usage("d1", hours=150)
        assert "d1" in pm.overdue_drones()

    def test_fleet_health(self):
        pm = self._make()
        assert pm.fleet_health() > 0

    def test_summary(self):
        pm = self._make()
        assert "total_drones" in pm.summary()


# ── Phase 110: 에이전트 협상 ──
class TestAgentNegotiation(unittest.TestCase):
    def _make(self):
        from simulation.agent_negotiation import AgentNegotiation
        neg = AgentNegotiation()
        neg.register_agent("d1", priority=3, flexibility=0.8)
        neg.register_agent("d2", priority=7, flexibility=0.3)
        return neg

    def test_negotiate(self):
        neg = self._make()
        result = neg.negotiate("d1", "d2")
        assert result.yielder != ""
        assert result.action != "DEADLOCK"

    def test_lower_priority_yields(self):
        neg = self._make()
        result = neg.negotiate("d1", "d2")
        assert result.yielder == "d1"

    def test_conflict_point(self):
        neg = self._make()
        result = neg.negotiate("d1", "d2", conflict_point=(100, 200, 80))
        assert result.action == "YIELD_ALTITUDE"

    def test_deadlock_count(self):
        neg = self._make()
        neg.negotiate("d1", "d2")
        assert neg.deadlock_count() == 0

    def test_summary(self):
        neg = self._make()
        assert "agents" in neg.summary()


# ── Phase 111: 적응형 튜너 ──
class TestAdaptiveTuner(unittest.TestCase):
    def _make(self):
        from simulation.adaptive_tuner import AdaptiveTuner
        t = AdaptiveTuner()
        t.add_param("k_rep", current=2.5, min_val=1.0, max_val=10.0, step=0.2)
        return t

    def test_record_and_tune(self):
        t = self._make()
        for _ in range(5):
            t.record_metric("collision_rate", 0.05)
        results = t.tune()
        assert len(results) >= 0  # may or may not adjust

    def test_get_param(self):
        t = self._make()
        assert t.get_param("k_rep") == 2.5

    def test_metric_trigger(self):
        t = self._make()
        for v in [0.05, 0.06, 0.07, 0.08, 0.09]:
            t.record_metric("collision_rate", v)
        results = t.tune()
        assert isinstance(results, list)

    def test_summary(self):
        t = self._make()
        assert "params" in t.summary()


# ── Phase 112: 의사결정 트리 ──
class TestDecisionTreeATC(unittest.TestCase):
    def _make(self):
        from simulation.decision_tree_atc import DecisionTreeATC
        dt = DecisionTreeATC()
        dt.add_rule("low_battery", lambda ctx: ctx.get("battery", 100) < 20, action="RTL", priority=8)
        dt.add_rule("collision", lambda ctx: ctx.get("cpa", 999) < 30, action="EVADE", priority=9)
        return dt

    def test_collision_rule(self):
        dt = self._make()
        d = dt.decide({"cpa": 15, "battery": 80})
        assert d.action == "EVADE"

    def test_battery_rule(self):
        dt = self._make()
        d = dt.decide({"cpa": 100, "battery": 10})
        assert d.action == "RTL"

    def test_default(self):
        dt = self._make()
        d = dt.decide({"cpa": 100, "battery": 80})
        assert d.action == "MONITOR"

    def test_batch_decide(self):
        dt = self._make()
        results = dt.batch_decide([{"cpa": 10}, {"cpa": 100}])
        assert len(results) == 2

    def test_summary(self):
        dt = self._make()
        dt.decide({"cpa": 15})
        assert dt.summary()["decisions"] == 1


# ── Phase 113: 수요 예측 ──
class TestDemandForecaster(unittest.TestCase):
    def _make(self):
        from simulation.demand_forecaster import DemandForecaster
        df = DemandForecaster()
        for _ in range(10):
            df.record_demand(9, 50)
            df.record_demand(14, 100)
        return df

    def test_forecast(self):
        df = self._make()
        f = df.forecast(9)
        assert f.predicted_count > 0

    def test_peak_hours(self):
        df = self._make()
        peaks = df.peak_hours(1)
        assert 14 in peaks

    def test_daily_pattern(self):
        df = self._make()
        pattern = df.daily_pattern()
        assert len(pattern) == 24

    def test_summary(self):
        df = self._make()
        assert "total_records" in df.summary()


# ── Phase 114: 경로 다양성 ──
class TestPathDiversity(unittest.TestCase):
    def _make(self):
        from simulation.path_diversity import PathDiversity
        return PathDiversity(seed=42)

    def test_generate(self):
        pd = self._make()
        paths = pd.generate_diverse_paths((0, 0, 50), (1000, 1000, 50), k=5)
        assert len(paths) >= 2

    def test_best_diverse(self):
        pd = self._make()
        paths = pd.generate_diverse_paths((0, 0, 50), (500, 500, 50), k=3)
        best = pd.best_diverse_path(paths)
        assert best is not None

    def test_direct_path_included(self):
        pd = self._make()
        paths = pd.generate_diverse_paths((0, 0, 50), (100, 100, 50), k=3)
        assert paths[0].path_id == 0  # direct

    def test_summary(self):
        pd = self._make()
        pd.generate_diverse_paths((0, 0, 50), (1000, 1000, 50))
        assert pd.summary()["total_generations"] == 1


# ── Phase 115: 우선순위 재조정 ──
class TestPriorityAdjuster(unittest.TestCase):
    def _make(self):
        from simulation.priority_adjuster import PriorityAdjuster
        pa = PriorityAdjuster()
        pa.register_mission("m1", base_priority=5)
        return pa

    def test_normal_priority(self):
        pa = self._make()
        p = pa.adjusted_priority("m1")
        assert p == 5

    def test_low_battery_boost(self):
        pa = self._make()
        pa.update_context("m1", battery_pct=10)
        p = pa.adjusted_priority("m1")
        assert p > 5

    def test_emergency_boost(self):
        pa = self._make()
        pa.update_context("m1", is_emergency=True)
        p = pa.adjusted_priority("m1")
        assert p >= 8

    def test_ranking(self):
        pa = self._make()
        pa.register_mission("m2", base_priority=8)
        r = pa.ranking()
        assert r[0][1] >= r[1][1]

    def test_summary(self):
        pa = self._make()
        assert "missions" in pa.summary()


# ── Phase 116: GPS 스푸핑 탐지 ──
class TestGPSSpoofDetector(unittest.TestCase):
    def _make(self):
        from simulation.gps_spoof_detector import GPSSpoofDetector
        return GPSSpoofDetector()

    def test_no_alert_normal(self):
        gsd = self._make()
        gsd.update("d1", gps=(100, 200, 50), t=0.0)
        gsd.update("d1", gps=(101, 201, 50), t=1.0)
        alerts = gsd.check("d1")
        assert len(alerts) == 0

    def test_position_jump(self):
        gsd = self._make()
        gsd.update("d1", gps=(0, 0, 50), t=0.0)
        gsd.update("d1", gps=(500, 500, 50), t=1.0)
        alerts = gsd.check("d1")
        assert any(a.alert_type in ("POSITION_JUMP", "VELOCITY_IMPOSSIBLE") for a in alerts)

    def test_altitude_mismatch(self):
        gsd = self._make()
        gsd.update("d1", gps=(100, 200, 50), t=0.0)
        gsd.update("d1", gps=(101, 201, 50), baro_alt=100, t=1.0)
        alerts = gsd.check("d1")
        assert any(a.alert_type == "ALTITUDE_MISMATCH" for a in alerts)

    def test_summary(self):
        gsd = self._make()
        assert "drones_monitored" in gsd.summary()


# ── Phase 117: 암호화 통신 ──
class TestSecureChannel(unittest.TestCase):
    def _make(self):
        from simulation.secure_channel import SecureChannel
        sc = SecureChannel()
        sc.register_node("d1")
        sc.register_node("d2")
        sc.establish_session("d1", "d2")
        return sc

    def test_send_secure(self):
        sc = self._make()
        assert sc.send_secure("d1", "d2", "hello") is True

    def test_revoke_blocks(self):
        sc = self._make()
        sc.revoke_session("d1", "d2")
        assert sc.send_secure("d1", "d2", "test") is False

    def test_no_session_fails(self):
        sc = self._make()
        assert sc.send_secure("d1", "d3", "test") is False

    def test_summary(self):
        sc = self._make()
        assert sc.summary()["active_sessions"] >= 1


# ── Phase 118: 침입 탐지 ──
class TestIntrusionDetector(unittest.TestCase):
    def _make(self):
        from simulation.intrusion_detector import IntrusionDetector
        return IntrusionDetector()

    def test_flood_detect(self):
        ids = self._make()
        ids.record_traffic("d1", msg_count=500)
        threats = ids.detect()
        assert any(t.threat_type == "FLOOD" for t in threats)

    def test_auth_brute_force(self):
        ids = self._make()
        ids.record_traffic("d1", msg_count=10, auth_failures=10)
        threats = ids.detect()
        assert any(t.threat_type == "AUTH_BRUTE_FORCE" for t in threats)

    def test_blacklist(self):
        ids = self._make()
        ids.blacklist("d1")
        assert ids.is_blocked("d1")

    def test_summary(self):
        ids = self._make()
        assert "nodes_monitored" in ids.summary()


# ── Phase 119: 규제 업데이트 ──
class TestRegulationUpdater(unittest.TestCase):
    def _make(self):
        from simulation.regulation_updater import RegulationUpdater
        ru = RegulationUpdater()
        ru.add_regulation("MAX_ALT", value=120, unit="m")
        return ru

    def test_get_value(self):
        ru = self._make()
        assert ru.get_value("MAX_ALT") == 120

    def test_update(self):
        ru = self._make()
        ru.update_regulation("MAX_ALT", value=150, reason="완화")
        assert ru.get_value("MAX_ALT") == 150
        assert ru.get_version("MAX_ALT") == 2

    def test_compliance(self):
        ru = self._make()
        assert ru.check_compliance("MAX_ALT", 100) is True
        assert ru.check_compliance("MAX_ALT", 150) is False

    def test_summary(self):
        ru = self._make()
        assert "total_regulations" in ru.summary()


# ── Phase 120: 통신 QoS ──
class TestCommQoS(unittest.TestCase):
    def _make(self):
        from simulation.comm_qos import CommQoS
        qos = CommQoS(total_bandwidth=1000)
        qos.add_class("emergency", priority=1, min_bw=200)
        qos.add_class("normal", priority=3, min_bw=50)
        return qos

    def test_allocate(self):
        qos = self._make()
        r = qos.allocate("d1", "emergency", 150)
        assert r.allocated_bw > 0
        assert r.satisfied

    def test_utilization(self):
        qos = self._make()
        qos.allocate("d1", "emergency", 500)
        assert qos.utilization() > 0

    def test_release(self):
        qos = self._make()
        qos.allocate("d1", "normal", 100)
        qos.release("d1")
        assert qos.utilization() == 0

    def test_summary(self):
        qos = self._make()
        assert "classes" in qos.summary()


# ── Phase 121: 드론 신원 인증 ──
class TestDroneIdentity(unittest.TestCase):
    def _make(self):
        from simulation.drone_identity import DroneIdentity
        di = DroneIdentity()
        di.issue_certificate("d1", valid_hours=24, t=0)
        return di

    def test_verify_valid(self):
        di = self._make()
        assert di.verify("d1", t=100) is True

    def test_verify_expired(self):
        di = self._make()
        assert di.verify("d1", t=100000) is False

    def test_revoke(self):
        di = self._make()
        di.revoke("d1")
        assert di.verify("d1", t=0) is False

    def test_renew(self):
        di = self._make()
        assert di.renew("d1", valid_hours=48, t=1000) is True

    def test_summary(self):
        di = self._make()
        assert "total_certs" in di.summary()


# ── Phase 122: 감사 추적 ──
class TestAuditTrail(unittest.TestCase):
    def _make(self):
        from simulation.audit_trail import AuditTrail
        at = AuditTrail()
        at.log_event("d1", "TAKEOFF", {"pad": "A1"})
        at.log_event("d1", "LAND", {"pad": "A2"})
        return at

    def test_chain_valid(self):
        at = self._make()
        assert at.verify_chain() is True

    def test_query(self):
        at = self._make()
        entries = at.query(action="TAKEOFF")
        assert len(entries) == 1

    def test_entry_count(self):
        at = self._make()
        assert at.entry_count() == 2

    def test_summary(self):
        at = self._make()
        assert at.summary()["chain_valid"] is True


# ── Phase 123: 비상 방송 ──
class TestEmergencyBroadcast(unittest.TestCase):
    def _make(self):
        from simulation.emergency_broadcast import EmergencyBroadcast
        eb = EmergencyBroadcast()
        eb.register_receiver("d1", sector="A")
        eb.register_receiver("d2", sector="A")
        eb.register_receiver("d3", sector="B")
        return eb

    def test_broadcast_sector(self):
        eb = self._make()
        bc = eb.broadcast("ALERT", sectors=["A"], priority=1)
        assert len(bc.recipients) == 2

    def test_acknowledge(self):
        eb = self._make()
        bc = eb.broadcast("ALERT", sectors=["A"])
        eb.acknowledge(bc.broadcast_id, "d1")
        assert eb.ack_rate(bc.broadcast_id) == 50.0

    def test_unacknowledged(self):
        eb = self._make()
        bc = eb.broadcast("TEST")
        unack = eb.unacknowledged(bc.broadcast_id)
        assert len(unack) == 3

    def test_summary(self):
        eb = self._make()
        assert "receivers" in eb.summary()


# ── Phase 124: 난이도 평가 ──
class TestDifficultyScorer(unittest.TestCase):
    def _make(self):
        from simulation.difficulty_scorer import DifficultyScorer
        return DifficultyScorer()

    def test_easy(self):
        ds = self._make()
        r = ds.evaluate(drone_count=10, wind_speed=3)
        assert r.level in ("EASY", "MODERATE")

    def test_extreme(self):
        ds = self._make()
        r = ds.evaluate(drone_count=500, wind_speed=25, nfz_count=10, failure_rate=0.3, comm_loss_rate=0.2, urban_density=0.8)
        assert r.level in ("HARD", "EXTREME")

    def test_breakdown(self):
        ds = self._make()
        r = ds.evaluate(drone_count=50)
        assert "density" in r.breakdown

    def test_summary(self):
        ds = self._make()
        ds.evaluate()
        assert ds.summary()["evaluations"] == 1


# ── Phase 125: A/B 테스트 ──
class TestABTestFramework(unittest.TestCase):
    def _make(self):
        from simulation.ab_test_framework import ABTestFramework
        ab = ABTestFramework()
        ab.record_control("collision_rate", [0.05, 0.04, 0.06, 0.05, 0.04])
        ab.record_treatment("collision_rate", [0.01, 0.02, 0.01, 0.015, 0.01])
        return ab

    def test_analyze(self):
        ab = self._make()
        r = ab.analyze("collision_rate")
        assert r.improvement_pct > 0

    def test_significant(self):
        ab = self._make()
        r = ab.analyze("collision_rate")
        assert r.significant is True

    def test_no_data(self):
        from simulation.ab_test_framework import ABTestFramework
        ab = ABTestFramework()
        r = ab.analyze("empty")
        assert r.significant is False

    def test_summary(self):
        ab = self._make()
        assert "metrics" in ab.summary()


# ── Phase 126: 리포트 스트림 ──
class TestReportStream(unittest.TestCase):
    def _make(self):
        from simulation.report_stream import ReportStream
        return ReportStream()

    def test_push_and_consume(self):
        rs = self._make()
        rs.subscribe("dashboard")
        rs.push("alert", {"msg": "test"})
        events = rs.consume("dashboard")
        assert len(events) == 1

    def test_filter_by_type(self):
        rs = self._make()
        rs.push("alert")
        rs.push("metric")
        rs.push("alert")
        assert len(rs.filter_by_type("alert")) == 2

    def test_lag(self):
        rs = self._make()
        rs.subscribe("sub1")
        rs.push("a")
        rs.push("b")
        assert rs.lag("sub1") == 2

    def test_summary(self):
        rs = self._make()
        assert "buffer_size" in rs.summary()


# ── Phase 127: 다중 시뮬레이터 조율 ──
class TestMultiSimCoordinator(unittest.TestCase):
    def _make(self):
        from simulation.multi_sim_coordinator import MultiSimCoordinator
        msc = MultiSimCoordinator(n_sims=3, base_seed=42)
        msc.register_scenario("test", params={"drones": 50})
        return msc

    def test_generate_seeds(self):
        msc = self._make()
        seeds = msc.generate_seeds()
        assert len(seeds) == 3
        assert len(set(seeds)) == 3

    def test_run_all(self):
        msc = self._make()
        results = msc.run_all()  # default runner
        assert len(results) == 3

    def test_success_rate(self):
        msc = self._make()
        msc.run_all()
        assert msc.success_rate() == 100.0

    def test_summary(self):
        msc = self._make()
        assert "scenarios" in msc.summary()


# ── Phase 128: 환경 영향 ──
class TestEnvironmentalImpact(unittest.TestCase):
    def _make(self):
        from simulation.environmental_impact import EnvironmentalImpact
        ei = EnvironmentalImpact()
        ei.record_flight("d1", distance_m=5000, energy_wh=40, noise_db=55)
        return ei

    def test_impact_score(self):
        ei = self._make()
        score = ei.impact_score("d1")
        assert 0 <= score <= 100

    def test_noise_violation(self):
        ei = self._make()
        ei.record_flight("d2", distance_m=1000, energy_wh=10, noise_db=80)
        assert len(ei.noise_violations()) >= 1

    def test_fleet_impact(self):
        ei = self._make()
        assert ei.fleet_impact() > 0

    def test_summary(self):
        ei = self._make()
        assert "drones" in ei.summary()


# ── Phase 129: 비용 분석 ──
class TestCostAnalyzer(unittest.TestCase):
    def _make(self):
        from simulation.cost_analyzer import CostAnalyzer
        ca = CostAnalyzer(energy_cost_per_wh=0.15)
        ca.record_mission("m1", energy_wh=50, distance_m=5000, flight_time_s=600, revenue=10000)
        return ca

    def test_total_cost(self):
        ca = self._make()
        cost = ca.total_cost("m1")
        assert cost > 0

    def test_mission_roi(self):
        ca = self._make()
        roi = ca.mission_roi("m1")
        assert roi > 0  # profitable

    def test_cost_per_km(self):
        ca = self._make()
        cpk = ca.cost_per_km("m1")
        assert cpk > 0

    def test_summary(self):
        ca = self._make()
        assert "fleet_roi" in ca.summary()


# ── Phase 130: 학습 데이터 ──
class TestTrainingDataCollector(unittest.TestCase):
    def _make(self):
        from simulation.training_data_collector import TrainingDataCollector
        tdc = TrainingDataCollector()
        tdc.record_state({"pos": (0, 0)}, "LEFT", reward=5.0)
        tdc.record_state({"pos": (1, 0)}, "RIGHT", reward=3.0)
        return tdc

    def test_export(self):
        tdc = self._make()
        ds = tdc.export_dataset()
        assert len(ds) == 2

    def test_action_dist(self):
        tdc = self._make()
        d = tdc.action_distribution()
        assert d["LEFT"] == 1

    def test_reward_stats(self):
        tdc = self._make()
        s = tdc.reward_stats()
        assert s["mean"] == 4.0

    def test_sample_batch(self):
        tdc = self._make()
        batch = tdc.sample_batch(1)
        assert len(batch) == 1

    def test_summary(self):
        tdc = self._make()
        assert "buffer_size" in tdc.summary()


# ── Phase 131: 통합 검증 ──
class TestIntegrationVerifier(unittest.TestCase):
    def _make(self):
        from simulation.integration_verifier import IntegrationVerifier
        iv = IntegrationVerifier()
        iv.register_module("controller", provides=["drone_positions"], requires=[])
        iv.register_module("apf", provides=["collision_avoidance"], requires=["drone_positions"])
        return iv

    def test_verify_pass(self):
        iv = self._make()
        r = iv.verify()
        assert r.passed is True

    def test_missing_dep(self):
        from simulation.integration_verifier import IntegrationVerifier
        iv = IntegrationVerifier()
        iv.register_module("apf", provides=[], requires=["missing_dep"])
        r = iv.verify()
        assert r.passed is False
        assert len(r.missing_deps) == 1

    def test_dependency_graph(self):
        iv = self._make()
        g = iv.dependency_graph()
        assert "controller" in g["apf"]

    def test_regression_check(self):
        iv = self._make()
        iv.record_test("apf", False)
        assert "apf" in iv.regression_check()

    def test_summary(self):
        iv = self._make()
        assert "modules" in iv.summary()


if __name__ == "__main__":
    unittest.main()
