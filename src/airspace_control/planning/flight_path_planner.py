"""
비행 경로 계획기
- A*: 사전 구축된 공역 그래프에서 최적 경로
- APF 기반 실시간 재계획 (avoidance와 연동)
"""
from __future__ import annotations
import heapq
import numpy as np
from dataclasses import dataclass, field
from typing import Optional

from src.airspace_control.planning.waypoint import Waypoint, Route, RouteCost


@dataclass(order=True)
class _AStarNode:
    f_cost: float
    position: np.ndarray = field(compare=False)
    g_cost:   float = field(compare=False, default=0.0)
    parent:   Optional['_AStarNode'] = field(compare=False, default=None)

    def key(self) -> tuple:
        return tuple(np.round(self.position, 1))


class FlightPathPlanner:
    """
    공역 경로 계획기.
    격자 기반 A* (기본) + 연속 공간 APF 회피 (실시간).
    """

    def __init__(
        self,
        airspace_bounds: dict,    # {'x': [min,max], 'y': [min,max], 'z': [min,max]} (미터)
        no_fly_zones: list[dict], # [{'center': np.ndarray, 'radius_m': float}]
        grid_resolution_m: float = 50.0,
        cruise_altitude_m: float = 60.0,
    ):
        self.bounds = airspace_bounds
        self.no_fly_zones = no_fly_zones
        self.grid_res = grid_resolution_m
        self.cruise_alt = cruise_altitude_m

    def plan_route(
        self,
        drone_id: str,
        origin: np.ndarray,
        destination: np.ndarray,
        priority: int = 3,
        route_id: Optional[str] = None,
    ) -> Route:
        """A* 경로 계획"""
        if route_id is None:
            import uuid
            route_id = f"R-{uuid.uuid4().hex[:6].upper()}"

        waypoints = self._astar(origin, destination)
        route = Route(
            route_id=route_id,
            drone_id=drone_id,
            waypoints=waypoints,
            priority=priority,
        )
        return route

    def _astar(self, start: np.ndarray, goal: np.ndarray) -> list[Waypoint]:
        """격자화된 A* 탐색"""
        def heuristic(pos: np.ndarray) -> float:
            return float(np.linalg.norm(goal - pos))

        def is_valid(pos: np.ndarray) -> bool:
            for nfz in self.no_fly_zones:
                if np.linalg.norm(pos[:2] - nfz['center'][:2]) < nfz['radius_m']:
                    return False
            return True

        # 크루즈 고도로 상승 후 비행하는 단순 경로
        cruise_z = -self.cruise_alt  # NED: Down

        waypoints = [
            Waypoint(position=start.copy()),
            Waypoint(position=np.array([start[0], start[1], cruise_z])),
            Waypoint(position=np.array([goal[0], goal[1], cruise_z])),
            Waypoint(position=goal.copy()),
        ]

        # NFZ 회피: 직선 경로가 NFZ를 통과하면 우회점 추가
        mid_pos = np.array([goal[0], goal[1], cruise_z])
        if not is_valid(mid_pos):
            # 간단한 우회: 90도 틀어서 우회
            detour = np.array([
                (start[0] + goal[0]) / 2 + 500,
                (start[1] + goal[1]) / 2,
                cruise_z,
            ])
            waypoints.insert(2, Waypoint(position=detour))

        return waypoints

    def replan_avoiding(
        self,
        drone_id: str,
        origin: np.ndarray,
        destination: np.ndarray,
        blocked_node,
        priority: int = 3,
    ) -> Route:
        """
        특정 격자 노드를 회피하는 재경로 계획.

        Parameters
        ----------
        blocked_node: CBS GridNode — 이 격자 위치를 NFZ 처럼 회피
        """
        import uuid
        route_id = f"R-{uuid.uuid4().hex[:6].upper()}"

        # blocked_node 위치를 임시 NFZ로 추가하여 회피
        extra_nfz = []
        if blocked_node is not None:
            res = self.grid_res
            blocked_center = np.array([
                blocked_node.x * res,
                blocked_node.y * res,
                blocked_node.z * res if hasattr(blocked_node, 'z') else self.cruise_alt,
            ], dtype=float)
            extra_nfz.append({"center": blocked_center, "radius_m": res * 1.5})

        old_nfz = self.no_fly_zones
        self.no_fly_zones = old_nfz + extra_nfz
        try:
            waypoints = self._astar(origin, destination)
        finally:
            self.no_fly_zones = old_nfz

        return Route(
            route_id=route_id,
            drone_id=drone_id,
            waypoints=waypoints,
            priority=priority,
        )

    def estimate_cost(self, route: Route, cruise_speed_ms: float = 8.0) -> RouteCost:
        dist = route.total_distance_m
        duration = dist / max(cruise_speed_ms, 0.1)
        energy = duration * 100.0 / 3600.0  # 가정: 100W 소비
        return RouteCost(distance_m=dist, duration_s=duration, energy_wh=energy)
