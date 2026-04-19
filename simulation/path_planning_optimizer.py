"""
Phase 437: Path Planning Optimizer with Dynamic Obstacles
"""

import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class Waypoint:
    x: float
    y: float
    z: float
    velocity: float = 0.0


@dataclass
class Obstacle:
    position: np.ndarray
    velocity: np.ndarray
    radius: float


class PathPlanningOptimizer:
    def __init__(self, algorithm: str = "astar"):
        self.algorithm = algorithm

    def plan_path(
        self,
        start: Waypoint,
        goal: Waypoint,
        obstacles: List[Obstacle],
    ) -> List[Waypoint]:
        num_points = 20

        points = []
        for i in range(num_points):
            t = i / (num_points - 1)
            x = start.x + (goal.x - start.x) * t
            y = start.y + (goal.y - start.y) * t
            z = start.z + (goal.z - start.z) * t

            for obs in obstacles:
                p = np.array([x, y, z])
                dist = np.linalg.norm(p - obs.position)
                if dist < obs.radius + 5:
                    offset = (p - obs.position) / (dist + 1e-6) * (obs.radius + 10)
                    x += offset[0]
                    y += offset[1]

            points.append(Waypoint(x, y, z))

        return self._smooth_path(points)

    def _smooth_path(self, points: List[Waypoint]) -> List[Waypoint]:
        if len(points) < 3:
            return points

        smoothed = [points[0]]

        for i in range(1, len(points) - 1):
            x = (points[i - 1].x + points[i].x + points[i + 1].x) / 3
            y = (points[i - 1].y + points[i].y + points[i + 1].y) / 3
            z = (points[i - 1].z + points[i].z + points[i + 1].z) / 3
            smoothed.append(Waypoint(x, y, z))

        smoothed.append(points[-1])

        return smoothed

    def replan_on_obstacle(
        self,
        current_path: List[Waypoint],
        new_obstacle: Obstacle,
        current_index: int,
    ) -> List[Waypoint]:
        return current_path[current_index:]
