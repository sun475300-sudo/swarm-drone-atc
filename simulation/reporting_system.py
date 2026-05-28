"""
Phase 470: Reporting System for Mission Summaries
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class MissionReport:
    """``MissionReport`` 관련 기능을 제공한다."""
    mission_id: str
    drone_id: str
    duration_sec: float
    distance_m: float
    collisions: int


class ReportingSystem:
    """``ReportingSystem`` 역할을 담당한다."""
    def __init__(self):
        """인스턴스를 초기화한다."""
        self.reports: list[MissionReport] = []

    def generate_report(
        self, mission_id: str, drone_id: str, stats: dict
    ) -> MissionReport:
        """`report` 결과를 생성한다."""
        report = MissionReport(
            mission_id=mission_id,
            drone_id=drone_id,
            duration_sec=stats.get("duration", 0),
            distance_m=stats.get("distance", 0),
            collisions=stats.get("collisions", 0),
        )
        self.reports.append(report)
        return report

    def get_summary(self) -> dict:
        """`summary` 정보를 조회한다."""
        if not self.reports:
            return {}

        return {
            "total_missions": len(self.reports),
            "avg_duration": np.mean([r.duration_sec for r in self.reports]),
            "total_distance": sum(r.distance_m for r in self.reports),
            "total_collisions": sum(r.collisions for r in self.reports),
        }
