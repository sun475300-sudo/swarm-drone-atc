"""충돌 해결률 공식의 통계적 검정력 분석 (GENESIS/ODYSSEY Phase 446).

프로젝트 핵심 KPI인 충돌 해결률
``resolution_rate = 1 - collisions / (conflicts + collisions)``
은 본질적으로 이항 비율(binomial proportion)이다. 본 모듈은 이 비율을
통계적으로 다루기 위한 도구를 제공한다.

- Wilson score 신뢰구간 (작은 표본·극단 비율에서 정규근사보다 정확)
- 2-비율 z-검정 (baseline 대비 SDACS 해결률 차이 유의성)
- 검정력(power) 계산 (주어진 표본 수에서 차이를 탐지할 확률)
- 목표 검정력 달성에 필요한 표본 수 산정

scipy 의존 없이 표준 라이브러리 ``math`` 만으로 정규분포 CDF/PPF 를 계산한다
(재현성·경량 배포 목적).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

__all__ = [
    "resolution_rate",
    "norm_cdf",
    "norm_ppf",
    "wilson_interval",
    "ProportionTest",
    "two_proportion_ztest",
    "power_two_proportion",
    "required_sample_size",
    "power_report",
]


def resolution_rate(conflicts: int, collisions: int) -> float:
    """충돌 해결률을 계산한다 (프로젝트 표준 공식).

    ``conflicts`` 는 해결된 충돌(근접) 횟수, ``collisions`` 는 미해결로
    실제 충돌에 이른 횟수다. 전체 이벤트가 0이면 1.0(완전 안전)을 반환한다.
    """
    total = conflicts + collisions
    if total <= 0:
        return 1.0
    return 1.0 - collisions / total


def norm_cdf(x: float) -> float:
    """표준정규분포 누적분포함수 Φ(x)."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def norm_ppf(p: float) -> float:
    """표준정규분포 분위수 함수 Φ⁻¹(p) (Acklam 유리근사).

    0 < p < 1 범위에서 |오차| < 1.15e-9.
    """
    if not 0.0 < p < 1.0:
        raise ValueError("p는 (0, 1) 범위여야 합니다")

    # Acklam 알고리즘 계수
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]

    p_low = 0.02425
    p_high = 1.0 - p_low

    if p < p_low:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    if p <= p_high:
        q = p - 0.5
        r = q * q
        return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
               (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
    q = math.sqrt(-2.0 * math.log(1.0 - p))
    return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
           ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)


def wilson_interval(
    successes: int, n: int, confidence: float = 0.95
) -> tuple[float, float]:
    """비율의 Wilson score 신뢰구간을 반환한다.

    정규근사(Wald)와 달리 0/1 경계 근처에서도 [0, 1] 안에 머물고,
    작은 표본에서 피복률(coverage)이 우수하다.
    """
    if n <= 0:
        return (0.0, 1.0)
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence는 (0, 1) 범위여야 합니다")

    z = norm_ppf(1.0 - (1.0 - confidence) / 2.0)
    phat = successes / n
    denom = 1.0 + z * z / n
    center = (phat + z * z / (2.0 * n)) / denom
    margin = (z * math.sqrt(phat * (1.0 - phat) / n + z * z / (4.0 * n * n))) / denom
    return (max(0.0, center - margin), min(1.0, center + margin))


@dataclass(frozen=True)
class ProportionTest:
    """2-비율 검정 결과."""

    rate_a: float
    rate_b: float
    diff: float
    z: float
    p_value: float
    significant: bool


def two_proportion_ztest(
    successes_a: int,
    n_a: int,
    successes_b: int,
    n_b: int,
    alpha: float = 0.05,
) -> ProportionTest:
    """두 해결률(예: baseline vs SDACS)의 차이에 대한 풀드 z-검정.

    귀무가설 H0: p_a = p_b (양측 검정).
    """
    if n_a <= 0 or n_b <= 0:
        raise ValueError("표본 수 n_a, n_b는 양수여야 합니다")

    p_a = successes_a / n_a
    p_b = successes_b / n_b
    pooled = (successes_a + successes_b) / (n_a + n_b)
    se = math.sqrt(pooled * (1.0 - pooled) * (1.0 / n_a + 1.0 / n_b))

    if se == 0.0:
        z = 0.0
        p_value = 1.0
    else:
        z = (p_b - p_a) / se
        p_value = 2.0 * (1.0 - norm_cdf(abs(z)))

    return ProportionTest(
        rate_a=p_a,
        rate_b=p_b,
        diff=p_b - p_a,
        z=z,
        p_value=p_value,
        significant=p_value < alpha,
    )


