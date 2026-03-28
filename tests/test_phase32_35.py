"""
Phase 32-35 테스트
==================
- Phase 32: EnergyPathPlanner (에너지 최적 A* 경로)
- Phase 33: ThreatAssessmentEngine (위협 평가)
- Phase 34: ScenarioScripter (YAML DSL 시나리오)
- Phase 35: StressTestRunner (E2E 스트레스 테스트)
"""
import numpy as np
import pytest

# ────────────────────────────────────────────
#  Phase 32: EnergyPathPlanner
# ────────────────────────────────────────────
from simulation.energy_path_planner import EnergyPathPlanner, _Node


class TestEnergyPathPlanner:
    """에너지 최적 경로 계획기 테스트"""

    def test_same_start_goal(self):
        planner = EnergyPathPlanner()
        start = np.array([0.0, 0.0, 60.0])
        path, cost = planner.plan(start, start)
        assert len(path) == 1
        assert cost == 0.0

    def test_basic_path(self):
        planner = EnergyPathPlanner(grid_resolution=200.0)
        start = np.array([0.0, 0.0, 60.0])
        goal = np.array([400.0, 0.0, 60.0])
        path, cost = planner.plan(start, goal)
        assert len(path) >= 2
        assert cost > 0

    def test_path_avoids_nfz(self):
        nfz = [{"x_range": (100, 300), "y_range": (-500, 500)}]
        planner = EnergyPathPlanner(grid_resolution=200.0, no_fly_zones=nfz)
        start = np.array([0.0, 0.0, 60.0])
        goal = np.array([400.0, 0.0, 60.0])
        path, cost = planner.plan(start, goal)
        # 경로가 NFZ를 통과하지 않아야 함
        for wp in path:
            in_nfz = 100 <= wp[0] <= 300 and -500 <= wp[1] <= 500
            # 스냅 그리드에서 경계값 허용
            assert not (150 <= wp[0] <= 250 and -400 <= wp[1] <= 400)

    def test_wind_increases_cost(self):
        start = np.array([0.0, 0.0, 60.0])
        goal = np.array([600.0, 0.0, 60.0])
        planner_no_wind = EnergyPathPlanner(grid_resolution=200.0)
        _, cost_no = planner_no_wind.plan(start, goal)

        # 역풍
        planner_headwind = EnergyPathPlanner(
            grid_resolution=200.0,
            wind_vector=np.array([-10.0, 0.0, 0.0]),
        )
        _, cost_hw = planner_headwind.plan(start, goal)
        assert cost_hw > cost_no

    def test_energy_cost_positive(self):
        planner = EnergyPathPlanner()
        cost = planner._energy_cost((0, 0, 60), (200, 0, 60))
        assert cost > 0

    def test_energy_cost_zero_distance(self):
        planner = EnergyPathPlanner()
        cost = planner._energy_cost((0, 0, 60), (0, 0, 60))
        assert cost == 0.0

    def test_climb_costs_more(self):
        planner = EnergyPathPlanner()
        cost_flat = planner._energy_cost((0, 0, 60), (200, 0, 60))
        cost_climb = planner._energy_cost((0, 0, 60), (200, 0, 120))
        assert cost_climb > cost_flat

    def test_plan_with_charging_direct(self):
        planner = EnergyPathPlanner(grid_resolution=200.0)
        start = np.array([0.0, 0.0, 60.0])
        goal = np.array([200.0, 0.0, 60.0])
        path, cost, stops = planner.plan_with_charging(start, goal, battery_wh=100)
        assert len(stops) == 0  # 충전 불필요

    def test_plan_with_charging_via_station(self):
        stations = [np.array([500.0, 0.0, 60.0])]
        planner = EnergyPathPlanner(
            grid_resolution=200.0,
            charging_stations=stations,
        )
        start = np.array([0.0, 0.0, 60.0])
        goal = np.array([1000.0, 0.0, 60.0])
        path, cost, stops = planner.plan_with_charging(start, goal, battery_wh=0.5)
        # 배터리 매우 작으면 충전소 경유 시도
        assert len(path) >= 2

    def test_estimate_range(self):
        planner = EnergyPathPlanner(cruise_speed=10.0)
        rng_km = planner.estimate_range_km(battery_wh=80.0, altitude=60.0)
        assert rng_km > 0

    def test_snap_grid(self):
        planner = EnergyPathPlanner(grid_resolution=200.0, alt_step=30.0)
        snapped = planner._snap(np.array([150.0, 310.0, 50.0]))
        assert snapped == (200.0, 400.0, 60.0)

    def test_neighbors_count(self):
        planner = EnergyPathPlanner(grid_resolution=200.0)
        neighbors = planner._neighbors((0.0, 0.0, 60.0))
        # 8방향 + 최대 2 수직 = 최대 10
        assert 5 <= len(neighbors) <= 10

    def test_node_ordering(self):
        n1 = _Node(f_cost=10.0, g_cost=5.0, position=(0, 0, 60))
        n2 = _Node(f_cost=20.0, g_cost=10.0, position=(1, 1, 60))
        assert n1 < n2


