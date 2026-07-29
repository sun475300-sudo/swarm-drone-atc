"""P739: Sim-to-Real Domain Randomization wrapper.

학습 중 풍속·센서 노이즈·배터리·통신지연 등 환경 파라미터를 무작위 변경하여
정책의 실기 일반화 성능을 향상.

Reference: Tobin et al. (IROS 2017), Akkaya et al. (2019 ADR).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class DomainConfig:
    """Domain Randomization 파라미터 분포."""

    wind_speed_range: tuple[float, float] = (0.0, 15.0)        # m/s
    wind_direction_range: tuple[float, float] = (0.0, 360.0)   # deg
    gps_noise_std_m: tuple[float, float] = (0.5, 5.0)          # 표준편차 m
    imu_bias_range: tuple[float, float] = (-0.05, 0.05)        # m/s^2
    battery_capacity_factor: tuple[float, float] = (0.8, 1.0)  # 신품·열화
    comm_latency_range_ms: tuple[float, float] = (5.0, 80.0)   # ms
    comm_packet_loss_range: tuple[float, float] = (0.0, 0.1)   # 0-10%


@dataclass
class DomainSample:
    """샘플된 도메인 인스턴스."""

    wind_speed: float
    wind_direction: float
    gps_noise_std: float
    imu_bias: np.ndarray
    battery_factor: float
    comm_latency_ms: float
    comm_packet_loss: float


class DomainRandomizer:
    """Episode 시작 시 도메인 파라미터 샘플 + 시뮬레이터에 주입."""

    def __init__(self, cfg: DomainConfig, seed: int = 42) -> None:
        """``__init__`` 동작을 수행한다."""
        self.cfg = cfg
        self.rng = np.random.default_rng(seed)
        self.history: list[DomainSample] = []

    def sample(self) -> DomainSample:
        """현재 RNG로 도메인 인스턴스 샘플."""
        s = DomainSample(
            wind_speed=float(self.rng.uniform(*self.cfg.wind_speed_range)),
            wind_direction=float(self.rng.uniform(*self.cfg.wind_direction_range)),
            gps_noise_std=float(self.rng.uniform(*self.cfg.gps_noise_std_m)),
            imu_bias=self.rng.uniform(self.cfg.imu_bias_range[0], self.cfg.imu_bias_range[1], 3),
            battery_factor=float(self.rng.uniform(*self.cfg.battery_capacity_factor)),
            comm_latency_ms=float(self.rng.uniform(*self.cfg.comm_latency_range_ms)),
            comm_packet_loss=float(self.rng.uniform(*self.cfg.comm_packet_loss_range)),
        )
        self.history.append(s)
        return s

    def apply_to_simulator(self, sample: DomainSample, sim_cfg: dict) -> dict:
        """샘플을 SwarmSimulator scenario_cfg에 주입."""
        # 사본 생성(immutability)
        cfg = {**sim_cfg}
        cfg.setdefault("weather", {})
        cfg["weather"]["wind_speed_mps"] = sample.wind_speed
        cfg["weather"]["wind_direction_deg"] = sample.wind_direction
        cfg.setdefault("sensors", {})
        cfg["sensors"]["gps_noise_std_m"] = sample.gps_noise_std
        cfg.setdefault("comms", {})
        cfg["comms"]["latency_ms"] = sample.comm_latency_ms
        cfg["comms"]["packet_loss_rate"] = sample.comm_packet_loss
        return cfg


def adr_curriculum(
    base_cfg: DomainConfig,
    success_rate: float,
    target: float = 0.7,
    expand_rate: float = 1.05,
) -> DomainConfig:
    """Automatic Domain Randomization (ADR) — 성공률이 높으면 범위 확장.

    참고: Akkaya et al. "Solving Rubik's Cube with a Robot Hand" (2019).
    """
    factor = expand_rate if success_rate > target else 1.0 / expand_rate
    return DomainConfig(
        wind_speed_range=(
            base_cfg.wind_speed_range[0],
            base_cfg.wind_speed_range[1] * factor,
        ),
        wind_direction_range=base_cfg.wind_direction_range,
        gps_noise_std_m=(
            base_cfg.gps_noise_std_m[0],
            base_cfg.gps_noise_std_m[1] * factor,
        ),
        imu_bias_range=(
            base_cfg.imu_bias_range[0] * factor,
            base_cfg.imu_bias_range[1] * factor,
        ),
        battery_capacity_factor=base_cfg.battery_capacity_factor,
        comm_latency_range_ms=(
            base_cfg.comm_latency_range_ms[0],
            base_cfg.comm_latency_range_ms[1] * factor,
        ),
        comm_packet_loss_range=(
            base_cfg.comm_packet_loss_range[0],
            min(0.5, base_cfg.comm_packet_loss_range[1] * factor),
        ),
    )
