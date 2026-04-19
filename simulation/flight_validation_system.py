"""
Phase 456: Flight Validation System for Safety Checks
"""

import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class FlightPlan:
    drone_id: str
    waypoints: List[np.ndarray]
    max_altitude: float
    battery_required: float


class FlightValidationSystem:
    def __init__(self, max_altitude_m: float = 120, min_battery_percent: float = 20):
        self.max_altitude = max_altitude_m
        self.min_battery = min_battery_percent

    def validate_plan(
        self, plan: FlightPlan, current_battery: float
    ) -> Tuple[bool, List[str]]:
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
        for wp1 in plan1.waypoints:
            for wp2 in plan2.waypoints:
                if np.linalg.norm(wp1 - wp2) < 10:
                    return True
        return False
