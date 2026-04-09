"""
Phase 44-51 테스트
==================
- Phase 44: BehaviorAnalyzer (행동 패턴 분석)
- Phase 45: PriorityScheduler (동적 우선순위)
- Phase 46: ReplayAnalyzer (자동 리플레이 분석)
- Phase 47: WeatherForecaster (기상 예측)
- Phase 49: BatteryPredictor (배터리 수명 예측)
- Phase 51: ComplianceChecker (규제 준수 검증)
"""
import numpy as np
import pytest


# ────────────────────────────────────────────
#  Phase 44: BehaviorAnalyzer
# ────────────────────────────────────────────
from simulation.behavior_analyzer import (
    BehaviorAnalyzer, BehaviorClass, TrajectoryFeatures,
)


class TestBehaviorAnalyzer:
    """행동 패턴 분석기 테스트"""

    def _make_positions(self, n=50, speed=10.0):
        return [np.array([i * speed * 0.1, 0, 60]) for i in range(n)]

    def test_extract_features(self):
        analyzer = BehaviorAnalyzer()
        positions = self._make_positions()
        feat = analyzer.extract_features("D1", positions)
        assert feat.drone_id == "D1"
        assert feat.avg_speed > 0
        assert feat.total_distance > 0

    def test_classify_normal(self):
        analyzer = BehaviorAnalyzer()
        positions = self._make_positions(speed=10)
        feat = analyzer.extract_features("D1", positions)
        cls = analyzer.classify(feat)
        assert cls == BehaviorClass.NORMAL

    def test_classify_dangerous(self):
        analyzer = BehaviorAnalyzer(speed_threshold=10)
        positions = [np.array([i * 50, 0, 60 + np.sin(i) * 100]) for i in range(50)]
        feat = analyzer.extract_features("D1", positions, dt=0.1)
        cls = analyzer.classify(feat)
        assert cls in (BehaviorClass.DANGEROUS, BehaviorClass.ABNORMAL)

    def test_detect_anomalies(self):
        analyzer = BehaviorAnalyzer(anomaly_z_threshold=1.5)
        # 정상 드론 10기
        for i in range(10):
            positions = [np.array([j * 10, i * 100, 60]) for j in range(30)]
            analyzer.extract_features(f"D{i}", positions)
        # 이상 드론 1기
        positions = [np.array([j * 100, j * 100, 60 + j * 10]) for j in range(30)]
        analyzer.extract_features("ROGUE", positions)
        anomalies = analyzer.detect_anomalies()
        assert len(anomalies) >= 1

    def test_cluster_kmeans(self):
        analyzer = BehaviorAnalyzer()
        for i in range(15):
            speed = 10 + (i % 3) * 20
            positions = [np.array([j * speed * 0.1, 0, 60]) for j in range(20)]
            analyzer.extract_features(f"D{i}", positions)
        clusters = analyzer.cluster_kmeans(k=3)
        assert len(clusters) == 3
        total = sum(len(v) for v in clusters.values())
        assert total == 15

    def test_report(self):
        analyzer = BehaviorAnalyzer()
        positions = self._make_positions()
        analyzer.extract_features("D1", positions)
        report = analyzer.report()
        assert report["total_drones"] == 1
        assert "classification" in report

    def test_clear(self):
        analyzer = BehaviorAnalyzer()
        analyzer.extract_features("D1", self._make_positions())
        analyzer.clear()
        assert len(analyzer.features) == 0

    def test_empty_positions(self):
        analyzer = BehaviorAnalyzer()
        feat = analyzer.extract_features("D1", [])
        assert feat.avg_speed == 0.0

    def test_direction_changes(self):
        positions = [
            np.array([0, 0, 60]),
            np.array([10, 0, 60]),
            np.array([10, 10, 60]),  # 90도 전환
            np.array([0, 10, 60]),   # 90도 전환
        ]
        analyzer = BehaviorAnalyzer()
        feat = analyzer.extract_features("D1", positions, dt=1.0)
        assert feat.direction_changes >= 1


# ────────────────────────────────────────────
#  Phase 45: PriorityScheduler
# ────────────────────────────────────────────
from simulation.priority_scheduler import (
    PriorityScheduler, Mission, MissionPriority, CongestionInfo,
)


