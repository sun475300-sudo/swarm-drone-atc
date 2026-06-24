"""ODYSSEY Phase 445 — 불확실성 정량화 (Monte Carlo 신뢰구간 자동 리포트).

Monte Carlo 스윕 결과의 점추정에 신뢰구간을 부여한다. 논문 §Results 에서
"충돌 0.4 ± 0.2" 처럼 단일 평균만 보고하던 것을 통계적으로 근거 있는
구간 추정으로 격상한다.

세 가지 방법을 제공한다:
- ``normal_ci``     : t-분포 기반 평균 신뢰구간 (연속형 KPI)
- ``bootstrap_ci``  : 분포 가정 없는 percentile bootstrap (왜도가 큰 KPI)
- ``proportion_ci`` : Wilson score 구간 (비율형 KPI — 충돌 해결률 등)

재현성: bootstrap 은 ``np.random.default_rng(seed)`` 를 사용한다
(프로젝트 규칙 — ``random.random()`` 금지).
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np
from scipy import stats

DEFAULT_CONFIDENCE = 0.95
DEFAULT_BOOTSTRAP_RESAMPLES = 10_000
DEFAULT_SEED = 42


@dataclass(frozen=True)
class ConfidenceInterval:
    """점추정 + 신뢰구간 결과."""

    point: float
    lower: float
    upper: float
    confidence: float
    method: str
    n: int

    @property
    def margin(self) -> float:
        """구간 반폭 ``(upper-lower)/2``.

        대칭 구간(normal·bootstrap)에서는 point 로부터의 ± 오차와 같다.
        Wilson score 같은 비대칭 구간에서는 point 와의 거리와 다를 수 있으므로
        보고 시 lower/upper 를 직접 사용한다.
        """
        return (self.upper - self.lower) / 2.0

    def contains(self, value: float) -> bool:
        """``value`` 가 신뢰구간 안에 있는지."""
        return self.lower <= value <= self.upper

    def as_dict(self) -> dict:
        """직렬화용 dict."""
        return {
            "point": self.point,
            "lower": self.lower,
            "upper": self.upper,
            "confidence": self.confidence,
            "method": self.method,
            "n": self.n,
        }

    def format(self, digits: int = 3) -> str:
        """사람이 읽는 한 줄 표현: ``0.942 [0.910, 0.974]``."""
        return (
            f"{self.point:.{digits}f} "
            f"[{self.lower:.{digits}f}, {self.upper:.{digits}f}]"
        )


def _validate_confidence(confidence: float) -> None:
    if not 0.0 < confidence < 1.0:
        raise ValueError(f"confidence 는 (0,1) 범위여야 합니다: {confidence}")


def normal_ci(
    samples: Sequence[float], confidence: float = DEFAULT_CONFIDENCE
) -> ConfidenceInterval:
    """t-분포 기반 평균 신뢰구간.

    표본 수 n>=2 필요. 표준편차 0 이면 폭 0 구간을 반환한다.
    """
    _validate_confidence(confidence)
    arr = np.asarray(samples, dtype=float)
    n = arr.size
    if n < 2:
        raise ValueError("normal_ci 는 표본 2개 이상이 필요합니다")

    mean = float(arr.mean())
    sem = float(stats.sem(arr))
    if sem == 0.0:
        return ConfidenceInterval(mean, mean, mean, confidence, "normal", n)

    half = float(stats.t.ppf(0.5 + confidence / 2.0, df=n - 1) * sem)
    return ConfidenceInterval(
        mean, mean - half, mean + half, confidence, "normal", n
    )


def bootstrap_ci(
    samples: Sequence[float],
    confidence: float = DEFAULT_CONFIDENCE,
    n_resamples: int = DEFAULT_BOOTSTRAP_RESAMPLES,
    seed: int = DEFAULT_SEED,
    statistic: Callable[[np.ndarray], float] = np.mean,
) -> ConfidenceInterval:
    """Percentile bootstrap 신뢰구간 (분포 가정 없음).

    ``seed`` 고정 시 완전 결정적. 비대칭/왜도가 큰 KPI 에 적합.
    """
    _validate_confidence(confidence)
    arr = np.asarray(samples, dtype=float)
    n = arr.size
    if n < 2:
        raise ValueError("bootstrap_ci 는 표본 2개 이상이 필요합니다")

    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(n_resamples, n))
    boot_stats = np.array([float(statistic(arr[row])) for row in idx])

    alpha = 1.0 - confidence
    lower = float(np.percentile(boot_stats, 100.0 * alpha / 2.0))
    upper = float(np.percentile(boot_stats, 100.0 * (1.0 - alpha / 2.0)))
    point = float(statistic(arr))
    return ConfidenceInterval(point, lower, upper, confidence, "bootstrap", n)


def proportion_ci(
    successes: int, trials: int, confidence: float = DEFAULT_CONFIDENCE
) -> ConfidenceInterval:
    """Wilson score 비율 신뢰구간.

    충돌 해결률처럼 0~1 비율형 KPI 에 사용. 표본 비율 0/1 경계에서도
    구간이 [0,1] 안에 머문다 (정규근사보다 강건).
    """
    _validate_confidence(confidence)
    if trials <= 0:
        raise ValueError("trials 는 1 이상이어야 합니다")
    if not 0 <= successes <= trials:
        raise ValueError("successes 는 0..trials 범위여야 합니다")

    p_hat = successes / trials
    z = float(stats.norm.ppf(0.5 + confidence / 2.0))
    z2 = z * z
    denom = 1.0 + z2 / trials
    center = (p_hat + z2 / (2 * trials)) / denom
    half = (
        z
        * np.sqrt(p_hat * (1.0 - p_hat) / trials + z2 / (4 * trials * trials))
        / denom
    )
    lower = max(0.0, float(center - half))
    upper = min(1.0, float(center + half))
    return ConfidenceInterval(
        float(p_hat), lower, upper, confidence, "wilson", trials
    )


def summarize_metric_ci(
    results: Sequence[dict],
    metric: str,
    confidence: float = DEFAULT_CONFIDENCE,
    method: str = "normal",
) -> ConfidenceInterval:
    """Monte Carlo 결과 리스트에서 한 지표의 신뢰구간을 계산.

    ``method`` 는 ``"normal"`` 또는 ``"bootstrap"``.
    """
    if not results:
        raise ValueError("results 가 비어 있습니다")
    try:
        samples = [float(row[metric]) for row in results]
    except KeyError as exc:
        raise KeyError(f"지표 '{metric}' 가 결과에 없습니다") from exc

    if method == "bootstrap":
        return bootstrap_ci(samples, confidence=confidence)
    return normal_ci(samples, confidence=confidence)


def confidence_report(
    results: Sequence[dict],
    metrics: Sequence[str],
    confidence: float = DEFAULT_CONFIDENCE,
) -> str:
    """Monte Carlo 결과를 신뢰구간 마크다운 표로 변환 (논문 §Results 삽입용)."""
    pct = f"{confidence:.0%}"
    lines = [
        f"### Monte Carlo {pct} 신뢰구간 (n={len(results)} runs)",
        "",
        f"| 지표 | 점추정 | {pct} CI 하한 | {pct} CI 상한 | ±오차 |",
        "|---|:-:|:-:|:-:|:-:|",
    ]
    for metric in metrics:
        ci = summarize_metric_ci(results, metric, confidence=confidence)
        lines.append(
            f"| {metric} | {ci.point:.3f} | {ci.lower:.3f} "
            f"| {ci.upper:.3f} | {ci.margin:.3f} |"
        )
    return "\n".join(lines)
