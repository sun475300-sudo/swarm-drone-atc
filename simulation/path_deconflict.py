"""
경로 탈충돌기
=============
4D 경로(x,y,z,t) 충돌 검사 + 시간 분리.
계획 단계에서 다중 드론 경로 간 충돌 사전 제거.

사용법:
    dc = PathDeconflict(separation=30.0)
    dc.add_path("drone_1", waypoints_with_time)
    dc.add_path("drone_2", waypoints_with_time)
    conflicts = dc.find_conflicts()
    resolved = dc.resolve_by_time_shift()
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class Waypoint4D:
    """4D 웨이포인트"""
    x: float
    y: float
    z: float
    t: float  # 예상 도착 시각 (s)


@dataclass
class PathConflict:
    """경로 충돌"""
    drone_a: str
    drone_b: str
    t: float  # 충돌 시각
    distance: float
    pos_a: tuple[float, float, float]
    pos_b: tuple[float, float, float]


class PathDeconflict:
    """
    4D 경로 탈충돌기.

    경로 간 최소 분리 위반 탐색 + 시간 이동 해소.
    """

    def __init__(
        self,
        separation_h: float = 30.0,
        separation_v: float = 10.0,
        time_step: float = 1.0,
    ) -> None:
        self.separation_h = separation_h
        self.separation_v = separation_v
        self.time_step = time_step
        self._paths: dict[str, list[Waypoint4D]] = {}
        self._time_offsets: dict[str, float] = {}  # 시간 이동량

    def add_path(
        self, drone_id: str, waypoints: list[Waypoint4D]
    ) -> None:
        self._paths[drone_id] = sorted(waypoints, key=lambda w: w.t)
        self._time_offsets[drone_id] = 0.0

    def remove_path(self, drone_id: str) -> None:
        self._paths.pop(drone_id, None)
        self._time_offsets.pop(drone_id, None)

    def find_conflicts(self) -> list[PathConflict]:
        """모든 경로 쌍 간 충돌 탐색"""
        conflicts = []
        drone_ids = list(self._paths.keys())

        for i in range(len(drone_ids)):
            for j in range(i + 1, len(drone_ids)):
                da, db = drone_ids[i], drone_ids[j]
                cs = self._check_pair(da, db)
                conflicts.extend(cs)

        return sorted(conflicts, key=lambda c: c.t)

    def resolve_by_time_shift(
        self, max_shift_s: float = 30.0, step_s: float = 5.0
    ) -> dict[str, float]:
        """시간 이동으로 충돌 해소"""
        conflicts = self.find_conflicts()
        if not conflicts:
            return dict(self._time_offsets)

        for conflict in conflicts:
            # 우선순위가 낮은 드론(알파벳 순)을 지연
            delayed = max(conflict.drone_a, conflict.drone_b)

            for shift in np.arange(step_s, max_shift_s + step_s, step_s):
                self._time_offsets[delayed] = shift
                # 이 쌍의 충돌 재검사
                remaining = self._check_pair(
                    conflict.drone_a, conflict.drone_b
                )
                if not remaining:
                    break
            else:
                # 최대 이동으로도 해소 불가 시 최대값 유지
                self._time_offsets[delayed] = max_shift_s

        return dict(self._time_offsets)

    def interpolate_position(
        self, drone_id: str, t: float
    ) -> tuple[float, float, float] | None:
        """시각 t에서의 보간 위치"""
        path = self._paths.get(drone_id)
        if not path:
            return None

        offset = self._time_offsets.get(drone_id, 0.0)
        t_adj = t - offset

        if t_adj <= path[0].t:
            return (path[0].x, path[0].y, path[0].z)
        if t_adj >= path[-1].t:
            return (path[-1].x, path[-1].y, path[-1].z)

        for k in range(len(path) - 1):
            if path[k].t <= t_adj <= path[k + 1].t:
                dt = path[k + 1].t - path[k].t
                if dt < 1e-6:
                    return (path[k].x, path[k].y, path[k].z)
                frac = (t_adj - path[k].t) / dt
                return (
                    path[k].x + (path[k + 1].x - path[k].x) * frac,
                    path[k].y + (path[k + 1].y - path[k].y) * frac,
                    path[k].z + (path[k + 1].z - path[k].z) * frac,
                )
        return None

    def _check_pair(self, da: str, db: str) -> list[PathConflict]:
        """두 경로 간 충돌 검사"""
        path_a = self._paths.get(da, [])
        path_b = self._paths.get(db, [])
        if not path_a or not path_b:
            return []

        off_a = self._time_offsets.get(da, 0.0)
        off_b = self._time_offsets.get(db, 0.0)

        t_min = min(path_a[0].t + off_a, path_b[0].t + off_b)
        t_max = max(path_a[-1].t + off_a, path_b[-1].t + off_b)

        conflicts = []
        t = t_min
        while t <= t_max:
            pos_a = self.interpolate_position(da, t)
            pos_b = self.interpolate_position(db, t)

            if pos_a and pos_b:
                h_dist = np.sqrt(
                    (pos_a[0] - pos_b[0])**2 + (pos_a[1] - pos_b[1])**2
                )
                v_dist = abs(pos_a[2] - pos_b[2])
                dist_3d = np.sqrt(
                    (pos_a[0] - pos_b[0])**2
                    + (pos_a[1] - pos_b[1])**2
                    + (pos_a[2] - pos_b[2])**2
                )

                if h_dist < self.separation_h and v_dist < self.separation_v:
                    conflicts.append(PathConflict(
                        drone_a=da, drone_b=db, t=t,
                        distance=float(dist_3d),
                        pos_a=pos_a, pos_b=pos_b,
                    ))

            t += self.time_step

        return conflicts

    @property
    def path_count(self) -> int:
        return len(self._paths)

    def summary(self) -> dict[str, Any]:
        conflicts = self.find_conflicts()
        return {
            "total_paths": self.path_count,
            "total_conflicts": len(conflicts),
            "time_offsets": dict(self._time_offsets),
            "min_conflict_dist": min(
                (c.distance for c in conflicts), default=0
            ),
        }
