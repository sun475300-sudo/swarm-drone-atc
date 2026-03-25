"""
Waypoint, Route, RouteCost 데이터클래스 단위 테스트
"""
from __future__ import annotations

import numpy as np
import pytest

from src.airspace_control.planning.waypoint import Waypoint, Route, RouteCost


class TestWaypoint:
    def test_default_speed(self):
        wp = Waypoint(position=np.array([0.0, 0.0, 0.0]))
        assert wp.speed_ms == 8.0

    def test_default_hover(self):
        wp = Waypoint(position=np.array([0.0, 0.0, 0.0]))
        assert wp.hover_s == 0.0

    def test_distance_to(self):
        wp1 = Waypoint(position=np.array([0.0, 0.0, 0.0]))
        wp2 = Waypoint(position=np.array([3.0, 4.0, 0.0]))
        assert wp1.distance_to(wp2) == pytest.approx(5.0)

    def test_distance_to_3d(self):
        wp1 = Waypoint(position=np.array([0.0, 0.0, 0.0]))
        wp2 = Waypoint(position=np.array([1.0, 2.0, 2.0]))
        assert wp1.distance_to(wp2) == pytest.approx(3.0)

    def test_distance_to_same_point(self):
        wp = Waypoint(position=np.array([5.0, 5.0, 5.0]))
        assert wp.distance_to(wp) == pytest.approx(0.0)

    def test_lateral_distance_to(self):
        """수평 거리만 계산 (z 무시)"""
        wp1 = Waypoint(position=np.array([0.0, 0.0, 0.0]))
        wp2 = Waypoint(position=np.array([3.0, 4.0, 100.0]))
        assert wp1.lateral_distance_to(wp2) == pytest.approx(5.0)

    def test_lateral_distance_ignores_z(self):
        wp1 = Waypoint(position=np.array([0.0, 0.0, 0.0]))
        wp2 = Waypoint(position=np.array([0.0, 0.0, 50.0]))
        assert wp1.lateral_distance_to(wp2) == pytest.approx(0.0)


class TestRoute:
    def _make_route(self, positions):
        waypoints = [Waypoint(position=np.array(p)) for p in positions]
        return Route(route_id="R-TEST", drone_id="D0", waypoints=waypoints)

    def test_total_distance_simple(self):
        r = self._make_route([[0, 0, 0], [3, 4, 0]])
        assert r.total_distance_m == pytest.approx(5.0)

    def test_total_distance_multi_segment(self):
        r = self._make_route([[0, 0, 0], [3, 0, 0], [3, 4, 0]])
        assert r.total_distance_m == pytest.approx(7.0)

    def test_total_distance_single_waypoint(self):
        r = self._make_route([[0, 0, 0]])
        assert r.total_distance_m == 0.0

    def test_total_distance_empty(self):
        r = Route(route_id="R-EMPTY", drone_id="D0", waypoints=[])
        assert r.total_distance_m == 0.0

    def test_origin(self):
        r = self._make_route([[10, 20, 30], [40, 50, 60]])
        assert np.allclose(r.origin, [10, 20, 30])

    def test_origin_empty(self):
        r = Route(route_id="R-EMPTY", drone_id="D0", waypoints=[])
        assert r.origin is None

    def test_destination(self):
        r = self._make_route([[10, 20, 30], [40, 50, 60]])
        assert np.allclose(r.destination, [40, 50, 60])

    def test_destination_empty(self):
        r = Route(route_id="R-EMPTY", drone_id="D0", waypoints=[])
        assert r.destination is None

    def test_get_current_waypoint(self):
        r = self._make_route([[0, 0, 0], [1, 1, 1], [2, 2, 2]])
        wp = r.get_current_waypoint(1)
        assert wp is not None
        assert np.allclose(wp.position, [1, 1, 1])

    def test_get_current_waypoint_out_of_bounds(self):
        r = self._make_route([[0, 0, 0]])
        assert r.get_current_waypoint(5) is None
        assert r.get_current_waypoint(-1) is None

    def test_priority_default(self):
        r = Route(route_id="R-TEST", drone_id="D0")
        assert r.priority == 3


class TestRouteCost:
    def test_creation(self):
        rc = RouteCost(distance_m=1000.0, duration_s=120.0, energy_wh=3.3)
        assert rc.distance_m == 1000.0
        assert rc.risk_score == 0.0  # default

    def test_risk_score(self):
        rc = RouteCost(distance_m=100.0, duration_s=10.0, energy_wh=1.0, risk_score=0.8)
        assert rc.risk_score == 0.8
