"""
Phase 465: Altitude Control System for Precision Height Maintenance
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class AltitudeTarget:
    """``AltitudeTarget`` 관련 기능을 제공한다."""
    target_height: float
    tolerance: float


class AltitudeControlSystem:
    """``AltitudeControlSystem`` 역할을 담당한다."""
    def __init__(self, kp: float = 1.5, ki: float = 0.1, kd: float = 0.5):
        """인스턴스를 초기화한다."""
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral = 0
        self.last_error = 0

    def compute_control(self, current_altitude: float, target: AltitudeTarget) -> float:
        """`control` 값을 계산한다."""
        error = target.target_height - current_altitude

        self.integral += error * 0.01
        self.integral = np.clip(self.integral, -10, 10)

        derivative = (error - self.last_error) / 0.01
        self.last_error = error

        output = self.kp * error + self.ki * self.integral + self.kd * derivative

        return np.clip(output, -100, 100)

    def reset(self):
        """`대상` 상태를 정리한다."""
        self.integral = 0
        self.last_error = 0
