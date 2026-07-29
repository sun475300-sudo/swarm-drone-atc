"""ODYSSEY Phase 446 — 충돌 해결률 공식의 통계적 검정력 분석.

충돌 해결률 ``1 - collisions/(conflicts + collisions)`` 은 본 시스템의 핵심
성능 지표다. "SDACS 가 베이스라인(p0)보다 해결률이 높다(p1)" 라는 주장을
통계적으로 뒷받침하려면 (1) 주어진 런 수에서의 검정력과 (2) 목표 검정력을
달성하는 최소 런 수를 알아야 한다.

단일 비율 z-검정(arcsine 안정화 변환, Cohen's h 효과크기) 기반의
닫힌 형식 근사를 제공한다 — Monte Carlo 런 수 설계에 직접 쓰인다.

관측 결과를 비교할 때는 Wilson 신뢰구간과 풀드 2-비율 z-검정을 제공한다.
이는 구형 ``resolution_rate_power`` 실험 브랜치에서 검증된 통계 기능만
현행 모듈의 데이터 모델과 SciPy 의존성에 맞춰 이식한 것이다.
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


@dataclass(frozen=True)
class ProportionComparison:
    """Baseline과 후보 시스템의 관측 해결률 비교 결과."""

    baseline_rate: float
    candidate_rate: float
    difference: float
    baseline_interval: tuple[float, float]
    candidate_interval: tuple[float, float]
    z_score: float
    p_value: float
    alpha: float
    power: float

    @property
    def significant(self) -> bool:
        """양측 검정 결과가 설정된 유의수준보다 작은지 여부."""
        return self.p_value < self.alpha


def _validate_proportion(p: float, name: str) -> None:
    if not 0.0 <= p <= 1.0:
        raise ValueError(f"{name} 는 [0,1] 범위여야 합니다: {p}")


def _validate_alpha(alpha: float) -> None:
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha 는 (0,1) 범위여야 합니다: {alpha}")


def _validate_binomial_counts(successes: int, total: int, name: str) -> None:
    if total < 0:
        raise ValueError(f"{name} total은 0 이상이어야 합니다: {total}")
    if successes < 0:
        raise ValueError(f"{name} successes는 0 이상이어야 합니다: {successes}")
    if successes > total:
        raise ValueError(
            f"{name} successes는 total 이하여야 합니다: {successes} > {total}"
        )


def resolution_rate(conflicts: int, collisions: int) -> float:
    """프로젝트 표준 공식으로 관측 충돌 해결률을 계산한다.

    ``conflicts``는 해결된 충돌 위험 이벤트, ``collisions``는 실제 충돌
    이벤트 수다. 관측 이벤트가 없으면 기존 KPI 계약에 따라 1.0을 반환한다.
    """
    if conflicts < 0 or collisions < 0:
        raise ValueError("conflicts와 collisions는 0 이상이어야 합니다")
    total = conflicts + collisions
    if total == 0:
        return 1.0
    return 1.0 - collisions / total


def wilson_interval(
    successes: int,
    total: int,
    confidence: float = 0.95,
) -> tuple[float, float]:
    """이항 비율의 Wilson score 신뢰구간을 반환한다.

    작은 표본과 0/1 경계에서도 Wald 구간보다 안정적이다. 관측치가 없으면
    정보가 없음을 나타내는 전체 구간 ``(0.0, 1.0)``을 반환한다.
    """
    _validate_binomial_counts(successes, total, "observed")
    if not 0.0 < confidence < 1.0:
        raise ValueError(f"confidence 는 (0,1) 범위여야 합니다: {confidence}")
    if total == 0:
        return (0.0, 1.0)

    z_score = float(stats.norm.ppf(0.5 + confidence / 2.0))
    observed = successes / total
    z_squared = z_score * z_score
    denominator = 1.0 + z_squared / total
    center = (observed + z_squared / (2.0 * total)) / denominator
    margin = (
        z_score
        * math.sqrt(
            observed * (1.0 - observed) / total
            + z_squared / (4.0 * total * total)
        )
        / denominator
    )
    return (max(0.0, center - margin), min(1.0, center + margin))


def two_proportion_power(
    p0: float,
    p1: float,
    n0: int,
    n1: int | None = None,
    alpha: float = 0.05,
    two_sided: bool = True,
) -> float:
    """두 독립 비율의 차이를 탐지하는 정규근사 검정력을 계산한다."""
    _validate_proportion(p0, "p0")
    _validate_proportion(p1, "p1")
    _validate_alpha(alpha)
    if n1 is None:
        n1 = n0
    if n0 < 1 or n1 < 1:
        raise ValueError("n0와 n1은 1 이상이어야 합니다")

    standard_error = math.sqrt(
        p0 * (1.0 - p0) / n0 + p1 * (1.0 - p1) / n1
    )
    if standard_error == 0.0:
        return 1.0 if p0 != p1 else alpha

    effect = (p1 - p0) / standard_error
    if two_sided:
        effect = abs(effect)
        critical = float(stats.norm.ppf(1.0 - alpha / 2.0))
        power = float(stats.norm.cdf(effect - critical))
        power += float(stats.norm.cdf(-effect - critical))
    else:
        critical = float(stats.norm.ppf(1.0 - alpha))
        power = float(stats.norm.cdf(effect - critical))
    return min(1.0, max(0.0, power))


def compare_resolution_rates(
    baseline_conflicts: int,
    baseline_collisions: int,
    candidate_conflicts: int,
    candidate_collisions: int,
    alpha: float = 0.05,
) -> ProportionComparison:
    """Baseline과 후보 시스템의 해결률을 양측 2-비율 z-검정으로 비교한다."""
    _validate_alpha(alpha)
    baseline_total = baseline_conflicts + baseline_collisions
    candidate_total = candidate_conflicts + candidate_collisions
    _validate_binomial_counts(
        baseline_conflicts, baseline_total, "baseline"
    )
    _validate_binomial_counts(
        candidate_conflicts, candidate_total, "candidate"
    )
    if baseline_total == 0 or candidate_total == 0:
        raise ValueError("해결률 비교에는 각 시스템별 관측 이벤트가 필요합니다")

    baseline_rate = resolution_rate(baseline_conflicts, baseline_collisions)
    candidate_rate = resolution_rate(candidate_conflicts, candidate_collisions)
    pooled_rate = (
        baseline_conflicts + candidate_conflicts
    ) / (baseline_total + candidate_total)
    standard_error = math.sqrt(
        pooled_rate
        * (1.0 - pooled_rate)
        * (1.0 / baseline_total + 1.0 / candidate_total)
    )
    if standard_error == 0.0:
        z_score = 0.0
        p_value = 1.0
    else:
        z_score = (candidate_rate - baseline_rate) / standard_error
        p_value = float(2.0 * stats.norm.sf(abs(z_score)))

    confidence = 1.0 - alpha
    return ProportionComparison(
        baseline_rate=baseline_rate,
        candidate_rate=candidate_rate,
        difference=candidate_rate - baseline_rate,
        baseline_interval=wilson_interval(
            baseline_conflicts, baseline_total, confidence
        ),
        candidate_interval=wilson_interval(
            candidate_conflicts, candidate_total, confidence
        ),
        z_score=z_score,
        p_value=p_value,
        alpha=alpha,
        power=two_proportion_power(
            baseline_rate,
            candidate_rate,
            baseline_total,
            candidate_total,
            alpha,
        ),
    )


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
    _validate_proportion(p0, "p0")
    _validate_proportion(p1, "p1")
    if n < 1:
        raise ValueError("n 은 1 이상이어야 합니다")
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha 는 (0,1) 범위여야 합니다: {alpha}")

    h = cohens_h(p0, p1)
    z_crit = stats.norm.ppf(1.0 - alpha / 2.0) if two_sided else stats.norm.ppf(
        1.0 - alpha
    )
    ncp = abs(h) * math.sqrt(n)  # 비중심 모수
    # 양측 검정 기각역 = {Z < -z_crit} ∪ {Z > z_crit}. 두 꼬리 기여항을 모두 더한다.
    #   효과 방향 꼬리: Φ(ncp - z_crit)
    #   반대편 꼬리:    Φ(-ncp - z_crit)  — h=0 일 때 power=alpha 를 보장하므로 생략 금지.
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
    _validate_proportion(p0, "p0")
    _validate_proportion(p1, "p1")
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


def resolution_rate_comparison_report(
    baseline_conflicts: int,
    baseline_collisions: int,
    candidate_conflicts: int,
    candidate_collisions: int,
    alpha: float = 0.05,
) -> str:
    """관측 해결률 비교 결과를 재현 가능한 Markdown 표로 반환한다."""
    result = compare_resolution_rates(
        baseline_conflicts,
        baseline_collisions,
        candidate_conflicts,
        candidate_collisions,
        alpha,
    )
    baseline_total = baseline_conflicts + baseline_collisions
    candidate_total = candidate_conflicts + candidate_collisions
    confidence_pct = (1.0 - alpha) * 100.0
    verdict = "유의함 (H0 기각)" if result.significant else "유의하지 않음"

    lines = [
        "### 관측 충돌 해결률 비교",
        "",
        f"양측 2-비율 z-검정, 유의수준 α={alpha:.3f}. "
        "H0: Baseline과 Candidate의 해결률이 동일함.",
        "",
        f"| 시스템 | 해결률 | {confidence_pct:.0f}% Wilson CI | 이벤트 수 |",
        "|---|:-:|:-:|:-:|",
        f"| Baseline | {result.baseline_rate:.4f} | "
        f"[{result.baseline_interval[0]:.4f}, {result.baseline_interval[1]:.4f}] "
        f"| {baseline_total} |",
        f"| Candidate | {result.candidate_rate:.4f} | "
        f"[{result.candidate_interval[0]:.4f}, {result.candidate_interval[1]:.4f}] "
        f"| {candidate_total} |",
        "",
        f"- 해결률 차이 Δ = {result.difference:+.4f}",
        f"- z = {result.z_score:.3f}, p-value = {result.p_value:.4g}",
        f"- 결론: **{verdict}**",
        f"- 현 표본의 근사 검정력 = {result.power:.3f}",
    ]
    return "\n".join(lines)
