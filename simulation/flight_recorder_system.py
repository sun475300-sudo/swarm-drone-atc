"""
Phase 477: Flight Recorder System for Data Logging
"""

import time
from dataclasses import dataclass

import numpy as np


@dataclass
class FlightRecord:
    timestamp: float
    position: np.ndarray
    velocity: np.ndarray
    battery: float


class FlightRecorderSystem:
    def __init__(self, max_records: int = 10000):
        self.max_records = max_records
        self.records: list[FlightRecord] = []

    def record(self, position: np.ndarray, velocity: np.ndarray, battery: float):
        record = FlightRecord(time.time(), position.copy(), velocity.copy(), battery)
        self.records.append(record)

        if len(self.records) > self.max_records:
            self.records.pop(0)

    def get_flight_data(self) -> list[dict]:
        return [
            {"time": r.timestamp, "position": r.position.tolist(), "battery": r.battery}
            for r in self.records
        ]
