"""
Area Scan Planner
Phase 399 - Grid Survey, Path Coverage Optimization
"""

import numpy as np
from typing import List, Tuple


class AreaScanner:
    def __init__(self, area_width: float, area_height: float, overlap: float = 0.2):
        self.width = area_width
        self.height = area_height
        self.overlap = overlap
        self.fov = 60

    def compute_grid(self, altitude: float) -> List[Tuple]:
        ground_coverage = 2 * altitude * np.tan(np.radians(self.fov / 2))
        spacing = ground_coverage * (1 - self.overlap)

        num_rows = int(self.height / spacing) + 1
        num_cols = int(self.width / spacing) + 1

        waypoints = []
        for row in range(num_rows):
            for col in range(num_cols):
                x = col * spacing
                y = row * spacing
                waypoints.append((x, y, altitude))

        return waypoints

    def optimize_path(self, start: Tuple, waypoints: List[Tuple]) -> List[Tuple]:
        if not waypoints:
            return []

        ordered = [start]
        remaining = waypoints.copy()

        while remaining:
            current = ordered[-1]
            nearest = min(
                remaining,
                key=lambda w: np.linalg.norm(np.array(w[:2]) - np.array(current[:2])),
            )
            ordered.append(nearest)
            remaining.remove(nearest)

        return ordered[1:]


if __name__ == "__main__":
    print("=== Area Scanner ===")
    scanner = AreaScanner(500, 500, 0.2)
    wp = scanner.compute_grid(100)
    print(f"Waypoints: {len(wp)}")
    optimized = scanner.optimize_path((0, 0, 100), wp[:20])
    print(f"Optimized: {len(optimized)}")
