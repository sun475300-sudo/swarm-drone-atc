"""
Phase 468: Obstacle Avoidance System with Reactive Control
"""

import numpy as np
from typing import List
from dataclasses import dataclass


@dataclass
class Obstacle:
    position: np.ndarray
    radius: float


class ObstacleAvoidanceSystem:
    def __init__(self, safety_distance: float = 5.0):
        self.safety_distance = safety_distance

    def compute_avoidance_vector(
        self, drone_pos: np.ndarray, obstacles: List[Obstacle]
    ) -> np.ndarray:
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
