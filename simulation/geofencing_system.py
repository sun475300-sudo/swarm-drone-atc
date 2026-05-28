"""
Phase 474: Geofencing System for Airspace Restrictions
"""

from dataclasses import dataclass


@dataclass
class GeoZone:
    """``GeoZone`` 관련 기능을 제공한다."""
    zone_id: str
    zone_type: str
    boundaries: list[tuple[float, float]]
    min_altitude: float
    max_altitude: float


class GeofencingSystem:
    """``GeofencingSystem`` 역할을 담당한다."""
    def __init__(self):
        """인스턴스를 초기화한다."""
        self.zones: dict[str, GeoZone] = {}

    def add_zone(self, zone: GeoZone):
        """`zone` 항목을 추가한다."""
        self.zones[zone.zone_id] = zone

    def check_position(self, position: tuple[float, float, float]) -> list[str]:
        """`position` 결과를 계산하거나 판정한다."""
        x, y, z = position
        violations = []

        for zone_id, zone in self.zones.items():
            if self._point_in_polygon(x, y, zone.boundaries):
                if z < zone.min_altitude or z > zone.max_altitude:
                    violations.append(zone_id)

        return violations

    def _point_in_polygon(
        self, x: float, y: float, polygon: list[tuple[float, float]]
    ) -> bool:
        n = len(polygon)
        inside = False

        for i in range(n):
            j = (i - 1) % n
            xi, yi = polygon[i]
            xj, yj = polygon[j]

            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside

        return inside
