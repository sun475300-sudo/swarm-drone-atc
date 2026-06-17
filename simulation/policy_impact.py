"""ODYSSEY Phase 469 — 정책 영향 시뮬레이션 (규제 파라미터 변경 효과 자동 비교).

규제 파라미터(고도 상한·최소 이격 거리·속도 상한 등)를 바꿨을 때 안전·처리량
KPI 가 어떻게 변하는지 자동으로 비교·순위화·리포트한다. 논문 §Discussion 의
"이격 거리를 늘리면 충돌은 줄지만 처리량이 떨어진다" 같은 정성 서술을, 기준
정책 대비 정량 델타(절대·백분율)와 목표별 최적 정책 순위로 격상한다.

**설계 — 비교 엔진과 평가의 분리:** KPI 추정은 주입된 평가 함수(``evaluate``)가
담당한다. 본 모듈은 *비교·순위·리포트 엔진* 이며 시뮬레이터와 독립적이다.
평가 함수를 실제 Monte Carlo 런(`simulation.monte_carlo`)에 연결하면 규제 설정
간 효과를 정량 비교할 수 있고, 테스트는 결정적 토이 평가 함수를 주입한다.
이렇게 분리하면 (1) 엔진 자체에 가짜 물리 모델을 박지 않아 보고 수치가 레포
실측과 어긋날 위험이 없고(프로젝트 규칙), (2) 무거운 시뮬 없이 비교 로직을
결정적으로 검증할 수 있다. 엔진 자체의 무작위성은 0.
"""
from __future__ import annotations

import dataclasses
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType

# KPI 이름 → 클수록 좋은가(True) / 작을수록 좋은가(False).
# 충돌 해결률 공식은 ``1 - collisions/(conflicts + collisions)`` (CLAUDE.md).
_KPI_HIGHER_IS_BETTER: Mapping[str, bool] = {
    "conflict_resolution_rate": True,
    "collisions": False,
    "throughput": True,
    "mean_completion_time_s": False,
}


@dataclass(frozen=True)
class RegulatoryPolicy:
    """비교 대상이 되는 규제 파라미터 묶음 (불변).

    공역 당국이 조정하는 운영 규칙. 값은 모두 양(+)이어야 한다.
    """

    min_separation_m: float
    max_altitude_m: float
    max_speed_mps: float

    def __post_init__(self) -> None:
        for name in ("min_separation_m", "max_altitude_m", "max_speed_mps"):
            value = getattr(self, name)
            if not math.isfinite(value) or value <= 0.0:
                raise ValueError(f"{name} 는 유한한 양수여야 합니다: {value}")

    def with_changes(self, **changes: float) -> RegulatoryPolicy:
        """일부 규제 파라미터만 바꾼 새 정책을 반환한다 (원본 불변)."""
        unknown = set(changes) - {f.name for f in dataclasses.fields(self)}
        if unknown:
            raise ValueError(f"알 수 없는 규제 파라미터: {sorted(unknown)}")
        return dataclasses.replace(self, **changes)

    def signature(self) -> tuple[float, float, float]:
        """결정적 정렬용 동률 분리 키."""
        return (self.min_separation_m, self.max_altitude_m, self.max_speed_mps)


@dataclass(frozen=True)
class PolicyKPIs:
    """한 정책에서 평가된 핵심 성능 지표 (불변).

    ``conflict_resolution_rate`` 는 [0,1], 나머지는 음이 아닌 값.
    """

    conflict_resolution_rate: float
    collisions: float
    throughput: float
    mean_completion_time_s: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.conflict_resolution_rate <= 1.0:
            raise ValueError(
                f"conflict_resolution_rate 는 [0,1] 이어야 합니다: "
                f"{self.conflict_resolution_rate}"
            )
        for name in ("collisions", "throughput", "mean_completion_time_s"):
            value = getattr(self, name)
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} 는 음이 아닌 유한 값이어야 합니다: {value}")

    def get(self, metric: str) -> float:
        """이름으로 KPI 값을 조회한다."""
        if metric not in _KPI_HIGHER_IS_BETTER:
            raise KeyError(f"알 수 없는 KPI: {metric}")
        return float(getattr(self, metric))


