"""
Phase 475: Auto Landing System for Precision Landing
"""

import numpy as np
from typing import Optional
from dataclasses import dataclass


@dataclass
class LandingTarget:
    x: float
    y: float
    z: float
    precision_cm: float


class AutoLandingSystem:
    def __init__(self):
        self.target: Optional[LandingTarget] = None

    def set_target(self, target: LandingTarget):
        self.target = target

    def compute_approach(self, current_pos: np.ndarray) -> np.ndarray:
        if not self.target:
            return np.zeros(3)

        target_pos = np.array([self.target.x, self.target.y, self.target.z])
        error = target_pos - current_pos

        return error * 0.5

    def is_landed(self, current_pos: np.ndarray) -> bool:
        if not self.target:
            return False

        error = np.linalg.norm(
            current_pos - np.array([self.target.x, self.target.y, self.target.z])
        )
        return error < 0.1
