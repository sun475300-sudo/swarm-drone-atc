"""P739 Domain Randomization 검증."""
from __future__ import annotations

import numpy as np

from src.training.domain_rand import (
    DomainConfig,
    DomainRandomizer,
    adr_curriculum,
)


def test_sample_within_config_bounds() -> None:
    """샘플 값이 cfg 범위 내."""
    cfg = DomainConfig()
    rng = DomainRandomizer(cfg, seed=42)
    s = rng.sample()
    assert cfg.wind_speed_range[0] <= s.wind_speed <= cfg.wind_speed_range[1]
    assert cfg.gps_noise_std_m[0] <= s.gps_noise_std <= cfg.gps_noise_std_m[1]
    assert cfg.battery_capacity_factor[0] <= s.battery_factor <= cfg.battery_capacity_factor[1]
    assert 0.0 <= s.comm_packet_loss <= 0.5


def test_reproducibility_with_seed() -> None:
    """같은 seed → 같은 샘플."""
    cfg = DomainConfig()
    rng1 = DomainRandomizer(cfg, seed=123)
    rng2 = DomainRandomizer(cfg, seed=123)
    s1, s2 = rng1.sample(), rng2.sample()
    assert s1.wind_speed == s2.wind_speed
    assert s1.gps_noise_std == s2.gps_noise_std


def test_apply_to_simulator_does_not_mutate_input() -> None:
    """원본 cfg는 변경 안 됨 (immutability)."""
    cfg = DomainConfig()
    rng = DomainRandomizer(cfg, seed=0)
    sample = rng.sample()
    sim_cfg = {"drones": {"default_count": 50}}
    out = rng.apply_to_simulator(sample, sim_cfg)
    assert sim_cfg == {"drones": {"default_count": 50}}  # unchanged
    assert out["weather"]["wind_speed_mps"] == sample.wind_speed


def test_history_accumulates() -> None:
    """샘플 호출마다 history 누적."""
    rng = DomainRandomizer(DomainConfig(), seed=42)
    for _ in range(5):
        rng.sample()
    assert len(rng.history) == 5


def test_adr_expand_on_high_success() -> None:
    """성공률 > target → 범위 확장."""
    base = DomainConfig(wind_speed_range=(0.0, 10.0))
    expanded = adr_curriculum(base, success_rate=0.9, target=0.7)
    assert expanded.wind_speed_range[1] > base.wind_speed_range[1]


def test_adr_shrink_on_low_success() -> None:
    """성공률 < target → 범위 축소."""
    base = DomainConfig(wind_speed_range=(0.0, 10.0))
    shrunk = adr_curriculum(base, success_rate=0.3, target=0.7)
    assert shrunk.wind_speed_range[1] < base.wind_speed_range[1]


def test_imu_bias_3d_vector() -> None:
    """IMU bias는 3차원."""
    rng = DomainRandomizer(DomainConfig(), seed=0)
    s = rng.sample()
    assert isinstance(s.imu_bias, np.ndarray)
    assert s.imu_bias.shape == (3,)
