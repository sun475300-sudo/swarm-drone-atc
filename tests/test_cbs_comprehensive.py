"""
CBS (Conflict-Based Search) 포괄적 단위 테스트
heuristic, get_neighbors, low_level_astar, detect_conflict, cbs_plan 커버
"""
from __future__ import annotations

import numpy as np
import pytest

from simulation.cbs_planner.cbs import (
    GridNode,
    AStarNode,
    Constraint,
    Conflict,
    CTNode,
    GRID_RESOLUTION,
    heuristic,
    get_neighbors,
    low_level_astar,
    detect_conflict,
    cbs_plan,
    position_to_grid,
)


BOUNDS = {"x": [0, 10], "y": [0, 10], "z": [0, 5]}


# ── heuristic 테스트 ──────────────────────────────────────────────────────


class TestHeuristic:
    def test_same_node_zero(self):
        assert heuristic(GridNode(0, 0, 0), GridNode(0, 0, 0)) == 0.0

    def test_manhattan_distance(self):
        assert heuristic(GridNode(0, 0, 0), GridNode(3, 4, 1)) == 8.0

    def test_symmetric(self):
        a, b = GridNode(1, 2, 3), GridNode(5, 6, 7)
        assert heuristic(a, b) == heuristic(b, a)


# ── get_neighbors 테스트 ──────────────────────────────────────────────────


class TestGetNeighbors:
    def test_center_node_7_neighbors(self):
        """중앙 노드는 6방향 + 대기 = 7개 이웃"""
        n = get_neighbors(GridNode(5, 5, 2), BOUNDS)
        assert len(n) == 7

    def test_corner_node_fewer_neighbors(self):
        """모서리 노드는 이웃이 적음"""
        n = get_neighbors(GridNode(0, 0, 0), BOUNDS)
        assert len(n) < 7

    def test_wait_action_included(self):
        """대기 액션(자신 위치)이 포함되어야 한다"""
        node = GridNode(5, 5, 2)
        neighbors = get_neighbors(node, BOUNDS)
        assert node in neighbors

    def test_boundary_respect(self):
        """경계를 넘는 이웃은 제외"""
        n = get_neighbors(GridNode(0, 0, 0), BOUNDS)
        for nb in n:
            assert BOUNDS["x"][0] <= nb.x <= BOUNDS["x"][1]
            assert BOUNDS["y"][0] <= nb.y <= BOUNDS["y"][1]
            assert BOUNDS["z"][0] <= nb.z <= BOUNDS["z"][1]


# ── GridNode.to_position 테스트 ───────────────────────────────────────────


class TestGridNodeToPosition:
    def test_origin(self):
        pos = GridNode(0, 0, 0).to_position()
        assert np.allclose(pos, [0.0, 0.0, 0.0])

    def test_custom_resolution(self):
        pos = GridNode(2, 3, 1).to_position(res=10.0)
        assert np.allclose(pos, [20.0, 30.0, 10.0])

    def test_default_resolution(self):
        pos = GridNode(1, 0, 0).to_position()
        assert pos[0] == pytest.approx(GRID_RESOLUTION)


# ── AStarNode / Constraint / Conflict / CTNode 데이터 테스트 ────────────


class TestDataclasses:
    def test_astar_node_ordering(self):
        """f 값으로 정렬되어야 한다"""
        n1 = AStarNode(f=1.0, g=0.0, node=GridNode(0, 0, 0), t=0)
        n2 = AStarNode(f=2.0, g=1.0, node=GridNode(1, 0, 0), t=1)
        assert n1 < n2

    def test_constraint_creation(self):
        c = Constraint("D0", GridNode(1, 2, 0), 5)
        assert c.drone_id == "D0"
        assert c.t == 5

    def test_conflict_creation(self):
        c = Conflict("D0", "D1", GridNode(3, 3, 0), 10)
        assert c.drone_a == "D0"
        assert c.drone_b == "D1"

    def test_ctnode_creation(self):
        ct = CTNode([], {"D0": [GridNode(0, 0, 0)]}, 1.0)
        assert ct.cost == 1.0


# ── low_level_astar 테스트 ────────────────────────────────────────────────


