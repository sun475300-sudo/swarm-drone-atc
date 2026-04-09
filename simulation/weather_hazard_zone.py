"""
기상 위험 구역
==============
동적 기상 위험 구역 + 자동 회피 경로 + 알림.

사용법:
    whz = WeatherHazardZone()
    whz.add_zone("WZ1", center=(500, 500), radius=200, hazard_type="THUNDERSTORM")
    safe = whz.is_safe((600, 600, 50))
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class HazardZone:
    """기상 위험 구역"""
    zone_id: str
    center: tuple[float, float]
    radius: float
    hazard_type: str  # THUNDERSTORM, ICING, TURBULENCE, FOG, WIND_SHEAR
    severity: int = 3  # 1=mild, 5=extreme
    altitude_range: tuple[float, float] = (0, 500)
    active: bool = True
    speed_limit: float = 5.0  # 구역 내 최대 속도
    movement_vector: tuple[float, float] = (0, 0)  # 이동 속도 m/s


class WeatherHazardZone:
    """동적 기상 위험 구역 관리."""

    def __init__(self) -> None:
        self._zones: dict[str, HazardZone] = {}
        self._alerts: list[dict[str, Any]] = []

    def add_zone(
        self,
        zone_id: str,
        center: tuple[float, float],
        radius: float,
        hazard_type: str = "THUNDERSTORM",
        severity: int = 3,
        altitude_range: tuple[float, float] = (0, 500),
        movement: tuple[float, float] = (0, 0),
    ) -> HazardZone:
        zone = HazardZone(
            zone_id=zone_id, center=center, radius=radius,
            hazard_type=hazard_type, severity=severity,
            altitude_range=altitude_range, movement_vector=movement,
        )
        self._zones[zone_id] = zone
        return zone

    def remove_zone(self, zone_id: str) -> bool:
        if zone_id in self._zones:
            self._zones[zone_id].active = False
            return True
        return False

    def update_positions(self, dt: float) -> None:
        """구역 이동 업데이트"""
        for zone in self._zones.values():
            if zone.active and (zone.movement_vector[0] != 0 or zone.movement_vector[1] != 0):
                zone.center = (
                    zone.center[0] + zone.movement_vector[0] * dt,
                    zone.center[1] + zone.movement_vector[1] * dt,
                )

    def is_safe(self, position: tuple[float, float, float]) -> bool:
        """위치 안전 여부"""
        for zone in self._zones.values():
            if not zone.active:
                continue
            if self._in_zone(position, zone):
                return False
        return True

    def check_hazards(
        self, position: tuple[float, float, float],
    ) -> list[HazardZone]:
        """위치의 위험 구역 목록"""
        return [
            z for z in self._zones.values()
            if z.active and self._in_zone(position, z)
        ]

    def check_path(
        self,
        start: tuple[float, float, float],
        end: tuple[float, float, float],
        steps: int = 20,
    ) -> list[HazardZone]:
        """경로 상 위험 구역"""
        hazards = set()
        for i in range(steps + 1):
            t = i / steps
            pos = (
                start[0] + (end[0] - start[0]) * t,
                start[1] + (end[1] - start[1]) * t,
                start[2] + (end[2] - start[2]) * t,
            )
            for z in self.check_hazards(pos):
                hazards.add(z.zone_id)
        return [self._zones[zid] for zid in hazards if zid in self._zones]

    def suggest_avoidance(
        self,
        position: tuple[float, float, float],
        destination: tuple[float, float, float],
    ) -> tuple[float, float, float] | None:
        """회피 방향 제안"""
        hazards = self.check_path(position, destination)
        if not hazards:
            return None

        # 가장 가까운 위험 구역에서 벗어나는 방향
        nearest = min(
            hazards,
            key=lambda z: np.sqrt(
                (position[0] - z.center[0])**2 + (position[1] - z.center[1])**2
            ),
        )
        dx = position[0] - nearest.center[0]
        dy = position[1] - nearest.center[1]
        dist = max(np.sqrt(dx*dx + dy*dy), 1.0)

        # 위험 구역 반대 방향으로 회피
        offset = nearest.radius * 1.5
        avoid_x = position[0] + (dx / dist) * offset
        avoid_y = position[1] + (dy / dist) * offset

        return (avoid_x, avoid_y, position[2])

    def alert_drones(
        self,
        positions: dict[str, tuple[float, float, float]],
    ) -> list[dict[str, Any]]:
        """드론 위치 기반 경보 발행"""
        alerts = []
        for did, pos in positions.items():
            hazards = self.check_hazards(pos)
            for z in hazards:
                alert = {
                    "drone_id": did,
                    "zone_id": z.zone_id,
                    "hazard_type": z.hazard_type,
                    "severity": z.severity,
                }
                alerts.append(alert)
                self._alerts.append(alert)
        return alerts

    def _in_zone(self, pos: tuple[float, float, float], zone: HazardZone) -> bool:
        dx = pos[0] - zone.center[0]
        dy = pos[1] - zone.center[1]
        if dx*dx + dy*dy > zone.radius * zone.radius:
            return False
        if pos[2] < zone.altitude_range[0] or pos[2] > zone.altitude_range[1]:
            return False
        return True

    def active_zones(self) -> list[HazardZone]:
        return [z for z in self._zones.values() if z.active]

    def summary(self) -> dict[str, Any]:
        active = self.active_zones()
        by_type: dict[str, int] = {}
        for z in active:
            by_type[z.hazard_type] = by_type.get(z.hazard_type, 0) + 1
        return {
            "total_zones": len(self._zones),
            "active_zones": len(active),
            "by_type": by_type,
            "total_alerts": len(self._alerts),
        }