# ────────────────────────────────────────────
#  Phase 33: ThreatAssessmentEngine
# ────────────────────────────────────────────
from simulation.threat_assessment import (
    Threat,
    ThreatAssessmentEngine,
    ThreatLevel,
)


class TestThreatAssessment:
    """위협 평가 엔진 테스트"""

    def test_no_threats(self):
        engine = ThreatAssessmentEngine()
        threats = engine.assess()
        assert threats == []

    def test_collision_critical(self):
        engine = ThreatAssessmentEngine()
        threats = engine.assess(collision_count=1)
        assert len(threats) == 1
        assert threats[0].level == ThreatLevel.CRITICAL
        assert threats[0].threat_type == "COLLISION"

    def test_near_miss_medium(self):
        engine = ThreatAssessmentEngine()
        threats = engine.assess(near_miss_count=3)
        assert threats[0].level == ThreatLevel.MEDIUM

    def test_near_miss_high(self):
        engine = ThreatAssessmentEngine()
        threats = engine.assess(near_miss_count=5)
        assert threats[0].level == ThreatLevel.HIGH

    def test_rogue_high(self):
        engine = ThreatAssessmentEngine()
        threats = engine.assess(rogue_count=1)
        assert threats[0].level == ThreatLevel.HIGH

    def test_rogue_critical(self):
        engine = ThreatAssessmentEngine()
        threats = engine.assess(rogue_count=3)
        assert threats[0].level == ThreatLevel.CRITICAL

    def test_weather_levels(self):
        engine = ThreatAssessmentEngine()
        # LOW
        t1 = engine.assess(wind_speed=5.0)
        assert t1[0].level == ThreatLevel.LOW

        engine.clear()
        # MEDIUM
        t2 = engine.assess(wind_speed=12.0)
        assert t2[0].level == ThreatLevel.MEDIUM

        engine.clear()
        # HIGH
        t3 = engine.assess(wind_speed=16.0)
        assert t3[0].level == ThreatLevel.HIGH

        engine.clear()
        # CRITICAL
        t4 = engine.assess(wind_speed=25.0)
        assert t4[0].level == ThreatLevel.CRITICAL

    def test_nfz_violation_critical(self):
        engine = ThreatAssessmentEngine()
        threats = engine.assess(nfz_violation_count=1)
        assert threats[0].level == ThreatLevel.CRITICAL
        assert threats[0].threat_type == "NFZ_VIOLATION"

    def test_multiple_threats_sorted(self):
        engine = ThreatAssessmentEngine()
        threats = engine.assess(
            collision_count=1,
            near_miss_count=2,
            wind_speed=5.0,
        )
        scores = [t.score for t in threats]
        assert scores == sorted(scores, reverse=True)

    def test_priority_matrix_empty(self):
        engine = ThreatAssessmentEngine()
        matrix = engine.priority_matrix([])
        assert matrix["overall_level"] == ThreatLevel.LOW
        assert matrix["total_score"] == 0

    def test_priority_matrix_escalation(self):
        """3개 이상 HIGH → CRITICAL 에스컬레이션"""
        engine = ThreatAssessmentEngine()
        threats = engine.assess(
            near_miss_count=5,  # HIGH
            failure_count=3,    # HIGH
            comms_loss_count=5, # HIGH
        )
        matrix = engine.priority_matrix(threats)
        assert matrix["overall_level"] == ThreatLevel.CRITICAL

    def test_recommended_actions(self):
        engine = ThreatAssessmentEngine()
        threats = engine.assess(collision_count=1)
        matrix = engine.priority_matrix(threats)
        assert len(matrix["recommended_actions"]) > 0
        assert any("APF" in a for a in matrix["recommended_actions"])

    def test_threat_score(self):
        t = Threat(threat_type="COLLISION", level=ThreatLevel.CRITICAL)
        assert t.score == 100  # 4 * 25 + 0

    def test_threat_score_with_drones(self):
        t = Threat(
            threat_type="COLLISION",
            level=ThreatLevel.CRITICAL,
            source_ids=["d1", "d2", "d3"],
        )
        assert t.score == 115  # 100 + 15

    def test_overall_threat_level(self):
        engine = ThreatAssessmentEngine()
        assert engine.overall_threat_level() == ThreatLevel.LOW
        engine.assess(collision_count=1)
        assert engine.overall_threat_level() == ThreatLevel.CRITICAL

    def test_history(self):
        engine = ThreatAssessmentEngine()
        engine.assess(wind_speed=5.0)
        engine.assess(collision_count=1)
        assert engine.history_len() == 2

    def test_clear(self):
        engine = ThreatAssessmentEngine()
        engine.assess(collision_count=1)
        engine.clear()
        assert engine.history_len() == 0


