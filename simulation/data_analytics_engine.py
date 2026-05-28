"""
Phase 453: Data Analytics Engine for Flight Data Analysis
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class FlightData:
    """``FlightData`` 관련 기능을 제공한다."""
    drone_id: str
    timestamp: float
    position: np.ndarray
    velocity: np.ndarray
    battery: float


class DataAnalyticsEngine:
    """``DataAnalyticsEngine`` 역할을 담당한다."""
    def __init__(self):
        """인스턴스를 초기화한다."""
        self.flight_data: dict[str, list[FlightData]] = {}
        self.analytics_results: dict = {}

    def ingest_data(self, data: FlightData):
        """``ingest_data`` 동작을 수행한다."""
        if data.drone_id not in self.flight_data:
            self.flight_data[data.drone_id] = []
        self.flight_data[data.drone_id].append(data)

    def calculate_statistics(self, drone_id: str) -> dict:
        """``calculate_statistics`` 동작을 수행한다."""
        if drone_id not in self.flight_data:
            return {}

        data = self.flight_data[drone_id]
        velocities = [d.velocity for d in data]

        return {
            "total_flights": len(data),
            "avg_speed": np.mean([np.linalg.norm(v) for v in velocities]),
            "max_speed": max(np.linalg.norm(v) for v in velocities),
        }

    def detect_patterns(self, drone_id: str) -> list[str]:
        """`patterns` 결과를 계산하거나 판정한다."""
        patterns = []
        if drone_id in self.flight_data and len(self.flight_data[drone_id]) > 100:
            patterns.append("frequent_flying")
        return patterns
