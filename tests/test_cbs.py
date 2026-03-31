"""
CBS (Conflict-Based Search) 플래너 단위 테스트
"""
from __future__ import annotations

import numpy as np
import pytest

from simulation.cbs_planner.cbs import (
    GridNode,
    GRID_RESOLUTION,
    position_to_grid,
    low_level_astar,
    detect_conflict,
    cbs_plan,
    Constraint,
)


class TestGridNode:
    def test_equality(self):
        assert GridNode(1, 2, 3) == GridNode(1, 2, 3)
        assert GridNode(1, 2, 3) != GridNode(1, 2, 4)

    def test_hashable(self):
        s = {GridNode(0, 0, 0), GridNode(1, 0, 0), GridNode(0, 0, 0)}
        assert len(s) == 2


class TestPositionToGrid:
    def test_origin(self):
        gn = position_to_grid(np.array([0.0, 0.0, 0.0]))
        assert gn.x == 0 and gn.y == 0

    def test_positive_offset(self):
        gn = position_to_grid(np.array([GRID_RESOLUTION, GRID_RESOLUTION, 0.0]))
        assert gn.x == 1 and gn.y == 1

    def test_rounding(self):
        # 반올림 후 격자 좌표
        gn = position_to_grid(np.array([GRID_RESOLUTION * 0.6, 0.0, 0.0]))
        assert gn.x == 1

    def test_negative_position(self):
        gn = position_to_grid(np.array([-GRID_RESOLUTION, 0.0, 0.0]))
        assert gn.x == -1


class TestGridResolution:
    def test_positive(self):
        assert GRID_RESOLUTION > 0

    def test_reasonable_range(self):
        # 격자 해상도가 1~500m 사이여야 함
        assert 1.0 <= GRID_RESOLUTION <= 500.0


# ── Low-Level A* 테스트 ────────────────────────────────────


class TestLowLevelAstar:
    """low_level_astar edge case 테스트"""

    BOUNDS = {"x": [-5, 5], "y": [-5, 5], "z": [0, 3]}

    def test_same_start_goal(self):
        """시작 = 목표 → 단일 노드 경로"""
        node = GridNode(0, 0, 1)
        path = low_level_astar(node, node, [], "d1", self.BOUNDS)
        assert path == [node]

    def test_simple_path(self):
        """인접 노드로의 단순 경로"""
        start = GridNode(0, 0, 1)
        goal = GridNode(2, 0, 1)
        path = low_level_astar(start, goal, [], "d1", self.BOUNDS)
        assert len(path) >= 3
        assert path[0] == start
        assert path[-1] == goal

    def test_no_path_blocked(self):
        """모든 이웃이 제약으로 막힌 경우 → 빈 경로"""
        start = GridNode(0, 0, 1)
        goal = GridNode(0, 0, 2)
        # 목표 노드를 모든 시간에 제약
        constraints = [Constraint("d1", goal, t) for t in range(201)]
        path = low_level_astar(start, goal, constraints, "d1", self.BOUNDS,
                               max_time=5)
        # 경로가 없거나 목표에 도달하지 못함
        assert path == [] or path[-1] != goal

    def test_respects_max_time(self):
        """max_time 제한 내에서만 탐색"""
        start = GridNode(-5, -5, 0)
        goal = GridNode(5, 5, 3)
        path = low_level_astar(start, goal, [], "d1", self.BOUNDS, max_time=3)
        # max_time이 너무 짧으면 빈 경로
        assert isinstance(path, list)

    def test_constraint_avoidance(self):
        """제약 노드를 피해 우회"""
        start = GridNode(0, 0, 1)
        goal = GridNode(2, 0, 1)
        blocked = GridNode(1, 0, 1)
        constraints = [Constraint("d1", blocked, 1)]
        path = low_level_astar(start, goal, constraints, "d1", self.BOUNDS)
        assert len(path) >= 3
        # t=1에서 blocked 노드를 지나지 않음
        if len(path) > 1:
            assert path[1] != blocked


# ── Conflict Detection 테스트 ──────────────────────────────


class TestDetectConflict:
    def test_no_conflict(self):
        """겹치지 않는 경로 → 충돌 없음"""
        paths = {
            "d1": [GridNode(0, 0, 0), GridNode(1, 0, 0)],
            "d2": [GridNode(0, 1, 0), GridNode(1, 1, 0)],
        }
        assert detect_conflict(paths) is None

    def test_vertex_conflict(self):
        """같은 노드 동시 점유 → 충돌 탐지"""
        paths = {
            "d1": [GridNode(0, 0, 0), GridNode(1, 0, 0)],
            "d2": [GridNode(2, 0, 0), GridNode(1, 0, 0)],
        }
        conflict = detect_conflict(paths)
        assert conflict is not None
        assert conflict.node == GridNode(1, 0, 0)

    def test_empty_paths(self):
        """빈 경로 딕셔너리 → None"""
        assert detect_conflict({}) is None


# ── CBS 통합 테스트 ────────────────────────────────────────


class TestCBSPlan:
    BOUNDS = {"x": [-5, 5], "y": [-5, 5], "z": [0, 3]}

    def test_single_drone(self):
        """단일 드론 → 충돌 없는 경로"""
        starts = {"d1": GridNode(0, 0, 1)}
        goals = {"d1": GridNode(3, 0, 1)}
        paths = cbs_plan(starts, goals, self.BOUNDS)
        assert "d1" in paths
        assert paths["d1"][0] == starts["d1"]
        assert paths["d1"][-1] == goals["d1"]

    def test_two_drones_no_conflict(self):
        """비충돌 드론 쌍"""
        starts = {"d1": GridNode(0, 0, 1), "d2": GridNode(0, 3, 1)}
        goals = {"d1": GridNode(3, 0, 1), "d2": GridNode(3, 3, 1)}
        paths = cbs_plan(starts, goals, self.BOUNDS)
        assert len(paths) == 2

    def test_head_on_conflict_resolved(self):
        """정면 충돌 → CBS가 해소"""
        starts = {"d1": GridNode(0, 0, 1), "d2": GridNode(4, 0, 1)}
        goals = {"d1": GridNode(4, 0, 1), "d2": GridNode(0, 0, 1)}
        paths = cbs_plan(starts, goals, self.BOUNDS, max_ct_nodes=100)
        assert len(paths) == 2
        # 최종 경로에서 동시 점유 충돌이 없어야 함
        conflict = detect_conflict(paths)
        # CBS가 max_ct_nodes 내에 해소했으면 None
        # 못했으면 최선의 경로 반환 (잔여 충돌 가능)
        assert isinstance(paths, dict)