# 방향 표(_KPI_HIGHER_IS_BETTER)와 KPI 필드가 따로 관리되어 조용히 어긋나는 것을
# 막는 가드 — 둘 중 하나만 바꾸면 임포트 시점에 즉시 실패한다.
assert {f.name for f in dataclasses.fields(PolicyKPIs)} == set(_KPI_HIGHER_IS_BETTER), (
    "PolicyKPIs 필드와 _KPI_HIGHER_IS_BETTER 키가 일치해야 합니다"
)


def _improvement(metric: str, baseline: float, candidate: float) -> float:
    """개선 방향으로 부호화한 변화량 (양수 = 더 나음)."""
    delta = candidate - baseline
    return delta if _KPI_HIGHER_IS_BETTER[metric] else -delta


def _pct_delta(baseline: float, candidate: float) -> float:
    """백분율 변화 (변화/기준 × 100). 기준 0 은 부호 있는 무한대/0 으로 규약."""
    if baseline == 0.0:
        if candidate == 0.0:
            return 0.0
        return math.inf if candidate > 0.0 else -math.inf
    return (candidate - baseline) / baseline * 100.0


@dataclass(frozen=True)
class PolicyDelta:
    """기준 정책 대비 한 변형 정책의 KPI 변화 (불변)."""

    policy: RegulatoryPolicy
    kpis: PolicyKPIs
    abs_delta: Mapping[str, float]
    pct_delta: Mapping[str, float]

    def improved(self, metric: str) -> bool:
        """해당 지표가 개선 방향으로 움직였는지."""
        return self.abs_delta[metric] * (
            1.0 if _KPI_HIGHER_IS_BETTER[metric] else -1.0
        ) > 0.0


@dataclass(frozen=True)
class PolicyComparison:
    """기준 정책 + 변형 정책들의 영향 비교 결과 (불변)."""

    baseline: RegulatoryPolicy
    baseline_kpis: PolicyKPIs
    deltas: tuple[PolicyDelta, ...]

    def ranked_by(self, metric: str) -> tuple[PolicyDelta, ...]:
        """한 지표의 개선 정도로 변형 정책을 내림차순 정렬 (동률은 정책 키)."""
        if metric not in _KPI_HIGHER_IS_BETTER:
            raise KeyError(f"알 수 없는 KPI: {metric}")
        baseline_value = self.baseline_kpis.get(metric)
        return tuple(
            sorted(
                self.deltas,
                key=lambda d: (
                    -_improvement(metric, baseline_value, d.kpis.get(metric)),
                    d.policy.signature(),
                ),
            )
        )

    def best_by(self, metric: str) -> PolicyDelta | None:
        """한 지표 기준 가장 개선된 변형 정책 (변형이 없으면 None)."""
        ranked = self.ranked_by(metric)
        return ranked[0] if ranked else None

    def to_markdown(self, objective: str = "conflict_resolution_rate") -> str:
        """기준 대비 영향 비교 자동 리포트 (Markdown)."""
        if objective not in _KPI_HIGHER_IS_BETTER:
            raise KeyError(f"알 수 없는 KPI: {objective}")
        metrics = list(_KPI_HIGHER_IS_BETTER)
        header = "| 정책 (sep/alt/spd) | " + " | ".join(metrics) + " |"
        sep = "|" + "---|" * (len(metrics) + 1)
        lines = [f"# 정책 영향 비교 (목표: {objective})", "", header, sep]

        def _row(label: str, kpis: PolicyKPIs, deltas: Mapping[str, float] | None) -> str:
            cells = []
            for m in metrics:
                if deltas is None:
                    cells.append(f"{kpis.get(m):.3g}")
                elif math.isfinite(deltas[m]):
                    cells.append(f"{kpis.get(m):.3g} ({deltas[m]:+.1f}%)")
                else:
                    # 기준이 0 이라 백분율이 정의되지 않음(예: 충돌 0→양수).
                    cells.append(f"{kpis.get(m):.3g} (신규)")
            return f"| {label} | " + " | ".join(cells) + " |"

        b = self.baseline
        lines.append(
            _row(
                f"기준 {b.min_separation_m:g}/{b.max_altitude_m:g}/{b.max_speed_mps:g}",
                self.baseline_kpis,
                None,
            )
        )
        for d in self.deltas:
            p = d.policy
            lines.append(
                _row(
                    f"{p.min_separation_m:g}/{p.max_altitude_m:g}/{p.max_speed_mps:g}",
                    d.kpis,
                    d.pct_delta,
                )
            )

        best = self.best_by(objective)
        if best is not None:
            p = best.policy
            best_pct = best.pct_delta[objective]
            change = f"{best_pct:+.1f}% vs 기준" if math.isfinite(best_pct) else "신규 vs 기준"
            lines += [
                "",
                f"**{objective} 최적 정책**: "
                f"sep={p.min_separation_m:g} / alt={p.max_altitude_m:g} / "
                f"spd={p.max_speed_mps:g} "
                f"({change})",
            ]
        return "\n".join(lines)


