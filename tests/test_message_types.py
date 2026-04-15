"""message_types 데이터클래스 테스트"""
import numpy as np
import pytest
from src.airspace_control.comms.message_types import (
    TelemetryMessage, ClearanceRequest, ClearanceResponse,
    ResolutionAdvisory, IntrusionAlert,
)

pytestmark = pytest.mark.unit


class TestTelemetryMessage:
    def test_creation(self):
        tm = TelemetryMessage(
            drone_id="DR001", position=[0, 0, 60],
            velocity=[10, 0, 0], battery_pct=85.0,
            flight_phase="ENROUTE", timestamp_s=10.0,
        )
        assert tm.drone_id == "DR001"
        assert tm.battery_pct == 85.0


class TestClearanceRequest:
    def test_creation(self):
        cr = ClearanceRequest(
            drone_id="DR001",
            origin=np.zeros(3),
            destination=np.array([1000, 1000, 60]),
            priority=2,
            timestamp_s=5.0,
        )
        assert cr.drone_id == "DR001"
        assert cr.priority == 2


class TestClearanceResponse:
    def test_approved(self):
        cr = ClearanceResponse(
            drone_id="DR001", approved=True,
            assigned_waypoints=[np.zeros(3)],
            altitude_band=(30, 120), timestamp_s=5.0,
        )
        assert cr.approved is True

    def test_denied(self):
        cr = ClearanceResponse(
            drone_id="DR001", approved=False,
            assigned_waypoints=[], altitude_band=(30, 120),
            timestamp_s=5.0, reason="voronoi_conflict:DR002",
        )
        assert cr.approved is False
        assert "voronoi" in cr.reason


class TestResolutionAdvisory:
    def test_creation(self):
        ra = ResolutionAdvisory(
            advisory_id="ADV-001",
            target_drone_id="DR001",
            advisory_type="TURN_RIGHT",
            magnitude=30.0,
            duration_s=15.0,
            timestamp_s=10.0,
        )
        assert ra.advisory_type == "TURN_RIGHT"
        assert ra.duration_s == 15.0
        assert ra.magnitude == 30.0


class TestIntrusionAlert:
    def test_creation(self):
        ia = IntrusionAlert(
            alert_id="ALT-001",
            intruder_id="ROGUE01",
            detection_position=np.array([500, 500, 60]),
            detection_time_s=30.0,
            threat_level="HIGH",
        )
        assert ia.threat_level == "HIGH"
        assert ia.intruder_id == "ROGUE01"
