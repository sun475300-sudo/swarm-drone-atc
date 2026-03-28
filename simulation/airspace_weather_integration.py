"""
공역-기상 통합
==============
기상 조건 기반 동적 공역 제한.
풍속/시정/온도에 따라 자동 공역 등급 전환 + 제한 사항 적용.

사용법:
    awi = AirspaceWeatherIntegration()
    awi.update_weather(wind_speed=15, visibility=3000)
    restrictions = awi.get_restrictions()
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

import numpy as np


class AirspaceClass(IntEnum):
    GREEN = 1    # 정상 운영
    YELLOW = 2   # 주의 (제한적 운영)
    ORANGE = 3   # 경고 (최소 운영)
    RED = 4      # 위험 (운영 중단)


@dataclass
class WeatherState:
    """기상 상태"""
    wind_speed_ms: float = 0.0
    wind_direction_deg: float = 0.0
    visibility_m: float = 10000.0
    temperature_c: float = 20.0
    precipitation: bool = False
    icing_risk: bool = False
    turbulence_level: int = 0  # 0~3


@dataclass
class AirspaceRestriction:
    """공역 제한"""
    name: str
    description: str
    max_altitude_m: float | None = None
    max_speed_ms: float | None = None
    max_drones: int | None = None
    min_separation_m: float | None = None
    no_new_launches: bool = False


class AirspaceWeatherIntegration:
    """
    공역-기상 통합 관리.

    기상 → 공역 등급 → 제한 사항 자동 전환.
    """

    def __init__(
        self,
        wind_yellow: float = 10.0,
        wind_orange: float = 15.0,
        wind_red: float = 20.0,
        vis_yellow: float = 5000.0,
        vis_orange: float = 2000.0,
        vis_red: float = 1000.0,
    ) -> None:
        self._thresholds = {
            "wind_yellow": wind_yellow,
            "wind_orange": wind_orange,
            "wind_red": wind_red,
            "vis_yellow": vis_yellow,
            "vis_orange": vis_orange,
            "vis_red": vis_red,
        }
        self._weather = WeatherState()
        self._airspace_class = AirspaceClass.GREEN
        self._history: list[tuple[float, AirspaceClass]] = []

    def update_weather(
        self,
        wind_speed: float = 0.0,
        wind_direction: float = 0.0,
        visibility: float = 10000.0,
        temperature: float = 20.0,
        precipitation: bool = False,
        icing_risk: bool = False,
        turbulence: int = 0,
        t: float = 0.0,
    ) -> AirspaceClass:
        """기상 업데이트 및 공역 등급 재계산"""
        self._weather = WeatherState(
            wind_speed_ms=wind_speed,
            wind_direction_deg=wind_direction,
            visibility_m=visibility,
            temperature_c=temperature,
            precipitation=precipitation,
            icing_risk=icing_risk,
            turbulence_level=turbulence,
        )

        old_class = self._airspace_class
        self._airspace_class = self._compute_class()

        if self._airspace_class != old_class:
            self._history.append((t, self._airspace_class))

        return self._airspace_class

    @property
    def current_class(self) -> AirspaceClass:
        return self._airspace_class

    @property
    def weather(self) -> WeatherState:
        return self._weather

    def get_restrictions(self) -> list[AirspaceRestriction]:
        """현재 공역 등급에 따른 제한 사항"""
        cls = self._airspace_class
        restrictions = []

        if cls == AirspaceClass.GREEN:
            return []

        if cls >= AirspaceClass.YELLOW:
            restrictions.append(AirspaceRestriction(
                name="풍속 주의",
                description="강풍 주의, 분리 간격 확대",
                min_separation_m=50.0,
                max_speed_ms=20.0,
            ))

        if cls >= AirspaceClass.ORANGE:
            restrictions.append(AirspaceRestriction(
                name="제한 운영",
                description="최소 필수 운항만 허용",
                max_altitude_m=80.0,
                max_speed_ms=15.0,
                max_drones=20,
                min_separation_m=80.0,
                no_new_launches=False,
            ))

        if cls >= AirspaceClass.RED:
            restrictions.append(AirspaceRestriction(
                name="운항 중단",
                description="모든 드론 즉시 RTL",
                max_altitude_m=50.0,
                max_speed_ms=10.0,
                max_drones=0,
                no_new_launches=True,
            ))

        # 추가 조건별 제한
        if self._weather.icing_risk:
            restrictions.append(AirspaceRestriction(
                name="결빙 위험",
                description="결빙 조건 - 고도 제한",
                max_altitude_m=60.0,
            ))

        if self._weather.visibility_m < self._thresholds["vis_orange"]:
            restrictions.append(AirspaceRestriction(
                name="저시정",
                description=f"시정 {self._weather.visibility_m:.0f}m",
                max_speed_ms=10.0,
                min_separation_m=60.0,
            ))

        return restrictions

    def can_launch(self) -> bool:
        """신규 이륙 가능 여부"""
        if self._airspace_class == AirspaceClass.RED:
            return False
        for r in self.get_restrictions():
            if r.no_new_launches:
                return False
        return True

    def max_allowed_drones(self) -> int | None:
        """현재 최대 허용 드론 수"""
        for r in self.get_restrictions():
            if r.max_drones is not None:
                return r.max_drones
        return None

    def effective_separation(self) -> float:
        """현재 유효 분리 기준"""
        base = 30.0
        for r in self.get_restrictions():
            if r.min_separation_m is not None:
                base = max(base, r.min_separation_m)
        return base

    def _compute_class(self) -> AirspaceClass:
        """기상 → 공역 등급"""
        w = self._weather

        # 풍속 기반
        if w.wind_speed_ms >= self._thresholds["wind_red"]:
            return AirspaceClass.RED
        if w.wind_speed_ms >= self._thresholds["wind_orange"]:
            return AirspaceClass.ORANGE
        if w.wind_speed_ms >= self._thresholds["wind_yellow"]:
            return AirspaceClass.YELLOW

        # 시정 기반
        if w.visibility_m < self._thresholds["vis_red"]:
            return AirspaceClass.RED
        if w.visibility_m < self._thresholds["vis_orange"]:
            return AirspaceClass.ORANGE
        if w.visibility_m < self._thresholds["vis_yellow"]:
            return AirspaceClass.YELLOW

        # 기타 위험
        if w.icing_risk:
            return AirspaceClass.ORANGE
        if w.turbulence_level >= 3:
            return AirspaceClass.ORANGE
        if w.turbulence_level >= 2:
            return AirspaceClass.YELLOW

        return AirspaceClass.GREEN

    def class_history(self) -> list[tuple[float, str]]:
        return [(t, cls.name) for t, cls in self._history]

    def summary(self) -> dict[str, Any]:
        return {
            "airspace_class": self._airspace_class.name,
            "wind_speed": self._weather.wind_speed_ms,
            "visibility": self._weather.visibility_m,
            "can_launch": self.can_launch(),
            "effective_separation": self.effective_separation(),
            "restrictions_count": len(self.get_restrictions()),
            "class_changes": len(self._history),
        }
