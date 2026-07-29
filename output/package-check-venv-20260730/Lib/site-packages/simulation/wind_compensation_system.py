"""
Phase 476: Wind Compensation System
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class WindVector:
    """``WindVector`` 관련 기능을 제공한다."""
    north_ms: float
    east_ms: float
    down_ms: float


class WindCompensationSystem:
    """``WindCompensationSystem`` 역할을 담당한다."""
    def __init__(self):
        """인스턴스를 초기화한다."""
        self.current_wind = WindVector(0, 0, 0)

    def update_wind(self, wind: WindVector):
        """`wind` 상태를 갱신한다."""
        self.current_wind = wind

    def compute_compensation(self, velocity: np.ndarray) -> np.ndarray:
        """`compensation` 값을 계산한다."""
        wind_vector = np.array(
            [
                self.current_wind.east_ms,
                self.current_wind.north_ms,
                self.current_wind.down_ms,
            ]
        )
        return -wind_vector
