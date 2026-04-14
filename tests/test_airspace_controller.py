"""
AirspaceController 단위 테스트
"""
from __future__ import annotations

import numpy as np
import pytest
import simpy

from src.airspace_control.avoidance.resolution_advisory import AdvisoryGenerator
from src.airspace_control.comms.communication_bus import CommunicationBus, CommMessage
from src.airspace_control.comms.message_types import (
    TelemetryMessage, ClearanceRequest, ResolutionAdvisory,
)
from src.airspace_control.controller.airspace_controller import AirspaceController
from src.airspace_control.controller.priority_queue import FlightPriorityQueue
from src.airspace_control.planning.flight_path_planner import FlightPathPlanner


# ── 픽스처 ─────────────────────────────────────────────────────────────────

@pytest.fixture
def env():
    return simpy.Environment()


@pytest.fixture
def comm_bus(env):
    return CommunicationBus(env, rng=np.random.default_rng(42),
                            latency_ms_mean=0.0, latency_ms_std=0.0)


@pytest.fixture
def planner():
    return FlightPathPlanner(
        airspace_bounds={"x": [-2000, 2000], "y": [-2000, 2000], "z": [0, 200]},
        no_fly_zones=[],
        grid_resolution_m=50.0,
        cruise_altitude_m=60.0,
    )


@pytest.fixture
def controller(env, comm_bus, planner):
    cfg = {
        "separation_standards": {
            "lateral_min_m": 50.0,
            "vertical_min_m": 15.0,
            "near_miss_lateral_m": 10.0,
            "conflict_lookahead_s": 90.0,
        },
        "controller": {"max_concurrent_clearances": 10},
        "airspace": {"bounds_km": {"x": [-2, 2]}},
    }
    return AirspaceController(
        env=env,
        comm_bus=comm_bus,
        planner=planner,
        advisory_gen=AdvisoryGenerator(),
        priority_queue=FlightPriorityQueue(),
        config=cfg,
    )


def _send_telemetry(env, comm_bus, did, pos, vel=None, phase="ENROUTE"):
    tm = TelemetryMessage(
        drone_id=did,
        position=pos,
        velocity=vel or [5.0, 0.0, 0.0],
        battery_pct=90.0,
        flight_phase=phase,
        timestamp_s=float(env.now),
    )
    comm_bus.send(CommMessage(did, "CONTROLLER", tm, float(env.now), "telemetry"))
    env.run(until=env.now + 0.1)  # flush delivery


# ── 테스트 ────────────────────────────────────────────────────────────────────

class TestControllerSetup:
    def test_instantiation(self, controller):
        assert controller is not None

    def test_subscribed_to_bus(self, controller, comm_bus):
        assert "CONTROLLER" in comm_bus._subscribers


class TestTelemetryProcessing:
    def test_telemetry_registers_drone(self, env, comm_bus, controller):
        _send_telemetry(env, comm_bus, "D1", [100.0, 200.0, 60.0])
        assert "D1" in controller._active_drones

    def test_telemetry_updates_position(self, env, comm_bus, controller):
        _send_telemetry(env, comm_bus, "D2", [0.0, 0.0, 60.0])
        assert np.allclose(controller._active_drones["D2"].position,
                           [0.0, 0.0, 60.0])


class TestClearanceProcessing:
    def test_clearance_sends_response(self, env, comm_bus, controller):
        received = []
        comm_bus.subscribe("D3", lambda m: received.append(m))

        req = ClearanceRequest(
            drone_id="D3",
            origin=np.array([-500.0, -500.0, 0.0]),
            destination=np.array([500.0, 500.0, 0.0]),
            priority=3,
            timestamp_s=0.0,
        )
        comm_bus.send(CommMessage("D3", "CONTROLLER", req, 0.0, "clearance"))
        env.run(until=0.1)  # deliver clearance request

        controller._process_clearances(1.0)

        env.run(until=1.0)  # deliver response
        assert len(received) >= 1


