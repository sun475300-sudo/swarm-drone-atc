"""
기상 예측 엔진
==============
과거 풍속 데이터 기반 단기 예측 (이동평균 + 트렌드).
예측 풍속으로 경로 사전 조정 및 기상 경고 자동 발령.

사용법:
    forecaster = WeatherForecaster()
    forecaster.record(t=10.0, wind_speed=5.0, wind_dir=45.0)
    pred = forecaster.predict(horizon_s=30.0)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class WeatherRecord:
    """기상 데이터 포인트"""
    t: float
    wind_speed: float  # m/s
    wind_direction: float  # degrees (0=North, 90=East)
    temperature: float = 20.0
    visibility: float = 10000.0  # m


@dataclass
class WeatherPrediction:
    """기상 예측 결과"""
    t_predict: float  # 예측 시점
    wind_speed: float
    wind_direction: float
    confidence: float  # 0~1
    alert_level: str = "NONE"  # NONE, CAUTION, WARNING, DANGER

    @property
    def wind_vector(self) -> np.ndarray:
        """풍향 벡터 (East, North)"""
        rad = np.radians(self.wind_direction)
        return np.array([
            self.wind_speed * np.sin(rad),
            self.wind_speed * np.cos(rad),
            0.0,
        ])


class WeatherForecaster:
    """
    단기 기상 예측기.

    이동평균 + 선형 트렌드 기반 풍속/풍향 예측.
    """

    def __init__(
        self,
        window_size: int = 30,
        max_history: int = 600,
        caution_speed: float = 10.0,
        warning_speed: float = 15.0,
        danger_speed: float = 20.0,
    ) -> None:
        self.window_size = window_size
        self.max_history = max_history
        self.caution_speed = caution_speed
        self.warning_speed = warning_speed
        self.danger_speed = danger_speed

        self._history: list[WeatherRecord] = []

    def record(
        self,
        t: float,
        wind_speed: float,
        wind_direction: float = 0.0,
        temperature: float = 20.0,
        visibility: float = 10000.0,
    ) -> None:
        """기상 데이터 기록"""
        self._history.append(WeatherRecord(
            t=t,
            wind_speed=wind_speed,
            wind_direction=wind_direction,
            temperature=temperature,
            visibility=visibility,
        ))
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history:]

    def predict(self, horizon_s: float = 30.0) -> WeatherPrediction:
        """단기 풍속 예측"""
        if not self._history:
            return WeatherPrediction(
                t_predict=horizon_s, wind_speed=0.0,
                wind_direction=0.0, confidence=0.0,
            )

        if len(self._history) < 2:
            last = self._history[-1]
            return WeatherPrediction(
                t_predict=last.t + horizon_s,
                wind_speed=last.wind_speed,
                wind_direction=last.wind_direction,
                confidence=0.3,
                alert_level=self._alert_level(last.wind_speed),
            )

        # 최근 window 데이터
        window = self._history[-self.window_size:]
        speeds = np.array([r.wind_speed for r in window])
        times = np.array([r.t for r in window])
        dirs = np.array([r.wind_direction for r in window])

        # 이동평균
        ma_speed = float(np.mean(speeds))

        # 선형 트렌드
        if len(times) >= 3:
            coeffs = np.polyfit(times - times[0], speeds, 1)
            trend = coeffs[0]  # slope per second
            pred_speed = ma_speed + trend * horizon_s
        else:
            pred_speed = ma_speed

        pred_speed = max(0.0, pred_speed)

        # 풍향 예측 (원형 평균)
        sin_sum = float(np.mean(np.sin(np.radians(dirs))))
        cos_sum = float(np.mean(np.cos(np.radians(dirs))))
        pred_dir = float(np.degrees(np.arctan2(sin_sum, cos_sum))) % 360

        # 신뢰도 (데이터 많을수록, 변동 적을수록 높음)
        data_factor = min(1.0, len(window) / self.window_size)
        std_factor = max(0.0, 1.0 - float(np.std(speeds)) / max(ma_speed, 1.0))
        confidence = data_factor * std_factor * 0.9

        t_pred = self._history[-1].t + horizon_s
        return WeatherPrediction(
            t_predict=t_pred,
            wind_speed=pred_speed,
            wind_direction=pred_dir,
            confidence=confidence,
            alert_level=self._alert_level(pred_speed),
        )

    def moving_average(self, window: int | None = None) -> float:
        """현재 이동평균 풍속"""
        w = window or self.window_size
        if not self._history:
            return 0.0
        recent = self._history[-w:]
        return float(np.mean([r.wind_speed for r in recent]))

    def trend(self) -> float:
        """풍속 트렌드 (m/s per second, 양수=증가)"""
        if len(self._history) < 3:
            return 0.0
        window = self._history[-self.window_size:]
        times = np.array([r.t for r in window])
        speeds = np.array([r.wind_speed for r in window])
        coeffs = np.polyfit(times - times[0], speeds, 1)
        return float(coeffs[0])

    def should_preemptive_rtl(self, horizon_s: float = 60.0) -> bool:
        """예측 풍속이 위험 수준이면 사전 RTL 권장"""
        pred = self.predict(horizon_s)
        return pred.wind_speed >= self.danger_speed

    def _alert_level(self, speed: float) -> str:
        if speed >= self.danger_speed:
            return "DANGER"
        if speed >= self.warning_speed:
            return "WARNING"
        if speed >= self.caution_speed:
            return "CAUTION"
        return "NONE"

    def summary(self) -> dict[str, Any]:
        """예보 요약"""
        if not self._history:
            return {"data_points": 0}

        speeds = [r.wind_speed for r in self._history]
        return {
            "data_points": len(self._history),
            "current_speed": self._history[-1].wind_speed,
            "moving_avg": self.moving_average(),
            "trend": self.trend(),
            "max_recorded": max(speeds),
            "min_recorded": min(speeds),
            "prediction_30s": self.predict(30).wind_speed,
            "alert_level": self.predict(30).alert_level,
        }

    def clear(self) -> None:
        self._history.clear()

    @property
    def history(self) -> list[WeatherRecord]:
        return list(self._history)
