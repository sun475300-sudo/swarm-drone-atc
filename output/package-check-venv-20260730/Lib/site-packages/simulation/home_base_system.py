"""
Phase 478: Home Base System for Return to Home
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class HomeBase:
    """``HomeBase`` 관련 기능을 제공한다."""
    position: np.ndarray
    radius: float


class HomeBaseSystem:
    """``HomeBaseSystem`` 역할을 담당한다."""
    def __init__(self):
        """인스턴스를 초기화한다."""
        self.home_base: HomeBase | None = None

    def set_home(self, position: np.ndarray, radius: float = 10.0):
        """`home` 상태를 갱신한다."""
        self.home_base = HomeBase(position, radius)

    def get_home_position(self) -> np.ndarray | None:
        """`home position` 정보를 조회한다."""
        if self.home_base:
            return self.home_base.position
        return None

    def is_at_home(self, position: np.ndarray) -> bool:
        """`at home` 여부를 반환한다."""
        if not self.home_base:
            return False
        return (
            np.linalg.norm(position - self.home_base.position) < self.home_base.radius
        )
