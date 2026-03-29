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
        traffic_summary: dict[str, Any] | None = None,
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        delivered = int(delivery_summary.get("delivered", 0))
        total_violations = int(compliance_report.get("total_violations", 0))
        success_rate = float(perf_report.get("success_rate", 1.0))
        events = int(recorder_summary.get("events", 0))
        traffic = dict(traffic_summary or {})
        traffic_pressure = float(traffic.get("avg_congestion", delivery_summary.get("avg_dispatch_congestion", 0.0)))
        traffic_penalty = min(0.12, max(0.0, traffic_pressure) * 0.12)
        health_score = max(
            0.0,
            min(
                1.0,
                (success_rate * 0.55)
                + (0.35 if total_violations == 0 else max(0.0, 0.35 - (0.05 * total_violations)))
                + (0.10 if delivered > 0 else 0.0)
                - traffic_penalty,
            ),
        )

        report = {
            "meta": self._normalize_meta(meta),
            "delivery": dict(delivery_summary),
            "compliance": dict(compliance_report),
            "recorder": dict(recorder_summary),
            "performance": dict(perf_report),
            "traffic": traffic,
            "kpi": {
                "health_score": round(health_score, 4),
                "delivered": delivered,
                "violations": total_violations,
                "success_rate": round(success_rate, 4),
                "events": events,
                "traffic_pressure": round(traffic_pressure, 4),
            },
        }
        report["sections"] = self._section_status(report)
        report["status"] = self._overall_status(report)
        self._reports.append(report)
        return report

    @staticmethod
    def _normalize_meta(meta: dict[str, Any] | None) -> dict[str, Any]:
        out = dict(meta or {})
        out.setdefault("schema_version", "phase172.v1")
        return out

    @staticmethod
    def _section_status(report: dict[str, Any]) -> dict[str, bool]:
        return {
            "delivery": bool(report.get("delivery")),
            "compliance": bool(report.get("compliance")),
            "recorder": bool(report.get("recorder")),
            "performance": bool(report.get("performance")),
            "traffic": bool(report.get("traffic")),
            "kpi": bool(report.get("kpi")),
        }

    @staticmethod
    def _overall_status(report: dict[str, Any]) -> str:
        kpi = report.get("kpi", {})
        health = float(kpi.get("health_score", 0.0))
        if health >= 0.85:
            return "GREEN"
        if health >= 0.65:
            return "YELLOW"
        return "RED"

    def history(self) -> list[dict[str, Any]]:
        return list(self._reports)

    def summary(self) -> dict[str, Any]:
        if not self._reports:
            return {"reports": 0, "avg_health_score": 0.0}
        avg = sum(float(r["kpi"]["health_score"]) for r in self._reports) / len(self._reports)
        status_counts: dict[str, int] = {}
        for r in self._reports:
            s = str(r.get("status", "UNKNOWN"))
            status_counts[s] = status_counts.get(s, 0) + 1
        return {
            "reports": len(self._reports),
            "avg_health_score": round(avg, 4),
            "status_counts": status_counts,
        }

    def clear(self) -> None:
        self._reports.clear()