# ────────────────────────────────────────────
#  Phase 34: ScenarioScripter
# ────────────────────────────────────────────
from simulation.scenario_scripter import (
    ScenarioScripter,
    ScriptedEvent,
    ScenarioScript,
    VALID_EVENT_TYPES,
)


class TestScenarioScripter:
    """YAML DSL 시나리오 스크립터 테스트"""

    SAMPLE_YAML = """
name: test_scenario
description: 테스트 시나리오
duration: 60
events:
  - time: 10
    type: SET_WIND
    params:
      speed: 15.0
  - time: 20
    type: INJECT_ROGUE
    params:
      count: 2
  - time: 30
    type: ADD_NFZ
    params:
      x_range: [100, 300]
      y_range: [-200, 200]
"""

    def test_load_yaml(self):
        s = ScenarioScripter()
        script = s.load_yaml(self.SAMPLE_YAML)
        assert script.name == "test_scenario"
        assert script.event_count == 3

    def test_events_sorted(self):
        s = ScenarioScripter()
        script = s.load_yaml(self.SAMPLE_YAML)
        times = [e.time for e in script.events]
        assert times == sorted(times)

    def test_get_events_at(self):
        s = ScenarioScripter()
        s.load_yaml(self.SAMPLE_YAML)
        events = s.get_events_at(t=15.0)
        assert len(events) == 1
        assert events[0].event_type == "SET_WIND"

    def test_events_fire_once(self):
        s = ScenarioScripter()
        s.load_yaml(self.SAMPLE_YAML)
        s.get_events_at(t=15.0)
        events2 = s.get_events_at(t=15.0)
        assert len(events2) == 0

    def test_get_events_at_multiple(self):
        s = ScenarioScripter()
        s.load_yaml(self.SAMPLE_YAML)
        events = s.get_events_at(t=25.0)
        assert len(events) == 2  # SET_WIND(10) + INJECT_ROGUE(20)

    def test_get_events_in_range(self):
        s = ScenarioScripter()
        s.load_yaml(self.SAMPLE_YAML)
        events = s.get_events_in_range(15.0, 25.0)
        assert len(events) == 1
        assert events[0].event_type == "INJECT_ROGUE"

    def test_peek_next(self):
        s = ScenarioScripter()
        s.load_yaml(self.SAMPLE_YAML)
        nxt = s.peek_next(t=5.0)
        assert nxt is not None
        assert nxt.time == 10.0

    def test_peek_next_after_all(self):
        s = ScenarioScripter()
        s.load_yaml(self.SAMPLE_YAML)
        s.get_events_at(t=100.0)
        nxt = s.peek_next(t=100.0)
        assert nxt is None

    def test_reset(self):
        s = ScenarioScripter()
        s.load_yaml(self.SAMPLE_YAML)
        s.get_events_at(t=100.0)
        s.reset()
        events = s.get_events_at(t=100.0)
        assert len(events) == 3

    def test_load_dict(self):
        s = ScenarioScripter()
        data = {
            "name": "dict_test",
            "duration": 30,
            "events": [
                {"time": 5, "type": "SET_WIND", "params": {"speed": 10}},
            ],
        }
        script = s.load_dict(data)
        assert script.name == "dict_test"
        assert script.event_count == 1

    def test_summary(self):
        s = ScenarioScripter()
        s.load_yaml(self.SAMPLE_YAML)
        sm = s.summary()
        assert sm["loaded"] is True
        assert sm["event_count"] == 3
        assert "SET_WIND" in sm["events_by_type"]

    def test_summary_empty(self):
        s = ScenarioScripter()
        sm = s.summary()
        assert sm["loaded"] is False

    def test_to_yaml(self):
        s = ScenarioScripter()
        s.load_yaml(self.SAMPLE_YAML)
        out = s.to_yaml()
        assert "test_scenario" in out
        assert "SET_WIND" in out

    def test_invalid_event_type(self):
        with pytest.raises(ValueError, match="Unknown event type"):
            ScriptedEvent(time=0, event_type="INVALID_TYPE")

    def test_negative_time(self):
        with pytest.raises(ValueError, match="time must be >= 0"):
            ScriptedEvent(time=-5, event_type="SET_WIND")

    def test_script_properties(self):
        script = ScenarioScript(name="t", events=[
            ScriptedEvent(time=0, event_type="SET_WIND"),
            ScriptedEvent(time=1, event_type="SET_WIND", fired=True),
        ])
        assert script.event_count == 2
        assert script.fired_count == 1


