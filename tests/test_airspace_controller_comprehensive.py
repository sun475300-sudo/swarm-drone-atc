"""
AirspaceController 포괄적 단위 테스트
_pick_target, _threat_level, _point_in_polygon,
_check_voronoi_conflict, _detect_intruders, _scan_conflicts 커버
"""
from __future__ import annotations

import numpy as np
import pytest
import simpy

from src.airspace_control.agents.drone_state import DroneState, FlightPhase
from src.airspace_control.agents.drone_profiles import DRONE_PROFILES
from src.airspace_control.comms.communication_bus import CommunicationBus, CommMessage
from src.airspace_control.comms.message_types import (
    TelemetryMessage, ClearanceRequest, IntrusionAlert,
)
from src.airspace_control.controller.priority_queue import FlightPriorityQueue
from src.airspace_control.controller.airspace_controller import (
    AirspaceController, _point_in_polygon,
)
from src.airspace_control.planning.flight_path_planner import FlightPathPlanner
from src.airspace_control.avoidance.resolution_advisory import AdvisoryGenerator


@pytest.fixture
def env():
    return simpy.Environment()


@pytest.fixture
def config():
    return {
        "separation_standards": {
            "lateral_min_m": 50.0,
            "vertical_min_m": 15.0,
            "near_miss_lateral_m": 10.0,
            "conflict_lookahead_s": 90.0,
        },
        "controller": {"max_concurrent_clearances": 50},
        "airspace": {"bounds_km": {"x": [-2, 2], "y": [-2, 2]}},
    }


@pytest.fixture
def controller(env, config):
    rng = np.random.default_rng(42)
    bus = CommunicationBus(env, rng)
    bounds = {"x": [-2000, 2000], "y": [-2000, 2000], "z": [0, 200]}
    planner = FlightPathPlanner(bounds, [])
    adv_gen = AdvisoryGenerator()
    pq = FlightPriorityQueue()
    return AirspaceController(env, bus, planner, adv_gen, pq, config)


# ── _point_in_polygon 테스트 ──────────────────────────────────────────────


class TestPointInPolygon:
    def test_inside_square(self):
        verts = [[0, 0], [10, 0], [10, 10], [0, 10]]
        assert _point_in_polygon(np.array([5, 5]), verts) is True

    def test_outside_square(self):
        verts = [[0, 0], [10, 0], [10, 10], [0, 10]]
        assert _point_in_polygon(np.array([15, 5]), verts) is False

    def test_triangle(self):
        verts = [[0, 0], [10, 0], [5, 10]]
        assert _point_in_polygon(np.array([5, 3]), verts) is True
        assert _point_in_polygon(np.array([0, 10]), verts) is False

    def test_on_edge(self):
        """경계 위의 점 (구현에 따라 True/False 가능)"""
        verts = [[0, 0], [10, 0], [10, 10], [0, 10]]
        result = _point_in_polygon(np.array([5, 0]), verts)
        assert isinstance(result, bool)


# ── _pick_target 테스트 ───────────────────────────────────────────────────


