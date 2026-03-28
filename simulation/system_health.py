"""
시스템 상태 모니터
==================
전체 시스템 건강 지표 + 알림 + 자가 진단.

사용법:
    sh = SystemHealth()
    sh.update("cpu_usage", 45.0)
    sh.update("memory_pct", 72.0)
    status = sh.diagnose()
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class HealthCheck:
    """건강 점검 결과"""
    component: str
    status: str  # OK, WARNING, CRITICAL
    value: float
    threshold: float
    message: str


class SystemHealth:
    """시스템 건강 모니터."""

    DEFAULT_THRESHOLDS = {
        "cpu_usage": (70.0, 90.0),       # warning, critical
        "memory_pct": (75.0, 90.0),
        "tick_time_ms": (50.0, 100.0),
        "collision_rate": (0.01, 0.05),
        "comm_loss_rate": (0.05, 0.15),
        "battery_min_pct": (20.0, 10.0),  # reversed: below is bad
    }

    def __init__(self) -> None:
        self._metrics: dict[str, float] = {}
        self._thresholds: dict[str, tuple[float, float]] = dict(self.DEFAULT_THRESHOLDS)
        self._alerts: list[dict[str, Any]] = []

    def update(self, metric: str, value: float) -> None:
        self._metrics[metric] = value

    def set_threshold(self, metric: str, warning: float, critical: float) -> None:
        self._thresholds[metric] = (warning, critical)

    def check(self, metric: str) -> HealthCheck:
        value = self._metrics.get(metric, 0)
        thresholds = self._thresholds.get(metric)

        if not thresholds:
            return HealthCheck(metric, "OK", value, 0, "임계치 미설정")

        warn, crit = thresholds

        # battery_min_pct는 역방향 (낮을수록 나쁨)
        if metric == "battery_min_pct":
            if value <= crit:
                status = "CRITICAL"
                msg = f"{metric}={value:.1f} ≤ {crit}"
            elif value <= warn:
                status = "WARNING"
                msg = f"{metric}={value:.1f} ≤ {warn}"
            else:
                status = "OK"
                msg = f"{metric}={value:.1f} 정상"
        else:
            if value >= crit:
                status = "CRITICAL"
                msg = f"{metric}={value:.1f} ≥ {crit}"
            elif value >= warn:
                status = "WARNING"
                msg = f"{metric}={value:.1f} ≥ {warn}"
            else:
                status = "OK"
                msg = f"{metric}={value:.1f} 정상"

        return HealthCheck(metric, status, value, warn, msg)

    def diagnose(self) -> list[HealthCheck]:
        """전체 자가 진단"""
        checks = []
        for metric in self._metrics:
            check = self.check(metric)
            checks.append(check)
            if check.status != "OK":
                self._alerts.append({
                    "metric": metric,
                    "status": check.status,
                    "value": check.value,
                    "message": check.message,
                })
        return checks

    def overall_status(self) -> str:
        """전체 상태"""
        checks = self.diagnose()
        if any(c.status == "CRITICAL" for c in checks):
            return "CRITICAL"
        if any(c.status == "WARNING" for c in checks):
            return "WARNING"
        return "OK"

    def is_healthy(self) -> bool:
        return self.overall_status() == "OK"

    def recent_alerts(self, n: int = 20) -> list[dict[str, Any]]:
        return self._alerts[-n:]

    def summary(self) -> dict[str, Any]:
        checks = self.diagnose()
        return {
            "overall": self.overall_status(),
            "metrics_count": len(self._metrics),
            "ok": sum(1 for c in checks if c.status == "OK"),
            "warnings": sum(1 for c in checks if c.status == "WARNING"),
            "criticals": sum(1 for c in checks if c.status == "CRITICAL"),
        }
