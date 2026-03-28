"""
비상 계획 수립기
================
대안 경로 사전 계산 + 실시간 전환 + 비용 비교.

사용법:
    cp = ContingencyPlanner()
    cp.set_primary_path("d1", waypoints)
    alts = cp.compute_alternatives("d1", blocked_zones=[(500,500,100)])
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class ContingencyRoute:
    """비상 대안 경로"""
    route_id: str
    waypoints: list[tuple[float, float, float]]
    total_distance_m: float
    detour_pct: float  # 주 경로 대비 우회율
    avoids: list[str] = field(default_factory=list)  # 회피 구역 ID
    priority: int = 1


class ContingencyPlanner:
    """비상 대안 경로 사전 계획."""

    def __init__(self, grid_step: float = 50.0) -> None:
        self._primary: dict[str, list[tuple[float, float, float]]] = {}
        self._alternatives: dict[str, list[ContingencyRoute]] = {}
        self._grid_step = grid_step

    def set_primary_path(
        self, drone_id: str, waypoints: list[tuple[float, float, float]]
    ) -> None:
        self._primary[drone_id] = list(waypoints)

    def compute_alternatives(
        self,
        drone_id: str,
        blocked_zones: list[tuple[float, float, float]] | None = None,
        n_alternatives: int = 3,
    ) -> list[ContingencyRoute]:
        """대안 경로 생성 (단순 우회)"""
        primary = self._primary.get(drone_id)
        if not primary or len(primary) < 2:
            return []

        blocked = blocked_zones or []
        primary_dist = self._total_dist(primary)
        alternatives = []

        offsets = [
            (self._grid_step, 0, 0),
            (-self._grid_step, 0, 0),
            (0, self._grid_step, 0),
            (self._grid_step, self._grid_step, 0),
            (0, 0, 20),
        ]

        for i, offset in enumerate(offsets[:n_alternatives]):
            alt_wps = [primary[0]]
            for wp in primary[1:-1]:
                new_wp = (wp[0] + offset[0], wp[1] + offset[1], wp[2] + offset[2])
                # 차단 구역 회피 검사
                safe = all(
                    np.sqrt((new_wp[0]-bz[0])**2 + (new_wp[1]-bz[1])**2) > bz[2]
                    for bz in blocked
                )
                alt_wps.append(new_wp if safe else (
                    wp[0] + offset[0]*2, wp[1] + offset[1]*2, wp[2] + offset[2]
                ))
            alt_wps.append(primary[-1])

            alt_dist = self._total_dist(alt_wps)
            detour = ((alt_dist - primary_dist) / max(primary_dist, 0.01)) * 100

            alternatives.append(ContingencyRoute(
                route_id=f"{drone_id}_ALT_{i+1}",
                waypoints=alt_wps,
                total_distance_m=alt_dist,
                detour_pct=max(0, detour),
                avoids=[f"zone_{j}" for j in range(len(blocked))],
                priority=i + 1,
            ))

        self._alternatives[drone_id] = alternatives
        return alternatives

    def get_best_alternative(self, drone_id: str) -> ContingencyRoute | None:
        alts = self._alternatives.get(drone_id, [])
        if not alts:
            return None
        return min(alts, key=lambda a: a.total_distance_m)

    def switch_to_alternative(
        self, drone_id: str, route_id: str
    ) -> bool:
        """대안 경로로 전환"""
        alts = self._alternatives.get(drone_id, [])
        for alt in alts:
            if alt.route_id == route_id:
                self._primary[drone_id] = alt.waypoints
                return True
        return False

    def _total_dist(self, wps: list[tuple[float, float, float]]) -> float:
        total = 0.0
        for i in range(len(wps) - 1):
            total += float(np.linalg.norm(
                np.array(wps[i+1]) - np.array(wps[i])
            ))
        return total

    def summary(self) -> dict[str, Any]:
        return {
            "primary_routes": len(self._primary),
            "alternatives_computed": sum(
                len(a) for a in self._alternatives.values()
            ),
        }
