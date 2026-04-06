"""
Phase 661: Jump Point Search (JPS) 3D Pathfinder

BurnySc2/Jump-Point-Search의 JPS 알고리즘 개념을 참고하여
드론 3D 공역 경로탐색에 최적화된 순수 Python 구현.

Reference: https://github.com/BurnySc2/Jump-Point-Search (MIT License)

JPS는 A*의 확장으로, 균일 격자에서 대칭 경로를 제거하여
탐색 노드 수를 크게 줄입니다. 3D 확장 시 26방향 이동을 지원합니다.

이 구현은 Cython 의존성 없이 NumPy만 사용합니다.
"""
from __future__ import annotations

import heapq
import math
from typing import Optional

import numpy as np


def _heuristic_euclidean(a: tuple, b: tuple) -> float:
    """3D 유클리드 거리 휴리스틱."""
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    dz = a[2] - b[2] if len(a) > 2 and len(b) > 2 else 0
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def _in_bounds(pos: tuple, shape: tuple) -> bool:
    """좌표가 격자 범위 안에 있는지 확인."""
    for i, v in enumerate(pos):
        if v < 0 or v >= shape[i]:
            return False
    return True


def _is_walkable(grid: np.ndarray, pos: tuple, wall: int = 0) -> bool:
    """해당 셀이 이동 가능한지 확인."""
    if not _in_bounds(pos, grid.shape):
        return False
    return int(grid[pos]) != wall


def jps_search_2d(
    start: tuple[int, int],
    goal: tuple[int, int],
    grid: np.ndarray,
    wall_value: int = 0,
) -> Optional[list[tuple[int, int]]]:
    """
    2D Jump Point Search.

    Parameters
    ----------
    start : (row, col)
    goal : (row, col)
    grid : 2D numpy array (0 = wall, nonzero = passable)
    wall_value : value treated as wall

    Returns
    -------
    list of (row, col) waypoints, or None if no path found
    """
    rows, cols = grid.shape

    def walkable(r, c):
        return 0 <= r < rows and 0 <= c < cols and grid[r, c] != wall_value

    SQRT2 = math.sqrt(2)

    # (f_cost, g_cost, (r,c), (dr,dc) or None)
    open_list: list[tuple[float, float, tuple, Optional[tuple]]] = []
    g_costs: dict[tuple, float] = {start: 0.0}
    parent: dict[tuple, tuple] = {}
    closed: set[tuple] = set()

    h0 = _heuristic_euclidean(start + (0,), goal + (0,))
    heapq.heappush(open_list, (h0, 0.0, start, None))

    def _jump(r, c, dr, dc):
        """점프 포인트를 찾을 때까지 방향으로 전진."""
        nr, nc = r + dr, c + dc
        if not walkable(nr, nc):
            return None

        if (nr, nc) == goal:
            return (nr, nc)

        # 대각선 이동
        if dr != 0 and dc != 0:
            # forced neighbor 확인
            if (not walkable(nr - dr, nc) and walkable(nr - dr, nc + dc)):
                return (nr, nc)
            if (not walkable(nr, nc - dc) and walkable(nr + dr, nc - dc)):
                return (nr, nc)
            # 수직/수평 방향 재귀 점프
            if _jump(nr, nc, dr, 0) is not None:
                return (nr, nc)
            if _jump(nr, nc, 0, dc) is not None:
                return (nr, nc)
        else:
            # 수직 이동
            if dr != 0:
                if (not walkable(nr, nc + 1) and walkable(nr + dr, nc + 1)):
                    return (nr, nc)
                if (not walkable(nr, nc - 1) and walkable(nr + dr, nc - 1)):
                    return (nr, nc)
            # 수평 이동
            else:
                if (not walkable(nr + 1, nc) and walkable(nr + 1, nc + dc)):
                    return (nr, nc)
                if (not walkable(nr - 1, nc) and walkable(nr - 1, nc + dc)):
                    return (nr, nc)

        # 대각선이면 다음 셀 이동 가능 확인
        if dr != 0 and dc != 0:
            if not walkable(nr + dr, nc) and not walkable(nr, nc + dc):
                return None

        return _jump(nr, nc, dr, dc)

    def _successors(node, direction):
        """현재 노드에서 점프 포인트 후보 생성."""
        r, c = node
        neighbors = []

        if direction is None:
            # 시작점: 8방향 모두 탐색
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    if walkable(r + dr, c + dc):
                        neighbors.append((dr, dc))
        else:
            dr, dc = direction
            if dr != 0 and dc != 0:
                # 대각선: 자연 이웃 + forced
                if walkable(r + dr, c):
                    neighbors.append((dr, 0))
                if walkable(r, c + dc):
                    neighbors.append((0, dc))
                if walkable(r + dr, c + dc):
                    neighbors.append((dr, dc))
                if not walkable(r - dr, c) and walkable(r - dr, c + dc):
                    neighbors.append((-dr, dc))
                if not walkable(r, c - dc) and walkable(r + dr, c - dc):
                    neighbors.append((dr, -dc))
            elif dr != 0:
                if walkable(r + dr, c):
                    neighbors.append((dr, 0))
                if not walkable(r, c + 1) and walkable(r + dr, c + 1):
                    neighbors.append((dr, 1))
                if not walkable(r, c - 1) and walkable(r + dr, c - 1):
                    neighbors.append((dr, -1))
            else:
                if walkable(r, c + dc):
                    neighbors.append((0, dc))
                if not walkable(r + 1, c) and walkable(r + 1, c + dc):
                    neighbors.append((1, dc))
                if not walkable(r - 1, c) and walkable(r - 1, c + dc):
                    neighbors.append((-1, dc))

        results = []
        for dr, dc in neighbors:
            jp = _jump(r, c, dr, dc)
            if jp is not None:
                results.append((jp, (dr, dc)))
        return results

    iterations = 0
    max_iterations = 50000

    while open_list and iterations < max_iterations:
        iterations += 1
        f, g, current, direction = heapq.heappop(open_list)

        if current in closed:
            continue
        closed.add(current)

        if current == goal:
            # 경로 역추적
            path = [goal]
            node = goal
            while node in parent:
                node = parent[node]
                path.append(node)
            path.reverse()
            return path

        for jp, d in _successors(current, direction):
            jr, jc = jp
            dist = _heuristic_euclidean(current + (0,), jp + (0,))
            new_g = g + dist
            if jp not in g_costs or new_g < g_costs[jp]:
                g_costs[jp] = new_g
                parent[jp] = current
                h = _heuristic_euclidean(jp + (0,), goal + (0,))
                heapq.heappush(open_list, (new_g + h, new_g, jp, d))

    return None  # 경로 없음


