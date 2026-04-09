"""
Phase 36-43 테스트
==================
시각화 대폭 강화 + 서브시스템 연동 테스트
- Phase 36: 위협 히트맵 + ThreatAssessment 연동
- Phase 37: 시나리오 타임라인 시각화
- Phase 38: 에너지 경로 3D (EnergyPathPlanner 연동)
- Phase 39: 구역별 관제 (MultiController 연동)
- Phase 40: SLA 대시보드 (SLAMonitor 연동)
- Phase 41: 드론 상세 정보 (확장)
- Phase 42: 경보 로그 + 이벤트 타임라인
- Phase 43: 성능 모니터
"""
import numpy as np
import pytest

# ────────────────────────────────────────────
#  Phase 36: 위협 평가 연동 (확장 테스트)
# ────────────────────────────────────────────
from simulation.threat_assessment import ThreatAssessmentEngine, ThreatLevel, Threat


class TestThreatAssessmentExtended:
    """위협 평가 확장 테스트"""

    def test_battery_threat(self):
        engine = ThreatAssessmentEngine()
        threats = engine.assess(low_battery_count=3)
        assert threats[0].threat_type == "BATTERY"
        assert threats[0].level == ThreatLevel.MEDIUM

    def test_battery_high(self):
        engine = ThreatAssessmentEngine()
        threats = engine.assess(low_battery_count=5)
        assert threats[0].level == ThreatLevel.HIGH

    def test_comms_loss(self):
        engine = ThreatAssessmentEngine()
        threats = engine.assess(comms_loss_count=2)
        assert threats[0].threat_type == "COMMS_LOSS"

    def test_evading_threat(self):
        engine = ThreatAssessmentEngine()
        threats = engine.assess(evading_count=3)
        assert threats[0].threat_type == "EVADING"
        assert threats[0].level == ThreatLevel.MEDIUM

    def test_evading_high(self):
        engine = ThreatAssessmentEngine()
        threats = engine.assess(evading_count=5)
        assert threats[0].level == ThreatLevel.HIGH

    def test_multi_threat_matrix_actions(self):
        engine = ThreatAssessmentEngine()
        threats = engine.assess(collision_count=1, rogue_count=2, wind_speed=16)
        matrix = engine.priority_matrix(threats)
        actions = matrix["recommended_actions"]
        assert any("APF" in a for a in actions)
        assert any("침입" in a for a in actions)
        assert any("풍" in a or "WINDY" in a or "속도" in a for a in actions)

    def test_threat_by_level(self):
        engine = ThreatAssessmentEngine()
        threats = engine.assess(collision_count=1, wind_speed=5)
        matrix = engine.priority_matrix(threats)
        by_level = matrix["threats_by_level"]
        assert "CRITICAL" in by_level
        assert "COLLISION" in by_level["CRITICAL"]

    def test_failure_medium(self):
        engine = ThreatAssessmentEngine()
        threats = engine.assess(failure_count=1)
        assert threats[0].level == ThreatLevel.MEDIUM

    def test_failure_high(self):
        engine = ThreatAssessmentEngine()
        threats = engine.assess(failure_count=3)
        assert threats[0].level == ThreatLevel.HIGH


# ────────────────────────────────────────────
#  Phase 37: 시나리오 스크립터 확장
# ────────────────────────────────────────────
from simulation.scenario_scripter import ScenarioScripter, VALID_EVENT_TYPES


class TestScenarioScripterExtended:
    """시나리오 스크립터 확장 테스트"""

    def test_all_valid_event_types(self):
        expected = {"SPAWN_DRONES", "INJECT_ROGUE", "SET_WIND", "ADD_NFZ",
                    "REMOVE_NFZ", "FAIL_DRONE", "COMMS_JAM", "BATTERY_DRAIN"}
        assert VALID_EVENT_TYPES == expected

    def test_complex_scenario(self):
        yaml_str = """
name: complex
duration: 120
events:
  - time: 0
    type: SPAWN_DRONES
    params: {count: 50}
  - time: 10
    type: SET_WIND
    params: {speed: 15}
  - time: 20
    type: INJECT_ROGUE
    params: {count: 3}
  - time: 30
    type: ADD_NFZ
    params: {x_range: [100, 300], y_range: [-200, 200]}
  - time: 40
    type: FAIL_DRONE
    params: {drone_id: DR001}
  - time: 50
    type: COMMS_JAM
    params: {duration: 10}
  - time: 60
    type: BATTERY_DRAIN
    params: {rate: 5.0}
  - time: 70
    type: REMOVE_NFZ
    params: {nfz_id: nfz_01}
"""
        s = ScenarioScripter()
        script = s.load_yaml(yaml_str)
        assert script.event_count == 8

        # 시간별 발화
        ev10 = s.get_events_at(t=10)
        assert len(ev10) == 2  # SPAWN(0) + SET_WIND(10)

    def test_roundtrip_yaml(self):
        s = ScenarioScripter()
        s.load_yaml("""
name: roundtrip
duration: 30
events:
  - time: 5
    type: SET_WIND
    params: {speed: 10}
""")
        yaml_out = s.to_yaml()
        s2 = ScenarioScripter()
        script2 = s2.load_yaml(yaml_out)
        assert script2.name == "roundtrip"
        assert script2.event_count == 1


