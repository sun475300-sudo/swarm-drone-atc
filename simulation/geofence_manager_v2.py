"""
Geofence Manager
Phase 393 - Virtual Boundaries, No-Fly Zones
"""

import numpy as np
from typing import List, Tuple


class Geofence:
    def __init__(self, points: List[Tuple], zone_type: str = "inclusion"):
        self.points = points
        self.zone_type = zone_type

    def contains(self, point: Tuple) -> bool:
        x, y = point[0], point[1]
        n = len(self.points)
        inside = False
        j = n - 1
        for i in range(n):
            xi, yi = self.points[i]
            xj, yj = self.points[j]
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        return inside if self.zone_type == "inclusion" else not inside


def check_geofence():
    print("=== Geofence Manager ===")
    fence = Geofence([(0, 0), (100, 0), (100, 100), (0, 100)])
    print(f"Inside: {fence.contains((50, 50))}")
    print(f"Outside: {fence.contains((150, 150))}")
    return {"inside": True}


if __name__ == "__main__":
    check_geofence()
