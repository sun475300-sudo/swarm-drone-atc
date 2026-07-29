"""
실시간 대시보드 데이터
=====================
대시보드 데이터 제공 + KPI 집계 + 경보 피드.

사용법:
    dd = DashboardData()
    dd.update_kpi("collision_rate", 0.02)
    snapshot = dd.snapshot()
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Alert:
    """경보"""
    alert_id: str
    level: str  # INFO, WARNING, CRITICAL
    message: str
    t: float = 0.0
    source: str = ""


class DashboardData:
    """대시보드 데이터 관리."""

    def __init__(self) -> None:
        """인스턴스를 초기화한다."""
        self._kpis: dict[str, float] = {}
        self._alerts: list[Alert] = []
        self._drone_count = 0
        self._active_missions = 0
        self._counter = 0
        self._history: dict[str, list[tuple[float, float]]] = {}

    def update_kpi(self, name: str, value: float, t: float = 0.0) -> None:
        """`kpi` 상태를 갱신한다."""
        self._kpis[name] = value
        if name not in self._history:
            self._history[name] = []
        self._history[name].append((t, value))
        if len(self._history[name]) > 200:
            self._history[name] = self._history[name][-200:]

    def set_counts(self, drones: int = 0, missions: int = 0) -> None:
        """`counts` 상태를 갱신한다."""
        self._drone_count = drones
        self._active_missions = missions

    def add_alert(
        self, level: str, message: str, t: float = 0.0, source: str = "",
    ) -> Alert:
        """`alert` 항목을 추가한다."""
        self._counter += 1
        alert = Alert(
            alert_id=f"A{self._counter:05d}",
            level=level, message=message, t=t, source=source,
        )
        self._alerts.append(alert)
        if len(self._alerts) > 500:
            self._alerts = self._alerts[-500:]
        return alert

    def recent_alerts(self, n: int = 10, level: str | None = None) -> list[Alert]:
        """``recent_alerts`` 동작을 수행한다."""
        filtered = self._alerts
        if level:
            filtered = [a for a in filtered if a.level == level]
        return filtered[-n:]

    def kpi_trend(self, name: str, n: int = 20) -> list[tuple[float, float]]:
        """``kpi_trend`` 동작을 수행한다."""
        return self._history.get(name, [])[-n:]

    def snapshot(self) -> dict[str, Any]:
        """``snapshot`` 동작을 수행한다."""
        return {
            "kpis": dict(self._kpis),
            "drone_count": self._drone_count,
            "active_missions": self._active_missions,
            "alert_count": len(self._alerts),
            "critical_alerts": sum(1 for a in self._alerts if a.level == "CRITICAL"),
        }

    def clear_alerts(self) -> None:
        """`alerts` 상태를 정리한다."""
        self._alerts.clear()

    def summary(self) -> dict[str, Any]:
        """현재 상태 요약을 반환한다."""
        return self.snapshot()
