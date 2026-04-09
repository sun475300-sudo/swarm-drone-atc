"""
자동 시나리오 생성기
====================
랜덤 파라미터 + 극한 조건 + 퍼지 테스트용 시나리오 자동 생성.

사용법:
    sg = ScenarioGenerator(seed=42)
    scenario = sg.generate_random()
    stress = sg.generate_stress_test(drones=200)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class GeneratedScenario:
    """생성된 시나리오"""
    name: str
    drone_count: int
    duration_s: float
    wind_speed_range: tuple[float, float]
    nfz_count: int
    failure_rate: float
    rogue_count: int
    params: dict[str, Any] = field(default_factory=dict)
    difficulty: str = "MEDIUM"  # EASY, MEDIUM, HARD, EXTREME


class ScenarioGenerator:
    """자동 시나리오 생성."""

    def __init__(self, seed: int = 42) -> None:
        self._rng = np.random.default_rng(seed)
        self._counter = 0

    def generate_random(self) -> GeneratedScenario:
        """완전 랜덤 시나리오"""
        self._counter += 1
        drones = int(self._rng.integers(10, 100))
        duration = float(self._rng.integers(30, 300))
        wind_lo = float(self._rng.uniform(0, 10))
        wind_hi = float(self._rng.uniform(wind_lo, wind_lo + 15))
        nfz = int(self._rng.integers(0, 5))
        fail_rate = float(self._rng.uniform(0, 0.1))
        rogues = int(self._rng.integers(0, 3))

        difficulty = self._estimate_difficulty(drones, wind_hi, fail_rate, rogues)

        return GeneratedScenario(
            name=f"RANDOM_{self._counter:04d}",
            drone_count=drones,
            duration_s=duration,
            wind_speed_range=(round(wind_lo, 1), round(wind_hi, 1)),
            nfz_count=nfz,
            failure_rate=round(fail_rate, 4),
            rogue_count=rogues,
            difficulty=difficulty,
        )

    def generate_stress_test(
        self, drones: int = 200, duration: float = 120.0
    ) -> GeneratedScenario:
        """스트레스 테스트 시나리오"""
        self._counter += 1
        return GeneratedScenario(
            name=f"STRESS_{self._counter:04d}",
            drone_count=drones,
            duration_s=duration,
            wind_speed_range=(5.0, 20.0),
            nfz_count=3,
            failure_rate=0.05,
            rogue_count=5,
            difficulty="EXTREME",
            params={"high_density": True, "multi_failure": True},
        )

    def generate_weather_extreme(self) -> GeneratedScenario:
        """극한 기상 시나리오"""
        self._counter += 1
        return GeneratedScenario(
            name=f"WEATHER_{self._counter:04d}",
            drone_count=50,
            duration_s=120.0,
            wind_speed_range=(15.0, 30.0),
            nfz_count=2,
            failure_rate=0.02,
            rogue_count=0,
            difficulty="HARD",
            params={"microburst": True, "icing": True, "visibility": 1000},
        )

    def generate_batch(self, n: int = 10) -> list[GeneratedScenario]:
        """배치 시나리오 생성"""
        return [self.generate_random() for _ in range(n)]

    def generate_progressive(
        self, levels: int = 5
    ) -> list[GeneratedScenario]:
        """난이도 점진 증가"""
        scenarios = []
        for i in range(levels):
            factor = (i + 1) / levels
            self._counter += 1
            scenarios.append(GeneratedScenario(
                name=f"PROGRESSIVE_{i+1}",
                drone_count=int(20 + 180 * factor),
                duration_s=60 + 240 * factor,
                wind_speed_range=(0, 5 + 20 * factor),
                nfz_count=int(factor * 5),
                failure_rate=round(factor * 0.1, 3),
                rogue_count=int(factor * 5),
                difficulty=["EASY", "MEDIUM", "MEDIUM", "HARD", "EXTREME"][i],
            ))
        return scenarios

    def _estimate_difficulty(
        self, drones: int, wind: float, fail_rate: float, rogues: int
    ) -> str:
        score = 0
        score += min(40, drones / 5)
        score += min(20, wind)
        score += min(20, fail_rate * 200)
        score += min(20, rogues * 7)

        if score >= 70:
            return "EXTREME"
        if score >= 50:
            return "HARD"
        if score >= 25:
            return "MEDIUM"
        return "EASY"

    def summary(self) -> dict[str, Any]:
        return {
            "scenarios_generated": self._counter,
        }
