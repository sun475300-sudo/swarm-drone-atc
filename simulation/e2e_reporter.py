"""Integrated E2E report builder for Phase 172-179.

Aggregates delivery/compliance/recorder/benchmark outputs into one report payload.
"""
from __future__ import annotations

from typing import Any


class E2EReporter:
    def __init__(self) -> None:
        self._reports: list[dict[str, Any]] = []

    def build(
        self,
        delivery_summary: dict[str, Any],
        compliance_report: dict[str, Any],
        recorder_summary: dict[str, Any],
        perf_report: dict[str, Any],
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        delivered = int(delivery_summary.get("delivered", 0))
        total_violations = int(compliance_report.get("total_violations", 0))
        success_rate = float(perf_report.get("success_rate", 1.0))
        events = int(recorder_summary.get("events", 0))
        health_score = max(
            0.0,
            min(
                1.0,
                (success_rate * 0.55)
                + (0.35 if total_violations == 0 else max(0.0, 0.35 - (0.05 * total_violations)))
                + (0.10 if delivered > 0 else 0.0),
            ),
        )

        report = {
            "meta": dict(meta or {}),
            "delivery": dict(delivery_summary),
            "compliance": dict(compliance_report),
            "recorder": dict(recorder_summary),
            "performance": dict(perf_report),
            "kpi": {
                "health_score": round(health_score, 4),
                "delivered": delivered,
                "violations": total_violations,
                "success_rate": round(success_rate, 4),
                "events": events,
            },
        }
        self._reports.append(report)
        return report

    def history(self) -> list[dict[str, Any]]:
        return list(self._reports)

    def summary(self) -> dict[str, Any]:
        if not self._reports:
            return {"reports": 0, "avg_health_score": 0.0}
        avg = sum(float(r["kpi"]["health_score"]) for r in self._reports) / len(self._reports)
        return {
            "reports": len(self._reports),
            "avg_health_score": round(avg, 4),
        }

    def clear(self) -> None:
        self._reports.clear()