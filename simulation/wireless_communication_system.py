"""
Phase 473: Wireless Communication System
"""

import numpy as np
from typing import Dict, List


class WirelessCommunicationSystem:
    def __init__(self):
        self.connections: Dict[str, Dict] = {}

    def establish_link(self, drone1: str, drone2: str, distance: float) -> bool:
        max_range = 500
        if distance > max_range:
            return False

        snr = 30 - distance / 20
        self.connections[f"{drone1}_{drone2}"] = {
            "snr": snr,
            "latency": distance / 300000 * 1000,
            "bandwidth": 100 * (1 - distance / max_range),
        }
        return True

    def get_link_quality(self, drone1: str, drone2: str) -> float:
        key = f"{drone1}_{drone2}"
        if key in self.connections:
            return self.connections[key]["snr"] / 30
        return 0.0
