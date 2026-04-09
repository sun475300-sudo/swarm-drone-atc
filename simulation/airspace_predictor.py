"""
공역 부문 예측
==============
시간대별 혼잡도 예측 + 이동평균 + 사전 제한.

사용법:
    ap = AirspacePredictor(sectors=9)
    ap.record(sector=3, density=15, t=10.0)
    pred = ap.predict(sector=3, horizon_s=60)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class PredictionResult:
    """예측 결과"""
    sector: int
    current_density: float
    predicted_density: float
    trend: str  # INCREASING, DECREASING, STABLE
    confidence: float
    recommended_action: str


class AirspacePredictor:
    """시간대별 공역 혼잡도 예측."""

    def __init__(
        self, sectors: int = 9,
        congestion_threshold: float = 15.0,
        max_history: int = 200,
    ) -> None:
        self._sectors = sectors
        self._threshold = congestion_threshold
        self._history: dict[int, list[tuple[float, float]]] = {
            i: [] for i in range(sectors)
        }
        self._max_history = max_history

    def record(self, sector: int, density: float, t: float) -> None:
        if sector not in self._history:
            self._history[sector] = []
        self._history[sector].append((t, density))
        if len(self._history[sector]) > self._max_history:
            self._history[sector] = self._history[sector][-self._max_history:]

    def predict(self, sector: int, horizon_s: float = 60.0) -> PredictionResult:
        """선형 트렌드 예측"""
        data = self._history.get(sector, [])

        if len(data) < 2:
            current = data[-1][1] if data else 0.0
            return PredictionResult(
                sector=sector, current_density=current,
                predicted_density=current, trend="STABLE",
                confidence=0.3, recommended_action="모니터링",
            )

        recent = data[-min(20, len(data)):]
        times = np.array([t for t, _ in recent])
        densities = np.array([d for _, d in recent])

        current = float(densities[-1])

        # 선형 회귀
        dt = times[-1] - times[0]
        if dt < 1e-6:
            predicted = current
            slope = 0.0
        else:
            coeffs = np.polyfit(times, densities, 1)
            slope = coeffs[0]
            predicted = max(0, float(densities[-1] + slope * horizon_s))

        # 트렌드
        if slope > 0.5:
            trend = "INCREASING"
        elif slope < -0.5:
            trend = "DECREASING"
        else:
            trend = "STABLE"

        # 신뢰도 (데이터 많을수록 높음)
        confidence = min(1.0, len(recent) / 15)

        # 권장 조치
        if predicted > self._threshold * 1.5:
            action = "유입 차단 — 과밀 예상"
        elif predicted > self._threshold:
            action = "유입 제한 — 혼잡 예상"
        elif trend == "INCREASING":
            action = "모니터링 강화"
        else:
            action = "정상 운영"

        return PredictionResult(
            sector=sector, current_density=current,
            predicted_density=predicted, trend=trend,
            confidence=confidence, recommended_action=action,
        )

    def predict_all(self, horizon_s: float = 60.0) -> list[PredictionResult]:
        return [self.predict(s, horizon_s) for s in range(self._sectors)]

    def congested_sectors(self, horizon_s: float = 60.0) -> list[int]:
        preds = self.predict_all(horizon_s)
        return [p.sector for p in preds if p.predicted_density > self._threshold]

    def summary(self) -> dict[str, Any]:
        total_records = sum(len(v) for v in self._history.values())
        return {
            "sectors": self._sectors,
            "total_records": total_records,
            "congested_now": len([
                s for s in range(self._sectors)
                if self._history[s] and self._history[s][-1][1] > self._threshold
            ]),
        }
