"""
시스템 대시보드 통합
===================
전체 모듈 통합 KPI + 실시간 상태 보드.

사용법:
    sd = SystemDashboard()
    sd.register_module("apf", status="OK")
    sd.update_kpi("collision_rate", 0.001)
    board = sd.get_board()
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import numpy as np


@dataclass
class ModuleStatus:
    name: str
    status: str = "OK"  # OK, WARNING, ERROR, OFFLINE
    last_update: float = 0.0
    metrics: dict[str, float] = field(default_factory=dict)


class SystemDashboard:
    def __init__(self) -> None:
        self._modules: dict[str, ModuleStatus] = {}
        self._kpis: dict[str, list[float]] = {}
        self._alerts: list[dict[str, Any]] = []

    def register_module(self, name: str, status: str = "OK") -> None:
        self._modules[name] = ModuleStatus(name=name, status=status)

    def update_module_status(self, name: str, status: str, t: float = 0.0) -> None:
        m = self._modules.get(name)
        if m:
            m.status = status
            m.last_update = t
            if status in ("ERROR", "OFFLINE"):
                self._alerts.append({"module": name, "status": status, "t": t})

    def update_kpi(self, name: str, value: float) -> None:
        if name not in self._kpis:
            self._kpis[name] = []
        self._kpis[name].append(value)
        if len(self._kpis[name]) > 500:
            self._kpis[name] = self._kpis[name][-500:]

    def get_kpi(self, name: str) -> float:
        vals = self._kpis.get(name, [])
        return round(float(np.mean(vals)), 4) if vals else 0

    def get_board(self) -> dict[str, Any]:
        return {
            "modules": {
                name: {"status": m.status, "last_update": m.last_update}
                for name, m in self._modules.items()
            },
            "kpis": {name: self.get_kpi(name) for name in self._kpis},
            "overall_health": self._overall_health(),
            "recent_alerts": self._alerts[-10:],
        }

    def _overall_health(self) -> str:
        statuses = [m.status for m in self._modules.values()]
        if any(s == "ERROR" for s in statuses):
            return "CRITICAL"
        if any(s in ("WARNING", "OFFLINE") for s in statuses):
            return "WARNING"
        return "OK"

    def healthy_modules(self) -> int:
        return sum(1 for m in self._modules.values() if m.status == "OK")

    def summary(self) -> dict[str, Any]:
        return {
            "modules": len(self._modules),
            "healthy": self.healthy_modules(),
            "kpis": len(self._kpis),
            "alerts": len(self._alerts),
            "overall": self._overall_health(),
        }
