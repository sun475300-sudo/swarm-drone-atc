"""FlightPriorityQueue + DroneProfiles 테스트"""
import numpy as np
import pytest
from src.airspace_control.controller.priority_queue import FlightPriorityQueue, PRIORITY_LABELS
from src.airspace_control.planning.waypoint import Route, Waypoint
from src.airspace_control.agents.drone_profiles import DRONE_PROFILES

pytestmark = pytest.mark.unit


def _make_route(drone_id: str, priority: int) -> Route:
    wp = Waypoint(position=np.zeros(3), speed_ms=10.0)
    return Route(route_id=f"R-{drone_id}", drone_id=drone_id,
                 waypoints=[wp], priority=priority)


class TestFlightPriorityQueue:
    def test_empty(self):
        pq = FlightPriorityQueue()
        assert pq.is_empty()
        assert len(pq) == 0
        assert pq.pop() is None

    def test_push_pop(self):
        pq = FlightPriorityQueue()
        r = _make_route("DR001", 2)
        pq.push(r, 1.0)
        assert len(pq) == 1
        popped = pq.pop()
        assert popped.drone_id == "DR001"
        assert pq.is_empty()

    def test_priority_order(self):
        pq = FlightPriorityQueue()
        pq.push(_make_route("LOW", 3), 1.0)
        pq.push(_make_route("EMRG", 0), 2.0)
        pq.push(_make_route("MED", 2), 3.0)
        assert pq.pop().drone_id == "EMRG"
        assert pq.pop().drone_id == "MED"
        assert pq.pop().drone_id == "LOW"

    def test_same_priority_fifo(self):
        pq = FlightPriorityQueue()
        pq.push(_make_route("FIRST", 2), 1.0)
        pq.push(_make_route("SECOND", 2), 2.0)
        assert pq.pop().drone_id == "FIRST"
        assert pq.pop().drone_id == "SECOND"

    def test_peek(self):
        pq = FlightPriorityQueue()
        pq.push(_make_route("DR001", 1), 1.0)
        assert pq.peek().drone_id == "DR001"
        assert len(pq) == 1  # peek은 제거하지 않음


class TestDroneProfiles:
    def test_all_profiles_exist(self):
        expected = ["COMMERCIAL_DELIVERY", "SURVEILLANCE", "EMERGENCY",
                    "RECREATIONAL", "ROGUE"]
        for name in expected:
            assert name in DRONE_PROFILES

    def test_emergency_highest_priority(self):
        emrg = DRONE_PROFILES["EMERGENCY"]
        comm = DRONE_PROFILES["COMMERCIAL_DELIVERY"]
        assert emrg.priority < comm.priority  # 낮은 숫자 = 높은 우선순위

    def test_profile_has_required_fields(self):
        for name, p in DRONE_PROFILES.items():
            assert p.max_speed_ms > 0
            assert p.cruise_speed_ms > 0
            assert p.battery_wh > 0
            assert p.endurance_min > 0


class TestPriorityLabels:
    def test_labels(self):
        assert PRIORITY_LABELS[0] == "EMERGENCY"
        assert PRIORITY_LABELS[3] == "RECREATIONAL"
