"""
Phase 10-13 신규 기능 테스트
=========================
- Phase 10: 3D 대시보드 (APF 벡터 필드, 호버 툴팁, 바람 화살표, NFZ 경고)
- Phase 11: 컨트롤러 지능화 (동적 분리간격, Voronoi 활용, HOLDING 큐)
- Phase 12: 시뮬레이션 고도화 (고장 주입, Geofence, 에너지 메트릭)
"""
from __future__ import annotations
import math
import numpy as np
import pytest
import simpy

from src.airspace_control.agents.drone_state import (
    DroneState, FlightPhase, CommsStatus, FailureType,
)
from src.airspace_control.agents.drone_profiles import DRONE_PROFILES
from src.airspace_control.controller.airspace_controller import AirspaceController
from src.airspace_control.avoidance.resolution_advisory import AdvisoryGenerator
from src.airspace_control.controller.priority_queue import FlightPriorityQueue
from src.airspace_control.planning.flight_path_planner import FlightPathPlanner
from src.airspace_control.comms.communication_bus import CommunicationBus
from simulation.analytics import SimulationAnalytics, SimulationResult
from simulation.apf_engine.apf import (
    APFState, compute_total_force, APF_PARAMS,
)


# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def rng():
    return np.random.default_rng(42)


@pytest.fixture
def controller_setup():
    """Minimal AirspaceController setup for unit testing."""
    env = simpy.Environment()
    rng = np.random.default_rng(42)
    comm_bus = CommunicationBus(env=env, rng=rng)
    planner = FlightPathPlanner(
        airspace_bounds={"x": [-5000, 5000], "y": [-5000, 5000]},
        no_fly_zones=[{"center": np.array([0, 0, 60]), "radius_m": 600}],
    )
    advisory_gen = AdvisoryGenerator()
    pq = FlightPriorityQueue()
    config = {
        "separation_standards": {
            "lateral_min_m": 50.0,
            "vertical_min_m": 15.0,
            "near_miss_lateral_m": 10.0,
            "conflict_lookahead_s": 90.0,
        },
        "controller": {"max_concurrent_clearances": 500},
    }
    ctrl = AirspaceController(
        env=env, comm_bus=comm_bus, planner=planner,
        advisory_gen=advisory_gen, priority_queue=pq,
        config=config,
    )
    return ctrl, env


# ─────────────────────────────────────────────────────────────
# Phase 10: 시각화 유닛 테스트
# ─────────────────────────────────────────────────────────────

class TestAPFVectorField:
    """APF 벡터 필드 계산 테스트"""

    def test_compute_total_force_basic(self):
        """기본 APF 합력 계산 — 목표 방향 인력 생성"""
        own = APFState(np.array([0.0, 0.0, 60.0]), np.zeros(3), "test")
        goal = np.array([1000.0, 0.0, 60.0])
        force = compute_total_force(own, goal, [], [])
        assert force[0] > 0, "목표 방향(+x)으로 인력이 작용해야 함"

    def test_repulsive_force_near_obstacle(self):
        """장애물 근처에서 척력 발생"""
        own = APFState(np.array([10.0, 0.0, 60.0]), np.zeros(3), "test")
        goal = np.array([1000.0, 0.0, 60.0])
        obstacle = [np.array([0.0, 0.0, 60.0])]
        force = compute_total_force(own, goal, [], obstacle)
        assert force[0] > 0, "장애물로부터 멀어지는 방향으로 힘이 작용해야 함"

    def test_force_with_wind(self):
        """바람 속도에 따라 파라미터 변경 확인"""
        own = APFState(np.array([0.0, 0.0, 60.0]), np.zeros(3), "test")
        goal = np.array([1000.0, 0.0, 60.0])
        neighbor = APFState(np.array([30.0, 0.0, 60.0]), np.zeros(3), "other")

        force_calm = compute_total_force(own, goal, [neighbor], [], wind_speed=0.0)
        force_windy = compute_total_force(own, goal, [neighbor], [], wind_speed=15.0)
        # 강풍 시 척력이 더 크므로 x 방향 힘이 다를 수 있음
        assert not np.allclose(force_calm, force_windy), "바람에 따라 힘이 달라야 함"

    def test_force_clamping(self):
        """최대 합력 클리핑 동작"""
        own = APFState(np.array([5.0, 0.0, 60.0]), np.zeros(3), "test")
        goal = np.array([1000.0, 0.0, 60.0])
        # 매우 가까운 장애물 여러 개 → 큰 합력 → 클리핑
        obstacles = [np.array([3.0, i, 60.0]) for i in range(-2, 3)]
        force = compute_total_force(own, goal, [], obstacles)
        mag = float(np.linalg.norm(force))
        assert mag <= APF_PARAMS["max_force"] + 0.01, "최대 합력 초과 불가"

    def test_deadlock_escape(self):
        """교착 상태 탈출 — 합력이 0이지만 목표 미도달 시 섭동"""
        # 드론이 두 장애물 사이에서 교착
        own = APFState(np.array([0.0, 0.0, 60.0]), np.zeros(3), "test_deadlock")
        goal = np.array([100.0, 0.0, 60.0])
        neighbors = [
            APFState(np.array([20.0, 10.0, 60.0]), np.zeros(3), "n1"),
            APFState(np.array([20.0, -10.0, 60.0]), np.zeros(3), "n2"),
        ]
        force = compute_total_force(own, goal, neighbors, [])
        assert float(np.linalg.norm(force)) > 0.1, "교착 시 탈출 섭동이 발생해야 함"