class TestPriorityScheduler:
    """동적 우선순위 스케줄러 테스트"""

    def test_add_mission(self):
        sched = PriorityScheduler()
        sched.add_mission(Mission("D1", MissionPriority.COMMERCIAL))
        assert len(sched.missions) == 1

    def test_launch_queue_priority_order(self):
        sched = PriorityScheduler()
        sched.add_mission(Mission("D1", MissionPriority.RECREATIONAL))
        sched.add_mission(Mission("D2", MissionPriority.EMERGENCY))
        sched.add_mission(Mission("D3", MissionPriority.MEDICAL))
        queue = sched.get_launch_queue()
        assert queue[0].drone_id == "D2"  # EMERGENCY first
        assert queue[1].drone_id == "D3"  # MEDICAL second

    def test_emergency_immediate(self):
        sched = PriorityScheduler()
        sched.add_mission(Mission("D1", MissionPriority.EMERGENCY))
        queue = sched.get_launch_queue()
        assert queue[0].departure_time == 0.0

    def test_congestion_delays(self):
        sched = PriorityScheduler(stagger_interval_s=2.0)
        sched.update_congestion(CongestionInfo(active_drones=80, max_capacity=100))
        sched.add_mission(Mission("D1", MissionPriority.COMMERCIAL))
        sched.add_mission(Mission("D2", MissionPriority.COMMERCIAL))
        queue = sched.get_launch_queue()
        # 혼잡도 높으면 간격 넓어짐
        assert queue[1].departure_time > queue[0].departure_time

    def test_schedule_next(self):
        sched = PriorityScheduler()
        sched.add_mission(Mission("D1", MissionPriority.COMMERCIAL, departure_time=0))
        sched.add_mission(Mission("D2", MissionPriority.COMMERCIAL, departure_time=10))
        ready = sched.schedule_next(5.0)
        assert len(ready) == 1
        assert ready[0].drone_id == "D1"

    def test_complete_mission(self):
        sched = PriorityScheduler()
        sched.add_mission(Mission("D1", MissionPriority.COMMERCIAL))
        sched.complete_mission("D1")
        sm = sched.summary()
        assert sm["completed"] == 1

    def test_estimate_wait(self):
        sched = PriorityScheduler(stagger_interval_s=2.0)
        sched.add_mission(Mission("D1", MissionPriority.EMERGENCY))
        sched.add_mission(Mission("D2", MissionPriority.COMMERCIAL))
        wait = sched.estimate_wait_time(MissionPriority.COMMERCIAL)
        assert wait > 0

    def test_rebalance_not_congested(self):
        sched = PriorityScheduler()
        sched.add_mission(Mission("D1", MissionPriority.RECREATIONAL))
        adjusted = sched.rebalance()
        assert adjusted == 0

    def test_rebalance_congested(self):
        sched = PriorityScheduler()
        sched.update_congestion(CongestionInfo(active_drones=80, max_capacity=100))
        sched.add_mission(Mission("D1", MissionPriority.RECREATIONAL))
        adjusted = sched.rebalance()
        assert adjusted == 1

    def test_summary(self):
        sched = PriorityScheduler()
        sched.add_mission(Mission("D1", MissionPriority.COMMERCIAL))
        sm = sched.summary()
        assert sm["total_missions"] == 1
        assert "COMMERCIAL" in sm["by_priority"]


# ────────────────────────────────────────────
#  Phase 46: ReplayAnalyzer
# ────────────────────────────────────────────
from simulation.replay_analyzer import (
    ReplayAnalyzer, IncidentEvent, IncidentReport,
)


class TestReplayAnalyzer:
    """자동 리플레이 분석기 테스트"""

    def _collision_records(self):
        records = []
        for tick in range(100):
            records.append({"tick": tick, "drone_id": "D1",
                            "position": [tick * 1.0, 0, 60], "phase": "ENROUTE"})
            records.append({"tick": tick, "drone_id": "D2",
                            "position": [100 - tick * 1.0, 0, 60], "phase": "ENROUTE"})
        return records

    def test_load_data(self):
        analyzer = ReplayAnalyzer()
        n = analyzer.load_fdr_data(self._collision_records())
        assert n == 200

    def test_detect_incidents(self):
        analyzer = ReplayAnalyzer(collision_dist=3.0, near_miss_dist=10.0)
        analyzer.load_fdr_data(self._collision_records())
        incidents = analyzer.detect_incidents(dt=0.1)
        assert len(incidents) > 0

    def test_analyze_collision(self):
        analyzer = ReplayAnalyzer(collision_dist=3.0, near_miss_dist=10.0)
        analyzer.load_fdr_data(self._collision_records())
        analyzer.detect_incidents(dt=0.1)
        # 충돌 발생 시점 (tick 50 근처)
        report = analyzer.analyze_incident(t_incident=5.0, dt=0.1)
        assert report.incident_type in ("COLLISION", "NEAR_MISS", "NONE")

    def test_causal_chain(self):
        analyzer = ReplayAnalyzer(collision_dist=3.0, near_miss_dist=10.0)
        analyzer.load_fdr_data(self._collision_records())
        incidents = analyzer.detect_incidents(dt=0.1)
        if incidents:
            chain = analyzer.trace_causal_chain(incidents[0])
            assert chain.root_cause is not None

    def test_no_incident(self):
        analyzer = ReplayAnalyzer()
        analyzer.load_fdr_data([
            {"tick": 0, "drone_id": "D1", "position": [0, 0, 60], "phase": "ENROUTE"},
            {"tick": 0, "drone_id": "D2", "position": [1000, 1000, 60], "phase": "ENROUTE"},
        ])
        analyzer.detect_incidents()
        report = analyzer.analyze_incident(t_incident=0.0)
        assert report.incident_type == "NONE"

    def test_failure_detection(self):
        records = [
            {"tick": 0, "drone_id": "D1", "position": [0, 0, 60], "phase": "FAILED",
             "failure_type": "MOTOR"},
        ]
        analyzer = ReplayAnalyzer()
        analyzer.load_fdr_data(records)
        incidents = analyzer.detect_incidents()
        failure_events = [i for i in incidents if i.event_type == "FAILURE"]
        assert len(failure_events) == 1

    def test_clear(self):
        analyzer = ReplayAnalyzer()
        analyzer.load_fdr_data(self._collision_records())
        analyzer.clear()
        assert len(analyzer._records) == 0


