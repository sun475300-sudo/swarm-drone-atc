"""
Phase 464: Path Smoothing System for Trajectory Optimization
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class PathPoint:
    """``PathPoint`` 관련 기능을 제공한다."""
    x: float
    y: float
    z: float


class PathSmoothingSystem:
    """``PathSmoothingSystem`` 역할을 담당한다."""
    def __init__(self, smoothness_factor: float = 0.5):
        """인스턴스를 초기화한다."""
        self.smoothness = smoothness_factor

    def smooth_path(self, waypoints: list[PathPoint]) -> list[PathPoint]:
        """``smooth_path`` 동작을 수행한다."""
        if len(waypoints) < 3:
            return waypoints

        smoothed = [waypoints[0]]

        for i in range(1, len(waypoints) - 1):
            prev = waypoints[i - 1]
            curr = waypoints[i]
            next_w = waypoints[i + 1]

            new_x = (
                curr.x * (1 - self.smoothness)
                + (prev.x + next_w.x) / 2 * self.smoothness
            )
            new_y = (
                curr.y * (1 - self.smoothness)
                + (prev.y + next_w.y) / 2 * self.smoothness
            )
            new_z = (
                curr.z * (1 - self.smoothness)
                + (prev.z + next_w.z) / 2 * self.smoothness
            )

            smoothed.append(PathPoint(new_x, new_y, new_z))

        smoothed.append(waypoints[-1])
        return smoothed

    def calculate_curvature(self, waypoints: list[PathPoint]) -> list[float]:
        """``calculate_curvature`` 동작을 수행한다."""
        curvatures = []

        for i in range(1, len(waypoints) - 1):
            p1 = np.array([waypoints[i - 1].x, waypoints[i - 1].y])
            p2 = np.array([waypoints[i].x, waypoints[i].y])
            p3 = np.array([waypoints[i + 1].x, waypoints[i + 1].y])

            v1 = p2 - p1
            v2 = p3 - p2

            cross = abs(v1[0] * v2[1] - v1[1] * v2[0])
            denom = np.linalg.norm(v1) * np.linalg.norm(v2)

            curvature = cross / (denom + 1e-6)
            curvatures.append(curvature)

        return curvatures
