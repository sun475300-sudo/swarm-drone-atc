"""DroneState 데이터클래스 테스트"""
import numpy as np
import pytest
from src.airspace_control.agents.drone_state import (
    DroneState, FlightPhase, CommsStatus, FailureType,
)


class TestDroneState:
    def test_default_creation(self):
        d = DroneState(drone_id="D-0001", position=np.zeros(3), velocity=np.zeros(3))
        assert d.drone_id == "D-0001"
        assert d.flight_phase == FlightPhase.GROUNDED
        assert d.battery_pct == 100.0

    def test_list_to_ndarray(self):
        d = DroneState(drone_id="D-0002", position=[1, 2, 3], velocity=[4, 5, 6])
        assert isinstance(d.position, np.ndarray)
        assert isinstance(d.velocity, np.ndarray)
        np.testing.assert_array_equal(d.position, [1, 2, 3])

    def test_is_active(self):
        d = DroneState(drone_id="D-0003", position=np.zeros(3), velocity=np.zeros(3),
                       flight_phase=FlightPhase.ENROUTE)
        assert d.is_active is True

    def test_grounded_not_active(self):
        d = DroneState(drone_id="D-0004", position=np.zeros(3), velocity=np.zeros(3))
        assert d.is_active is False

    def test_failed_not_active(self):
        d = DroneState(drone_id="D-0005", position=np.zeros(3), velocity=np.zeros(3),
                       flight_phase=FlightPhase.FAILED)
        assert d.is_active is False

    def test_is_failed(self):
        d = DroneState(drone_id="D-0006", position=np.zeros(3), velocity=np.zeros(3),
                       failure_type=FailureType.MOTOR_FAILURE)
        assert d.is_failed is True

    def test_speed(self):
        d = DroneState(drone_id="D-0007", position=np.zeros(3),
                       velocity=np.array([3.0, 4.0, 0.0]))
        assert d.speed == pytest.approx(5.0)

    def test_to_dict(self):
        d = DroneState(drone_id="D-0008", position=np.array([1, 2, 3]),
                       velocity=np.zeros(3))
        result = d.to_dict()
        assert result["drone_id"] == "D-0008"
        assert result["position"] == [1.0, 2.0, 3.0]
        assert result["flight_phase"] == "GROUNDED"


class TestEnums:
    def test_flight_phases(self):
        phases = [FlightPhase.GROUNDED, FlightPhase.TAKEOFF, FlightPhase.ENROUTE,
                  FlightPhase.HOLDING, FlightPhase.LANDING, FlightPhase.FAILED,
                  FlightPhase.RTL, FlightPhase.EVADING]
        assert len(phases) == 8

    def test_comms_status(self):
        assert CommsStatus.NOMINAL != CommsStatus.LOST

    def test_failure_types(self):
        assert len(FailureType) == 6


class TestDroneStateTupleInput:
    """P1-01: tuple 입력도 np.ndarray로 변환되어야 한다."""

    def test_tuple_position_converted(self):
        d = DroneState(drone_id="T1", position=(10.0, 20.0, 30.0),
                       velocity=(1.0, 2.0, 3.0))
        assert isinstance(d.position, np.ndarray)
        assert isinstance(d.velocity, np.ndarray)

    def test_tuple_values_correct(self):
        d = DroneState(drone_id="T2", position=(5.0, 6.0, 7.0),
                       velocity=(0.0, 0.0, 0.0))
        np.testing.assert_array_equal(d.position, [5.0, 6.0, 7.0])

    def test_ndarray_passthrough(self):
        pos = np.array([1.0, 2.0, 3.0])
        d = DroneState(drone_id="T3", position=pos, velocity=np.zeros(3))
        assert d.position is pos  # 동일 객체 (복사 안 함)


class TestWaypointTracking:
    """F-03: DroneState waypoints 필드 기본값 검증"""

    def test_waypoints_default_empty(self):
        d = DroneState(drone_id="W1", position=np.zeros(3), velocity=np.zeros(3))
        assert d.waypoints == []
        assert d.current_waypoint_idx == 0

    def test_waypoints_assignable(self):
        d = DroneState(drone_id="W2", position=np.zeros(3), velocity=np.zeros(3))
        d.waypoints = [np.array([100.0, 0.0, 60.0]), np.array([200.0, 0.0, 60.0])]
        assert len(d.waypoints) == 2
