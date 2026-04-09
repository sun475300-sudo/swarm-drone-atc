"""
Phase 476: Wind Compensation System
"""

import numpy as np
from dataclasses import dataclass


@dataclass
class WindVector:
    north_ms: float
    east_ms: float
    down_ms: float


class WindCompensationSystem:
    def __init__(self):
        self.current_wind = WindVector(0, 0, 0)

    def update_wind(self, wind: WindVector):
        self.current_wind = wind

    def compute_compensation(self, velocity: np.ndarray) -> np.ndarray:
        wind_vector = np.array(
            [
                self.current_wind.east_ms,
                self.current_wind.north_ms,
                self.current_wind.down_ms,
            ]
        )
        return -wind_vector
