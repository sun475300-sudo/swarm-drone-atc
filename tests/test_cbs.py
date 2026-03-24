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