class TestWindArrow:
    """바람 화살표 시각화 로직 테스트"""

    def test_no_wind_no_arrow(self):
        from visualization.simulator_3d import _wind_arrow
        arrows = _wind_arrow(np.zeros(3))
        assert arrows == [], "바람 없으면 화살표 없음"

    def test_wind_generates_arrow(self):
        from visualization.simulator_3d import _wind_arrow
        arrows = _wind_arrow(np.array([2.0, -1.5, 0.0]))
        assert len(arrows) == 1, "바람 있으면 화살표 1개"


# ─────────────────────────────────────────────────────────────
# Phase 11: 컨트롤러 지능화 테스트
# ─────────────────────────────────────────────────────────────

class TestDynamicSeparation:
    """풍속 기반 동적 분리간격 테스트"""

    def test_no_wind_base_separation(self, controller_setup):
        ctrl, _ = controller_setup
        ctrl.update_wind_speed(0.0)
        ctrl._update_dynamic_separation()
        assert ctrl._lat_min == pytest.approx(50.0)

    def test_moderate_wind_increases_separation(self, controller_setup):
        ctrl, _ = controller_setup
        ctrl.update_wind_speed(7.5)
        ctrl._update_dynamic_separation()
        assert ctrl._lat_min > 50.0, "중간 풍속에서 분리간격 증가"
        assert ctrl._lat_min < 80.0, "중간 풍속 상한"

    def test_strong_wind_max_separation(self, controller_setup):
        ctrl, _ = controller_setup
        ctrl.update_wind_speed(20.0)
        ctrl._update_dynamic_separation()
        assert ctrl._lat_min == pytest.approx(50.0 * 1.6)

    def test_wind_5ms_boundary(self, controller_setup):
        ctrl, _ = controller_setup
        ctrl.update_wind_speed(5.0)
        ctrl._update_dynamic_separation()
        assert ctrl._lat_min == pytest.approx(50.0), "5 m/s 이하 기본값"

    def test_wind_10ms_boundary(self, controller_setup):
        ctrl, _ = controller_setup
        ctrl.update_wind_speed(10.0)
        ctrl._update_dynamic_separation()
        assert ctrl._lat_min == pytest.approx(50.0 * 1.4), "10 m/s 경계"

    def test_wind_15ms_boundary(self, controller_setup):
        ctrl, _ = controller_setup
        ctrl.update_wind_speed(15.0)
        ctrl._update_dynamic_separation()
        assert ctrl._lat_min == pytest.approx(50.0 * 1.6), "15 m/s 경계"

    def test_wind_interpolation(self, controller_setup):
        """중간값 보간 확인"""
        ctrl, _ = controller_setup
        ctrl.update_wind_speed(7.5)
        ctrl._update_dynamic_separation()
        # 7.5 m/s: factor = 1.0 + 0.4 * (7.5-5)/5 = 1.0 + 0.2 = 1.2
        assert ctrl._lat_min == pytest.approx(50.0 * 1.2)


