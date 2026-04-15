"""
FlightPathPlanner 단위 테스트
"""
from __future__ import annotations

import numpy as np
import pytest

from src.airspace_control.planning.flight_path_planner import FlightPathPlanner

pytestmark = pytest.mark.integration


@pytest.fixture
def planner_no_nfz(airspace_bounds):
    return FlightPathPlanner(
        airspace_bounds=airspace_bounds,
        no_fly_zones=[],
        grid_resolution_m=50.0,
        cruise_altitude_m=60.0,
    )


@pytest.fixture
def planner_with_nfz(airspace_bounds, no_fly_zones):
    return FlightPathPlanner(
        airspace_bounds=airspace_bounds,
        no_fly_zones=no_fly_zones,
        grid_resolution_m=50.0,
        cruise_altitude_m=60.0,
    )


class TestPlanRoute:
    def test_returns_route_with_waypoints(self, planner_no_nfz):
        origin = np.array([-500.0, -500.0, 0.0])
        dest   = np.array([ 500.0,  500.0, 0.0])
        route = planner_no_nfz.plan_route("D0", origin, dest)
        assert len(route.waypoints) >= 2

    def test_first_waypoint_near_origin(self, planner_no_nfz):
        origin = np.array([-500.0, -500.0, 0.0])
        dest   = np.array([ 500.0,  500.0, 0.0])
        route = planner_no_nfz.plan_route("D0", origin, dest)
        wp0 = route.waypoints[0].position
        assert np.linalg.norm(wp0[:2] - origin[:2]) < 100.0

    def test_last_waypoint_near_dest(self, planner_no_nfz):
        origin = np.array([-500.0, -500.0, 0.0])
        dest   = np.array([ 500.0,  500.0, 0.0])
        route = planner_no_nfz.plan_route("D0", origin, dest)
        wpN = route.waypoints[-1].position
        assert np.linalg.norm(wpN[:2] - dest[:2]) < 100.0

    def test_nfz_avoidance(self, planner_with_nfz):
        """NFZ 중심을 통과하는 직선 경로를 피해야 한다."""
        origin = np.array([-800.0, 0.0, 0.0])
        dest   = np.array([ 800.0, 0.0, 0.0])
        route = planner_with_nfz.plan_route("D0", origin, dest)
        # 모든 순항 웨이포인트가 NFZ 반경 바깥이어야 함
        nfz_center = np.array([0.0, 0.0])
        nfz_radius = 200.0
        for wp in route.waypoints[1:-1]:  # 이륙/착륙 제외
            dist = np.linalg.norm(wp.position[:2] - nfz_center)
            assert dist >= nfz_radius - 60.0, (
                f"Waypoint {wp.position[:2]} is inside NFZ (dist={dist:.1f})"
            )

    def test_same_origin_and_dest(self, planner_no_nfz):
        pos = np.array([100.0, 100.0, 0.0])
        route = planner_no_nfz.plan_route("D0", pos, pos.copy())
        assert len(route.waypoints) >= 1


class TestEstimateCost:
    def test_nonzero_distance(self, planner_no_nfz):
        origin = np.array([-500.0, 0.0, 0.0])
        dest   = np.array([ 500.0, 0.0, 0.0])
        route = planner_no_nfz.plan_route("D0", origin, dest)
        cost = planner_no_nfz.estimate_cost(route)
        assert cost.distance_m > 0.0
        assert cost.duration_s > 0.0
        assert cost.energy_wh >= 0.0
        assert 0.0 <= cost.risk_score <= 1.0

    def test_zero_distance_route(self, planner_no_nfz):
        pos = np.array([0.0, 0.0, 0.0])
        route = planner_no_nfz.plan_route("D0", pos, pos.copy())
        cost = planner_no_nfz.estimate_cost(route)
        assert cost.distance_m >= 0.0


class TestReplanAvoiding:
    def test_replan_returns_route(self, planner_no_nfz):
        from simulation.cbs_planner.cbs import GridNode
        origin = np.array([-500.0, 0.0, 0.0])
        dest   = np.array([ 500.0, 0.0, 0.0])
        blocked = GridNode(0, 0, 1)
        route = planner_no_nfz.replan_avoiding("D0", origin, dest, blocked)
        assert len(route.waypoints) >= 2
