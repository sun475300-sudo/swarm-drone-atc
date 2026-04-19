"""
Phase 478: Home Base System for Return to Home
"""

import numpy as np
from typing import Optional
from dataclasses import dataclass


@dataclass
class HomeBase:
    position: np.ndarray
    radius: float


class HomeBaseSystem:
    def __init__(self):
        self.home_base: Optional[HomeBase] = None

    def set_home(self, position: np.ndarray, radius: float = 10.0):
        self.home_base = HomeBase(position, radius)

    def get_home_position(self) -> Optional[np.ndarray]:
        if self.home_base:
            return self.home_base.position
        return None

    def is_at_home(self, position: np.ndarray) -> bool:
        if not self.home_base:
            return False
        return (
            np.linalg.norm(position - self.home_base.position) < self.home_base.radius
        )