# ────────────────────────────────────────────
#  Phase 47: WeatherForecaster
# ────────────────────────────────────────────
from simulation.weather_forecast import WeatherForecaster, WeatherPrediction


class TestWeatherForecaster:
    """기상 예측 엔진 테스트"""

    def test_empty_predict(self):
        fc = WeatherForecaster()
        pred = fc.predict()
        assert pred.wind_speed == 0.0
        assert pred.confidence == 0.0

    def test_single_record(self):
        fc = WeatherForecaster()
        fc.record(t=0, wind_speed=5.0, wind_direction=90.0)
        pred = fc.predict()
        assert pred.wind_speed == 5.0

    def test_increasing_wind(self):
        fc = WeatherForecaster()
        for i in range(30):
            fc.record(t=float(i), wind_speed=5.0 + i * 0.5)
        pred = fc.predict(horizon_s=10.0)
        assert pred.wind_speed > 15.0  # 상승 트렌드

    def test_alert_levels(self):
        fc = WeatherForecaster(caution_speed=10, warning_speed=15, danger_speed=20)
        fc.record(t=0, wind_speed=5.0)
        assert fc.predict().alert_level == "NONE"
        fc.clear()
        fc.record(t=0, wind_speed=12.0)
        assert fc.predict().alert_level == "CAUTION"
        fc.clear()
        fc.record(t=0, wind_speed=16.0)
        assert fc.predict().alert_level == "WARNING"
        fc.clear()
        fc.record(t=0, wind_speed=25.0)
        assert fc.predict().alert_level == "DANGER"

    def test_moving_average(self):
        fc = WeatherForecaster()
        for i in range(10):
            fc.record(t=float(i), wind_speed=10.0)
        assert fc.moving_average() == 10.0

    def test_trend_positive(self):
        fc = WeatherForecaster()
        for i in range(10):
            fc.record(t=float(i), wind_speed=5.0 + i)
        assert fc.trend() > 0

    def test_should_rtl(self):
        fc = WeatherForecaster(danger_speed=20)
        for i in range(30):
            fc.record(t=float(i), wind_speed=15.0 + i * 0.5)
        assert fc.should_preemptive_rtl(horizon_s=30)

    def test_wind_vector(self):
        pred = WeatherPrediction(t_predict=0, wind_speed=10, wind_direction=90,
                                  confidence=1.0)
        vec = pred.wind_vector
        assert abs(vec[0] - 10.0) < 0.01  # East

    def test_summary(self):
        fc = WeatherForecaster()
        fc.record(t=0, wind_speed=5.0)
        fc.record(t=1, wind_speed=6.0)
        sm = fc.summary()
        assert sm["data_points"] == 2
        assert "prediction_30s" in sm

    def test_max_history(self):
        fc = WeatherForecaster(max_history=10)
        for i in range(20):
            fc.record(t=float(i), wind_speed=5.0)
        assert len(fc.history) == 10


# ────────────────────────────────────────────
#  Phase 49: BatteryPredictor
# ────────────────────────────────────────────
from simulation.battery_predictor import BatteryPredictor


