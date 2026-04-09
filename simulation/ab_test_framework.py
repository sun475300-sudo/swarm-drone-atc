"""
A/B 테스트 프레임워크
===================
알고리즘 변경 전후 비교 + 통계 유의성 검정.

사용법:
    ab = ABTestFramework()
    ab.record_control("collision_rate", [0.02, 0.03, 0.01])
    ab.record_treatment("collision_rate", [0.01, 0.01, 0.005])
    result = ab.analyze("collision_rate")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class ABResult:
    """A/B 테스트 결과"""
    metric: str
    control_mean: float
    treatment_mean: float
    improvement_pct: float
    p_value: float
    significant: bool
    recommendation: str


class ABTestFramework:
    """A/B 테스트."""

    def __init__(self, significance_level: float = 0.05) -> None:
        self.significance_level = significance_level
        self._control: dict[str, list[float]] = {}
        self._treatment: dict[str, list[float]] = {}
        self._results: list[ABResult] = []

    def record_control(self, metric: str, values: list[float]) -> None:
        if metric not in self._control:
            self._control[metric] = []
        self._control[metric].extend(values)

    def record_treatment(self, metric: str, values: list[float]) -> None:
        if metric not in self._treatment:
            self._treatment[metric] = []
        self._treatment[metric].extend(values)

    def _welch_t_test(self, a: list[float], b: list[float]) -> float:
        """Welch's t-test p-value 근사"""
        n1, n2 = len(a), len(b)
        if n1 < 2 or n2 < 2:
            return 1.0
        m1, m2 = np.mean(a), np.mean(b)
        v1, v2 = np.var(a, ddof=1), np.var(b, ddof=1)
        se = np.sqrt(v1 / n1 + v2 / n2)
        if se < 1e-10:
            return 0.0 if abs(m1 - m2) > 1e-10 else 1.0
        t_stat = abs(m1 - m2) / se
        # 대략적 p-value (정규 근사)
        p = float(np.exp(-0.717 * t_stat - 0.416 * t_stat ** 2))
        return min(1.0, p)

    def analyze(self, metric: str) -> ABResult:
        control = self._control.get(metric, [])
        treatment = self._treatment.get(metric, [])

        if not control or not treatment:
            return ABResult(metric, 0, 0, 0, 1.0, False, "데이터 부족")

        c_mean = float(np.mean(control))
        t_mean = float(np.mean(treatment))

        if c_mean != 0:
            improvement = (c_mean - t_mean) / abs(c_mean) * 100
        else:
            improvement = 0.0

        p_value = self._welch_t_test(control, treatment)
        significant = p_value < self.significance_level

        if significant and improvement > 0:
            rec = f"Treatment 채택 권장 ({improvement:.1f}% 개선)"
        elif significant and improvement < 0:
            rec = f"Treatment 거부 ({abs(improvement):.1f}% 악화)"
        else:
            rec = "통계적 유의성 없음 — 추가 데이터 수집"

        result = ABResult(
            metric=metric, control_mean=round(c_mean, 4),
            treatment_mean=round(t_mean, 4),
            improvement_pct=round(improvement, 2),
            p_value=round(p_value, 4),
            significant=significant, recommendation=rec,
        )
        self._results.append(result)
        return result

    def analyze_all(self) -> list[ABResult]:
        metrics = set(self._control.keys()) | set(self._treatment.keys())
        return [self.analyze(m) for m in sorted(metrics)]

    def summary(self) -> dict[str, Any]:
        return {
            "metrics": len(set(self._control.keys()) | set(self._treatment.keys())),
            "results": len(self._results),
            "significant_improvements": sum(1 for r in self._results if r.significant and r.improvement_pct > 0),
        }
