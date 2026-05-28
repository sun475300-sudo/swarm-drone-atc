"""
Phase 471: Flight Analysis System for Performance Review
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class FlightSegment:
    start_time: float
    end_time: float
    avg_speed: float
    max_altitude: float


class FlightAnalysisSystem:
    def __init__(self):
        self.flights: dict[str, list[FlightSegment]] = {}

    def analyze_flight(self, drone_id: str, telemetry: list[dict]) -> dict:
        speeds = [t.get("speed", 0) for t in telemetry]
        altitudes = [t.get("altitude", 0) for t in telemetry]

        return {
            "avg_speed": np.mean(speeds),
            "max_speed": np.max(speeds),
            "avg_altitude": np.mean(altitudes),
            "max_altitude": np.max(altitudes),
            "flight_duration": telemetry[-1].get("time", 0)
            - telemetry[0].get("time", 0),
        }
