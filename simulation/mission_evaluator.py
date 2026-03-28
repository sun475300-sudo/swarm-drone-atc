"""
임무 결과 평가
==============
임무 성공률 + KPI 점수 + 개선 권장.

사용법:
    me = MissionEvaluator()
    me.record_mission("m1", success=True, duration_s=300, distance_m=2000)
    score = me.evaluate("m1")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class MissionRecord:
    """임무 기록"""
    mission_id: str
    success: bool
    duration_s: float
    distance_m: float
    energy_wh: float = 0.0
    incidents: int = 0
    on_time: bool = True
    drone_id: str = ""


@dataclass
class EvaluationResult:
    """평가 결과"""
    mission_id: str
    score: float  # 0~100
    grade: str  # A, B, C, D, F
    recommendations: list[str]


class MissionEvaluator:
    """임무 결과 평가."""

    def __init__(self) -> None:
        self._records: dict[str, MissionRecord] = {}

    def record_mission(
        self, mission_id: str, success: bool = True,
        duration_s: float = 0.0, distance_m: float = 0.0,
        energy_wh: float = 0.0, incidents: int = 0,
        on_time: bool = True, drone_id: str = "",
    ) -> MissionRecord:
        record = MissionRecord(
            mission_id=mission_id, success=success,
            duration_s=duration_s, distance_m=distance_m,
            energy_wh=energy_wh, incidents=incidents,
            on_time=on_time, drone_id=drone_id,
        )
        self._records[mission_id] = record
        return record

    def evaluate(self, mission_id: str) -> EvaluationResult:
        record = self._records.get(mission_id)
        if not record:
            return EvaluationResult(mission_id, 0, "F", ["임무 기록 없음"])

        score = 100.0
        recs = []

        if not record.success:
            score -= 40
            recs.append("임무 실패 — 원인 분석 필요")

        if not record.on_time:
            score -= 15
            recs.append("시간 초과 — 경로 최적화 권장")

        if record.incidents > 0:
            score -= record.incidents * 10
            recs.append(f"사고 {record.incidents}건 — 안전 점검 필요")

        # 에너지 효율
        if record.distance_m > 0 and record.energy_wh > 0:
            eff = record.energy_wh / (record.distance_m / 1000)
            if eff > 30:
                score -= 10
                recs.append(f"에너지 비효율 ({eff:.1f} Wh/km) — 경로/속도 조정")

        score = max(0, min(100, score))

        if score >= 90:
            grade = "A"
        elif score >= 75:
            grade = "B"
        elif score >= 60:
            grade = "C"
        elif score >= 40:
            grade = "D"
        else:
            grade = "F"

        if not recs:
            recs.append("우수 — 현 수준 유지")

        return EvaluationResult(mission_id=mission_id, score=score, grade=grade, recommendations=recs)

    def success_rate(self) -> float:
        if not self._records:
            return 0.0
        return sum(1 for r in self._records.values() if r.success) / len(self._records) * 100

    def on_time_rate(self) -> float:
        if not self._records:
            return 0.0
        return sum(1 for r in self._records.values() if r.on_time) / len(self._records) * 100

    def grade_distribution(self) -> dict[str, int]:
        dist: dict[str, int] = {}
        for mid in self._records:
            grade = self.evaluate(mid).grade
            dist[grade] = dist.get(grade, 0) + 1
        return dist

    def summary(self) -> dict[str, Any]:
        return {
            "total_missions": len(self._records),
            "success_rate": round(self.success_rate(), 1),
            "on_time_rate": round(self.on_time_rate(), 1),
            "grade_distribution": self.grade_distribution(),
        }
