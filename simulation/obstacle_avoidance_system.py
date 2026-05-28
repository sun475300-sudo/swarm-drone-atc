"""
Phase 468: Obstacle Avoidance System with Reactive Control
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class Obstacle:
    """``Obstacle`` 관련 기능을 제공한다."""
    position: np.ndarray
    radius: float


class ObstacleAvoidanceSystem:
    """``ObstacleAvoidanceSystem`` 역할을 담당한다."""
    def __init__(self, safety_distance: float = 5.0):
        """인스턴스를 초기화한다."""
        self.safety_distance = safety_distance

    def compute_avoidance_vector(
        self, drone_pos: np.ndarray, obstacles: list[Obstacle]
    ) -> np.ndarray:
        """`avoidance vector` 값을 계산한다."""
        avoidance = np.zeros(3)

        for obs in obstacles:
            diff = drone_pos - obs.position
            dist = np.linalg.norm(diff)

            if dist < self.safety_distance + obs.radius:
                magnitude = (
                    self.safety_distance + obs.radius - dist
                ) / self.safety_distance
                direction = diff / (dist + 1e-6)
                avoidance += direction * magnitude * 10

        return avoidance