def power_two_proportion(
    p1: float,
    p2: float,
    n1: int,
    n2: int | None = None,
    alpha: float = 0.05,
    two_sided: bool = True,
) -> float:
    """2-비율 검정의 검정력(power)을 계산한다.

    p1, p2 가 참인 모비율일 때, 그룹당 n1·n2 표본으로 차이를 탐지할 확률.
    표준 비풀드(unpooled) 정규근사를 사용한다.
    """
    if not 0.0 <= p1 <= 1.0 or not 0.0 <= p2 <= 1.0:
        raise ValueError("p1, p2는 [0, 1] 범위여야 합니다")
    if n2 is None:
        n2 = n1
    if n1 <= 0 or n2 <= 0:
        raise ValueError("표본 수는 양수여야 합니다")

    z_alpha = norm_ppf(1.0 - alpha / 2.0) if two_sided else norm_ppf(1.0 - alpha)
    se = math.sqrt(p1 * (1.0 - p1) / n1 + p2 * (1.0 - p2) / n2)
    if se == 0.0:
        # 분산이 0이면 차이가 있을 때 검정력 1, 없으면 alpha.
        return 1.0 if p1 != p2 else alpha

    effect = (p2 - p1) / se
    # 상단 기각역 기여 + (양측이면) 반대쪽 꼬리 기여.
    power = 1.0 - norm_cdf(z_alpha - effect)
    if two_sided:
        power += norm_cdf(-z_alpha - effect)
    return min(1.0, max(0.0, power))


def required_sample_size(
    p1: float,
    p2: float,
    power: float = 0.8,
    alpha: float = 0.05,
    two_sided: bool = True,
) -> int:
    """목표 검정력 달성에 필요한 그룹당 표본 수(올림)를 반환한다."""
    if not 0.0 <= p1 <= 1.0 or not 0.0 <= p2 <= 1.0:
        raise ValueError("p1, p2는 [0, 1] 범위여야 합니다")
    if p1 == p2:
        raise ValueError("p1 == p2 이면 표본 수를 정의할 수 없습니다")
    if not 0.0 < power < 1.0:
        raise ValueError("power는 (0, 1) 범위여야 합니다")

    z_alpha = norm_ppf(1.0 - alpha / 2.0) if two_sided else norm_ppf(1.0 - alpha)
    z_beta = norm_ppf(power)
    numerator = (
        z_alpha * math.sqrt(2.0 * _avg(p1, p2) * (1.0 - _avg(p1, p2)))
        + z_beta * math.sqrt(p1 * (1.0 - p1) + p2 * (1.0 - p2))
    ) ** 2
    n = numerator / (p1 - p2) ** 2
    return math.ceil(n)


def _avg(a: float, b: float) -> float:
    return (a + b) / 2.0


def power_report(
    baseline_conflicts: int,
    baseline_collisions: int,
    sdacs_conflicts: int,
    sdacs_collisions: int,
    alpha: float = 0.05,
    target_power: float = 0.8,
) -> str:
    """baseline 대비 SDACS 충돌 해결률 비교 보고서(Markdown)를 생성한다."""
    n_base = baseline_conflicts + baseline_collisions
    n_sdacs = sdacs_conflicts + sdacs_collisions
    r_base = resolution_rate(baseline_conflicts, baseline_collisions)
    r_sdacs = resolution_rate(sdacs_conflicts, sdacs_collisions)

    ci_base = wilson_interval(baseline_conflicts, n_base, 1.0 - alpha)
    ci_sdacs = wilson_interval(sdacs_conflicts, n_sdacs, 1.0 - alpha)

    test = two_proportion_ztest(
        baseline_conflicts, n_base, sdacs_conflicts, n_sdacs, alpha
    )
    observed_power = power_two_proportion(r_base, r_sdacs, n_base, n_sdacs, alpha)

    lines = [
        "# 충돌 해결률 통계적 검정력 분석",
        "",
        f"- 유의수준 α = {alpha:.3f}, 목표 검정력 = {target_power:.2f}",
        "",
        "| 시스템 | 해결률 | 95% Wilson CI | 표본(이벤트) |",
        "|---|:-:|:-:|:-:|",
        f"| Baseline | {r_base:.4f} | [{ci_base[0]:.4f}, {ci_base[1]:.4f}] | {n_base} |",
        f"| SDACS | {r_sdacs:.4f} | [{ci_sdacs[0]:.4f}, {ci_sdacs[1]:.4f}] | {n_sdacs} |",
        "",
        "## 2-비율 z-검정 (H0: 두 해결률 동일)",
        "",
        f"- 해결률 차이 Δ = {test.diff:+.4f}",
        f"- z = {test.z:.3f}, p-value = {test.p_value:.4g}",
        f"- 결론: **{'유의함 (H0 기각)' if test.significant else '유의하지 않음'}**",
        f"- 현 표본의 관측 검정력 ≈ {observed_power:.3f}",
    ]

    if not test.significant and r_base != r_sdacs:
        need = required_sample_size(r_base, r_sdacs, target_power, alpha)
        lines.append(
            f"- 검정력 {target_power:.2f} 달성에 필요한 그룹당 이벤트 수 ≈ {need}"
        )

    return "\n".join(lines)