# ────────────────────────────────────────────
#  Phase 35: StressTestRunner
# ────────────────────────────────────────────
from simulation.stress_test import (
    StressTestConfig,
    StressTestResult,
    StressTestRunner,
    TickMetrics,
)


class TestStressTest:
    """E2E 스트레스 테스트 프레임워크"""

    def test_config_defaults(self):
        cfg = StressTestConfig()
        assert cfg.n_drones == 100
        assert cfg.duration_s == 60.0

    def test_config_invalid_drones(self):
        with pytest.raises(ValueError):
            StressTestConfig(n_drones=0)

    def test_config_invalid_duration(self):
        with pytest.raises(ValueError):
            StressTestConfig(duration_s=-1)

    def test_quick_benchmark(self):
        runner = StressTestRunner(n_drones=10, duration_s=1.0)
        result = runner.run_quick_benchmark(ticks=50)
        assert result.completed is True
        assert result.total_ticks == 50
        assert len(result.tick_metrics) == 50

    def test_synthetic_run(self):
        runner = StressTestRunner(n_drones=20, duration_s=1.0, tick_hz=10.0)
        result = runner.run_synthetic()
        assert result.completed is True
        assert result.total_ticks == 10
        assert result.total_wall_time_s > 0

    def test_summary(self):
        runner = StressTestRunner(n_drones=10, duration_s=1.0)
        result = runner.run_quick_benchmark(ticks=20)
        sm = result.summary()
        assert "n_drones" in sm
        assert sm["completed"] is True

    def test_avg_tick(self):
        result = StressTestResult(config=StressTestConfig())
        assert result.avg_tick_ms == 0.0
        result.tick_metrics.append(TickMetrics(
            tick=0, sim_time=0, wall_time_ms=5.0, active_drones=10
        ))
        result.tick_metrics.append(TickMetrics(
            tick=1, sim_time=0.1, wall_time_ms=15.0, active_drones=10
        ))
        assert result.avg_tick_ms == 10.0

    def test_max_tick(self):
        result = StressTestResult(config=StressTestConfig())
        result.tick_metrics = [
            TickMetrics(tick=i, sim_time=i * 0.1, wall_time_ms=float(i), active_drones=10)
            for i in range(10)
        ]
        assert result.max_tick_ms == 9.0

    def test_p95_p99(self):
        result = StressTestResult(config=StressTestConfig())
        result.tick_metrics = [
            TickMetrics(tick=i, sim_time=i * 0.1, wall_time_ms=float(i), active_drones=10)
            for i in range(100)
        ]
        assert result.p95_tick_ms >= 90.0
        assert result.p99_tick_ms >= 95.0

    def test_resolution_rate(self):
        result = StressTestResult(config=StressTestConfig())
        result.total_collisions = 5
        result.total_conflicts = 95
        assert abs(result.resolution_rate - 0.95) < 0.01

    def test_resolution_rate_no_events(self):
        result = StressTestResult(config=StressTestConfig())
        # 충돌+충돌위험 모두 0이면 collision_rate=0, resolution=1.0
        assert result.resolution_rate == 1.0

    def test_realtime_factor(self):
        result = StressTestResult(config=StressTestConfig(duration_s=60))
        result.total_wall_time_s = 30.0
        assert result.realtime_factor == 2.0

    def test_compare(self):
        r1 = StressTestRunner(n_drones=10, duration_s=0.5)
        r1.run_quick_benchmark(ticks=10)

        r2 = StressTestRunner(n_drones=20, duration_s=0.5)
        res2 = r2.run_quick_benchmark(ticks=10)

        cmp = r1.compare(res2)
        assert "avg_tick_ratio" in cmp

    def test_result_property(self):
        runner = StressTestRunner(n_drones=5)
        assert runner.result is None
        runner.run_quick_benchmark(ticks=5)
        assert runner.result is not None
        assert runner.result.completed
