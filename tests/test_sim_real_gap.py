"""P449: 시뮬-실측 갭 모델 — DR 파라미터 보정 자동화 테스트.

관측된 실기 텔레메트리 분포와 시뮬레이션 DomainConfig 범위 사이의 갭을
정량화하고, 범위를 실측 데이터에 맞게 자동 보정하는 동작을 검증.
"""
from __future__ import annotations

import numpy as np
import pytest

from src.training.domain_rand import DomainConfig
from src.training.sim_real_gap import (
    SimRealGap,
    SimRealGapCalibrator,
    compute_gap,
)


@pytest.fixture
def base_cfg() -> DomainConfig:
    return DomainConfig()


def _make_observed(rng_seed: int = 0) -> dict[str, np.ndarray]:
    """기본 범위 내부에 들어오는 합성 실측 표본."""
    rng = np.random.default_rng(rng_seed)
    return {
        "wind_speed": rng.uniform(2.0, 8.0, 200),
        "gps_noise_std": rng.uniform(1.0, 3.0, 200),
        "comm_latency_ms": rng.uniform(20.0, 50.0, 200),
        "comm_packet_loss": rng.uniform(0.0, 0.05, 200),
    }


def test_compute_gap_returns_zero_outofrange_when_fully_covered(base_cfg):
    # Arrange: 모든 표본이 기본 범위 안에 있음
    observed = _make_observed()

    # Act
    gap = compute_gap(observed, base_cfg)

    # Assert
    assert isinstance(gap, SimRealGap)
    assert gap.out_of_range_fraction == pytest.approx(0.0, abs=1e-9)
    assert 0.0 <= gap.aggregate <= 1.0


def test_compute_gap_detects_out_of_range_samples(base_cfg):
    # Arrange: 풍속이 기본 상한(15)을 초과하는 표본
    observed = {
        "wind_speed": np.array([5.0, 10.0, 20.0, 25.0]),  # 2/4 초과
    }

    # Act
    gap = compute_gap(observed, base_cfg)

    # Assert: 절반이 범위 밖
    assert gap.out_of_range_fraction == pytest.approx(0.5, abs=1e-9)
    assert gap.per_parameter["wind_speed"] > 0.0


def test_calibrate_envelops_observed_extremes(base_cfg):
    # Arrange: 실측이 기본 범위를 벗어남(풍속 0~25, 지연 5~200ms)
    observed = {
        "wind_speed": np.linspace(0.0, 25.0, 100),
        "comm_latency_ms": np.linspace(5.0, 200.0, 100),
    }

    # Act
    calibrated = calibrate_and_recompute(observed, base_cfg)

    # Assert: 보정 후 범위가 실측 극값을 포함
    assert calibrated.cfg.wind_speed_range[1] >= 25.0
    assert calibrated.cfg.comm_latency_range_ms[1] >= 200.0
    # 보정 후 갭(범위 밖 비율)은 0
    assert calibrated.gap_after.out_of_range_fraction == pytest.approx(0.0, abs=1e-9)


def test_calibrate_reduces_aggregate_gap(base_cfg):
    # Arrange: 명확히 어긋난 실측
    observed = {
        "wind_speed": np.linspace(10.0, 30.0, 100),
        "gps_noise_std": np.linspace(4.0, 12.0, 100),
    }
    before = compute_gap(observed, base_cfg)

    # Act
    result = calibrate_and_recompute(observed, base_cfg)

    # Assert: 보정이 갭을 줄임
    assert result.gap_after.aggregate <= before.aggregate


def test_calibrate_is_immutable(base_cfg):
    # Arrange
    observed = {"wind_speed": np.array([0.0, 30.0])}
    original_range = base_cfg.wind_speed_range

    # Act
    SimRealGapCalibrator(base_cfg).calibrate(observed)

    # Assert: 원본 cfg는 변경되지 않음
    assert base_cfg.wind_speed_range == original_range


def test_calibrate_ignores_unknown_parameters(base_cfg):
    # Arrange: 매핑에 없는 파라미터는 무시(범위 변화 없음)
    observed = {"unknown_param": np.array([1.0, 2.0, 3.0])}

    # Act
    calibrated = SimRealGapCalibrator(base_cfg).calibrate(observed)

    # Assert
    assert calibrated == base_cfg


def test_compute_gap_empty_observed_raises(base_cfg):
    with pytest.raises(ValueError):
        compute_gap({}, base_cfg)


# 헬퍼: 보정 + 재계산을 한 번에
def calibrate_and_recompute(observed, cfg):
    return SimRealGapCalibrator(cfg).calibrate_report(observed)
