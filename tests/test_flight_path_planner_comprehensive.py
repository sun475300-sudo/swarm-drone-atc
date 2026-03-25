"""
FlightPathPlanner 포괄적 단위 테스트
_build_blocked, _is_blocked, _heuristic, _neighbors_2d,
_astar_2d, _smooth, _plan, _path_risk, estimate_cost, replan_avoiding 커버
"""
from __future__ import annotations

import math
import numpy as np
import pytest

from src.airspace_control.planning.flight_path_planner import FlightPathPlanner
from src.airspace_control.planning.waypoint import Waypoint, Route
from simulation.cbs_planner.cbs import GridNode


@pytest.fixture
def planner():
    bounds = {"x": [-2000, 2000], "y": [-2000, 2000], "z": [0, 200]}
    nfz = [{"center": np.array([0.0, 0.0, 0.0]), "radius_m": 200.0}]
    return FlightPathPlanner(bounds, nfz, grid_resolution_m=50.0, cruise_altitude_m=60.0)


@pytest.fixture
def planner_no_nfz():
    bounds = {"x": [-2000, 2000], "y": [-2000, 2000], "z": [0, 200]}
    return FlightPathPlanner(bounds, [], grid_resolution_m=50.0, cruise_altitude_m=60.0)


class TestBuildBlocked:
    def test_nfz_blocks_cells(self, planner):
        blocked = planner._build_blocked()
        assert len(blocked) > 0

    def test_no_nfz_no_blocks(self, planner_no_nfz):
        blocked = planner_no_nfz._build_blocked()
        assert len(blocked) == 0

    def test_cache_returns_same(self, planner):
        b1 = planner._build_blocked()
        b2 = planner._build_blocked()
        assert b1 is b2  # 캐시된 동일 객체

    def test_center_is_blocked(self, planner):
        """NFZ 중심은 블록되어야 한다"""
        assert planner._is_blocked(0, 0)


class TestHeuristic:
    def test_same_node(self, planner):
        a = GridNode(0, 0, 0)
        assert planner._heuristic(a, a) == 0.0

    def test_euclidean_2d(self, planner):
        a = GridNode(0, 0, 0)
        b = GridNode(3, 4, 0)
        assert planner._heuristic(a, b) == pytest.approx(5.0)


class TestNeighbors2d:
    def test_unblocked_returns_8(self, planner_no_nfz):
        """NFZ 없고 내부 노드이면 8개 이웃"""
        neighbors = planner_no_nfz._neighbors_2d(GridNode(0, 0, 1))
        assert len(neighbors) == 8

    def test_blocked_neighbor_excluded(self, planner):
        """NFZ 내 이웃은 제외"""
        # (0,0)은 NFZ 내부이므로 이웃에 포함 안 됨
        neighbors = planner._neighbors_2d(GridNode(1, 0, 1))
        coords = [(n.x, n.y) for n in neighbors]
        assert (0, 0) not in coords

    def test_z_preserved(self, planner_no_nfz):
        """이웃 노드의 z 좌표는 유지"""
        neighbors = planner_no_nfz._neighbors_2d(GridNode(0, 0, 3))
        for n in neighbors:
            assert n.z == 3


class TestAstar2d:
    def test_finds_path(self, planner_no_nfz):
        path = planner_no_nfz._astar_2d(GridNode(0, 0, 1), GridNode(5, 0, 1))
        assert len(path) > 0
        assert path[0] == GridNode(0, 0, 1)
        assert path[-1] == GridNode(5, 0, 1)

    def test_avoids_nfz(self, planner):
        """NFZ를 통과하는 직선 경로 대신 우회"""
        path = planner._astar_2d(GridNode(-10, 0, 1), GridNode(10, 0, 1))
        assert len(path) > 0
        for node in path:
            assert not planner._is_blocked(node.x, node.y)

    def test_same_start_goal(self, planner_no_nfz):
        path = planner_no_nfz._astar_2d(GridNode(0, 0, 1), GridNode(0, 0, 1))
        assert len(path) >= 1