class PolicyImpactAnalyzer:
    """규제 정책 변경 효과를 기준 대비 자동 비교한다.

    ``evaluate`` 는 한 ``RegulatoryPolicy`` 를 ``PolicyKPIs`` 로 사상하는 함수다
    (예: 그 정책으로 Monte Carlo 스윕을 돌려 집계 KPI 반환). 본 클래스는 결정적
    비교·순위·리포트만 책임지며, ``evaluate`` 가 결정적이면 결과도 결정적이다.
    """

    def __init__(
        self,
        baseline: RegulatoryPolicy,
        evaluate: Callable[[RegulatoryPolicy], PolicyKPIs],
    ) -> None:
        self._baseline = baseline
        self._evaluate = evaluate

    def _delta(self, baseline_kpis: PolicyKPIs, policy: RegulatoryPolicy) -> PolicyDelta:
        kpis = self._evaluate(policy)
        # frozen dataclass 의 불변성을 매핑 내용까지 확장 (프로젝트 규칙).
        abs_delta = MappingProxyType(
            {m: kpis.get(m) - baseline_kpis.get(m) for m in _KPI_HIGHER_IS_BETTER}
        )
        pct_delta = MappingProxyType(
            {
                m: _pct_delta(baseline_kpis.get(m), kpis.get(m))
                for m in _KPI_HIGHER_IS_BETTER
            }
        )
        return PolicyDelta(
            policy=policy, kpis=kpis, abs_delta=abs_delta, pct_delta=pct_delta
        )

    def compare(self, variations: Sequence[RegulatoryPolicy]) -> PolicyComparison:
        """기준 정책 대비 변형 정책들의 KPI 영향을 비교한다."""
        baseline_kpis = self._evaluate(self._baseline)
        deltas = tuple(self._delta(baseline_kpis, p) for p in variations)
        return PolicyComparison(
            baseline=self._baseline,
            baseline_kpis=baseline_kpis,
            deltas=deltas,
        )

    def sweep(self, param: str, values: Sequence[float]) -> PolicyComparison:
        """규제 파라미터 하나를 격자값으로 변화시키며 영향을 비교한다.

        기준 정책에서 ``param`` 만 각 값으로 바꾼 변형들을 평가한다. 입력
        순서를 보존하므로 단조 스윕(예: 이격 거리 5→10→15m)의 추세를 그대로
        읽을 수 있다.
        """
        if param not in {f.name for f in dataclasses.fields(RegulatoryPolicy)}:
            raise ValueError(f"알 수 없는 규제 파라미터: {param}")
        variations = [self._baseline.with_changes(**{param: v}) for v in values]
        return self.compare(variations)
