"""
Phase 465: Altitude Control System for Precision Height Maintenance
"""

import numpy as np
from typing import Dict
from dataclasses import dataclass


@dataclass
class AltitudeTarget:
    target_height: float
    tolerance: float


class AltitudeControlSystem:
    def __init__(self, kp: float = 1.5, ki: float = 0.1, kd: float = 0.5):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral = 0
        self.last_error = 0

    def compute_control(self, current_altitude: float, target: AltitudeTarget) -> float:
        error = target.target_height - current_altitude

        self.integral += error * 0.01
        self.integral = np.clip(self.integral, -10, 10)

        derivative = (error - self.last_error) / 0.01
        self.last_error = error

        output = self.kp * error + self.ki * self.integral + self.kd * derivative

        return np.clip(output, -100, 100)

    def reset(self):
        self.integral = 0
        self.last_error = 0
