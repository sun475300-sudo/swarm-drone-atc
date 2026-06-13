"""ODYSSEY Phase 446 — 충돌 해결률 공식의 통계적 검정력 분석.

충돌 해결률 ``1 - collisions/(conflicts + collisions)`` 은 본 시스템의 핵심
성능 지표다. "SDACS 가 베이스라인(p0)보다 해결률이 높다(p1)" 라는 주장을
통계적으로 뒷받침하려면 (1) 주어진 런 수에서의 검정력과 (2) 목표 검정력을
달성하는 최소 런 수를 알아야 한다.

단일 비율 z-검정(arcsine 안정화 변환, Cohen's h 효과크기) 기반의
닫힌 형식 근사를 제공한다 — Monte Carlo 런 수 설계에 직접 쓰인다.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from scipy import stats


@dataclass(frozen=True)
class PowerResult:
    """검정력 분석 결과."""

    p0: float
    p1: float
    n: int
    alpha: float
    power: float
    effect_size: float  # Cohen's h


def _validate_proportion(p: float, name: str) -> None:
    if not 0.0 <= p <= 1.0:
        raise ValueError(f"{name} 는 [0,1] 범위여야 합니다: {p}")


def cohens_h(p0: float, p1: float) -> float:
    """두 비율 간 Cohen's h 효과크기 (arcsine 변환 차이).

    ``h = 2*arcsin(sqrt(p1)) - 2*arcsin(sqrt(p0))``. p1>p0 이면 양수.
    """
    _validate_proportion(p0, "p0")
    _validate_proportion(p1, "p1")
    phi0 = 2.0 * math.asin(math.sqrt(p0))
    phi1 = 2.0 * math.asin(math.sqrt(p1))
    return phi1 - phi0


def proportion_power(
    p0: float,
    p1: float,
    n: int,
    alpha: float = 0.05,
    two_sided: bool = True,
) -> PowerResult:
    """단일 비율 검정의 검정력 (arcsine 변환 근사).

    효과가 없으면(p0==p1) 검정력은 유의수준 alpha 로 수렴한다.
    """
    if n < 1:
        raise ValueError("n 은 1 이상이어야 합니다")
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha 는 (0,1) 범위여야 합니다: {alpha}")

    h = cohens_h(p0, p1)
    z_crit = stats.norm.ppf(1.0 - alpha / 2.0) if two_sided else stats.norm.ppf(
        1.0 - alpha
    )
    ncp = abs(h) * math.sqrt(n)  # 비중심 모수
    # 단측 기각역 확률 (효과 방향). two_sided 에서 반대편 꼬리는 무시 가능 수준.
    power = float(stats.norm.cdf(ncp - z_crit))
    if two_sided:
        power += float(stats.norm.cdf(-ncp - z_crit))
    power = min(1.0, max(0.0, power))
    return PowerResult(p0, p1, n, alpha, power, h)


def required_sample_size(
    p0: float,
    p1: float,
    alpha: float = 0.05,
    power: float = 0.80,
    two_sided: bool = True,
) -> int:
    """목표 검정력을 달성하는 최소 표본(런) 수.

    ``n = ((z_alpha + z_power) / h)^2`` 의 천장값.
    """
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha 는 (0,1) 범위여야 합니다: {alpha}")
    if not 0.0 < power < 1.0:
        raise ValueError(f"power 는 (0,1) 범위여야 합니다: {power}")

    h = cohens_h(p0, p1)
    if h == 0.0:
        raise ValueError("효과크기가 0 입니다 (p0 == p1) — 표본 수 계산 불가")

    z_alpha = stats.norm.ppf(1.0 - alpha / 2.0) if two_sided else stats.norm.ppf(
        1.0 - alpha
    )
    z_power = stats.norm.ppf(power)
    n = ((z_alpha + z_power) / abs(h)) ** 2
    return int(math.ceil(n))


def resolution_rate_power_report(
    baseline: float,
    target: float,
    n_runs: int,
    alpha: float = 0.05,
    target_power: float = 0.80,
) -> str:
    """충돌 해결률 검정력 분석을 마크다운 표로 (논문 §Statistical Power 삽입용)."""
    res = proportion_power(baseline, target, n_runs, alpha=alpha)
    n_needed = required_sample_size(
        baseline, target, alpha=alpha, power=target_power
    )
    verdict = "✅ 충분" if res.power >= target_power else "⚠️ 부족"
    lines = [
        "### 충돌 해결률 통계적 검정력 분석",
        "",
        f"단일 비율 z-검정 (arcsine 변환), 유의수준 α={alpha:.2f}, "
        f"양측. H0: 해결률 ≤ {baseline:.3f}, H1: 해결률 = {target:.3f}.",
        "",
        "| 항목 | 값 |",
        "|---|:-:|",
        f"| 베이스라인 해결률 p0 | {baseline:.3f} |",
        f"| 목표 해결률 p1 | {target:.3f} |",
        f"| 효과크기 (Cohen's h) | {res.effect_size:.3f} |",
        f"| 현재 런 수 n | {n_runs} |",
        f"| 현재 검정력 | {res.power:.1%} ({verdict}) |",
        f"| 목표 검정력 {target_power:.0%} 달성 최소 런 수 | {n_needed} |",
    ]
    return "\n".join(lines)
