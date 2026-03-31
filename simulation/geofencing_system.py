"""
Phase 474: Geofencing System for Airspace Restrictions
"""

import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class GeoZone:
    zone_id: str
    zone_type: str
    boundaries: List[Tuple[float, float]]
    min_altitude: float
    max_altitude: float


class GeofencingSystem:
    def __init__(self):
        self.zones: Dict[str, GeoZone] = {}

    def add_zone(self, zone: GeoZone):
        self.zones[zone.zone_id] = zone

    def check_position(self, position: Tuple[float, float, float]) -> List[str]:
        x, y, z = position
        violations = []

        for zone_id, zone in self.zones.items():
            if self._point_in_polygon(x, y, zone.boundaries):
                if z < zone.min_altitude or z > zone.max_altitude:
                    violations.append(zone_id)

        return violations

    def _point_in_polygon(
        self, x: float, y: float, polygon: List[Tuple[float, float]]
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