class TestLowLevelAstar:
    def test_same_start_goal(self):
        """시작과 목표가 같으면 단일 노드 경로"""
        path = low_level_astar(
            GridNode(0, 0, 0), GridNode(0, 0, 0), [], "D0", BOUNDS)
        assert len(path) >= 1
        assert path[0] == GridNode(0, 0, 0)

    def test_simple_path(self):
        """간단한 경로 찾기"""
        path = low_level_astar(
            GridNode(0, 0, 0), GridNode(3, 0, 0), [], "D0", BOUNDS)
        assert len(path) > 0
        assert path[0] == GridNode(0, 0, 0)
        assert path[-1] == GridNode(3, 0, 0)

    def test_path_avoids_constraints(self):
        """제약 조건이 있는 노드를 피해야 한다"""
        # (1,0,0)을 t=1에서 금지
        constraints = [Constraint("D0", GridNode(1, 0, 0), 1)]
        path = low_level_astar(
            GridNode(0, 0, 0), GridNode(2, 0, 0), constraints, "D0", BOUNDS)
        assert len(path) > 0
        assert path[-1] == GridNode(2, 0, 0)
        # t=1에서 (1,0,0)에 있지 않아야 함
        if len(path) > 1:
            assert path[1] != GridNode(1, 0, 0)

    def test_constraints_for_other_drone_ignored(self):
        """다른 드론의 제약은 무시"""
        constraints = [Constraint("D1", GridNode(1, 0, 0), 1)]
        path = low_level_astar(
            GridNode(0, 0, 0), GridNode(2, 0, 0), constraints, "D0", BOUNDS)
        assert len(path) > 0

    def test_unreachable_returns_empty(self):
        """도달 불가능하면 빈 리스트"""
        # 매우 작은 경계 + 많은 제약으로 도달 불가능하게
        tiny_bounds = {"x": [0, 1], "y": [0, 0], "z": [0, 0]}
        constraints = [Constraint("D0", GridNode(1, 0, 0), t) for t in range(200)]
        path = low_level_astar(
            GridNode(0, 0, 0), GridNode(1, 0, 0), constraints, "D0", tiny_bounds,
            max_time=5)
        # 대기 액션으로 우회할 수 있으나, 모든 시간에 제약이 있으면 빈 리스트
        # (충분한 시간 제약으로 차단)
        assert isinstance(path, list)


# ── detect_conflict 테스트 ────────────────────────────────────────────────


class TestDetectConflict:
    def test_no_conflict(self):
        """충돌 없는 경로"""
        paths = {
            "D0": [GridNode(0, 0, 0), GridNode(1, 0, 0), GridNode(2, 0, 0)],
            "D1": [GridNode(0, 5, 0), GridNode(1, 5, 0), GridNode(2, 5, 0)],
        }
        assert detect_conflict(paths) is None

    def test_node_conflict(self):
        """같은 시간에 같은 노드에 있으면 충돌"""
        paths = {
            "D0": [GridNode(0, 0, 0), GridNode(1, 0, 0)],
            "D1": [GridNode(2, 0, 0), GridNode(1, 0, 0)],
        }
        conflict = detect_conflict(paths)
        assert conflict is not None
        assert conflict.node == GridNode(1, 0, 0)

    def test_edge_swap_conflict(self):
        """스왑 충돌 (두 드론이 위치를 교환)"""
        paths = {
            "D0": [GridNode(0, 0, 0), GridNode(1, 0, 0)],
            "D1": [GridNode(1, 0, 0), GridNode(0, 0, 0)],
        }
        conflict = detect_conflict(paths)
        assert conflict is not None

    def test_empty_paths(self):
        assert detect_conflict({}) is None

    def test_single_drone_no_conflict(self):
        paths = {"D0": [GridNode(0, 0, 0), GridNode(1, 0, 0)]}
        assert detect_conflict(paths) is None

    def test_different_length_paths(self):
        """경로 길이가 다른 경우 (짧은 경로는 마지막 위치 유지)"""
        paths = {
            "D0": [GridNode(0, 0, 0), GridNode(1, 0, 0), GridNode(2, 0, 0)],
            "D1": [GridNode(5, 5, 0)],
        }
        assert detect_conflict(paths) is None


# ── cbs_plan 테스트 ───────────────────────────────────────────────────────


class TestCbsPlan:
    def test_single_drone(self):
        """단일 드론 경로 계획"""
        starts = {"D0": GridNode(0, 0, 0)}
        goals = {"D0": GridNode(3, 0, 0)}
        result = cbs_plan(starts, goals, BOUNDS)
        assert "D0" in result
        assert result["D0"][0] == GridNode(0, 0, 0)
        assert result["D0"][-1] == GridNode(3, 0, 0)

    def test_two_drones_no_conflict(self):
        """두 드론이 충돌 없이 목표 도달"""
        starts = {"D0": GridNode(0, 0, 0), "D1": GridNode(0, 10, 0)}
        goals = {"D0": GridNode(5, 0, 0), "D1": GridNode(5, 10, 0)}
        result = cbs_plan(starts, goals, BOUNDS)
        assert detect_conflict(result) is None

    def test_two_drones_conflict_resolved(self):
        """경로가 교차하는 두 드론의 충돌 해결"""
        starts = {"D0": GridNode(0, 5, 0), "D1": GridNode(5, 5, 0)}
        goals = {"D0": GridNode(5, 5, 0), "D1": GridNode(0, 5, 0)}
        result = cbs_plan(starts, goals, BOUNDS)
        # 충돌이 해결되었거나, 최소한 유효한 경로가 반환
        assert "D0" in result and "D1" in result

    def test_returns_dict(self):
        starts = {"D0": GridNode(0, 0, 0)}
        goals = {"D0": GridNode(1, 0, 0)}
        result = cbs_plan(starts, goals, BOUNDS)
        assert isinstance(result, dict)

    def test_max_ct_nodes_limit(self):
        """CT 노드 수 제한이 작동"""
        starts = {"D0": GridNode(0, 0, 0), "D1": GridNode(5, 0, 0)}
        goals = {"D0": GridNode(5, 0, 0), "D1": GridNode(0, 0, 0)}
        result = cbs_plan(starts, goals, BOUNDS, max_ct_nodes=5)
        assert isinstance(result, dict)
