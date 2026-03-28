"""
시뮬레이션 설정 pydantic 검증 스키마

YAML 설정 파일 로드 시 타입·범위·필수키 검증.
잘못된 설정은 명확한 에러 메시지와 함께 조기 차단.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator


# ── 개별 섹션 모델 ──────────────────────────────────────────


class SimulationSection(BaseModel):
    seed: int = 42
    duration_minutes: float = Field(default=10, gt=0, le=1440)
    time_step_hz: int = Field(default=10, ge=1, le=100)
    control_hz: int = Field(default=1, ge=1, le=10)
    real_time_factor: float = Field(default=0, ge=0)


class BoundsRange(BaseModel):
    x: list[float] = [-5.0, 5.0]
    y: list[float] = [-5.0, 5.0]
    z: list[float] = [0.0, 0.12]

    @field_validator("x", "y", "z")
    @classmethod
    def validate_range(cls, v: list[float]) -> list[float]:
        if len(v) != 2:
            raise ValueError("범위는 [min, max] 2개 값이어야 합니다")
        if v[0] >= v[1]:
            raise ValueError(f"min({v[0]}) >= max({v[1]}): 최솟값이 최댓값보다 작아야 합니다")
        return v


class HomePosition(BaseModel):
    lat: float = Field(default=35.1595, ge=-90, le=90)
    lon: float = Field(default=126.8526, ge=-180, le=180)
    alt_m: float = Field(default=30.0, ge=0)


class AirspaceSection(BaseModel):
    bounds_km: BoundsRange = BoundsRange()
    area_km2: float = Field(default=100, gt=0)
    home: HomePosition = HomePosition()


class SeparationSection(BaseModel):
    lateral_min_m: float = Field(default=50.0, gt=0, le=1000)
    vertical_min_m: float = Field(default=15.0, gt=0, le=500)
    near_miss_lateral_m: float = Field(default=10.0, gt=0)
    near_miss_vertical_m: float = Field(default=3.0, gt=0)
    conflict_lookahead_s: float = Field(default=90.0, gt=0, le=600)

    @model_validator(mode="after")
    def near_miss_less_than_separation(self) -> "SeparationSection":
        if self.near_miss_lateral_m >= self.lateral_min_m:
            raise ValueError(
                f"near_miss_lateral_m({self.near_miss_lateral_m}) >= "
                f"lateral_min_m({self.lateral_min_m}): 근접경고 기준이 분리 기준보다 작아야 합니다"
            )
        return self


class DronesSection(BaseModel):
    default_count: int = Field(default=100, ge=1, le=2000)
    max_speed_ms: float = Field(default=15.0, gt=0, le=100)
    cruise_speed_ms: float = Field(default=8.0, gt=0)
    max_altitude_m: float = Field(default=120.0, gt=0)
    min_altitude_m: float = Field(default=30.0, ge=0)
    battery_capacity_wh: float = Field(default=50.0, gt=0)
    comm_range_m: float = Field(default=2000.0, gt=0)

    @model_validator(mode="after")
    def altitude_range_valid(self) -> "DronesSection":
        if self.min_altitude_m >= self.max_altitude_m:
            raise ValueError(
                f"min_altitude_m({self.min_altitude_m}) >= "
                f"max_altitude_m({self.max_altitude_m})"
            )
        return self

    @model_validator(mode="after")
    def cruise_less_than_max(self) -> "DronesSection":
        if self.cruise_speed_ms > self.max_speed_ms:
            raise ValueError(
                f"cruise_speed_ms({self.cruise_speed_ms}) > "
                f"max_speed_ms({self.max_speed_ms})"
            )
        return self


class ControllerSection(BaseModel):
    max_concurrent_clearances: int = Field(default=500, ge=1)
    clearance_timeout_s: float = Field(default=300.0, gt=0)
    advisory_retry_limit: int = Field(default=3, ge=0)


class LoggingSection(BaseModel):
    level: str = "INFO"
    save_trajectory: bool = True
    save_events: bool = True
    output_dir: str = "data/results"

    @field_validator("level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid:
            raise ValueError(f"로그 레벨 '{v}'이 유효하지 않습니다. 허용: {valid}")
        return v.upper()


class FailureInjectionSection(BaseModel):
    drone_failure_rate: float = Field(default=0.0, ge=0, le=1.0)
    comms_loss_rate: float = Field(default=0.0, ge=0, le=1.0)
    failure_types: list[str] = Field(default_factory=lambda: ["MOTOR", "BATTERY", "GPS"])


# ── 최상위 설정 모델 ──────────────────────────────────────────


class SimulationConfig(BaseModel):
    """default_simulation.yaml 전체 스키마"""
    simulation: SimulationSection = SimulationSection()
    airspace: AirspaceSection = AirspaceSection()
    separation_standards: SeparationSection = SeparationSection()
    drones: DronesSection = DronesSection()
    controller: ControllerSection = ControllerSection()
    logging: LoggingSection = LoggingSection()
    failure_injection: Optional[FailureInjectionSection] = None
    weather: Optional[dict] = None
    scenario: Optional[dict] = None

    model_config = {"extra": "allow"}  # 시나리오 오버라이드 등 추가 키 허용


# ── Monte Carlo 설정 모델 ──────────────────────────────────


class MCSweepSection(BaseModel):
    drone_density: list[int] = Field(default_factory=lambda: [50, 100])
    area_size_km2: list[float] = Field(default_factory=lambda: [100])
    failure_rate_pct: list[float] = Field(default_factory=lambda: [0])
    comms_loss_rate: list[float] = Field(default_factory=lambda: [0])
    wind_speed_ms: list[float] = Field(default_factory=lambda: [0])
    wind_direction_deg: list[float] = Field(default_factory=lambda: [0])
    duration_s: list[float] = Field(default_factory=lambda: [600])
    n_per_config: int = Field(default=30, ge=1)


class AcceptanceThresholds(BaseModel):
    collision_rate_per_1000h: float = Field(default=0.0, ge=0)
    conflict_resolution_rate_pct: float = Field(default=99.5, ge=0, le=100)
    route_efficiency_max: float = Field(default=1.15, gt=0)
    advisory_latency_p50_s: float = Field(default=2.0, gt=0)
    advisory_latency_p99_s: float = Field(default=10.0, gt=0)


class MonteCarloConfig(BaseModel):
    """monte_carlo.yaml 전체 스키마"""
    master_seed: int = 42
    quick_sweep: MCSweepSection = MCSweepSection()
    full_sweep: Optional[MCSweepSection] = None
    acceptance_thresholds: AcceptanceThresholds = AcceptanceThresholds()
    parallel: dict = Field(default_factory=lambda: {"n_workers": -1})

    model_config = {"extra": "allow"}


# ── 로드 함수 ──────────────────────────────────────────────


def load_validated_config(path: str | Path) -> SimulationConfig:
    """YAML 파일을 로드하고 pydantic 검증 후 반환"""
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return SimulationConfig(**raw)


def load_validated_mc_config(path: str | Path) -> MonteCarloConfig:
    """Monte Carlo YAML 파일을 로드하고 검증 후 반환"""
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return MonteCarloConfig(**raw)