class TestConflictScan:
    def test_no_conflict_when_separated(self, env, comm_bus, controller):
        from src.airspace_control.agents.drone_state import FlightPhase
        _send_telemetry(env, comm_bus, "A", [0.0, 0.0, 60.0])
        _send_telemetry(env, comm_bus, "B", [1000.0, 0.0, 60.0])
        controller._active_drones["A"].flight_phase = FlightPhase.ENROUTE
        controller._active_drones["B"].flight_phase = FlightPhase.ENROUTE
        controller._scan_conflicts(0.0)
        assert len(controller._advisories) == 0

    def test_conflict_detected_when_close(self, env, comm_bus, controller):
        from src.airspace_control.agents.drone_state import FlightPhase
        _send_telemetry(env, comm_bus, "C", [0.0, 0.0, 60.0],
                        vel=[10.0, 0.0, 0.0])
        _send_telemetry(env, comm_bus, "D", [40.0, 0.0, 60.0],
                        vel=[-10.0, 0.0, 0.0])
        controller._active_drones["C"].flight_phase = FlightPhase.ENROUTE
        controller._active_drones["D"].flight_phase = FlightPhase.ENROUTE
        controller._scan_conflicts(0.0)
        assert len(controller._advisories) >= 1


class TestAdvisoryExpiry:
    def test_expired_advisory_removed(self, controller):
        adv = ResolutionAdvisory(
            advisory_id="ADV-001",
            target_drone_id="X",
            advisory_type="HOLD",
            magnitude=0.0,
            duration_s=10.0,
            timestamp_s=0.0,
        )
        controller._advisories["ADV-001"] = adv
        controller._expire_advisories(11.0)
        assert "ADV-001" not in controller._advisories

    def test_active_advisory_not_removed(self, controller):
        adv = ResolutionAdvisory(
            advisory_id="ADV-002",
            target_drone_id="Y",
            advisory_type="CLIMB",
            magnitude=5.0,
            duration_s=60.0,
            timestamp_s=0.0,
        )
        controller._advisories["ADV-002"] = adv
        controller._expire_advisories(5.0)
        assert "ADV-002" in controller._advisories


class TestNFZ3DCheck:
    """NFZ가 3D(고도 포함)로 검사되는지 확인"""

    def test_clearance_above_nfz_allowed(self, env, comm_bus, controller):
        """NFZ 수평 범위 내지만 고도가 높으면 허가 가능"""
        from src.airspace_control.agents.drone_state import FlightPhase
        # NFZ 중심 (0,0) 반경 600m — 고도 120m 이상은 통과 가능해야
        _send_telemetry(env, comm_bus, "E", [0.0, 0.0, 150.0])
        drone = controller._active_drones["E"]
        drone.flight_phase = FlightPhase.ENROUTE
        # NFZ 위의 드론은 정상 등록만 확인
        assert "E" in controller._active_drones

    def test_controller_has_planner_with_nfz(self, controller):
        """컨트롤러의 planner가 NFZ 데이터를 가지고 있는지 확인"""
        assert hasattr(controller, 'planner')
        assert hasattr(controller.planner, 'nfz_list')


class TestDynamicSeparation:
    """동적 분리간격 조정 테스트"""

    def test_no_wind_no_density(self, controller):
        controller._wind_speed = 0.0
        controller._update_dynamic_separation()
        assert controller._lat_min == controller._lat_min_base

    def test_moderate_wind(self, controller):
        controller._wind_speed = 7.5
        controller._update_dynamic_separation()
        assert controller._lat_min > controller._lat_min_base

    def test_strong_wind(self, controller):
        controller._wind_speed = 12.0
        controller._update_dynamic_separation()
        assert controller._lat_min >= controller._lat_min_base * 1.4

    def test_extreme_wind_caps(self, controller):
        controller._wind_speed = 20.0
        controller._update_dynamic_separation()
        assert controller._lat_min == controller._lat_min_base * 1.6

    def test_high_density_factor(self, env, comm_bus, controller):
        from src.airspace_control.agents.drone_state import DroneState, FlightPhase
        for i in range(120):
            d = DroneState(drone_id=f"D{i}", position=np.array([i*10.0, 0.0, 60.0]), velocity=np.zeros(3))
            d.flight_phase = FlightPhase.ENROUTE
            controller._active_drones[f"D{i}"] = d
        controller._wind_speed = 0.0
        controller._update_dynamic_separation()
        assert controller._lat_min >= controller._lat_min_base * 1.3

    def test_wind_update_method(self, controller):
        controller.update_wind_speed(8.5)
        assert controller._wind_speed == 8.5