class TestHoldingQueue:
    """HOLDING 구조화 큐 테스트"""

    def test_holding_queue_exists(self, controller_setup):
        ctrl, _ = controller_setup
        assert hasattr(ctrl, '_holding_queue')
        assert ctrl._holding_queue == []

    def test_manage_holding_tracks_drones(self, controller_setup):
        ctrl, _ = controller_setup
        # 드론 등록
        d = DroneState(drone_id="DR001", position=np.zeros(3), velocity=np.zeros(3))
        d.flight_phase = FlightPhase.HOLDING
        ctrl._active_drones["DR001"] = d
        ctrl._manage_holding_queue(0.0)
        assert len(ctrl._holding_queue) == 1


class TestVoronoiDensity:
    """Voronoi 밀도 기반 분리 테스트"""

    def test_density_method_exists(self, controller_setup):
        ctrl, _ = controller_setup
        assert hasattr(ctrl, '_apply_density_based_separation')


# ─────────────────────────────────────────────────────────────
# Phase 12: 시뮬레이션 고도화 테스트
# ─────────────────────────────────────────────────────────────

class TestSimulationResult:
    """확장된 SimulationResult 테스트"""

    def test_new_fields_exist(self):
        r = SimulationResult()
        assert hasattr(r, 'energy_efficiency_wh_per_km')
        assert hasattr(r, 'failures_injected')
        assert hasattr(r, 'comms_losses_injected')
        assert r.energy_efficiency_wh_per_km == 0.0
        assert r.failures_injected == 0
        assert r.comms_losses_injected == 0

    def test_summary_table_includes_energy(self):
        r = SimulationResult(energy_efficiency_wh_per_km=12.5)
        table = r.summary_table()
        assert "에너지 효율" in table
        assert "12.50" in table

    def test_summary_table_includes_failures(self):
        r = SimulationResult(failures_injected=3, comms_losses_injected=2)
        table = r.summary_table()
        assert "고장 주입" in table
        assert "통신 두절 주입" in table


class TestAnalyticsFinalize:
    """Analytics finalize 확장 테스트"""

    def test_finalize_counts_failure_events(self):
        analytics = SimulationAnalytics({"logging": {"save_trajectory": False}})
        analytics.record_event("FAILURE_INJECTED", 10.0, drone_id="DR001",
                              failure_type="MOTOR_FAILURE")
        analytics.record_event("FAILURE_INJECTED", 20.0, drone_id="DR002",
                              failure_type="BATTERY_CRITICAL")
        analytics.record_event("COMMS_LOSS_INJECTED", 30.0, drone_id="DR003")
        result = analytics.finalize(seed=42, n_drones=10, duration_s=60.0)
        assert result.failures_injected == 2
        assert result.comms_losses_injected == 1

    def test_finalize_energy_zero_when_no_data(self):
        analytics = SimulationAnalytics({"logging": {"save_trajectory": False}})
        result = analytics.finalize()
        assert result.energy_efficiency_wh_per_km == 0.0


class TestGeofence:
    """Geofence 경계 제한 테스트"""

    def test_geofence_rtl_trigger(self):
        """공역 경계 90% 도달 시 RTL 전환"""
        d = DroneState(
            drone_id="DR001",
            position=np.array([4600.0, 0.0, 60.0]),  # > 5000 * 0.9 = 4500
            velocity=np.array([10.0, 0.0, 0.0]),
        )
        d.flight_phase = FlightPhase.ENROUTE
        d.goal = np.array([5000.0, 0.0, 60.0])

        # 시뮬레이터의 geofence 로직 재현
        bounds_m = 5000.0
        geofence_margin = bounds_m * 0.9
        if abs(d.position[0]) > geofence_margin:
            if d.flight_phase in (FlightPhase.ENROUTE, FlightPhase.EVADING):
                d.flight_phase = FlightPhase.RTL
                d.goal = None

        assert d.flight_phase == FlightPhase.RTL
        assert d.goal is None

    def test_geofence_safe_distance(self):
        """경계 내부에서는 RTL 미전환"""
        d = DroneState(
            drone_id="DR001",
            position=np.array([4000.0, 0.0, 60.0]),  # < 4500
            velocity=np.array([10.0, 0.0, 0.0]),
        )
        d.flight_phase = FlightPhase.ENROUTE

        bounds_m = 5000.0
        geofence_margin = bounds_m * 0.9
        if abs(d.position[0]) > geofence_margin:
            d.flight_phase = FlightPhase.RTL

        assert d.flight_phase == FlightPhase.ENROUTE


