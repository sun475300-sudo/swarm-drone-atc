"""
Phase 472: Battery Management System
"""

import numpy as np
from typing import Dict


class BatteryManagementSystem:
    def __init__(self):
        self.batteries: Dict[str, Dict] = {}

    def register_battery(self, drone_id: str, capacity_wh: float):
        self.batteries[drone_id] = {
            "capacity": capacity_wh,
            "current": capacity_wh,
            "cycles": 0,
            "health": 100.0,
        }

    def get_charge_level(self, drone_id: str) -> float:
        if drone_id not in self.batteries:
            return 0.0
        return (
            self.batteries[drone_id]["current"]
            / self.batteries[drone_id]["capacity"]
            * 100
        )

    def estimate_flight_time(self, drone_id: str, power_w: float) -> float:
        if drone_id not in self.batteries:
            return 0.0
        return self.batteries[drone_id]["current"] / power_w