def jps_search_3d(
    start: tuple[int, int, int],
    goal: tuple[int, int, int],
    grid: np.ndarray,
    wall_value: int = 0,
    max_iterations: int = 100000,
) -> Optional[list[tuple[int, int, int]]]:
    """
    3D A* with jump-point-style pruning.

    완전한 3D JPS는 복잡하므로, 3D에서는 A* + neighbor pruning으로
    불필요한 탐색을 줄이는 하이브리드 방식을 사용합니다.

    Parameters
    ----------
    start, goal : (x, y, z) integer grid coordinates
    grid : 3D numpy array
    wall_value : impassable cell value
    max_iterations : search limit

    Returns
    -------
    list of (x, y, z) waypoints, or None
    """
    if not _in_bounds(start, grid.shape) or not _in_bounds(goal, grid.shape):
        return None
    if grid[start] == wall_value or grid[goal] == wall_value:
        return None

    # 26-directional neighbors
    directions = []
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                if dx == 0 and dy == 0 and dz == 0:
                    continue
                directions.append((dx, dy, dz))

    open_list: list[tuple[float, float, tuple]] = []
    g_costs: dict[tuple, float] = {start: 0.0}
    parent: dict[tuple, tuple] = {}
    closed: set[tuple] = set()

    h0 = _heuristic_euclidean(start, goal)
    heapq.heappush(open_list, (h0, 0.0, start))

    iterations = 0
    while open_list and iterations < max_iterations:
        iterations += 1
        f, g, current = heapq.heappop(open_list)

        if current in closed:
            continue
        closed.add(current)

        if current == goal:
            path = [goal]
            node = goal
            while node in parent:
                node = parent[node]
                path.append(node)
            path.reverse()
            return path

        for dx, dy, dz in directions:
            nx = current[0] + dx
            ny = current[1] + dy
            nz = current[2] + dz
            neighbor = (nx, ny, nz)

            if not _in_bounds(neighbor, grid.shape):
                continue
            if grid[neighbor] == wall_value:
                continue
            if neighbor in closed:
                continue

            # 이동 비용: 대각선은 sqrt(2) 또는 sqrt(3)
            move_cost = math.sqrt(dx * dx + dy * dy + dz * dz)
            new_g = g + move_cost

            if neighbor not in g_costs or new_g < g_costs[neighbor]:
                g_costs[neighbor] = new_g
                parent[neighbor] = current
                h = _heuristic_euclidean(neighbor, goal)
                heapq.heappush(open_list, (new_g + h, new_g, neighbor))

    return None