class TestPickTarget:
    def test_lower_priority_gets_advisory(self, controller):
        """우선순위가 낮은 드론이 어드바이저리 대상"""
        da = DroneState(drone_id="D_EMERG", position=np.zeros(3),
                        velocity=np.zeros(3), profile_name="EMERGENCY")
        db = DroneState(drone_id="D_COMM", position=np.zeros(3),
                        velocity=np.zeros(3), profile_name="COMMERCIAL_DELIVERY")
        target = controller._pick_target(da, db)
        # EMERGENCY priority=1, COMMERCIAL_DELIVERY priority=2
        # 높은 숫자 = 낮은 우선순위
        assert target.drone_id == "D_COMM"

    def test_same_priority(self, controller):
        da = DroneState(drone_id="D_A", position=np.zeros(3),
                        velocity=np.zeros(3), profile_name="COMMERCIAL_DELIVERY")
        db = DroneState(drone_id="D_B", position=np.zeros(3),
                        velocity=np.zeros(3), profile_name="COMMERCIAL_DELIVERY")
        target = controller._pick_target(da, db)
        # 동일 우선순위면 da 반환 (pri_a >= pri_b)
        assert target.drone_id == "D_A"

    def test_unknown_profile_defaults(self, controller):
        """알 수 없는 프로필이면 COMMERCIAL_DELIVERY 기본값"""
        da = DroneState(drone_id="D_A", position=np.zeros(3),
                        velocity=np.zeros(3), profile_name="UNKNOWN_PROFILE")
        db = DroneState(drone_id="D_B", position=np.zeros(3),
                        velocity=np.zeros(3), profile_name="EMERGENCY")
        target = controller._pick_target(da, db)
        # UNKNOWN → COMMERCIAL_DELIVERY(pri=2) >= EMERGENCY(pri=1)
        assert target.drone_id == "D_A"


# ── _threat_level 테스트 ──────────────────────────────────────────────────


class TestThreatLevel:
    def _setup_drones(self, controller, intruder_pos, other_positions):
        intruder = DroneState(
            drone_id="INTRUDER", position=np.array(intruder_pos),
            velocity=np.zeros(3), flight_phase=FlightPhase.ENROUTE,
        )
        controller._active_drones["INTRUDER"] = intruder
        for i, pos in enumerate(other_positions):
            d = DroneState(
                drone_id=f"D{i}", position=np.array(pos),
                velocity=np.zeros(3), flight_phase=FlightPhase.ENROUTE,
            )
            controller._active_drones[f"D{i}"] = d
        return intruder

    def test_critical(self, controller):
        intruder = self._setup_drones(controller, [0, 0, 60], [[50, 0, 60]])
        assert controller._threat_level(intruder) == "CRITICAL"

    def test_high(self, controller):
        intruder = self._setup_drones(controller, [0, 0, 60], [[200, 0, 60]])
        assert controller._threat_level(intruder) == "HIGH"

    def test_medium(self, controller):
        intruder = self._setup_drones(controller, [0, 0, 60], [[500, 0, 60]])
        assert controller._threat_level(intruder) == "MEDIUM"

    def test_low(self, controller):
        intruder = self._setup_drones(controller, [0, 0, 60], [[2000, 0, 60]])
        assert controller._threat_level(intruder) == "LOW"

    def test_no_other_drones(self, controller):
        """다른 드론이 없으면 LOW"""
        intruder = DroneState(
            drone_id="INTRUDER", position=np.array([0, 0, 60]),
            velocity=np.zeros(3),
        )
        controller._active_drones["INTRUDER"] = intruder
        assert controller._threat_level(intruder) == "LOW"


# ── _expire_advisories 테스트 ─────────────────────────────────────────────


class TestExpireAdvisories:
    def test_expired_removed(self, controller):
        from src.airspace_control.comms.message_types import ResolutionAdvisory
        adv = ResolutionAdvisory(
            advisory_id="ADV-TEST", target_drone_id="D0",
            advisory_type="CLIMB", magnitude=20.0,
            duration_s=10.0, timestamp_s=0.0, conflict_pair="D1",
        )
        controller._advisories["ADV-TEST"] = adv
        controller._expire_advisories(t=20.0)
        assert "ADV-TEST" not in controller._advisories

    def test_active_not_removed(self, controller):
        from src.airspace_control.comms.message_types import ResolutionAdvisory
        adv = ResolutionAdvisory(
            advisory_id="ADV-TEST", target_drone_id="D0",
            advisory_type="CLIMB", magnitude=20.0,
            duration_s=100.0, timestamp_s=0.0, conflict_pair="D1",
        )
        controller._advisories["ADV-TEST"] = adv
        controller._expire_advisories(t=20.0)
        assert "ADV-TEST" in controller._advisories


