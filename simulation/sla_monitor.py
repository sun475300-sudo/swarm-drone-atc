"""
SLA 자동 위반 감지 + 자가 튜닝
================================
실시간으로 SLA 지표를 모니터링하고
위반 감지 시 경보 발생 + 파라미터 자동 조정.

사용법:
    monitor = SLAMonitor()
    violations = monitor.check(collision_count=5, resolution_rate=98.0, ...)
    adjustments = monitor.auto_tune(violations)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SLAThreshold:
    """SLA 임계치 정의"""
    name: str
    metric: str
    max_value: float | None = None
    min_value: float | None = None
    severity: str = "WARNING"  # WARNING, CRITICAL


@dataclass
class SLAViolation:
    """SLA 위반 이벤트"""
    threshold_name: str
    metric: str
    actual_value: float
    limit_value: float
    severity: str
    message: str


DEFAULT_THRESHOLDS: list[SLAThreshold] = [
    SLAThreshold("충돌률", "collision_count", max_value=0, severity="CRITICAL"),
    SLAThreshold("해결률", "conflict_resolution_rate_pct", min_value=99.5, severity="CRITICAL"),
    SLAThreshold("경로효율", "route_efficiency_mean", max_value=1.15, severity="WARNING"),
    SLAThreshold("지연P50", "advisory_latency_p50", max_value=2.0, severity="WARNING"),
    SLAThreshold("지연P99", "advisory_latency_p99", max_value=10.0, severity="CRITICAL"),
    SLAThreshold("통신드롭률", "comm_drop_rate", max_value=0.05, severity="WARNING"),
    SLAThreshold("근접경고", "near_miss_count", max_value=10, severity="WARNING"),
]


class SLAMonitor:
    """
    SLA 실시간 모니터.

    매 체크 주기마다 현재 메트릭을 SLA 임계치와 비교하고
    위반 이벤트를 기록한다.
    """

    def __init__(
        self,
        thresholds: list[SLAThreshold] | None = None,
    ) -> None:
        self.thresholds = thresholds or list(DEFAULT_THRESHOLDS)
        self._history: list[list[SLAViolation]] = []
        self._tune_history: list[dict] = []

    def check(self, **metrics: float) -> list[SLAViolation]:
        """
        현재 메트릭으로 SLA 위반 검사.

        Parameters
        ----------
        **metrics : 메트릭 이름=값 쌍

        Returns
        -------
        위반 목록
        """
        violations = []

        for th in self.thresholds:
            val = metrics.get(th.metric)
            if val is None:
                continue

            if th.max_value is not None and val > th.max_value:
                violations.append(SLAViolation(
                    threshold_name=th.name,
                    metric=th.metric,
                    actual_value=val,
                    limit_value=th.max_value,
                    severity=th.severity,
                    message=f"{th.name}: {val:.4f} > {th.max_value} ({th.severity})",
                ))

            if th.min_value is not None and val < th.min_value:
                violations.append(SLAViolation(
                    threshold_name=th.name,
                    metric=th.metric,
                    actual_value=val,
                    limit_value=th.min_value,
                    severity=th.severity,
                    message=f"{th.name}: {val:.4f} < {th.min_value} ({th.severity})",
                ))

        self._history.append(violations)
        return violations

    def auto_tune(self, violations: list[SLAViolation]) -> dict[str, Any]:
        """
        SLA 위반에 따른 자동 파라미터 조정 제안.

        Returns
        -------
        조정 딕셔너리 {param_name: new_value}
        """
        adjustments: dict[str, Any] = {}

        for v in violations:
            if v.metric == "collision_count" and v.actual_value > 0:
                # 충돌 발생 → APF 척력 증가
                adjustments["apf_k_rep_increase"] = 1.5
                adjustments["separation_multiplier"] = 1.2

            elif v.metric == "conflict_resolution_rate_pct":
                # 해결률 낮음 → 스캔 주기 단축
                adjustments["scan_interval_reduction"] = 0.5
                adjustments["apf_d0_increase"] = 1.3

            elif v.metric == "advisory_latency_p99":
                # 지연 높음 → 스캔 반경 축소
                adjustments["scan_radius_reduction"] = 0.8

            elif v.metric == "comm_drop_rate":
                # 통신 드롭 높음 → 재전송 횟수 증가
                adjustments["comm_retry_increase"] = 2

        if adjustments:
            self._tune_history.append(adjustments)

        return adjustments

    def violation_count(self, severity: str | None = None) -> int:
        """누적 위반 수"""
        total = 0
        for vlist in self._history:
            for v in vlist:
                if severity is None or v.severity == severity:
                    total += 1
        return total

    def latest_violations(self) -> list[SLAViolation]:
        """가장 최근 위반 목록"""
        return self._history[-1] if self._history else []

    def tune_history(self) -> list[dict]:
        """자동 튜닝 이력"""
        return list(self._tune_history)

    def add_threshold(self, threshold: SLAThreshold) -> None:
        """SLA 임계치 추가"""
        self.thresholds.append(threshold)

    def reset(self) -> None:
        """이력 초기화"""
        self._history.clear()
        self._tune_history.clear()