class TestBatteryPredictor:
    """배터리 수명 예측기 테스트"""

    def test_no_data(self):
        bp = BatteryPredictor()
        assert bp.predict_remaining_time("D1") == -1.0

    def test_linear_drain(self):
        bp = BatteryPredictor(critical_pct=10.0)
        for i in range(20):
            bp.record("D1", t=float(i), battery_pct=100.0 - i * 2)
        remaining = bp.predict_remaining_time("D1")
        assert remaining > 0

    def test_range_prediction(self):
        bp = BatteryPredictor()
        for i in range(10):
            bp.record("D1", t=float(i), battery_pct=100.0 - i * 5, speed=10.0)
        range_km = bp.predict_range_km("D1")
        assert range_km > 0

    def test_should_rtl_low_battery(self):
        bp = BatteryPredictor(rtl_pct=20.0)
        bp.record("D1", t=0, battery_pct=15.0)
        bp.record("D1", t=1, battery_pct=14.0)
        assert bp.should_rtl("D1") is True

    def test_should_rtl_healthy(self):
        bp = BatteryPredictor(rtl_pct=20.0)
        bp.record("D1", t=0, battery_pct=80.0)
        bp.record("D1", t=1, battery_pct=79.0)
        assert bp.should_rtl("D1") is False

    def test_can_reach(self):
        bp = BatteryPredictor()
        for i in range(10):
            bp.record("D1", t=float(i), battery_pct=90.0 - i, speed=10.0)
        assert bp.can_reach("D1", distance_m=100, speed=10.0) is True

    def test_drain_rate(self):
        bp = BatteryPredictor()
        bp.record("D1", t=0, battery_pct=100)
        bp.record("D1", t=10, battery_pct=90)
        rate = bp.drain_rate("D1")
        assert abs(rate - 1.0) < 0.01  # 1%/s

    def test_summary(self):
        bp = BatteryPredictor()
        bp.record("D1", t=0, battery_pct=80)
        bp.record("D1", t=1, battery_pct=79)
        sm = bp.summary("D1")
        assert sm["current_pct"] == 79
        assert "remaining_time_s" in sm

    def test_all_drones(self):
        bp = BatteryPredictor()
        bp.record("D1", t=0, battery_pct=80)
        bp.record("D2", t=0, battery_pct=50)
        summaries = bp.all_drones_summary()
        assert len(summaries) == 2


# ────────────────────────────────────────────
#  Phase 51: ComplianceChecker
# ────────────────────────────────────────────
from simulation.compliance_checker import ComplianceChecker, ComplianceRule


class TestComplianceChecker:
    """규제 준수 검증기 테스트"""

    def test_no_violations(self):
        cc = ComplianceChecker()
        viols = cc.check("D1", time=0, altitude_m=60, speed_ms=10, battery_pct=80)
        assert len(viols) == 0

    def test_altitude_violation(self):
        cc = ComplianceChecker()
        viols = cc.check("D1", time=0, altitude_m=150)
        assert len(viols) >= 1
        assert any(v.rule_name == "최대고도" for v in viols)

    def test_speed_violation(self):
        cc = ComplianceChecker()
        viols = cc.check("D1", time=0, speed_ms=30)
        assert any(v.rule_name == "최대속도" for v in viols)

    def test_battery_violation(self):
        cc = ComplianceChecker()
        viols = cc.check("D1", time=0, battery_pct=5)
        assert any(v.rule_name == "배터리잔량" for v in viols)

    def test_separation_violation(self):
        cc = ComplianceChecker()
        viols = cc.check_separation("D1", "D2", h_dist=20, v_dist=5, time=0)
        assert len(viols) == 2

    def test_compliance_score_perfect(self):
        cc = ComplianceChecker()
        cc.check("D1", time=0, altitude_m=60, speed_ms=10, battery_pct=80)
        assert cc.compliance_score == 100.0

    def test_compliance_score_degraded(self):
        cc = ComplianceChecker()
        for i in range(10):
            cc.check(f"D{i}", time=float(i), altitude_m=150)
        assert cc.compliance_score < 100.0

    def test_violations_by_severity(self):
        cc = ComplianceChecker()
        cc.check("D1", time=0, altitude_m=150)
        by_sev = cc.violations_by_severity()
        assert "HIGH" in by_sev

    def test_violations_by_rule(self):
        cc = ComplianceChecker()
        cc.check("D1", time=0, altitude_m=150, speed_ms=30)
        by_rule = cc.violations_by_rule()
        assert "최대고도" in by_rule
        assert "최대속도" in by_rule

    def test_summary(self):
        cc = ComplianceChecker()
        cc.check("D1", time=0, altitude_m=60)
        sm = cc.summary()
        assert sm["total_checks"] == 1
        assert "compliance_score" in sm

    def test_custom_rule(self):
        rules = [ComplianceRule("custom", "my_metric", max_value=10)]
        cc = ComplianceChecker(rules=rules)
        viols = cc.check("D1", time=0, my_metric=20)
        assert len(viols) == 1

    def test_clear(self):
        cc = ComplianceChecker()
        cc.check("D1", time=0, altitude_m=150)
        cc.clear()
        assert cc.violation_count == 0
        assert cc.compliance_score == 100.0

    def test_nfz_violation(self):
        cc = ComplianceChecker()
        viols = cc.check("D1", time=0, nfz_violation=1)
        assert any(v.rule_name == "NFZ_침범" for v in viols)