# ── _update_drone_state 테스트 ────────────────────────────────────────────


class TestUpdateDroneState:
    def test_new_drone_registered(self, controller):
        tm = TelemetryMessage(
            drone_id="NEW_D", position=[100, 200, 60],
            velocity=[5, 0, 0], battery_pct=95.0,
            flight_phase="ENROUTE", timestamp_s=10.0,
        )
        controller._update_drone_state(tm)
        assert "NEW_D" in controller._active_drones
        d = controller._active_drones["NEW_D"]
        assert d.last_update_s == 10.0
        assert np.allclose(d.position, [100, 200, 60])

    def test_existing_drone_updated(self, controller):
        tm1 = TelemetryMessage(
            drone_id="D0", position=[0, 0, 60],
            velocity=[0, 0, 0], battery_pct=100.0,
            flight_phase="ENROUTE", timestamp_s=0.0,
        )
        controller._update_drone_state(tm1)

        tm2 = TelemetryMessage(
            drone_id="D0", position=[100, 0, 60],
            velocity=[10, 0, 0], battery_pct=90.0,
            flight_phase="ENROUTE", timestamp_s=10.0,
        )
        controller._update_drone_state(tm2)
        d = controller._active_drones["D0"]
        assert d.position[0] == pytest.approx(100.0)
        assert d.battery_pct == pytest.approx(90.0)

    def test_invalid_flight_phase_ignored(self, controller):
        tm = TelemetryMessage(
            drone_id="D0", position=[0, 0, 60],
            velocity=[0, 0, 0], battery_pct=100.0,
            flight_phase="INVALID_PHASE", timestamp_s=0.0,
        )
        controller._update_drone_state(tm)
        # KeyError가 발생하지 않아야 함
        assert "D0" in controller._active_drones


# ── _check_voronoi_conflict 테스트 ────────────────────────────────────────


class TestCheckVoronoiConflict:
    def test_no_cells_returns_empty(self, controller):
        result = controller._check_voronoi_conflict("D0", np.array([0, 0, 60]))
        assert result == ""

    def test_own_cell_not_conflict(self, controller):
        """자신의 셀 안에 목적지가 있으면 충돌 아님"""
        class FakeCell:
            vertices = [[0, 0], [100, 0], [100, 100], [0, 100]]
        controller._voronoi_cells = {"D0": FakeCell()}
        result = controller._check_voronoi_conflict("D0", np.array([50, 50, 60]))
        assert result == ""

    def test_other_cell_is_conflict(self, controller):
        """다른 드론의 셀 안에 목적지가 있으면 충돌"""
        class FakeCell:
            vertices = [[0, 0], [100, 0], [100, 100], [0, 100]]
        controller._voronoi_cells = {"D_OTHER": FakeCell()}
        result = controller._check_voronoi_conflict("D0", np.array([50, 50, 60]))
        assert result == "D_OTHER"


# ── _detect_intruders 테스트 ──────────────────────────────────────────────


class TestDetectIntruders:
    def test_rogue_detected(self, controller, env):
        """ROGUE 프로필 드론이 침입자로 탐지"""
        d = DroneState(
            drone_id="ROGUE_D", position=np.array([0, 0, 60]),
            velocity=np.zeros(3), flight_phase=FlightPhase.ENROUTE,
            profile_name="ROGUE",
        )
        controller._active_drones["ROGUE_D"] = d
        delivered = []
        controller.comm_bus.subscribe("BROADCAST", lambda msg: delivered.append(msg))

        controller._detect_intruders(t=10.0)
        assert "ROGUE_D" in controller._intruders

    def test_non_rogue_not_detected(self, controller):
        d = DroneState(
            drone_id="NORMAL_D", position=np.array([0, 0, 60]),
            velocity=np.zeros(3), flight_phase=FlightPhase.ENROUTE,
            profile_name="COMMERCIAL_DELIVERY",
        )
        controller._active_drones["NORMAL_D"] = d
        controller._detect_intruders(t=10.0)
        assert "NORMAL_D" not in controller._intruders

    def test_already_detected_not_repeated(self, controller):
        """이미 탐지된 침입자는 다시 탐지하지 않음"""
        d = DroneState(
            drone_id="ROGUE_D", position=np.array([0, 0, 60]),
            velocity=np.zeros(3), flight_phase=FlightPhase.ENROUTE,
            profile_name="ROGUE",
        )
        controller._active_drones["ROGUE_D"] = d
        controller._intruders.add("ROGUE_D")

        # send를 모니터링하기 위해 sent count 확인
        initial_sent = controller.comm_bus.stats["sent"]
        controller._detect_intruders(t=10.0)
        assert controller.comm_bus.stats["sent"] == initial_sent


