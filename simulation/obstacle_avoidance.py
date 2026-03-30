"""
Obstacle Avoidance Controller
Phase 394 - Reactive Planning, LIDAR-based Avoidance
"""

import numpy as np
from typing import Tuple


class ObstacleAvoidance:
    def __init__(self, safe_distance: float = 5.0):
        self.safe_distance = safe_distance

    def compute_avoidance(
        self, current_pos: Tuple, target: Tuple, obstacles: list
    ) -> Tuple:
        direction = np.array(target) - np.array(current_pos)
        norm = np.linalg.norm(direction)
        if norm < 0.1:
            return current_pos
        desired = direction / norm

        avoidance = np.zeros(3)
        for obs in obstacles:
            to_obs = np.array(current_pos) - np.array(obs[:3])
            dist = np.linalg.norm(to_obs)
            if dist < self.safe_distance and dist > 0.1:
                avoidance += (to_obs / dist) * (self.safe_distance - dist)

        new_direction = desired + avoidance * 0.5
        new_direction /= np.linalg.norm(new_direction) + 1e-6

        return tuple(np.array(current_pos) + new_direction * 2)


if __name__ == "__main__":
    print("=== Obstacle Avoidance ===")
    ao = ObstacleAvoidance(5.0)
    new_pos = ao.compute_avoidance((0, 0, 10), (100, 100, 10), [(10, 10, 10)])
    print(f"New position: {new_pos}")
