"""
비행 경로 계획기 — NFZ 회피 A* 격자 탐색
CBS cbs.py의 GridNode/get_neighbors 구조를 재활용하되,
NFZ 블록 셀을 직접 처리하는 독립 A* 구현.
"""
from __future__ import annotations
import heapq
import uuid
import math
import numpy as np
from dataclasses import dataclass, field
from typing import Optional

from src.airspace_control.planning.waypoint import Waypoint, Route, RouteCost
from simulation.cbs_planner.cbs import GridNode, GRID_RESOLUTION, position_to_grid


@dataclass(order=True)
class _Node:
    f: float
    g: float       = field(compare=False)
    node: GridNode = field(compare=False)
    parent: Optional["_Node"] = field(compare=False, default=None)


class FlightPathPlanner:
    """
    공역 경로 계획기.
    - NFZ 블록 셀을 회피하는 2D A* (고도는 cruise_altitude_m 고정)
    - 경로 스무딩 (공선 제거)
    - 비용 추정 (거리/시간/에너지/위험도)
    """

    def __init__(
        self,
        airspace_bounds: dict,     # {'x':[min,max],'y':[min,max],'z':[min,max]} (m)
        no_fly_zones: list[dict],  # [{'center': np.ndarray, 'radius_m': float}]
        grid_resolution_m: float = GRID_RESOLUTION,
        cruise_altitude_m: float = 60.0,
    ) -> None:
        self.bounds   = airspace_bounds
        self.nfz_list = no_fly_zones
        self.grid_res = grid_resolution_m
        self.cruise_alt = cruise_altitude_m
        self._blocked: frozenset[tuple[int, int]] | None = None
        self._nfz_hash: int = -1

    # ── 공개 API ─────────────────────────────────────────────

    def plan_route(
        self,
        drone_id: str,
        origin: np.ndarray,
        destination: np.ndarray,
        priority: int = 3,
        route_id: Optional[str] = None,
        cruise_speed_ms: float = 8.0,
    ) -> Route:
        if route_id is None:
            route_id = f"R-{uuid.uuid4().hex[:6].upper()}"

        waypoints = self._plan(origin, destination, cruise_speed_ms)
        return Route(
            route_id=route_id,
            drone_id=drone_id,
            waypoints=waypoints,
            priority=priority,
        )

    def estimate_cost(self, route: Route, cruise_speed_ms: float = 8.0) -> RouteCost:
        dist = route.total_distance_m
        if dist < 1.0:
            return RouteCost(0.0, 0.0, 0.0, 0.0)
        duration = dist / max(cruise_speed_ms, 0.1)
        energy   = duration * 100.0 / 3600.0   # 100 W 소비 가정
        risk     = self._path_risk(route)
        return RouteCost(distance_m=dist, duration_s=duration,
                         energy_wh=energy, risk_score=risk)

    def replan_avoiding(
        self,
        drone_id: str,
        current_pos: np.ndarray,
        destination: np.ndarray,
        blocked_node: GridNode,
        priority: int = 3,
        route_id: Optional[str] = None,
    ) -> Route:
        """임시 장애물을 추가해 재계획"""
        extra = frozenset([(blocked_node.x, blocked_node.y)])
        old_blocked = self._blocked
        self._blocked = (self._blocked or frozenset()) | extra
        route = self.plan_route(drone_id, current_pos, destination,
                                priority, route_id)
        self._blocked = old_blocked
        return route

    # ── 내부 구현 ─────────────────────────────────────────────

    def _build_blocked(self) -> frozenset[tuple[int, int]]:
        h = hash(str([(n['center'].tolist(), n['radius_m'])
                      for n in self.nfz_list]))
        if self._blocked is not None and h == self._nfz_hash:
            return self._blocked

        blocked: set[tuple[int, int]] = set()
        res = self.grid_res
        bx = self.bounds.get('x', [-5000, 5000])
        by = self.bounds.get('y', [-5000, 5000])

        for nfz in self.nfz_list:
            cx, cy = float(nfz['center'][0]), float(nfz['center'][1])
            r = float(nfz['radius_m']) + res
            ix_min = int(math.floor((cx - r) / res))
            ix_max = int(math.ceil( (cx + r) / res))
            iy_min = int(math.floor((cy - r) / res))
            iy_max = int(math.ceil( (cy + r) / res))
            for ix in range(ix_min, ix_max + 1):
                for iy in range(iy_min, iy_max + 1):
                    dx = ix * res - cx
                    dy = iy * res - cy
                    if math.hypot(dx, dy) < r:
                        blocked.add((ix, iy))

        self._blocked  = frozenset(blocked)
        self._nfz_hash = h
        return self._blocked

    def _is_blocked(self, x: int, y: int) -> bool:
        blocked = self._build_blocked()
        return (x, y) in blocked

    def _heuristic(self, a: GridNode, b: GridNode) -> float:
        return math.hypot(a.x - b.x, a.y - b.y)

    def _neighbors_2d(self, node: GridNode) -> list[GridNode]:
        bx = self.bounds.get('x', [-5000, 5000])
        by = self.bounds.get('y', [-5000, 5000])
        ix_min = int(bx[0] / self.grid_res)
        ix_max = int(bx[1] / self.grid_res)
        iy_min = int(by[0] / self.grid_res)
        iy_max = int(by[1] / self.grid_res)
        z = node.z
        result = []
        for dx, dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
            nx, ny = node.x + dx, node.y + dy
            if ix_min <= nx <= ix_max and iy_min <= ny <= iy_max:
                if not self._is_blocked(nx, ny):
                    result.append(GridNode(nx, ny, z))
        return result

    def _astar_2d(self, start: GridNode, goal: GridNode) -> list[GridNode]:
        open_heap: list[_Node] = []
        start_n = _Node(f=self._heuristic(start, goal), g=0.0, node=start)
        heapq.heappush(open_heap, start_n)
        visited: dict[tuple, float] = {}

        while open_heap:
            cur = heapq.heappop(open_heap)
            key = (cur.node.x, cur.node.y)
            if key in visited and visited[key] <= cur.g:
                continue
            visited[key] = cur.g

            if cur.node.x == goal.x and cur.node.y == goal.y:
                path = []
                n = cur
                while n:
                    path.append(n.node)
                    n = n.parent
                return list(reversed(path))

            step = 1.0
            for nb in self._neighbors_2d(cur.node):
                # 대각선 이동 비용
                is_diag = (nb.x != cur.node.x and nb.y != cur.node.y)
                move_cost = math.sqrt(2) if is_diag else 1.0
                g_new = cur.g + move_cost
                nb_key = (nb.x, nb.y)
                if nb_key not in visited or visited[nb_key] > g_new:
                    f_new = g_new + self._heuristic(nb, goal)
                    heapq.heappush(open_heap, _Node(f=f_new, g=g_new,
                                                    node=nb, parent=cur))
        return []  # 경로 없음

    def _smooth(self, grid_path: list[GridNode]) -> list[GridNode]:
        """공선에 가까운 중간 노드 제거 (5° 이내 방향 변화)"""
        if len(grid_path) <= 2:
            return grid_path
        result = [grid_path[0]]
        for i in range(1, len(grid_path) - 1):
            prev = result[-1]
            cur  = grid_path[i]
            nxt  = grid_path[i + 1]
            v1 = (cur.x - prev.x, cur.y - prev.y)
            v2 = (nxt.x - cur.x,  nxt.y - cur.y)
            a1 = math.atan2(v1[1], v1[0])
            a2 = math.atan2(v2[1], v2[0])
            delta = abs(math.degrees(a2 - a1)) % 360
            if delta > 180:
                delta = 360 - delta
            if delta > 5.0:
                result.append(cur)
        result.append(grid_path[-1])
        return result

    def _plan(
        self, origin: np.ndarray, destination: np.ndarray, speed: float
    ) -> list[Waypoint]:
        res = self.grid_res
        alt = self.cruise_alt

        # 격자 변환 (2D, 고도 고정)
        start_g = GridNode(
            int(round(origin[0] / res)),
            int(round(origin[1] / res)),
            int(round(alt / res)),
        )
        goal_g = GridNode(
            int(round(destination[0] / res)),
            int(round(destination[1] / res)),
            int(round(alt / res)),
        )

        grid_path = self._astar_2d(start_g, goal_g)
        if not grid_path:
            # 폴백: 직선 경로
            grid_path = [start_g, goal_g]

        smoothed = self._smooth(grid_path)

        waypoints: list[Waypoint] = []
        # 이륙점
        waypoints.append(Waypoint(position=origin.copy(), speed_ms=speed))
        # 상승
        climb_pos = np.array([origin[0], origin[1], alt])
        waypoints.append(Waypoint(position=climb_pos, speed_ms=speed))
        # 격자 경로 → 연속 좌표
        for gn in smoothed[1:-1]:
            pos = np.array([gn.x * res, gn.y * res, alt])
            waypoints.append(Waypoint(position=pos, speed_ms=speed))
        # 목적지 순항 고도
        dest_alt = np.array([destination[0], destination[1], alt])
        waypoints.append(Waypoint(position=dest_alt, speed_ms=speed))
        # 착륙점
        waypoints.append(Waypoint(position=destination.copy(), speed_ms=speed * 0.5))

        return waypoints

    def _path_risk(self, route: Route) -> float:
        """NFZ 근접도 기반 위험 점수 (0~1)"""
        if not route.waypoints or not self.nfz_list:
            return 0.0
        max_risk = 0.0
        for wp in route.waypoints:
            for nfz in self.nfz_list:
                dist = float(np.linalg.norm(wp.position[:2] - nfz['center'][:2]))
                margin = dist - nfz['radius_m']
                if margin < 200.0:
                    risk = max(0.0, 1.0 - margin / 200.0)
                    max_risk = max(max_risk, risk)
        return float(np.clip(max_risk, 0.0, 1.0))
