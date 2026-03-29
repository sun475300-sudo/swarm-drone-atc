"""Canonical weather risk model used across polyglot implementations."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WeatherRiskInput:
    wind_mps: float
    visibility_km: float
    precipitation_level: float
    congestion: float


@dataclass(frozen=True)
class WeatherRiskOutput:
    score: float
    category: str


class WeatherRiskModel:
    @staticmethod
    def _clamp(value: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, float(value)))

    def score(self, data: WeatherRiskInput) -> WeatherRiskOutput:
        wind_norm = self._clamp(data.wind_mps / 20.0, 0.0, 1.0)
        vis_norm = self._clamp(data.visibility_km / 10.0, 0.0, 1.0)
        vis_penalty = 1.0 - vis_norm
        precip = self._clamp(data.precipitation_level, 0.0, 1.0)
        congestion = self._clamp(data.congestion, 0.0, 1.0)

        raw = 0.35 * wind_norm + 0.25 * vis_penalty + 0.20 * precip + 0.20 * congestion
        score = round(self._clamp(raw, 0.0, 1.0), 4)

        if score < 0.25:
            category = "GREEN"
        elif score < 0.50:
            category = "YELLOW"
        elif score < 0.75:
            category = "ORANGE"
        else:
            category = "RED"

        return WeatherRiskOutput(score=score, category=category)