# ────────────────────────────────────────────
#  Phase 38: 에너지 경로 확장
# ────────────────────────────────────────────
from simulation.energy_path_planner import EnergyPathPlanner


class TestEnergyPathExtended:
    """에너지 경로 확장 테스트"""

    def test_tailwind_reduces_cost(self):
        start = np.array([0.0, 0.0, 60.0])
        goal = np.array([600.0, 0.0, 60.0])
        planner_tw = EnergyPathPlanner(
            grid_resolution=200.0,
            wind_vector=np.array([10.0, 0.0, 0.0]),  # 순풍
        )
        _, cost_tw = planner_tw.plan(start, goal)
        planner_no = EnergyPathPlanner(grid_resolution=200.0)
        _, cost_no = planner_no.plan(start, goal)
        assert cost_tw < cost_no

    def test_alt_factor(self):
        planner = EnergyPathPlanner()
        cost_low = planner._energy_cost((0, 0, 30), (200, 0, 30))
        cost_high = planner._energy_cost((0, 0, 120), (200, 0, 120))
        assert cost_high > cost_low  # 고도 높을수록 비용 증가

    def test_range_increases_with_battery(self):
        planner = EnergyPathPlanner(cruise_speed=10.0)
        r1 = planner.estimate_range_km(battery_wh=40.0)
        r2 = planner.estimate_range_km(battery_wh=80.0)
        assert r2 > r1

    def test_nfz_filter(self):
        planner = EnergyPathPlanner()
        assert not planner._in_nfz((1000, 1000, 60))


# ────────────────────────────────────────────
#  Phase 39: 다중 관제 구역 확장
# ────────────────────────────────────────────
from simulation.multi_controller import MultiControllerManager


class TestMultiControllerExtended:
    """다중 관제 구역 확장 테스트"""

    def test_handoff_counts(self):
        mgr = MultiControllerManager(bounds=1000, n_sectors=4)
        pos1 = np.array([-500, -500, 60])
        mgr.register_drone("D1", pos1)
        pos2 = np.array([500, 500, 60])
        mgr.update_drone_position("D1", pos2)
        assert mgr.total_handoffs == 1

    def test_density_calculation(self):
        mgr = MultiControllerManager(bounds=1000, n_sectors=4)
        for i in range(10):
            mgr.register_drone(f"D{i}", np.array([-500, -500, 60]))
        stats = mgr.sector_stats()
        # 하나의 섹터에 10기 집중
        densities = [s["density"] for s in stats.values()]
        assert max(densities) > 0

    def test_outside_bounds(self):
        mgr = MultiControllerManager(bounds=1000, n_sectors=4)
        sid = mgr.assign_sector(np.array([5000, 5000, 60]))
        assert sid is None

    def test_global_stats(self):
        mgr = MultiControllerManager(bounds=1000, n_sectors=4)
        mgr.register_drone("D1", np.array([0, 0, 60]))
        gs = mgr.global_stats()
        assert gs["total_drones"] == 1
        assert gs["total_sectors"] == 4


# ────────────────────────────────────────────
#  Phase 40: SLA 모니터 확장
# ────────────────────────────────────────────
from simulation.sla_monitor import SLAMonitor


class TestSLAMonitorExtended:
    """SLA 모니터 확장 테스트"""

    def test_multiple_violations(self):
        mon = SLAMonitor()
        viols = mon.check(collision_count=5, conflict_resolution_rate_pct=80.0)
        assert len(viols) >= 2

    def test_custom_threshold(self):
        from simulation.sla_monitor import SLAThreshold
        custom = [SLAThreshold(
            name="test_metric",
            metric="custom_val",
            max_value=10.0,
            severity="WARNING",
        )]
        mon = SLAMonitor(thresholds=custom)
        viols = mon.check(custom_val=15.0)
        assert len(viols) == 1
        assert viols[0].threshold_name == "test_metric"

    def test_auto_tune(self):
        mon = SLAMonitor()
        viols = mon.check(collision_rate=0.5)
        if viols:
            suggestions = mon.auto_tune(viols)
            assert isinstance(suggestions, list)


