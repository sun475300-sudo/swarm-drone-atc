"""
Phase 456: Flight Validation System for Safety Checks
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class FlightPlan:
    """``FlightPlan`` 관련 기능을 제공한다."""
    drone_id: str
    waypoints: list[np.ndarray]
    max_altitude: float
    battery_required: float


class FlightValidationSystem:
    """``FlightValidationSystem`` 역할을 담당한다."""
    def __init__(self, max_altitude_m: float = 120, min_battery_percent: float = 20):
        """인스턴스를 초기화한다."""
        self.max_altitude = max_altitude_m
        self.min_battery = min_battery_percent

    def validate_plan(
        self, plan: FlightPlan, current_battery: float
    ) -> tuple[bool, list[str]]:
        """`plan` 결과를 계산하거나 판정한다."""
        errors = []

        for i, wp in enumerate(plan.waypoints):
            if wp[2] > self.max_altitude:
                errors.append(f"Waypoint {i} exceeds max altitude")

        if current_battery < self.min_battery:
            errors.append(
                f"Battery {current_battery}% below minimum {self.min_battery}%"
            )

        return len(errors) == 0, errors

    def check_collision_risk(self, plan1: FlightPlan, plan2: FlightPlan) -> bool:
        """`collision risk` 결과를 계산하거나 판정한다."""
        for wp1 in plan1.waypoints:
            for wp2 in plan2.waypoints:
                if np.linalg.norm(wp1 - wp2) < 10:
                    return True
        return False
