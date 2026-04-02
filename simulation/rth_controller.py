"""
Return-to-Home Controller
Phase 398 - RTH Logic, Smart RTH
"""
import numpy as np
from typing import Tuple


class RTHController:
    def __init__(self, home_pos: Tuple):
        self.home = home_pos
        self.safe_altitude = 50.0
        self.min_battery_percent = 20.0

    def should_activate(self, battery_percent: float, signal_lost: bool, 
                      distance_home: float) -> bool:
        if battery_percent < self.min_battery_percent:
            return True
        if signal_lost:
            return True
        if distance_home > 1000:
            return True
        return False

    def compute_route(self, current_pos: Tuple, battery_percent: float) -> list:
        cx, cy, cz = current_pos
        hx, hy, hz = self.home
        
        if cz < self.safe_altitude:
            climb_points = [(cx, cy, cz + 5) for _ in range(int((self.safe_altitude - cz)/5))]
        else:
            climb_points = []
        
        cruise = [(cx + (hx-cx)*i/10, cy + (hy-cy)*i/10, self.safe_altitude) for i in range(1, 10)]
        
        descend = [(hx, hy, hz)]
        
        return climb_points + cruise + descend


if __name__ == "__main__":
    print("=== RTH ===")
    rth = RTHController((0, 0, 0))
    print(f"Activate: {rth.should_activate(15, False, 500)}")
    route = rth.compute_route((100, 100, 30), 20)
    print(f"Route points: {len(route)}")
