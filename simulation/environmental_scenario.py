"""Phase 699: 풍동·강우·저조도 환경 시나리오 시뮬레이션."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np

from simulation.apf_engine.apf import APF_PARAMS, APF_PARAMS_WINDY


class EnvScenario(Enum):
    """환경 시나리오 종류."""
    CALM = "calm"
    WIND_TUNNEL = "wind_tunnel"
    RAIN = "rain"
    LOW_LIGHT = "low_light"
    COMBINED = "combined"


@dataclass
class WindCondition:
    """바람 조건."""
    speed_ms: float = 0.0
    direction_deg: float = 0.0
    turbulence_intensity: float = 0.0

    @property
    def is_high_wind(self) -> bool:
        return self.speed_ms > 10.0


@dataclass
class RainCondition:
    """강우 조건."""
    intensity_mm_hr: float = 0.0

    @property
    def drag_multiplier(self) -> float:
        if self.intensity_mm_hr <= 0:
            return 1.0
        return 1.0 + 0.012 * self.intensity_mm_hr


@dataclass
class LightCondition:
    """조도 조건."""
    lux: float = 10000.0

    @property
    def detection_probability(self) -> float:
        if self.lux >= 1000:
            return 1.0
        if self.lux <= 1:
            return 0.3
        return 0.3 + 0.7 * (self.lux - 1) / 999.0


@dataclass
class EnvironmentState:
    """통합 환경 상태."""
    scenario: EnvScenario
    wind: WindCondition = field(default_factory=WindCondition)
    rain: RainCondition = field(default_factory=RainCondition)
    light: LightCondition = field(default_factory=LightCondition)
    apf_params: dict[str, float] = field(default_factory=dict)


@dataclass
class ScenarioMetrics:
    """시나리오별 성능 지표."""
    scenario: str
    near_miss_count: int = 0
    collision_count: int = 0
    avg_deviation_m: float = 0.0
    detection_rate: float = 1.0
    path_efficiency: float = 1.0
    duration_s: float = 0.0


SCENARIO_PRESETS: dict[EnvScenario, dict[str, Any]] = {
    EnvScenario.CALM: {
        "wind_speed": 2.0,
        "rain_mm_hr": 0.0,
        "lux": 10000.0,
    },
    EnvScenario.WIND_TUNNEL: {
        "wind_speed": 15.0,
        "rain_mm_hr": 0.0,
        "lux": 8000.0,
    },
    EnvScenario.RAIN: {
        "wind_speed": 5.0,
        "rain_mm_hr": 25.0,
        "lux": 3000.0,
    },
    EnvScenario.LOW_LIGHT: {
        "wind_speed": 3.0,
        "rain_mm_hr": 0.0,
        "lux": 10.0,
    },
    EnvScenario.COMBINED: {
        "wind_speed": 12.0,
        "rain_mm_hr": 15.0,
        "lux": 50.0,
    },
}


class EnvironmentalScenarioSim:
    """환경 시나리오 시뮬레이터 (APF 파라미터 자동 전환 포함)."""

    def __init__(self, seed: int = 42) -> None:
        self.rng = np.random.default_rng(seed)
        self._current: EnvironmentState | None = None
        self._metrics: list[ScenarioMetrics] = []

    def load_scenario(self, scenario: EnvScenario) -> EnvironmentState:
        """시나리오 사전 설정 로드."""
        preset = SCENARIO_PRESETS[scenario]
        wind = WindCondition(
            speed_ms=float(preset["wind_speed"]),
            direction_deg=float(self.rng.uniform(0, 360)),
            turbulence_intensity=float(self.rng.uniform(0.0, 0.3)),
        )
        rain = RainCondition(intensity_mm_hr=float(preset["rain_mm_hr"]))
        light = LightCondition(lux=float(preset["lux"]))

        apf = self._select_apf_params(wind)
        env = EnvironmentState(
            scenario=scenario,
            wind=wind,
            rain=rain,
            light=light,
            apf_params=dict(apf),
        )
        self._current = env
        return env

    def _select_apf_params(self, wind: WindCondition) -> dict[str, float]:
        """풍속 >10 m/s → APF_PARAMS_WINDY 자동 전환."""
        if wind.is_high_wind:
            return dict(APF_PARAMS_WINDY)
        return dict(APF_PARAMS)

    def apply_wind_force(
        self,
        velocity: np.ndarray,
        env: EnvironmentState | None = None,
    ) -> np.ndarray:
        """바람 영향 속도 보정 (3D 벡터)."""
        if env is None:
            env = self._current
        if env is None or env.wind.speed_ms <= 0:
            return velocity
        wind_dir_rad = np.radians(env.wind.direction_deg)
        wind_vec = np.array([
            env.wind.speed_ms * np.cos(wind_dir_rad),
            env.wind.speed_ms * np.sin(wind_dir_rad),
            0.0,
        ])
        turb = self.rng.normal(0, env.wind.turbulence_intensity, 3)
        return velocity + wind_vec * 0.1 + turb

    def apply_rain_drag(self, force: np.ndarray, env: EnvironmentState | None = None) -> np.ndarray:
        """강우 드래그 계수 적용."""
        if env is None:
            env = self._current
        if env is None:
            return force
        return force / env.rain.drag_multiplier

    def sample_detection(self, env: EnvironmentState | None = None) -> bool:
        """저조도 탐지 확률 샘플링."""
        if env is None:
            env = self._current
        if env is None:
            return True
        return float(self.rng.random()) < env.light.detection_probability

    def run_scenario(
        self,
        scenario: EnvScenario,
        steps: int = 100,
        drone_count: int = 10,
    ) -> ScenarioMetrics:
        """시나리오 실행 및 지표 수집."""
        env = self.load_scenario(scenario)
        near_miss = 0
        collision = 0
        total_dev = 0.0
        detect_count = 0

        for _ in range(steps):
            vel = self.rng.normal(0, 5, 3)
            vel = self.apply_wind_force(vel, env)
            dev = float(np.linalg.norm(vel[:2])) * 0.01
            total_dev += dev
            if dev > 0.5:
                near_miss += 1
            if dev > 2.0:
                collision += 1
            if self.sample_detection(env):
                detect_count += 1

        metrics = ScenarioMetrics(
            scenario=scenario.value,
            near_miss_count=near_miss,
            collision_count=collision,
            avg_deviation_m=total_dev / max(steps, 1),
            detection_rate=detect_count / max(steps, 1),
            path_efficiency=max(0.0, 1.0 - collision / max(steps, 1)),
            duration_s=float(steps) * 0.1,
        )
        self._metrics.append(metrics)
        return metrics

    def run_all_scenarios(self, steps: int = 100) -> list[ScenarioMetrics]:
        """모든 시나리오 일괄 실행."""
        return [self.run_scenario(s, steps) for s in EnvScenario]

    def get_apf_params_for_current(self) -> dict[str, float]:
        """현재 환경에 대한 APF 파라미터 반환."""
        if self._current is None:
            return dict(APF_PARAMS)
        return dict(self._current.apf_params)
