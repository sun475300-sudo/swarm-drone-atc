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


class TestROGUEGuard:
    """ROGUE 드론 어드바이저리 차단 테스트"""

    def test_rogue_not_advisory_target(self, env, comm_bus, controller):
        """ROGUE+등록 쌍 → 등록 드론만 어드바이저리 수신"""
        from src.airspace_control.agents.drone_state import FlightPhase
        _send_telemetry(env, comm_bus, "REG1", [0.0, 0.0, 60.0],
                        vel=[10.0, 0.0, 0.0])
        _send_telemetry(env, comm_bus, "ROGUE1", [40.0, 0.0, 60.0],
                        vel=[-10.0, 0.0, 0.0], phase="ENROUTE")
        controller._active_drones["REG1"].flight_phase = FlightPhase.ENROUTE
        controller._active_drones["ROGUE1"].flight_phase = FlightPhase.ENROUTE
        controller._active_drones["ROGUE1"].profile_name = "ROGUE"
        controller._scan_conflicts(0.0)
        for adv in controller._advisories.values():
            assert adv.target_drone_id == "REG1"

    def test_rogue_rogue_skip(self, env, comm_bus, controller):
        """두 ROGUE 드론 간 충돌 → 어드바이저리 없음"""
        from src.airspace_control.agents.drone_state import FlightPhase
        _send_telemetry(env, comm_bus, "R1", [0.0, 0.0, 60.0],
                        vel=[10.0, 0.0, 0.0])
        _send_telemetry(env, comm_bus, "R2", [40.0, 0.0, 60.0],
                        vel=[-10.0, 0.0, 0.0])
        controller._active_drones["R1"].flight_phase = FlightPhase.ENROUTE
        controller._active_drones["R2"].flight_phase = FlightPhase.ENROUTE
        controller._active_drones["R1"].profile_name = "ROGUE"
        controller._active_drones["R2"].profile_name = "ROGUE"
        controller._scan_conflicts(0.0)
        assert len(controller._advisories) == 0


class TestNonManeuverableGuard:
    """LANDING/TAKEOFF/RTL 드론 어드바이저리 재배정 테스트"""

    def test_landing_drone_not_target(self, env, comm_bus, controller):
        """LANDING 드론 + ENROUTE 드론 → ENROUTE 드론이 어드바이저리 수신"""
        from src.airspace_control.agents.drone_state import FlightPhase
        _send_telemetry(env, comm_bus, "LAND1", [0.0, 0.0, 60.0],
                        vel=[0.0, 0.0, -2.0], phase="LANDING")
        _send_telemetry(env, comm_bus, "FLY1", [40.0, 0.0, 60.0],
                        vel=[-10.0, 0.0, 0.0])
        controller._active_drones["LAND1"].flight_phase = FlightPhase.LANDING
        controller._active_drones["FLY1"].flight_phase = FlightPhase.ENROUTE
        controller._scan_conflicts(0.0)
        for adv in controller._advisories.values():
            assert adv.target_drone_id == "FLY1"

    def test_both_landing_skip(self, env, comm_bus, controller):
        """두 LANDING 드론 → 어드바이저리 없음"""
        from src.airspace_control.agents.drone_state import FlightPhase
        _send_telemetry(env, comm_bus, "L1", [0.0, 0.0, 30.0],
                        vel=[0.0, 0.0, -2.0], phase="LANDING")
        _send_telemetry(env, comm_bus, "L2", [4.0, 0.0, 30.0],
                        vel=[0.0, 0.0, -2.0], phase="LANDING")
        controller._active_drones["L1"].flight_phase = FlightPhase.LANDING
        controller._active_drones["L2"].flight_phase = FlightPhase.LANDING
        controller._scan_conflicts(0.0)
        assert len(controller._advisories) == 0


class TestDestinationValidation:
    """clearance 목적지 NFZ/경계 검증 테스트"""

    def test_destination_in_nfz_rejected(self, env, comm_bus, controller):
        """NFZ 내부 목적지 → clearance 거부"""
        controller.planner.nfz_list = [
            {"center": np.array([0.0, 0.0, 60.0]), "radius_m": 500.0},
        ]
        received = []
        comm_bus.subscribe("DN", lambda m: received.append(m))
        req = ClearanceRequest(
            drone_id="DN", origin=np.array([-2000.0, 0.0, 0.0]),
            destination=np.array([100.0, 100.0, 60.0]),
            priority=3, timestamp_s=0.0,
        )
        comm_bus.send(CommMessage("DN", "CONTROLLER", req, 0.0, "clearance"))
        env.run(until=0.1)
        controller._process_clearances(1.0)
        env.run(until=1.5)
        resp = [m for m in received if hasattr(m.payload, 'approved')]
        assert len(resp) >= 1
        assert resp[0].payload.approved is False

    def test_destination_out_of_bounds_rejected(self, env, comm_bus, controller):
        """경계 외부 목적지 → clearance 거부"""
        received = []
        comm_bus.subscribe("DO", lambda m: received.append(m))
        req = ClearanceRequest(
            drone_id="DO", origin=np.array([0.0, 0.0, 0.0]),
            destination=np.array([99999.0, 0.0, 60.0]),
            priority=3, timestamp_s=0.0,
        )
        comm_bus.send(CommMessage("DO", "CONTROLLER", req, 0.0, "clearance"))
        env.run(until=0.1)
        controller._process_clearances(1.0)
        env.run(until=1.5)
        resp = [m for m in received if hasattr(m.payload, 'approved')]
        assert len(resp) >= 1
        assert resp[0].payload.approved is False

    def test_valid_destination_approved(self, env, comm_bus, controller):
        """정상 목적지 → clearance 승인"""
        received = []
        comm_bus.subscribe("DV", lambda m: received.append(m))
        req = ClearanceRequest(
            drone_id="DV", origin=np.array([0.0, 0.0, 0.0]),
            destination=np.array([500.0, 500.0, 60.0]),
            priority=3, timestamp_s=0.0,
        )
        comm_bus.send(CommMessage("DV", "CONTROLLER", req, 0.0, "clearance"))
        env.run(until=0.1)
        controller._process_clearances(1.0)
        env.run(until=1.5)
        resp = [m for m in received if hasattr(m.payload, 'approved')]
        assert len(resp) >= 1
        assert resp[0].payload.approved is True


class TestGroundedDroneCleanup:
    """착지 드론 _active_drones 제거 테스트"""

    def test_grounded_drone_removed(self, env, comm_bus, controller):
        _send_telemetry(env, comm_bus, "GD1", [0.0, 0.0, 60.0], phase="ENROUTE")
        assert "GD1" in controller._active_drones
        _send_telemetry(env, comm_bus, "GD1", [0.0, 0.0, 0.0], phase="GROUNDED")
        assert "GD1" not in controller._active_drones
