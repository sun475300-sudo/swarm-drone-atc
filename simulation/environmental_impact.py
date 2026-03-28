"""
환경 영향 분석
=============
소음/에너지 종합 환경 점수 + 친환경 경로.

사용법:
    ei = EnvironmentalImpact()
    ei.record_flight("d1", distance_m=5000, energy_wh=40, noise_db=65)
    score = ei.impact_score("d1")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class FlightImpact:
    """비행 환경 영향"""
    drone_id: str
    distance_m: float
    energy_wh: float
    noise_db: float
    altitude_m: float = 50.0
    over_residential: bool = False


class EnvironmentalImpact:
    """환경 영향 분석."""

    NOISE_LIMIT_DB = 70.0
    ENERGY_TARGET_WH_KM = 10.0

    def __init__(self) -> None:
        self._records: dict[str, list[FlightImpact]] = {}

    def record_flight(
        self, drone_id: str, distance_m: float = 0,
        energy_wh: float = 0, noise_db: float = 50,
        altitude_m: float = 50, over_residential: bool = False,
    ) -> None:
        if drone_id not in self._records:
            self._records[drone_id] = []
        self._records[drone_id].append(FlightImpact(
            drone_id=drone_id, distance_m=distance_m,
            energy_wh=energy_wh, noise_db=noise_db,
            altitude_m=altitude_m, over_residential=over_residential,
        ))

    def impact_score(self, drone_id: str) -> float:
        """환경 점수 (0=최악, 100=최상)"""
        records = self._records.get(drone_id, [])
        if not records:
            return 100.0

        scores = []
        for r in records:
            noise_score = max(0, 100 - max(0, r.noise_db - 40) * 2)
            if r.over_residential:
                noise_score *= 0.7

            energy_score = 100.0
            if r.distance_m > 0:
                eff = r.energy_wh / (r.distance_m / 1000)
                energy_score = max(0, 100 - max(0, eff - self.ENERGY_TARGET_WH_KM) * 5)

            alt_bonus = min(10, r.altitude_m / 12)
            scores.append(noise_score * 0.5 + energy_score * 0.4 + alt_bonus)

        return round(float(np.mean(scores)), 1)

    def fleet_impact(self) -> float:
        if not self._records:
            return 100.0
        scores = [self.impact_score(did) for did in self._records]
        return round(float(np.mean(scores)), 1)

    def noise_violations(self) -> list[tuple[str, float]]:
        violations = []
        for did, records in self._records.items():
            for r in records:
                if r.noise_db > self.NOISE_LIMIT_DB:
                    violations.append((did, r.noise_db))
        return violations

    def total_energy_wh(self) -> float:
        total = sum(
            r.energy_wh for records in self._records.values() for r in records
        )
        return round(total, 1)

    def eco_ranking(self) -> list[tuple[str, float]]:
        ranking = [(did, self.impact_score(did)) for did in self._records]
        ranking.sort(key=lambda x: -x[1])
        return ranking

    def summary(self) -> dict[str, Any]:
        return {
            "drones": len(self._records),
            "fleet_score": self.fleet_impact(),
            "noise_violations": len(self.noise_violations()),
            "total_energy_wh": self.total_energy_wh(),
        }