class TestSmooth:
    def test_straight_line_smoothed(self, planner):
        """직선 경로의 중간점 제거"""
        path = [GridNode(0, 0, 0), GridNode(1, 0, 0), GridNode(2, 0, 0), GridNode(3, 0, 0)]
        smoothed = planner._smooth(path)
        assert len(smoothed) == 2  # 시작과 끝만

    def test_turn_preserved(self, planner):
        """직각 턴의 중간점은 유지"""
        path = [GridNode(0, 0, 0), GridNode(1, 0, 0), GridNode(1, 1, 0)]
        smoothed = planner._smooth(path)
        assert len(smoothed) == 3  # 턴이므로 모두 유지

    def test_short_path_unchanged(self, planner):
        path = [GridNode(0, 0, 0), GridNode(1, 0, 0)]
        smoothed = planner._smooth(path)
        assert len(smoothed) == 2

    def test_single_node(self, planner):
        path = [GridNode(0, 0, 0)]
        smoothed = planner._smooth(path)
        assert len(smoothed) == 1


class TestPlanRoute:
    def test_waypoint_sequence(self, planner):
        """경로는 이륙-상승-순항-하강-착륙 구조"""
        route = planner.plan_route("D0", np.array([500.0, 500.0, 0.0]),
                                    np.array([1000.0, 1000.0, 0.0]))
        assert len(route.waypoints) >= 4  # 최소 이륙, 상승, 목적지고도, 착륙

    def test_first_waypoint_at_origin(self, planner):
        origin = np.array([500.0, 500.0, 0.0])
        route = planner.plan_route("D0", origin, np.array([1000.0, 1000.0, 0.0]))
        assert np.allclose(route.waypoints[0].position, origin)

    def test_last_waypoint_at_destination(self, planner):
        dest = np.array([1000.0, 1000.0, 0.0])
        route = planner.plan_route("D0", np.array([500.0, 500.0, 0.0]), dest)
        assert np.allclose(route.waypoints[-1].position, dest)

    def test_landing_speed_halved(self, planner):
        route = planner.plan_route("D0", np.array([500.0, 500.0, 0.0]),
                                    np.array([1000.0, 1000.0, 0.0]),
                                    cruise_speed_ms=10.0)
        assert route.waypoints[-1].speed_ms == pytest.approx(5.0)

    def test_custom_route_id(self, planner):
        route = planner.plan_route("D0", np.array([500.0, 500.0, 0.0]),
                                    np.array([1000.0, 1000.0, 0.0]),
                                    route_id="MY-ROUTE")
        assert route.route_id == "MY-ROUTE"


class TestEstimateCost:
    def test_nonzero_route(self, planner):
        route = planner.plan_route("D0", np.array([500.0, 500.0, 0.0]),
                                    np.array([1000.0, 1000.0, 0.0]))
        cost = planner.estimate_cost(route)
        assert cost.distance_m > 0
        assert cost.duration_s > 0
        assert cost.energy_wh > 0

    def test_zero_distance(self, planner):
        route = Route(route_id="R0", drone_id="D0", waypoints=[
            Waypoint(position=np.array([0.0, 0.0, 0.0]))])
        cost = planner.estimate_cost(route)
        assert cost.distance_m == 0.0
        assert cost.duration_s == 0.0


class TestPathRisk:
    def test_far_from_nfz_low_risk(self, planner):
        route = planner.plan_route("D0", np.array([1500.0, 1500.0, 0.0]),
                                    np.array([1800.0, 1800.0, 0.0]))
        cost = planner.estimate_cost(route)
        assert cost.risk_score < 0.5

    def test_no_nfz_zero_risk(self, planner_no_nfz):
        route = planner_no_nfz.plan_route("D0", np.array([0.0, 0.0, 0.0]),
                                           np.array([100.0, 100.0, 0.0]))
        cost = planner_no_nfz.estimate_cost(route)
        assert cost.risk_score == 0.0


class TestReplanAvoiding:
    def test_returns_valid_route(self, planner):
        route = planner.replan_avoiding(
            "D0",
            np.array([500.0, 500.0, 0.0]),
            np.array([1000.0, 1000.0, 0.0]),
            GridNode(12, 12, 1),
        )
        assert len(route.waypoints) >= 2

    def test_blocked_restored(self, planner):
        """replan 후 원래 blocked 상태 복원"""
        original = planner._blocked
        planner.replan_avoiding(
            "D0",
            np.array([500.0, 500.0, 0.0]),
            np.array([1000.0, 1000.0, 0.0]),
            GridNode(12, 12, 1),
        )
        assert planner._blocked is original