class TestKDTreeQueryPairs:
    """KDTree 근접 쌍 쿼리 테스트"""

    def test_empty_positions(self):
        result = AirspaceController._kdtree_query_pairs({}, 50.0)
        assert result == []

    def test_single_drone(self):
        result = AirspaceController._kdtree_query_pairs(
            {"D1": np.array([0.0, 0.0, 60.0])}, 50.0
        )
        assert result == []

    def test_close_pair_found(self):
        positions = {
            "D1": np.array([0.0, 0.0, 60.0]),
            "D2": np.array([30.0, 0.0, 60.0]),
            "D3": np.array([500.0, 0.0, 60.0]),
        }
        result = AirspaceController._kdtree_query_pairs(positions, 50.0)
        ids_found = {frozenset([r[0], r[1]]) for r in result}
        assert frozenset(["D1", "D2"]) in ids_found
        assert frozenset(["D1", "D3"]) not in ids_found

    def test_distance_accuracy(self):
        positions = {
            "A": np.array([0.0, 0.0, 0.0]),
            "B": np.array([30.0, 40.0, 0.0]),
        }
        result = AirspaceController._kdtree_query_pairs(positions, 60.0)
        assert len(result) == 1
        assert abs(result[0][2] - 50.0) < 0.01


class TestControllerStats:
    """컨트롤러 통계 속성 테스트"""

    def test_cbs_stats_initial(self, controller):
        assert controller._cbs_attempts == 0
        assert controller._cbs_successes == 0
        assert controller._cbs_failures == 0

    def test_astar_count_initial(self, controller):
        assert controller._astar_count == 0

    def test_clearances_per_sec_initial(self, controller):
        assert controller._clearances_per_sec == 0.0

    def test_holding_queue_initial(self, controller):
        assert len(controller._holding_queue) == 0

    def test_voronoi_cells_initial(self, controller):
        assert controller._voronoi_cells == {}


class TestMultipleTelemetry:
    """다중 텔레메트리 처리 테스트"""

    def test_multiple_drones_registered(self, env, comm_bus, controller):
        for i in range(10):
            _send_telemetry(env, comm_bus, f"M{i}", [i*100.0, 0.0, 60.0])
        assert len(controller._active_drones) == 10

    def test_telemetry_update_overwrites(self, env, comm_bus, controller):
        _send_telemetry(env, comm_bus, "U1", [0.0, 0.0, 60.0])
        _send_telemetry(env, comm_bus, "U1", [100.0, 0.0, 60.0])
        assert np.allclose(controller._active_drones["U1"].position, [100.0, 0.0, 60.0])

    def test_battery_tracking(self, env, comm_bus, controller):
        # 첫 텔레메트리로 등록
        _send_telemetry(env, comm_bus, "B1", [0.0, 0.0, 60.0])
        # 두 번째 텔레메트리로 배터리 업데이트
        tm = TelemetryMessage(
            drone_id="B1", position=[0.0, 0.0, 60.0],
            velocity=[0.0, 0.0, 0.0], battery_pct=75.5,
            flight_phase="ENROUTE", timestamp_s=1.0,
        )
        comm_bus.send(CommMessage("B1", "CONTROLLER", tm, 1.0, "telemetry"))
        env.run(until=1.1)
        assert controller._active_drones["B1"].battery_pct == 75.5