# ────────────────────────────────────────────
#  Phase 41-42: 이벤트 타임라인 확장
# ────────────────────────────────────────────
from simulation.event_timeline import EventTimeline


class TestEventTimelineExtended:
    """이벤트 타임라인 확장 테스트"""

    def test_severity_filter(self):
        tl = EventTimeline()
        tl.add("COLLISION", t=10, severity="CRITICAL")
        tl.add("ADVISORY", t=15, severity="INFO")
        critical = tl.query(severity="CRITICAL")
        assert len(critical) == 1
        assert critical[0].severity == "CRITICAL"

    def test_multiple_types(self):
        tl = EventTimeline()
        tl.add("COLLISION", t=10)
        tl.add("EVADING", t=15)
        tl.add("NFZ_VIOLATION", t=20)
        all_events = tl.query()
        assert len(all_events) == 3

    def test_event_types(self):
        tl = EventTimeline()
        tl.add("A", t=1)
        tl.add("B", t=2)
        tl.add("A", t=3)
        types = tl.event_types()
        assert set(types) == {"A", "B"}

    def test_count_by_type(self):
        tl = EventTimeline()
        tl.add("A", t=1)
        tl.add("A", t=2)
        tl.add("B", t=3)
        counts = tl.count_by_type()
        assert counts["A"] == 2
        assert counts["B"] == 1


# ────────────────────────────────────────────
#  Phase 43: 스트레스 테스트 확장
# ────────────────────────────────────────────
from simulation.stress_test import StressTestRunner, StressTestConfig


class TestStressTestExtended:
    """스트레스 테스트 확장"""

    def test_synthetic_with_conflicts(self):
        runner = StressTestRunner(n_drones=50, duration_s=2.0, tick_hz=10.0)
        result = runner.run_synthetic()
        assert result.total_ticks == 20
        assert result.completed

    def test_config_custom(self):
        cfg = StressTestConfig(
            n_drones=200,
            duration_s=30.0,
            wind_speed=15.0,
            rogue_count=5,
            seed=99,
        )
        assert cfg.n_drones == 200
        assert cfg.seed == 99

    def test_benchmark_performance(self):
        """벤치마크가 합리적 시간에 완료"""
        runner = StressTestRunner(n_drones=100)
        result = runner.run_quick_benchmark(ticks=50)
        assert result.avg_tick_ms < 100  # 100ms 이하 (보수적)
        assert result.completed

    def test_tick_metrics_fields(self):
        runner = StressTestRunner(n_drones=10)
        result = runner.run_quick_benchmark(ticks=5)
        m = result.tick_metrics[0]
        assert m.tick == 0
        assert m.active_drones == 10
        assert m.wall_time_ms >= 0


# ────────────────────────────────────────────
#  시각화 통합 (import 검증)
# ────────────────────────────────────────────
class TestVisualizationImports:
    """시각화 모듈 임포트 검증"""

    def test_simulator_3d_imports(self):
        import visualization.simulator_3d as sim3d
        assert hasattr(sim3d, 'build_figure')
        assert hasattr(sim3d, 'SimState')
        assert hasattr(sim3d, '_sector_overlay')
        assert hasattr(sim3d, '_threat_heatmap_overlay')

    def test_simstate_has_subsystems(self):
        from visualization.simulator_3d import SimState
        state = SimState()
        assert hasattr(state, 'threat_engine')
        assert hasattr(state, 'sector_mgr')
        assert hasattr(state, 'sla_monitor')
        assert hasattr(state, 'timeline')
        assert hasattr(state, 'tick_times_ms')

    def test_simstate_reset_clears_subsystems(self):
        from visualization.simulator_3d import SimState
        state = SimState()
        state.threat_engine.assess(collision_count=1)
        state.timeline.add("TEST", t=1.0)
        state.tick_times_ms.append(5.0)
        state.reset(10)
        assert state.threat_engine.history_len() == 0
        assert len(state.timeline._events) == 0
        assert len(state.tick_times_ms) == 0

    def test_build_figure_runs(self):
        from visualization.simulator_3d import SimState, build_figure
        state = SimState()
        state.reset(5)
        fig = build_figure(state)
        assert fig is not None
        assert len(fig.data) > 0
