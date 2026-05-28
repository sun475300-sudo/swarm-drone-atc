"""
Phase 475: Auto Landing System for Precision Landing
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class LandingTarget:
    """``LandingTarget`` 관련 기능을 제공한다."""
    x: float
    y: float
    z: float
    precision_cm: float


class AutoLandingSystem:
    """``AutoLandingSystem`` 역할을 담당한다."""
    def __init__(self):
        """인스턴스를 초기화한다."""
        self.target: LandingTarget | None = None

    def set_target(self, target: LandingTarget):
        """`target` 상태를 갱신한다."""
        self.target = target

    def compute_approach(self, current_pos: np.ndarray) -> np.ndarray:
        """`approach` 값을 계산한다."""
        if not self.target:
            return np.zeros(3)

        target_pos = np.array([self.target.x, self.target.y, self.target.z])
        error = target_pos - current_pos

        return error * 0.5

    def is_landed(self, current_pos: np.ndarray) -> bool:
        """`landed` 여부를 반환한다."""
        if not self.target:
            return False

        error = np.linalg.norm(
            current_pos - np.array([self.target.x, self.target.y, self.target.z])
        )
        return error < 0.1
