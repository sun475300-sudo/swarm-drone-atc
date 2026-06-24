"""심화: A* 최적화 동치성(behavior-preserving) 증명 테스트.

최적화 내용: `_astar_2d`가 차단 노드 집합(blocked)을 탐색당 1회만 계산하고
`_neighbors_2d(node, blocked)`로 전달(이전: 이웃마다 `_is_blocked` 호출 →
`_build_blocked` 재실행). NFZ는 탐색 동안 불변이므로 결과는 동일해야 한다.

검증 전략: 동일 플래너에서
  (a) 최적화 경로  = planner._astar_2d(s, g)
  (b) 구(old) 경로 = `_neighbors_2d`를 '이웃마다 _is_blocked 호출' 버전으로
                     몽키패치한 뒤 planner._astar_2d(s, g)
를 다수 무작위 (start, goal, NFZ) 조합에서 노드 단위로 비교한다.
또한 반환 경로가 차단 셀을 통과하지 않음(안전 불변식)을 확인한다.
"""
from __future__ import annotations

import types

import numpy as np
import pytest

from simulation.cbs_planner.cbs import GridNode
from src.airspace_control.planning.flight_path_planner import FlightPathPlanner

pytestmark = pytest.mark.unit


def _old_neighbors(self, node: GridNode, blocked) -> list[GridNode]:
    """구 동작 재현: 전달된 blocked를 무시하고 이웃마다 _is_blocked를 호출."""
    bx = self.bounds.get("x", [-5000, 5000])
    by = self.bounds.get("y", [-5000, 5000])
    ix_min = int(bx[0] / self.grid_res)
    ix_max = int(bx[1] / self.grid_res)
    iy_min = int(by[0] / self.grid_res)
    iy_max = int(by[1] / self.grid_res)
    z = node.z
    result = []
    for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]:
        nx, ny = node.x + dx, node.y + dy
        if ix_min <= nx <= ix_max and iy_min <= ny <= iy_max and not self._is_blocked(nx, ny):
            result.append(GridNode(nx, ny, z))
    return result


def _make_planner(nfz_list):
    return FlightPathPlanner(
        airspace_bounds={"x": [-5000, 5000], "y": [-5000, 5000], "z": [0, 120]},
        no_fly_zones=nfz_list,
    )


def _path_key(path):
    return [(n.x, n.y) for n in path]


def test_astar_optimized_equals_per_call_reference():
    """최적화 A* 경로 == 구(per-call _is_blocked) 기준 경로 (노드 단위 동일)."""
    rng = np.random.default_rng(20260620)
    res = GridNode  # noqa: F841  (가독성용 — 사용 안 함)
    cases = 0
    for _ in range(40):
        # 무작위 NFZ 0~2개
        n_nfz = int(rng.integers(0, 3))
        nfz = [
            {
                "center": np.array(
                    [float(rng.integers(-2500, 2500)), float(rng.integers(-2500, 2500)), 60.0]
                ),
                "radius_m": float(rng.integers(200, 800)),
            }
            for _ in range(n_nfz)
        ]
        planner = _make_planner(nfz)
        grid = planner.grid_res
        s = GridNode(int(rng.integers(-4000, 4000) / grid), int(rng.integers(-4000, 4000) / grid),
                     int(60 / grid))
        g = GridNode(int(rng.integers(-4000, 4000) / grid), int(rng.integers(-4000, 4000) / grid),
                     int(60 / grid))

        # (a) 최적화 경로
        path_opt = planner._astar_2d(s, g)

        # (b) 구 동작으로 몽키패치 후 경로
        planner2 = _make_planner(nfz)
        planner2._neighbors_2d = types.MethodType(_old_neighbors, planner2)
        path_old = planner2._astar_2d(s, g)

        assert _path_key(path_opt) == _path_key(path_old), (
            f"경로 불일치 (NFZ={n_nfz}, s=({s.x},{s.y}), g=({g.x},{g.y}))"
        )
        cases += 1
    assert cases == 40


def test_returned_path_avoids_blocked_cells():
    """반환 경로의 모든 격자 노드는 차단(blocked) 셀이 아니어야 한다(안전 불변식)."""
    rng = np.random.default_rng(7)
    for _ in range(15):
        nfz = [
            {
                "center": np.array([float(rng.integers(-1500, 1500)),
                                    float(rng.integers(-1500, 1500)), 60.0]),
                "radius_m": float(rng.integers(300, 700)),
            }
        ]
        planner = _make_planner(nfz)
        blocked = planner._build_blocked()
        grid = planner.grid_res
        s = GridNode(int(-4000 / grid), int(-4000 / grid), int(60 / grid))
        g = GridNode(int(4000 / grid), int(4000 / grid), int(60 / grid))
        path = planner._astar_2d(s, g)
        if not path:
            continue
        # 시작/도착을 제외한 중간 노드는 차단 셀을 통과하지 않아야 한다
        for n in path[1:-1]:
            assert (n.x, n.y) not in blocked, f"경로가 차단 셀 통과: ({n.x},{n.y})"


def test_plan_route_deterministic():
    """동일 입력 → 동일 경로(결정성)."""
    nfz = [{"center": np.array([0.0, 0.0, 60.0]), "radius_m": 600.0}]
    p1 = _make_planner(nfz)
    p2 = _make_planner(nfz)
    o = np.array([-3000.0, -3000.0, 0.0])
    d = np.array([3000.0, 3000.0, 60.0])
    r1 = p1.plan_route("D", o, d)
    r2 = p2.plan_route("D", o, d)
    k1 = [tuple(np.round(w.position, 3)) for w in r1.waypoints]
    k2 = [tuple(np.round(w.position, 3)) for w in r2.waypoints]
    assert k1 == k2
