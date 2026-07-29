"""
Phase 477: Flight Recorder System for Data Logging
"""

import time
from dataclasses import dataclass

import numpy as np


@dataclass
class FlightRecord:
    """``FlightRecord`` 데이터를 표현한다."""
    timestamp: float
    position: np.ndarray
    velocity: np.ndarray
    battery: float


class FlightRecorderSystem:
    """``FlightRecorderSystem`` 역할을 담당한다."""
    def __init__(self, max_records: int = 10000):
        """인스턴스를 초기화한다."""
        self.max_records = max_records
        self.records: list[FlightRecord] = []

    def record(self, position: np.ndarray, velocity: np.ndarray, battery: float):
        """`대상` 정보를 기록한다."""
        record = FlightRecord(time.time(), position.copy(), velocity.copy(), battery)
        self.records.append(record)

        if len(self.records) > self.max_records:
            self.records.pop(0)

    def get_flight_data(self) -> list[dict]:
        """`flight data` 정보를 조회한다."""
        return [
            {"time": r.timestamp, "position": r.position.tolist(), "battery": r.battery}
            for r in self.records
        ]
