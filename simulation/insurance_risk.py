"""Phase 696: 드론 비행 보험 리스크 계산기."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List

import numpy as np


class CoverageTier(Enum):
    BASIC = "basic"
    STANDARD = "standard"
    PREMIUM = "premium"


@dataclass(frozen=True)
class RiskFactors:
    population_density: float
    flight_hours: float
    weather_severity: float
    drone_mtow_kg: float
    operator_experience_hours: float
    payload_hazard_level: int
    proximity_airports_km: float


TIER_MULTIPLIER = {
    CoverageTier.BASIC: 1.0,
    CoverageTier.STANDARD: 1.6,
    CoverageTier.PREMIUM: 2.4,
}

TIER_LIMIT_KRW = {
    CoverageTier.BASIC: 50_000_000,
    CoverageTier.STANDARD: 200_000_000,
    CoverageTier.PREMIUM: 1_000_000_000,
}


_DEFAULT_INSURANCE_HISTORY = 10_000


class InsuranceRiskCalculator:
    """드론 비행에 대한 보험 리스크 점수와 예상 보험료를 계산."""

    def __init__(
        self,
        base_premium_krw: float = 50_000.0,
        max_history: int = _DEFAULT_INSURANCE_HISTORY,
    ) -> None:
        if max_history <= 0:
            raise ValueError("max_history must be positive")
        if base_premium_krw <= 0:
            raise ValueError(f"base_premium_krw must be positive, got {base_premium_krw}")
        self.base_premium_krw = base_premium_krw
        self.max_history = max_history
        self.history: List[Dict[str, Any]] = []

    def compute_risk_score(self, f: RiskFactors) -> float:
        if not math.isfinite(f.drone_mtow_kg) or f.drone_mtow_kg <= 0:
            raise ValueError(f"drone_mtow_kg must be finite and positive, got {f.drone_mtow_kg}")
        if not math.isfinite(f.population_density) or f.population_density < 0:
            raise ValueError(
                f"population_density must be finite and non-negative, got {f.population_density}"
            )
        if not math.isfinite(f.flight_hours) or f.flight_hours < 0:
            raise ValueError(f"flight_hours must be finite and non-negative, got {f.flight_hours}")
        if not math.isfinite(f.operator_experience_hours) or f.operator_experience_hours < 0:
            raise ValueError(
                f"operator_experience_hours must be finite and non-negative, "
                f"got {f.operator_experience_hours}"
            )
        if not math.isfinite(f.proximity_airports_km) or f.proximity_airports_km < 0:
            raise ValueError(
                f"proximity_airports_km must be finite and non-negative, "
                f"got {f.proximity_airports_km}"
            )
        pop = min(f.population_density / 10_000.0, 5.0)
        weather = max(0.0, min(f.weather_severity, 1.0))
        weight = min(f.drone_mtow_kg / 25.0, 2.0)
        experience_bonus = max(0.0, 1.0 - f.operator_experience_hours / 500.0)
        payload = max(0, min(f.payload_hazard_level, 5)) / 5.0
        airport = max(0.0, min(1.0, 1.0 - f.proximity_airports_km / 30.0))
        hours = np.log1p(max(0.0, f.flight_hours)) / 5.0

        score = (
            0.30 * pop
            + 0.15 * weather
            + 0.15 * weight
            + 0.15 * experience_bonus
            + 0.10 * payload
            + 0.10 * airport
            + 0.05 * hours
        )
        return float(min(max(score, 0.0), 2.0))

    def recommend_tier(self, risk_score: float) -> CoverageTier:
        if risk_score < 0.4:
            return CoverageTier.BASIC
        if risk_score < 0.9:
            return CoverageTier.STANDARD
        return CoverageTier.PREMIUM

    def _record_quote(self, score: float, tier: CoverageTier, premium: float) -> None:
        self.history.append({"score": score, "tier": tier.value, "premium_krw": premium})
        overflow = len(self.history) - self.max_history
        if overflow > 0:
            del self.history[:overflow]

    def estimate_premium_krw(self, f: RiskFactors, tier: CoverageTier) -> float:
        score = self.compute_risk_score(f)
        multiplier = TIER_MULTIPLIER[tier]
        premium = self.base_premium_krw * (1.0 + score) * multiplier
        self._record_quote(score, tier, premium)
        return premium

    def quote(self, f: RiskFactors) -> Dict[str, Any]:
        # compute_risk_score 를 1회만 호출 (DRY)
        score = self.compute_risk_score(f)
        tier = self.recommend_tier(score)
        multiplier = TIER_MULTIPLIER[tier]
        premium = self.base_premium_krw * (1.0 + score) * multiplier
        self._record_quote(score, tier, premium)
        return {
            "risk_score": score,
            "recommended_tier": tier.value,
            "premium_krw": premium,
            "coverage_limit_krw": TIER_LIMIT_KRW[tier],
        }

    def stats(self) -> Dict[str, Any]:
        if not self.history:
            return {"quotes": 0}
        avg_score = float(np.mean([h["score"] for h in self.history]))
        avg_premium = float(np.mean([h["premium_krw"] for h in self.history]))
        return {
            "quotes": len(self.history),
            "avg_risk_score": avg_score,
            "avg_premium_krw": avg_premium,
        }
