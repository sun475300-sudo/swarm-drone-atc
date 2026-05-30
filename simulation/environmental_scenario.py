"""환경 시나리오 모듈 - 바람/비/저조도 + APF 자동 전환 (풍속 >10 m/s)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np


class APFMode(Enum):
    """인공 포텐셜 필드(APF) 동작 모드."""

    NORMAL = "normal"   # 표준 파라미터
    WINDY = "windy"     # 강풍 대응 파라미터


# APF 모드 전환 풍속 임계값 (m/s) — CLAUDE.md 정의와 일치
_WINDY_THRESHOLD_MS = 10.0


@dataclass
class WeatherCondition:
    """기상 조건 데이터클래스."""

    wind_speed_ms: float    # 풍속 (m/s)
    rainfall_mm_h: float    # 강수량 (mm/h)
    visibility_m: float     # 시정 (m)
    light_lux: float        # 조도 (lux)


# -----------------------------------------------------------------
# 사전 정의 기상 조건
# -----------------------------------------------------------------
CALM = WeatherCondition(
    wind_speed_ms=1.5,
    rainfall_mm_h=0.0,
    visibility_m=10000.0,
    light_lux=80000.0,
)

WINDY_STORM = WeatherCondition(
    wind_speed_ms=18.0,
    rainfall_mm_h=5.0,
    visibility_m=3000.0,
    light_lux=15000.0,
)

RAIN_HEAVY = WeatherCondition(
    wind_speed_ms=7.0,
    rainfall_mm_h=50.0,
    visibility_m=500.0,
    light_lux=5000.0,
)

LOW_LIGHT = WeatherCondition(
    wind_speed_ms=2.0,
    rainfall_mm_h=0.0,
    visibility_m=8000.0,
    light_lux=10.0,
)


class EnvironmentalScenario:
    """환경 조건에 따른 APF 모드 결정 및 바람 외란 적용 클래스."""

    def __init__(self, seed: int = 42) -> None:
        """
        Args:
            seed: 난수 시드 (재현성 보장).
        """
        self._rng = np.random.default_rng(seed)

    def get_apf_mode(self, weather: WeatherCondition) -> APFMode:
        """풍속에 따라 APF 모드를 결정한다.

        Args:
            weather: 현재 기상 조건.

        Returns:
            풍속 > 10 m/s 이면 APFMode.WINDY, 그 외 APFMode.NORMAL.
        """
        if weather.wind_speed_ms > _WINDY_THRESHOLD_MS:
            return APFMode.WINDY
        return APFMode.NORMAL

    def apply_wind_disturbance(
        self,
        position: list[float],
        weather: WeatherCondition,
    ) -> list[float]:
        """위치 벡터에 바람 외란을 적용한다.

        바람 방향은 시드로 고정된 난수로 결정하며,
        크기는 풍속에 비례하고 가우시안 지터를 포함한다.

        Args:
            position: [x, y, z] 위치 (m). z는 고도.
            weather: 현재 기상 조건.

        Returns:
            바람 외란이 적용된 새 위치 리스트 [x, y, z].

        Raises:
            ValueError: position 길이가 3이 아닌 경우.
        """
        if len(position) != 3:
            raise ValueError(f"position은 길이 3 리스트여야 합니다, 받은 길이: {len(position)}")

        v = weather.wind_speed_ms
        if v <= 0.0:
            return list(position)

        # 바람 벡터: xy 평면, 가우시안 성분 (표준편차 = 풍속의 20%)
        sigma = v * 0.2
        wx = float(self._rng.normal(v * 0.7, sigma))   # 주풍 방향 (X)
        wy = float(self._rng.normal(0.0, sigma))        # 횡풍 성분 (Y)
        # 고도에는 수직 성분(약 10%)만 적용
        wz = float(self._rng.normal(0.0, v * 0.05))

        # 시간 스텝 0.1s 기준 위치 변화 (드론 제어 보상 전 순수 외란)
        dt = 0.1
        return [
            position[0] + wx * dt,
            position[1] + wy * dt,
            position[2] + wz * dt,
        ]

    def is_safe_to_fly(self, weather: WeatherCondition) -> bool:
        """비행 안전 여부를 판단한다 (간이 기준).

        기준:
          - 풍속 < 25 m/s
          - 시정 > 200 m
          - 강수량 < 100 mm/h

        Args:
            weather: 현재 기상 조건.

        Returns:
            True: 비행 가능. False: 비행 불가.
        """
        return (
            weather.wind_speed_ms < 25.0
            and weather.visibility_m > 200.0
            and weather.rainfall_mm_h < 100.0
        )