# ── _scan_conflicts 테스트 ────────────────────────────────────────────────


class TestScanConflicts:
    def test_no_conflict_separated(self, controller):
        """거리가 먼 드론 → 충돌 없음"""
        for i, x in enumerate([0, 2000]):
            d = DroneState(
                drone_id=f"D{i}", position=np.array([x, 0, 60], dtype=float),
                velocity=np.array([0, 0, 0], dtype=float),
                flight_phase=FlightPhase.ENROUTE,
            )
            controller._active_drones[f"D{i}"] = d
        initial = controller.comm_bus.stats["sent"]
        controller._scan_conflicts(t=10.0)
        # 어드바이저리가 발령되지 않아야 함
        assert controller.comm_bus.stats["sent"] == initial

    def test_conflict_when_close_approaching(self, controller):
        """가까이 접근 중인 드론 → 어드바이저리 발령"""
        d0 = DroneState(
            drone_id="D0", position=np.array([0, 0, 60], dtype=float),
            velocity=np.array([10, 0, 0], dtype=float),
            flight_phase=FlightPhase.ENROUTE,
            profile_name="COMMERCIAL_DELIVERY",
        )
        d1 = DroneState(
            drone_id="D1", position=np.array([30, 0, 60], dtype=float),
            velocity=np.array([-10, 0, 0], dtype=float),
            flight_phase=FlightPhase.ENROUTE,
            profile_name="COMMERCIAL_DELIVERY",
        )
        controller._active_drones["D0"] = d0
        controller._active_drones["D1"] = d1
        controller._scan_conflicts(t=10.0)
        assert len(controller._advisories) > 0

    def test_single_drone_no_scan(self, controller):
        """드론 1대이면 스캔 안 함"""
        d = DroneState(
            drone_id="D0", position=np.array([0, 0, 60], dtype=float),
            velocity=np.zeros(3), flight_phase=FlightPhase.ENROUTE,
        )
        controller._active_drones["D0"] = d
        controller._scan_conflicts(t=10.0)
        assert len(controller._advisories) == 0


# ── _on_message 테스트 ────────────────────────────────────────────────────


class TestOnMessage:
    def test_telemetry_received(self, controller):
        tm = TelemetryMessage(
            drone_id="D0", position=[0, 0, 60],
            velocity=[0, 0, 0], battery_pct=100.0,
            flight_phase="ENROUTE", timestamp_s=0.0,
        )
        msg = CommMessage("D0", "CONTROLLER", tm, 0.0)
        controller._on_message(msg)
        assert "D0" in controller._active_drones

    def test_clearance_request_queued(self, controller):
        cr = ClearanceRequest(
            drone_id="D0", origin=np.array([0, 0, 0]),
            destination=np.array([1000, 0, 0]),
            priority=2, timestamp_s=0.0,
            profile_name="COMMERCIAL_DELIVERY",
        )
        msg = CommMessage("D0", "CONTROLLER", cr, 0.0)
        controller._on_message(msg)
        assert len(controller._pending) == 1
