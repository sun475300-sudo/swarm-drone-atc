"""
Battery Management System
Phase 383 - SOC Estimation, Balancing, Protection
"""

import numpy as np
from dataclasses import dataclass
from typing import List


@dataclass
class Cell:
    voltage: float
    soc: float
    temperature: float
    resistance: float


class BMS:
    def __init__(self, n_cells: int = 4):
        self.cells = [Cell(3.7, 0.8, 25, 0.05) for _ in range(n_cells)]
        self.min_voltage = 3.0
        self.max_voltage = 4.2
        self.max_temp = 60

    def estimate_soc(self) -> float:
        return np.mean([c.soc for c in self.cells])

    def balance(self):
        avg_soc = self.estimate_soc()
        for c in self.cells:
            if c.soc > avg_soc + 0.05:
                c.soc -= 0.01

    def protect(self) -> str:
        max_v = max(c.voltage for c in self.cells)
        max_t = max(c.temperature for c in self.cells)

        if max_v > self.max_voltage:
            return "OVP"
        if max_v < self.min_voltage:
            return "UVP"
        if max_t > self.max_temp:
            return "OTP"
        return "OK"


def simulate_bms():
    print("=== Battery Management System ===")
    bms = BMS(n_cells=6)
    print(f"SOC: {bms.estimate_soc() * 100:.1f}%")
    bms.balance()
    status = bms.protect()
    print(f"Status: {status}")
    return {"soc": bms.estimate_soc(), "status": status}


if __name__ == "__main__":
    simulate_bms()
