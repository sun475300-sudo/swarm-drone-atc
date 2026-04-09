"""
Phase 470: Reporting System for Mission Summaries
"""

import numpy as np
from typing import Dict, List
from dataclasses import dataclass
import time


@dataclass
class MissionReport:
    mission_id: str
    drone_id: str
    duration_sec: float
    distance_m: float
    collisions: int


class ReportingSystem:
    def __init__(self):
        self.reports: List[MissionReport] = []

    def generate_report(
        self, mission_id: str, drone_id: str, stats: Dict
    ) -> MissionReport:
        report = MissionReport(
            mission_id=mission_id,
            drone_id=drone_id,
            duration_sec=stats.get("duration", 0),
            distance_m=stats.get("distance", 0),
            collisions=stats.get("collisions", 0),
        )
        self.reports.append(report)
        return report

    def get_summary(self) -> Dict:
        if not self.reports:
            return {}

        return {
            "total_missions": len(self.reports),
            "avg_duration": np.mean([r.duration_sec for r in self.reports]),
            "total_distance": sum(r.distance_m for r in self.reports),
            "total_collisions": sum(r.collisions for r in self.reports),
        }
