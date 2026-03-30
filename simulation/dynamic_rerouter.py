"""Phase 282: Dynamic Re-routing Engine — 동적 경로 재설정 엔진.

실시간 장애물, 기상변화, NFZ(No-Fly Zone) 활성화에 따른
즉각적인 경로 재계산 및 A* 기반 회피 경로 생성.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
import heapq


class ObstacleType(Enum):
    STATIC = "static"
    DYNAMIC = "dynamic"
    NFZ = "nfz"
    WEATHER = "weather"
    TEMPORARY = "temporary"


@dataclass
class Obstacle:
    obstacle_id: str
    center: np.ndarray
    radius: float
    otype: ObstacleType = ObstacleType.STATIC
    active: bool = True
    expiry_sec: Optional[float] = None


@dataclass
class RouteSegment:
    start: np.ndarray
    end: np.ndarray
    cost: float = 0.0
    altitude: float = 50.0


@dataclass
class Route:
    route_id: str
    drone_id: str
    segments: List[RouteSegment] = field(default_factory=list)
    total_cost: float = 0.0
    reroute_count: int = 0
    is_valid: bool = True


class AStarPathfinder:
    """3D A* 경로 탐색기 (격자 기반)."""

    def __init__(self, grid_size: float = 10.0, bounds: Tuple[float, float, float] = (500.0, 500.0, 200.0)):
        self.grid_size = grid_size
        self.bounds = bounds

    def _to_grid(self, pos: np.ndarray) -> Tuple[int, int, int]:
        return tuple(int(p / self.grid_size) for p in pos[:3])

    def _to_world(self, grid: Tuple[int, int, int]) -> np.ndarray:
        return np.array([g * self.grid_size + self.grid_size / 2 for g in grid])

    def _heuristic(self, a: Tuple[int, int, int], b: Tuple[int, int, int]) -> float:
        return sum((ai - bi) ** 2 for ai, bi in zip(a, b)) ** 0.5 * self.grid_size

    def _is_blocked(self, pos: np.ndarray, obstacles: List[Obstacle]) -> bool:
        for obs in obstacles:
            if obs.active and np.linalg.norm(pos[:3] - obs.center[:3]) < obs.radius:
                return True
        return False

    def find_path(self, start: np.ndarray, goal: np.ndarray, obstacles: List[Obstacle], max_iterations: int = 2000) -> List[np.ndarray]:
        start_g = self._to_grid(start)
        goal_g = self._to_grid(goal)
        open_set = [(self._heuristic(start_g, goal_g), 0, start_g)]
        came_from: Dict[Tuple, Tuple] = {}
        g_score: Dict[Tuple, float] = {start_g: 0}
        closed: Set[Tuple] = set()
        iterations = 0
        neighbors_3d = [(dx, dy, dz) for dx in [-1, 0, 1] for dy in [-1, 0, 1] for dz in [-1, 0, 1] if (dx, dy, dz) != (0, 0, 0)]

        while open_set and iterations < max_iterations:
            iterations += 1
            _, g, current = heapq.heappop(open_set)
            if current == goal_g:
                path = [self._to_world(goal_g)]
                node = goal_g
                while node in came_from:
                    node = came_from[node]
                    path.append(self._to_world(node))
                return list(reversed(path))
            if current in closed:
                continue
            closed.add(current)
            for dx, dy, dz in neighbors_3d:
                nb = (current[0] + dx, current[1] + dy, current[2] + dz)
                if any(n < 0 for n in nb):
                    continue
                nb_pos = self._to_world(nb)
                if self._is_blocked(nb_pos, obstacles):
                    continue
                move_cost = self.grid_size * (abs(dx) + abs(dy) + abs(dz)) ** 0.5
                tentative_g = g_score.get(current, float("inf")) + move_cost
                if tentative_g < g_score.get(nb, float("inf")):
                    g_score[nb] = tentative_g
                    came_from[nb] = current
                    f = tentative_g + self._heuristic(nb, goal_g)
                    heapq.heappush(open_set, (f, tentative_g, nb))
        # Fallback: direct path
        return [start, goal]


class DynamicRerouter:
    """동적 경로 재설정 엔진.

    - 실시간 장애물 등록/해제
    - A* 기반 회피 경로 생성
    - 경로 유효성 검증
    - 재라우팅 이력 추적
    """

    def __init__(self, rng_seed: int = 42):
        self._rng = np.random.default_rng(rng_seed)
        self._obstacles: Dict[str, Obstacle] = {}
        self._routes: Dict[str, Route] = {}
        self._pathfinder = AStarPathfinder()
        self._reroute_history: List[dict] = []

    def add_obstacle(self, obstacle: Obstacle):
        self._obstacles[obstacle.obstacle_id] = obstacle

    def remove_obstacle(self, obstacle_id: str) -> bool:
        if obstacle_id in self._obstacles:
            del self._obstacles[obstacle_id]
            return True
        return False

    def create_route(self, route_id: str, drone_id: str, waypoints: List[np.ndarray]) -> Route:
        segments = []
        for i in range(len(waypoints) - 1):
            cost = np.linalg.norm(waypoints[i + 1] - waypoints[i])
            segments.append(RouteSegment(start=waypoints[i], end=waypoints[i + 1], cost=cost))
        total = sum(s.cost for s in segments)
        route = Route(route_id=route_id, drone_id=drone_id, segments=segments, total_cost=total)
        self._routes[route_id] = route
        return route

    def validate_route(self, route_id: str) -> bool:
        route = self._routes.get(route_id)
        if not route:
            return False
        active_obs = [o for o in self._obstacles.values() if o.active]
        for seg in route.segments:
            n_checks = max(2, int(seg.cost / 5.0))
            for t in np.linspace(0, 1, n_checks):
                point = seg.start * (1 - t) + seg.end * t
                for obs in active_obs:
                    if np.linalg.norm(point[:3] - obs.center[:3]) < obs.radius:
                        route.is_valid = False
                        return False
        route.is_valid = True
        return True

    def reroute(self, route_id: str) -> Optional[Route]:
        route = self._routes.get(route_id)
        if not route or not route.segments:
            return None
        start = route.segments[0].start
        goal = route.segments[-1].end
        active_obs = [o for o in self._obstacles.values() if o.active]
        path = self._pathfinder.find_path(start, goal, active_obs)
        if len(path) < 2:
            return None
        new_segments = []
        for i in range(len(path) - 1):
            cost = np.linalg.norm(path[i + 1] - path[i])
            new_segments.append(RouteSegment(start=path[i], end=path[i + 1], cost=cost))
        route.segments = new_segments
        route.total_cost = sum(s.cost for s in new_segments)
        route.reroute_count += 1
        route.is_valid = True
        self._reroute_history.append({"route": route_id, "drone": route.drone_id, "reroute_count": route.reroute_count})
        return route

    def auto_reroute_all(self) -> List[str]:
        rerouted = []
        for rid in list(self._routes.keys()):
            if not self.validate_route(rid):
                result = self.reroute(rid)
                if result:
                    rerouted.append(rid)
        return rerouted

    def get_route(self, route_id: str) -> Optional[Route]:
        return self._routes.get(route_id)

    def summary(self) -> dict:
        valid = sum(1 for r in self._routes.values() if r.is_valid)
        return {
            "total_routes": len(self._routes),
            "valid_routes": valid,
            "total_obstacles": len(self._obstacles),
            "active_obstacles": sum(1 for o in self._obstacles.values() if o.active),
            "total_reroutes": len(self._reroute_history),
        }