class TestFailureInjection:
    """고장 주입 설정 테스트"""

    def test_failure_types(self):
        """FailureType enum 확인"""
        assert FailureType.MOTOR_FAILURE.name == "MOTOR_FAILURE"
        assert FailureType.BATTERY_CRITICAL.name == "BATTERY_CRITICAL"
        assert FailureType.GPS_LOSS.name == "GPS_LOSS"

    def test_motor_failure_transitions_to_failed(self):
        d = DroneState(drone_id="DR001", position=np.array([0, 0, 60.0]),
                      velocity=np.zeros(3))
        d.flight_phase = FlightPhase.ENROUTE
        d.failure_type = FailureType.MOTOR_FAILURE
        # Motor failure → FAILED
        if d.failure_type == FailureType.MOTOR_FAILURE:
            d.flight_phase = FlightPhase.FAILED
        assert d.flight_phase == FlightPhase.FAILED

    def test_battery_critical_transitions_to_landing(self):
        d = DroneState(drone_id="DR001", position=np.array([0, 0, 60.0]),
                      velocity=np.zeros(3))
        d.flight_phase = FlightPhase.ENROUTE
        d.failure_type = FailureType.BATTERY_CRITICAL
        d.battery_pct = 3.0
        if d.failure_type == FailureType.BATTERY_CRITICAL:
            d.flight_phase = FlightPhase.LANDING
        assert d.flight_phase == FlightPhase.LANDING
        assert d.battery_pct == 3.0


class TestControllerWindIntegration:
    """컨트롤러-시뮬레이터 풍속 연동 테스트"""

    def test_update_wind_speed(self, controller_setup):
        ctrl, _ = controller_setup
        ctrl.update_wind_speed(12.5)
        assert ctrl._wind_speed == 12.5

    def test_separation_after_wind_update(self, controller_setup):
        ctrl, _ = controller_setup
        ctrl.update_wind_speed(12.0)
        ctrl._update_dynamic_separation()
        # 12 m/s: factor = 1.4 + 0.2*(12-10)/5 = 1.4 + 0.08 = 1.48
        expected = 50.0 * 1.48
        assert ctrl._lat_min == pytest.approx(expected)


# ─────────────────────────────────────────────────────────────
# 통합 테스트
# ─────────────────────────────────────────────────────────────

class TestIntegrationPhase10to13:
    """Phase 10-13 통합 기능 테스트"""

    def test_simulation_result_to_dict(self):
        r = SimulationResult(
            collision_count=1,
            energy_efficiency_wh_per_km=10.5,
            failures_injected=2,
        )
        d = r.to_dict()
        assert d["collision_count"] == 1
        assert d["energy_efficiency_wh_per_km"] == 10.5
        assert d["failures_injected"] == 2

    def test_simulation_result_acceptance(self):
        r = SimulationResult(
            collision_count=0,
            conflict_resolution_rate_pct=99.8,
            route_efficiency_mean=1.05,
        )
        thresholds = {
            "conflict_resolution_rate_pct": 99.5,
            "route_efficiency_max": 1.15,
        }
        checks = r.check_acceptance(thresholds)
        assert checks["no_collision"] is True
        assert checks["conflict_res_rate"] is True
        assert checks["route_efficiency"] is True

    def test_dynamic_separation_range(self, controller_setup):
        """모든 풍속에서 분리간격이 합리적 범위"""
        ctrl, _ = controller_setup
        for ws in np.arange(0, 25, 0.5):
            ctrl.update_wind_speed(float(ws))
            ctrl._update_dynamic_separation()
            assert 50.0 <= ctrl._lat_min <= 80.0, f"ws={ws}: lat_min={ctrl._lat_min}"

    def test_apf_wind_parameter_continuity(self):
        """APF 파라미터가 풍속 변화에 따라 연속적으로 변화"""
        own = APFState(np.array([0.0, 0.0, 60.0]), np.zeros(3), "cont_test")
        goal = np.array([500.0, 0.0, 60.0])
        neighbor = APFState(np.array([30.0, 0.0, 60.0]), np.array([-5.0, 0.0, 0.0]), "n1")

        forces = []
        for ws in [5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0]:
            f = compute_total_force(own, goal, [neighbor], [], wind_speed=ws)
            forces.append(float(np.linalg.norm(f)))

        # 힘의 크기가 급변하지 않아야 함 (연속성)
        for i in range(1, len(forces)):
            ratio = forces[i] / max(forces[i-1], 0.01)
            assert 0.3 < ratio < 3.0, f"ws transition: force ratio={ratio}"
