"""
동적 지오펜스 관리자
====================
다각형/원형 지오펜스 정의, 시간별 활성화, 실시간 침범 감지.
동적으로 지오펜스 추가/제거/수정 가능.

사용법:
    gm = GeofenceManager()
    gm.add_circle("hospital", center=(500, 500), radius=100)
    gm.add_polygon("park", vertices=[(0,0),(100,0),(100,100),(0,100)])
    violations = gm.check_position("drone_1", (510, 510, 50), t=10.0)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np


class GeofenceType(Enum):
    CIRCLE = "circle"
    POLYGON = "polygon"
    CORRIDOR = "corridor"


class GeofenceAction(Enum):
    DENY = "deny"  # 진입 불가 (NFZ)
    WARN = "warn"  # 경고만
    RESTRICT = "restrict"  # 허가 필요
    ALTITUDE_LIMIT = "altitude_limit"  # 고도 제한


@dataclass
class Geofence:
    """지오펜스 정의"""
    fence_id: str
    fence_type: GeofenceType
    action: GeofenceAction = GeofenceAction.DENY
    active: bool = True
    # 시간 기반 활성화
    active_start: float | None = None  # None = 항상
    active_end: float | None = None
    # 고도 범위
    min_altitude: float = 0.0
    max_altitude: float = 200.0
    # 원형
    center: tuple[float, float] | None = None
    radius: float = 0.0
    # 다각형
    vertices: list[tuple[float, float]] = field(default_factory=list)
    # 회랑
    start_point: tuple[float, float] | None = None
    end_point: tuple[float, float] | None = None
    width: float = 0.0
    # 메타
    description: str = ""
    priority: int = 0  # 높을수록 우선


@dataclass
class GeofenceViolation:
    """지오펜스 침범 이벤트"""
    fence_id: str
    drone_id: str
    t: float
    action: GeofenceAction
    distance_to_boundary: float  # 음수=내부, 양수=외부
    position: tuple[float, float, float]
    description: str = ""


class GeofenceManager:
    """
    동적 지오펜스 관리자.

    원형/다각형/회랑 지오펜스 + 시간별 활성화 + 침범 감지.
    """

    def __init__(self, buffer_m: float = 10.0) -> None:
        self._fences: dict[str, Geofence] = {}
        self._violations: list[GeofenceViolation] = []
        self._buffer_m = buffer_m  # 경고 버퍼 거리
        self._check_count = 0

    def add_circle(
        self,
        fence_id: str,
        center: tuple[float, float],
        radius: float,
        action: GeofenceAction = GeofenceAction.DENY,
        min_altitude: float = 0.0,
        max_altitude: float = 200.0,
        active_start: float | None = None,
        active_end: float | None = None,
        description: str = "",
        priority: int = 0,
    ) -> Geofence:
        """원형 지오펜스 추가"""
        fence = Geofence(
            fence_id=fence_id,
            fence_type=GeofenceType.CIRCLE,
            action=action,
            center=center,
            radius=radius,
            min_altitude=min_altitude,
            max_altitude=max_altitude,
            active_start=active_start,
            active_end=active_end,
            description=description or f"원형 지오펜스 r={radius}m",
            priority=priority,
        )
        self._fences[fence_id] = fence
        return fence

    def add_polygon(
        self,
        fence_id: str,
        vertices: list[tuple[float, float]],
        action: GeofenceAction = GeofenceAction.DENY,
        min_altitude: float = 0.0,
        max_altitude: float = 200.0,
        active_start: float | None = None,
        active_end: float | None = None,
        description: str = "",
        priority: int = 0,
    ) -> Geofence:
        """다각형 지오펜스 추가"""
        fence = Geofence(
            fence_id=fence_id,
            fence_type=GeofenceType.POLYGON,
            action=action,
            vertices=vertices,
            min_altitude=min_altitude,
            max_altitude=max_altitude,
            active_start=active_start,
            active_end=active_end,
            description=description or f"다각형 지오펜스 {len(vertices)}꼭짓점",
            priority=priority,
        )
        self._fences[fence_id] = fence
        return fence

    def add_corridor(
        self,
        fence_id: str,
        start: tuple[float, float],
        end: tuple[float, float],
        width: float,
        action: GeofenceAction = GeofenceAction.RESTRICT,
        description: str = "",
    ) -> Geofence:
        """회랑형 지오펜스 추가"""
        fence = Geofence(
            fence_id=fence_id,
            fence_type=GeofenceType.CORRIDOR,
            action=action,
            start_point=start,
            end_point=end,
            width=width,
            description=description or f"회랑 w={width}m",
        )
        self._fences[fence_id] = fence
        return fence

    def remove(self, fence_id: str) -> bool:
        """지오펜스 제거"""
        if fence_id in self._fences:
            del self._fences[fence_id]
            return True
        return False

    def activate(self, fence_id: str) -> None:
        if fence_id in self._fences:
            self._fences[fence_id].active = True

    def deactivate(self, fence_id: str) -> None:
        if fence_id in self._fences:
            self._fences[fence_id].active = False

    def check_position(
        self,
        drone_id: str,
        position: tuple[float, float, float],
        t: float = 0.0,
    ) -> list[GeofenceViolation]:
        """위치에 대한 지오펜스 침범 검사"""
        self._check_count += 1
        violations = []
        x, y, z = position

        for fence in self._fences.values():
            if not self._is_active(fence, t):
                continue

            # 고도 범위 체크
            if z < fence.min_altitude or z > fence.max_altitude:
                continue  # 고도 범위 밖이면 이 펜스 무관

            dist = self._distance_to_fence(fence, x, y)

            if dist < 0:  # 내부
                v = GeofenceViolation(
                    fence_id=fence.fence_id,
                    drone_id=drone_id,
                    t=t,
                    action=fence.action,
                    distance_to_boundary=dist,
                    position=position,
                    description=f"{fence.description} 침범 ({abs(dist):.1f}m 내부)",
                )
                violations.append(v)
                self._violations.append(v)
            elif dist < self._buffer_m and fence.action != GeofenceAction.WARN:
                # 버퍼 내 근접 경고
                v = GeofenceViolation(
                    fence_id=fence.fence_id,
                    drone_id=drone_id,
                    t=t,
                    action=GeofenceAction.WARN,
                    distance_to_boundary=dist,
                    position=position,
                    description=f"{fence.description} 근접 ({dist:.1f}m)",
                )
                violations.append(v)
                self._violations.append(v)

        return violations

    def check_path(
        self,
        drone_id: str,
        start: tuple[float, float, float],
        end: tuple[float, float, float],
        t: float = 0.0,
        steps: int = 10,
    ) -> list[GeofenceViolation]:
        """경로의 지오펜스 침범 검사 (보간)"""
        violations = []
        for i in range(steps + 1):
            frac = i / steps
            pos = (
                start[0] + (end[0] - start[0]) * frac,
                start[1] + (end[1] - start[1]) * frac,
                start[2] + (end[2] - start[2]) * frac,
            )
            vs = self.check_position(drone_id, pos, t)
            violations.extend(vs)
        return violations

    def get_active_fences(self, t: float = 0.0) -> list[Geofence]:
        """현재 시각 활성 지오펜스 목록"""
        return [f for f in self._fences.values() if self._is_active(f, t)]

    @property
    def violation_count(self) -> int:
        return len(self._violations)

    def violations_by_fence(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for v in self._violations:
            counts[v.fence_id] = counts.get(v.fence_id, 0) + 1
        return counts

    def _is_active(self, fence: Geofence, t: float) -> bool:
        """시간 기반 활성 여부"""
        if not fence.active:
            return False
        if fence.active_start is not None and t < fence.active_start:
            return False
        if fence.active_end is not None and t > fence.active_end:
            return False
        return True

    def _distance_to_fence(self, fence: Geofence, x: float, y: float) -> float:
        """
        점에서 지오펜스까지의 거리.
        음수 = 내부, 양수 = 외부.
        """
        if fence.fence_type == GeofenceType.CIRCLE:
            if fence.center is None:
                return float("inf")
            cx, cy = fence.center
            dist = np.sqrt((x - cx)**2 + (y - cy)**2)
            return dist - fence.radius  # 음수면 내부

        elif fence.fence_type == GeofenceType.POLYGON:
            return self._point_polygon_distance(x, y, fence.vertices)

        elif fence.fence_type == GeofenceType.CORRIDOR:
            return self._point_corridor_distance(
                x, y, fence.start_point, fence.end_point, fence.width
            )

        return float("inf")

    def _point_polygon_distance(
        self, x: float, y: float, vertices: list[tuple[float, float]]
    ) -> float:
        """점-다각형 부호 거리 (음수=내부)"""
        n = len(vertices)
        if n < 3:
            return float("inf")

        inside = self._point_in_polygon(x, y, vertices)

        # 최소 변까지 거리
        min_dist = float("inf")
        for i in range(n):
            x1, y1 = vertices[i]
            x2, y2 = vertices[(i + 1) % n]
            d = self._point_line_segment_dist(x, y, x1, y1, x2, y2)
            min_dist = min(min_dist, d)

        return -min_dist if inside else min_dist

    @staticmethod
    def _point_in_polygon(
        x: float, y: float, vertices: list[tuple[float, float]]
    ) -> bool:
        """레이 캐스팅 알고리즘"""
        n = len(vertices)
        inside = False
        j = n - 1
        for i in range(n):
            xi, yi = vertices[i]
            xj, yj = vertices[j]
            if ((yi > y) != (yj > y)) and (
                x < (xj - xi) * (y - yi) / (yj - yi) + xi
            ):
                inside = not inside
            j = i
        return inside

    @staticmethod
    def _point_line_segment_dist(
        px: float, py: float,
        x1: float, y1: float,
        x2: float, y2: float,
    ) -> float:
        """점에서 선분까지의 최단 거리"""
        dx, dy = x2 - x1, y2 - y1
        length_sq = dx * dx + dy * dy
        if length_sq < 1e-10:
            return float(np.sqrt((px - x1)**2 + (py - y1)**2))

        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / length_sq))
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy
        return float(np.sqrt((px - proj_x)**2 + (py - proj_y)**2))

    def _point_corridor_distance(
        self,
        x: float, y: float,
        start: tuple[float, float] | None,
        end: tuple[float, float] | None,
        width: float,
    ) -> float:
        """점에서 회랑까지의 부호 거리"""
        if start is None or end is None:
            return float("inf")
        d = self._point_line_segment_dist(
            x, y, start[0], start[1], end[0], end[1]
        )
        half_w = width / 2.0
        return d - half_w  # 음수면 회랑 내부

    def summary(self) -> dict[str, Any]:
        return {
            "total_fences": len(self._fences),
            "active_fences": sum(1 for f in self._fences.values() if f.active),
            "total_checks": self._check_count,
            "total_violations": self.violation_count,
            "by_fence": self.violations_by_fence(),
        }

    def clear(self) -> None:
        self._fences.clear()
        self._violations.clear()
        self._check_count = 0
