"""P449: 시뮬-실측 갭 모델 — Domain Randomization 파라미터 자동 보정.

실기 비행에서 관측된 텔레메트리 분포(풍속·GPS 노이즈·통신 지연·패킷 손실)와
시뮬레이션 ``DomainConfig`` 범위 사이의 갭을 정량화하고, 범위를 실측에 맞게
자동 보정하여 sim-to-real 격차를 좁힌다.

P739(domain_rand) 위에 얹는 보정 계층으로, 학습용 도메인 분포를 실측 데이터로
캘리브레이션하는 ODYSSEY Phase 449에 해당한다.

Reference: Chebotar et al. "Closing the Sim-to-Real Loop" (ICRA 2019).
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass

import numpy as np

from src.training.domain_rand import DomainConfig

# 관측 키 → DomainConfig 범위 필드 매핑.
# (실기에서 직접 계측 가능한 파라미터만 보정 대상으로 둔다.)
_PARAM_TO_FIELD: dict[str, str] = {
    "wind_speed": "wind_speed_range",
    "gps_noise_std": "gps_noise_std_m",
    "comm_latency_ms": "comm_latency_range_ms",
    "comm_packet_loss": "comm_packet_loss_range",
}

# 보정 시 실측 극값에 부여하는 여유(범위 폭 대비 비율).
_ENVELOPE_MARGIN = 0.02
# 패킷 손실률 상한(물리적 의미상 100%).
_PACKET_LOSS_CEILING = 1.0


@dataclass(frozen=True)
class SimRealGap:
    """시뮬-실측 갭 정량화 결과.

    - ``per_parameter``: 파라미터별 갭 [0,1] (범위이탈 비율·중심 오프셋 결합)
    - ``out_of_range_fraction``: 전체 표본 중 시뮬 범위 밖 비율 [0,1]
    - ``aggregate``: 파라미터별 갭의 평균 [0,1]
    """

    per_parameter: dict[str, float]
    out_of_range_fraction: float
    aggregate: float


@dataclass(frozen=True)
class CalibrationResult:
    """보정 결과 + 보정 전후 갭."""

    cfg: DomainConfig
    gap_before: SimRealGap
    gap_after: SimRealGap


def _known_items(observed: dict[str, np.ndarray]) -> list[tuple[str, str, np.ndarray]]:
    """관측 dict에서 보정 대상(param, field, samples)만 추린다."""
    items: list[tuple[str, str, np.ndarray]] = []
    for param, field in _PARAM_TO_FIELD.items():
        if param in observed:
            samples = np.asarray(observed[param], dtype=float)
            if samples.size > 0:
                items.append((param, field, samples))
    return items


def compute_gap(observed: dict[str, np.ndarray], cfg: DomainConfig) -> SimRealGap:
    """관측 분포와 ``cfg`` 범위 사이의 갭을 계산.

    Args:
        observed: 파라미터명 → 실측 표본 배열.
        cfg: 현재 도메인 분포.

    Raises:
        ValueError: 관측이 비었거나 보정 대상 파라미터가 하나도 없을 때.
    """
    items = _known_items(observed)
    if not items:
        raise ValueError("관측 데이터에 보정 가능한 파라미터가 없습니다.")

    per_parameter: dict[str, float] = {}
    total_samples = 0
    total_out = 0

    for param, field, samples in items:
        lo, hi = getattr(cfg, field)
        half_width = max((hi - lo) / 2.0, 1e-9)
        midpoint = (hi + lo) / 2.0

        out_mask = (samples < lo) | (samples > hi)
        oor_param = float(np.count_nonzero(out_mask)) / samples.size
        center_offset = float(np.clip(abs(samples.mean() - midpoint) / half_width, 0.0, 1.0))

        per_parameter[param] = float(np.clip(0.5 * oor_param + 0.5 * center_offset, 0.0, 1.0))
        total_samples += samples.size
        total_out += int(np.count_nonzero(out_mask))

    return SimRealGap(
        per_parameter=per_parameter,
        out_of_range_fraction=total_out / total_samples,
        aggregate=float(np.mean(list(per_parameter.values()))),
    )


class SimRealGapCalibrator:
    """관측된 실측 분포로 ``DomainConfig`` 범위를 자동 보정."""

    def __init__(self, cfg: DomainConfig) -> None:
        self.cfg = cfg

    def calibrate(self, observed: dict[str, np.ndarray]) -> DomainConfig:
        """실측 극값을 감싸도록 범위를 확장한 새 ``DomainConfig`` 반환(불변)."""
        updates: dict[str, tuple[float, float]] = {}
        for _param, field, samples in _known_items(observed):
            obs_lo = float(samples.min())
            obs_hi = float(samples.max())
            margin = _ENVELOPE_MARGIN * max(obs_hi - obs_lo, 1e-9)

            new_lo = max(0.0, obs_lo - margin)  # 4개 대상 모두 음수 불가
            new_hi = obs_hi + margin
            if field == "comm_packet_loss_range":
                new_hi = min(_PACKET_LOSS_CEILING, new_hi)
            updates[field] = (new_lo, new_hi)

        if not updates:
            return self.cfg
        return dataclasses.replace(self.cfg, **updates)

    def calibrate_report(self, observed: dict[str, np.ndarray]) -> CalibrationResult:
        """보정 + 보정 전후 갭을 함께 반환."""
        gap_before = compute_gap(observed, self.cfg)
        new_cfg = self.calibrate(observed)
        gap_after = compute_gap(observed, new_cfg)
        return CalibrationResult(cfg=new_cfg, gap_before=gap_before, gap_after=gap_after)
