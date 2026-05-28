"""Waypoint / Route / RouteCost 데이터클래스 엣지 케이스 테스트"""
import numpy as np
import pytest

from src.airspace_control.planning.waypoint import Route, RouteCost, Waypoint

pytestmark = pytest.mark.unit


class TestWaypoint:
    def test_distance_to(self):
        a = Waypoint(np.array([0.0, 0.0, 0.0]))
        b = Waypoint(np.array([3.0, 4.0, 0.0]))
        assert a.distance_to(b) == pytest.approx(5.0)

    def test_lateral_distance_ignores_altitude(self):
        a = Waypoint(np.array([0.0, 0.0, 0.0]))
        b = Waypoint(np.array([3.0, 4.0, 100.0]))
        # only xy: sqrt(9+16) = 5, ignores z=100
        assert a.lateral_distance_to(b) == pytest.approx(5.0)

    def test_lateral_distance_same_xy(self):
        a = Waypoint(np.array([1.0, 2.0, 0.0]))
        b = Waypoint(np.array([1.0, 2.0, 50.0]))
        assert a.lateral_distance_to(b) == pytest.approx(0.0)


class TestRoute:
    def _make_route(self, n: int) -> Route:
        wps = [Waypoint(np.array([float(i) * 10, 0.0, 0.0])) for i in range(n)]
        return Route(route_id="R1", drone_id="D0", waypoints=wps)

    def test_total_distance_zero_when_no_waypoints(self):
        r = Route(route_id="R1", drone_id="D0")
        assert r.total_distance_m == pytest.approx(0.0)

    def test_total_distance_zero_single_waypoint(self):
        r = self._make_route(1)
        assert r.total_distance_m == pytest.approx(0.0)

    def test_total_distance_two_waypoints(self):
        r = self._make_route(3)  # [0,10,20] → 10+10 = 20m
        assert r.total_distance_m == pytest.approx(20.0)

    def test_origin_none_when_empty(self):
        r = Route(route_id="R1", drone_id="D0")
        assert r.origin is None

    def test_origin_returns_first_position(self):
        r = self._make_route(3)
        np.testing.assert_array_equal(r.origin, [0.0, 0.0, 0.0])

    def test_destination_none_when_empty(self):
        r = Route(route_id="R1", drone_id="D0")
        assert r.destination is None

    def test_destination_returns_last_position(self):
        r = self._make_route(3)
        np.testing.assert_array_equal(r.destination, [20.0, 0.0, 0.0])

    def test_get_current_waypoint_valid_idx(self):
        r = self._make_route(3)
        wp = r.get_current_waypoint(1)
        assert wp is not None
        assert wp.position[0] == pytest.approx(10.0)

    def test_get_current_waypoint_out_of_range(self):
        r = self._make_route(3)
        assert r.get_current_waypoint(10) is None

    def test_get_current_waypoint_negative_idx(self):
        r = self._make_route(3)
        assert r.get_current_waypoint(-1) is None

    def test_get_current_waypoint_empty(self):
        r = Route(route_id="R1", drone_id="D0")
        assert r.get_current_waypoint(0) is None


class TestRouteCost:
    def test_defaults(self):
        rc = RouteCost(distance_m=100.0, duration_s=30.0, energy_wh=0.5)
        assert rc.risk_score == pytest.approx(0.0)

    def test_custom_risk_score(self):
        rc = RouteCost(distance_m=50.0, duration_s=15.0, energy_wh=0.3, risk_score=0.8)
        assert rc.risk_score == pytest.approx(0.8)
