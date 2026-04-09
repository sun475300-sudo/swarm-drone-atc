"""
공역 수요 예측기
===============
시간대별 수요 패턴 학습 + 사전 자원 배치.

사용법:
    df = DemandForecaster(n_slots=24)
    df.record_demand(hour=9, count=50)
    forecast = df.forecast(hour=10)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class DemandRecord:
    """수요 기록"""
    hour: int
    count: int
    sector: str = "default"


@dataclass
class Forecast:
    """예측 결과"""
    hour: int
    predicted_count: float
    confidence: float  # 0~1
    trend: str  # RISING, FALLING, STABLE
    recommended_capacity: int


class DemandForecaster:
    """공역 수요 예측."""

    def __init__(self, n_slots: int = 24, capacity_margin: float = 1.3) -> None:
        self.n_slots = n_slots
        self.capacity_margin = capacity_margin
        self._history: dict[int, list[int]] = {h: [] for h in range(n_slots)}
        self._sector_history: dict[str, dict[int, list[int]]] = {}

    def record_demand(self, hour: int, count: int, sector: str = "default") -> None:
        h = hour % self.n_slots
        self._history[h].append(count)
        if len(self._history[h]) > 100:
            self._history[h] = self._history[h][-100:]

        if sector not in self._sector_history:
            self._sector_history[sector] = {i: [] for i in range(self.n_slots)}
        self._sector_history[sector][h].append(count)

    def forecast(self, hour: int, sector: str | None = None) -> Forecast:
        h = hour % self.n_slots

        if sector and sector in self._sector_history:
            data = self._sector_history[sector][h]
        else:
            data = self._history[h]

        if not data:
            return Forecast(hour=h, predicted_count=0, confidence=0, trend="STABLE", recommended_capacity=0)

        predicted = float(np.mean(data))
        std = float(np.std(data)) if len(data) > 1 else predicted * 0.3
        confidence = min(1.0, len(data) / 20.0)

        # 트렌드
        if len(data) >= 5:
            recent = np.mean(data[-3:])
            older = np.mean(data[:-3])
            if recent > older * 1.1:
                trend = "RISING"
            elif recent < older * 0.9:
                trend = "FALLING"
            else:
                trend = "STABLE"
        else:
            trend = "STABLE"

        recommended = int(np.ceil(predicted * self.capacity_margin))

        return Forecast(
            hour=h, predicted_count=round(predicted, 1),
            confidence=round(confidence, 2),
            trend=trend, recommended_capacity=recommended,
        )

    def peak_hours(self, top_n: int = 3) -> list[int]:
        avgs = []
        for h in range(self.n_slots):
            if self._history[h]:
                avgs.append((h, np.mean(self._history[h])))
            else:
                avgs.append((h, 0))
        avgs.sort(key=lambda x: -x[1])
        return [h for h, _ in avgs[:top_n]]

    def daily_pattern(self) -> list[float]:
        return [
            round(float(np.mean(self._history[h])), 1) if self._history[h] else 0
            for h in range(self.n_slots)
        ]

    def summary(self) -> dict[str, Any]:
        total = sum(len(v) for v in self._history.values())
        return {
            "total_records": total,
            "peak_hours": self.peak_hours(),
            "sectors": len(self._sector_history),
        }
