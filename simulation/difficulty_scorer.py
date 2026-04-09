"""
시나리오 난이도 평가
===================
밀도/기상/NFZ/장애 복합 난이도 점수.

사용법:
    ds = DifficultyScorer()
    score = ds.evaluate(drone_count=100, wind_speed=15, nfz_count=5, failure_rate=0.1)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class DifficultyResult:
    """난이도 결과"""
    total_score: float  # 0~100
    level: str  # EASY, MODERATE, HARD, EXTREME
    breakdown: dict[str, float]
    recommendations: list[str]


class DifficultyScorer:
    """시나리오 난이도 평가."""

    WEIGHTS = {
        "density": 0.3,
        "weather": 0.25,
        "nfz": 0.15,
        "failure": 0.2,
        "terrain": 0.1,
    }

    def __init__(self) -> None:
        self._evaluations: list[DifficultyResult] = []

    def _density_score(self, drone_count: int, area_km2: float = 1.0) -> float:
        density = drone_count / max(area_km2, 0.01)
        return min(100, density / 5)  # 500대/km2 = 100

    def _weather_score(self, wind_speed: float = 0, visibility_km: float = 10, precipitation: float = 0) -> float:
        wind_s = min(100, wind_speed / 25 * 100)
        vis_s = max(0, (10 - visibility_km) / 10 * 100)
        rain_s = min(100, precipitation / 50 * 100)
        return wind_s * 0.5 + vis_s * 0.3 + rain_s * 0.2

    def _nfz_score(self, nfz_count: int = 0, nfz_coverage_pct: float = 0) -> float:
        count_s = min(100, nfz_count * 10)
        coverage_s = min(100, nfz_coverage_pct * 2)
        return count_s * 0.5 + coverage_s * 0.5

    def _failure_score(self, failure_rate: float = 0, comm_loss_rate: float = 0) -> float:
        fail_s = min(100, failure_rate * 500)
        comm_s = min(100, comm_loss_rate * 300)
        return fail_s * 0.6 + comm_s * 0.4

    def _terrain_score(self, max_altitude_var: float = 0, urban_density: float = 0) -> float:
        alt_s = min(100, max_altitude_var / 200 * 100)
        urban_s = min(100, urban_density * 100)
        return alt_s * 0.5 + urban_s * 0.5

    def evaluate(
        self, drone_count: int = 50, area_km2: float = 1.0,
        wind_speed: float = 5, visibility_km: float = 10,
        precipitation: float = 0, nfz_count: int = 0,
        nfz_coverage_pct: float = 0, failure_rate: float = 0,
        comm_loss_rate: float = 0, max_altitude_var: float = 0,
        urban_density: float = 0,
    ) -> DifficultyResult:
        breakdown = {
            "density": self._density_score(drone_count, area_km2),
            "weather": self._weather_score(wind_speed, visibility_km, precipitation),
            "nfz": self._nfz_score(nfz_count, nfz_coverage_pct),
            "failure": self._failure_score(failure_rate, comm_loss_rate),
            "terrain": self._terrain_score(max_altitude_var, urban_density),
        }

        total = sum(breakdown[k] * self.WEIGHTS[k] for k in breakdown)
        total = round(min(100, max(0, total)), 1)

        if total >= 80:
            level = "EXTREME"
        elif total >= 60:
            level = "HARD"
        elif total >= 35:
            level = "MODERATE"
        else:
            level = "EASY"

        recs = []
        if breakdown["density"] > 70:
            recs.append("드론 수 감소 또는 공역 확장 권장")
        if breakdown["weather"] > 60:
            recs.append("기상 안정 시 실행 권장")
        if breakdown["failure"] > 50:
            recs.append("장애 대비 여유 드론 배치")

        result = DifficultyResult(
            total_score=total, level=level,
            breakdown={k: round(v, 1) for k, v in breakdown.items()},
            recommendations=recs,
        )
        self._evaluations.append(result)
        return result

    def compare_scenarios(self, results: list[DifficultyResult]) -> dict[str, Any]:
        if not results:
            return {}
        scores = [r.total_score for r in results]
        return {
            "easiest": round(min(scores), 1),
            "hardest": round(max(scores), 1),
            "average": round(float(np.mean(scores)), 1),
        }

    def summary(self) -> dict[str, Any]:
        return {
            "evaluations": len(self._evaluations),
            "avg_difficulty": round(
                float(np.mean([e.total_score for e in self._evaluations])), 1
            ) if self._evaluations else 0,
        }
