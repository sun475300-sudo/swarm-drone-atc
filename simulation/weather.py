"""
바람/기상 모델
시나리오 YAML의 weather 섹션을 읽어 WindModel 리스트를 생성한다.

지원 모델:
  constant  — 일정 방향/속도 바람
  variable  — 돌풍(gust) Poisson 프로세스
  shear     — 고도별 선형 풍속 변화
"""
from __future__ import annotations
import math
import numpy as np


class WindModel:
    """기저 클래스 — get_wind_vector(position, t) → [wx, wy, 0]"""

    def get_wind_vector(self, position: np.ndarray, t: float) -> np.ndarray:
        return np.zeros(3)


class ConstantWind(WindModel):
    def __init__(self, speed_ms: float, direction_deg: float) -> None:
        rad = math.radians(direction_deg)
        self._vec = np.array([
            speed_ms * math.cos(rad),
            speed_ms * math.sin(rad),
            0.0,
        ])

    def get_wind_vector(self, position: np.ndarray, t: float) -> np.ndarray:
        return self._vec.copy()


class VariableWind(WindModel):
    """
    평균 바람 + 랜덤 돌풍.
    돌풍 발생 간격: Poisson(rate=1/mean_interval_s).
    """

    def __init__(
        self,
        mean_speed_ms: float,
        direction_deg: float,
        gust_speed_ms: float,
        gust_duration_s: float,
        rng: np.random.Generator | None = None,
    ) -> None:
        self._rng = rng or np.random.default_rng()
        rad = math.radians(direction_deg)
        self._base = np.array([
            mean_speed_ms * math.cos(rad),
            mean_speed_ms * math.sin(rad),
            0.0,
        ])
        self._gust_speed = gust_speed_ms
        self._gust_dur   = gust_duration_s
        self._gust_start: float | None = None
        self._gust_vec   = np.zeros(3)
        self._next_gust  = self._rng.exponential(30.0)  # 첫 돌풍 시각

    def get_wind_vector(self, position: np.ndarray, t: float) -> np.ndarray:
        # 돌풍 발생 체크
        if t >= self._next_gust and self._gust_start is None:
            angle = self._rng.uniform(0, 2 * math.pi)
            self._gust_vec = np.array([
                self._gust_speed * math.cos(angle),
                self._gust_speed * math.sin(angle),
                0.0,
            ])
            self._gust_start = t
            self._next_gust  = t + self._rng.exponential(30.0)

        # 돌풍 만료 체크
        if (self._gust_start is not None
                and t > self._gust_start + self._gust_dur):
            self._gust_start = None
            self._gust_vec   = np.zeros(3)

        return self._base + self._gust_vec


class ShearWind(WindModel):
    """고도에 따라 선형으로 변하는 윈드 시어"""

    def __init__(
        self,
        low_alt_speed_ms: float,
        high_alt_speed_ms: float,
        direction_deg: float,
        transition_alt_m: float = 60.0,
    ) -> None:
        self._low   = low_alt_speed_ms
        self._high  = high_alt_speed_ms
        self._dir   = math.radians(direction_deg)
        self._trans = transition_alt_m

    def get_wind_vector(self, position: np.ndarray, t: float) -> np.ndarray:
        alt    = float(position[2]) if len(position) > 2 else 60.0
        ratio  = float(np.clip(alt / max(self._trans, 1.0), 0.0, 2.0))
        speed  = self._low + (self._high - self._low) * min(ratio, 1.0)
        return np.array([
            speed * math.cos(self._dir),
            speed * math.sin(self._dir),
            0.0,
        ])


def build_wind_models(
    weather_cfg: dict,
    rng: np.random.Generator | None = None,
) -> list[WindModel]:
    """
    시나리오 YAML weather 섹션 → WindModel 리스트.

    예시 YAML:
      weather:
        wind_models:
          - type: constant
            speed_ms: 5.0
            direction_deg: 45.0
          - type: variable
            mean_speed_ms: 3.0
            direction_deg: 90.0
            gust_speed_ms: 8.0
            gust_duration_s: 10.0
    """
    rng = rng or np.random.default_rng()
    models: list[WindModel] = []
    for cfg in weather_cfg.get("wind_models", []):
        wtype = cfg.get("type", "constant")
        if wtype == "constant":
            models.append(ConstantWind(
                speed_ms=float(cfg.get("speed_ms", 0.0)),
                direction_deg=float(cfg.get("direction_deg", 0.0)),
            ))
        elif wtype == "variable":
            models.append(VariableWind(
                mean_speed_ms=float(cfg.get("mean_speed_ms", 2.0)),
                direction_deg=float(cfg.get("direction_deg", 0.0)),
                gust_speed_ms=float(cfg.get("gust_speed_ms", 5.0)),
                gust_duration_s=float(cfg.get("gust_duration_s", 10.0)),
                rng=rng,
            ))
        elif wtype == "shear":
            models.append(ShearWind(
                low_alt_speed_ms=float(cfg.get("low_alt_speed_ms", 1.0)),
                high_alt_speed_ms=float(cfg.get("high_alt_speed_ms", 8.0)),
                direction_deg=float(cfg.get("direction_deg", 0.0)),
                transition_alt_m=float(cfg.get("transition_alt_m", 60.0)),
            ))
    return models
