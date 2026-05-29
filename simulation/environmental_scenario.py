"""P699: 풍동·강우·저조도 환경 시나리오 + APF 파라미터 자동 전환.

APF_PARAMS_WINDY 자동 전환 기준: 풍속 >10 m/s (CLAUDE.md 규칙 준수).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np


class ConditionSeverity(Enum):
    NOMINAL = "nominal"
    MODERATE = "moderate"
    SEVERE = "severe"
    EXTREME = "extreme"


# CLAUDE.md: APF 강풍 모드 기준 10 m/s
WIND_APF_SWITCH_THRESHOLD_MS = 10.0

# APF 파라미터 프리셋 (SDACS 기존 컨벤션)
APF_PARAMS_NOMINAL = {
    "k_att": 1.0,
    "k_rep": 150.0,
    "influence_radius": 15.0,
    "max_force": 3.0,
}
APF_PARAMS_WINDY = {
    "k_att": 0.7,
    "k_rep": 200.0,
    "influence_radius": 20.0,
    "max_force": 5.0,
}
APF_PARAMS_RAIN = {
    "k_att": 0.9,
    "k_rep": 175.0,
    "influence_radius": 18.0,
    "max_force": 4.0,
}
APF_PARAMS_LOW_LIGHT = {
    "k_att": 0.8,
    "k_rep": 160.0,
    "influence_radius": 22.0,
    "max_force": 4.0,
}


@dataclass
class WindState:
    speed_ms: float = 0.0       # 풍속 (m/s)
    direction_deg: float = 0.0  # 풍향 (°, 0=북)
    gust_ms: float = 0.0        # 돌풍 최대 (m/s)

    @property
    def severity(self) -> ConditionSeverity:
        effective = self.speed_ms + self.gust_ms
        if effective < 5.0:
            return ConditionSeverity.NOMINAL
        if effective < 10.0:
            return ConditionSeverity.MODERATE
        if effective < 20.0:
            return ConditionSeverity.SEVERE
        return ConditionSeverity.EXTREME

    @property
    def apf_params(self) -> dict[str, float]:
        return APF_PARAMS_WINDY if self.speed_ms > WIND_APF_SWITCH_THRESHOLD_MS else APF_PARAMS_NOMINAL


@dataclass
class RainState:
    intensity_mm_hr: float = 0.0    # 강수 강도 (mm/hr)
    visibility_m: float = 10000.0   # 가시거리 (m)

    @property
    def severity(self) -> ConditionSeverity:
        if self.intensity_mm_hr < 2.5:
            return ConditionSeverity.NOMINAL
        if self.intensity_mm_hr < 25.0:
            return ConditionSeverity.MODERATE
        if self.intensity_mm_hr < 75.0:
            return ConditionSeverity.SEVERE
        return ConditionSeverity.EXTREME

    @property
    def apf_params(self) -> dict[str, float]:
        return APF_PARAMS_RAIN if self.intensity_mm_hr > 2.5 else APF_PARAMS_NOMINAL


@dataclass
class LightState:
    lux: float = 10000.0    # 조도 (lux)

    @property
    def severity(self) -> ConditionSeverity:
        if self.lux >= 1000:
            return ConditionSeverity.NOMINAL
        if self.lux >= 100:
            return ConditionSeverity.MODERATE
        if self.lux >= 10:
            return ConditionSeverity.SEVERE
        return ConditionSeverity.EXTREME

    @property
    def apf_params(self) -> dict[str, float]:
        return APF_PARAMS_LOW_LIGHT if self.lux < 100 else APF_PARAMS_NOMINAL


@dataclass
class EnvironmentState:
    wind: WindState = field(default_factory=WindState)
    rain: RainState = field(default_factory=RainState)
    light: LightState = field(default_factory=LightState)

    @property
    def active_apf_params(self) -> dict[str, float]:
        """가장 제한적인 환경 조건의 APF 파라미터 선택."""
        if self.wind.speed_ms > WIND_APF_SWITCH_THRESHOLD_MS:
            return self.wind.apf_params
        if self.rain.severity != ConditionSeverity.NOMINAL:
            return self.rain.apf_params
        if self.light.severity != ConditionSeverity.NOMINAL:
            return self.light.apf_params
        return APF_PARAMS_NOMINAL

    @property
    def overall_severity(self) -> ConditionSeverity:
        severities = [self.wind.severity, self.rain.severity, self.light.severity]
        return max(severities, key=lambda s: list(ConditionSeverity).index(s))

    def to_dict(self) -> dict[str, Any]:
        return {
            "wind_ms": self.wind.speed_ms,
            "wind_dir_deg": self.wind.direction_deg,
            "rain_mm_hr": self.rain.intensity_mm_hr,
            "visibility_m": self.rain.visibility_m,
            "lux": self.light.lux,
            "severity": self.overall_severity.value,
            "apf_mode": "WINDY" if self.active_apf_params is APF_PARAMS_WINDY else (
                "RAIN" if self.active_apf_params is APF_PARAMS_RAIN else (
                    "LOW_LIGHT" if self.active_apf_params is APF_PARAMS_LOW_LIGHT else "NOMINAL"
                )
            ),
        }


class EnvironmentalScenarioRunner:
    """시나리오 시퀀스를 실행하며 APF 파라미터 변환 이벤트를 기록."""

    PRESETS = {
        "calm": EnvironmentState(),
        "strong_wind": EnvironmentState(wind=WindState(speed_ms=15.0, direction_deg=270.0, gust_ms=5.0)),
        "heavy_rain": EnvironmentState(rain=RainState(intensity_mm_hr=50.0, visibility_m=500.0)),
        "night": EnvironmentState(light=LightState(lux=5.0)),
        "combined_severe": EnvironmentState(
            wind=WindState(speed_ms=12.0), rain=RainState(intensity_mm_hr=30.0), light=LightState(lux=20.0)
        ),
    }

    def __init__(self, rng: np.random.Generator | None = None) -> None:
        self._rng = rng if rng is not None else np.random.default_rng(0)
        self._current = EnvironmentState()
        self._log: list[dict[str, Any]] = []

    def apply_preset(self, name: str) -> EnvironmentState:
        if name not in self.PRESETS:
            raise ValueError(f"알 수 없는 프리셋: {name}. 사용 가능: {list(self.PRESETS)}")
        self._current = self.PRESETS[name]
        self._log.append({"event": "preset_applied", "name": name, "state": self._current.to_dict()})
        return self._current

    def apply_state(self, state: EnvironmentState) -> None:
        self._current = state
        self._log.append({"event": "state_applied", "state": state.to_dict()})

    @property
    def current(self) -> EnvironmentState:
        return self._current

    @property
    def log(self) -> list[dict[str, Any]]:
        return list(self._log)
