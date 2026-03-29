"""
Health checker infrastructure.
==============================
Tracks module heartbeats, latency, and error budget for system readiness checks.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import time


@dataclass
class ModuleHealth:
    module_id: str
    last_heartbeat: float
    total_requests: int = 0
    total_errors: int = 0
    avg_latency_ms: float = 0.0


class HealthChecker:
    def __init__(self, stale_after_sec: float = 5.0) -> None:
        self.stale_after_sec = max(0.05, float(stale_after_sec))
        self._modules: dict[str, ModuleHealth] = {}

    def _now(self) -> float:
        return time.monotonic()

    def heartbeat(self, module_id: str) -> None:
        now = self._now()
        if module_id not in self._modules:
            self._modules[module_id] = ModuleHealth(module_id=module_id, last_heartbeat=now)
            return
        self._modules[module_id].last_heartbeat = now

    def report(self, module_id: str, latency_ms: float, success: bool = True) -> None:
        self.heartbeat(module_id)
        m = self._modules[module_id]
        m.total_requests += 1
        if not success:
            m.total_errors += 1
        alpha = 0.2
        if m.total_requests == 1:
            m.avg_latency_ms = float(latency_ms)
        else:
            m.avg_latency_ms = (1 - alpha) * m.avg_latency_ms + alpha * float(latency_ms)

    def status(self, module_id: str) -> dict[str, Any]:
        m = self._modules.get(module_id)
        if m is None:
            return {"module_id": module_id, "status": "UNKNOWN"}
        age = self._now() - m.last_heartbeat
        err_rate = (m.total_errors / m.total_requests) if m.total_requests else 0.0
        if age > self.stale_after_sec:
            status = "STALE"
        elif err_rate > 0.2:
            status = "DEGRADED"
        else:
            status = "HEALTHY"
        return {
            "module_id": module_id,
            "status": status,
            "age_sec": round(age, 3),
            "error_rate": round(err_rate, 4),
            "avg_latency_ms": round(m.avg_latency_ms, 3),
        }

    def overall(self) -> dict[str, Any]:
        items = [self.status(mid) for mid in self._modules]
        counts = {"HEALTHY": 0, "DEGRADED": 0, "STALE": 0, "UNKNOWN": 0}
        for it in items:
            counts[it["status"]] = counts.get(it["status"], 0) + 1
        return {
            "modules": len(items),
            "counts": counts,
            "details": items,
        }

    def summary(self) -> dict[str, Any]:
        o = self.overall()
        return {
            "modules": o["modules"],
            "healthy": o["counts"].get("HEALTHY", 0),
            "degraded": o["counts"].get("DEGRADED", 0),
            "stale": o["counts"].get("STALE", 0),
        }
