"""Integrated E2E report builder for Phase 172-179.

Aggregates delivery/compliance/recorder/benchmark outputs into one report payload.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from simulation.report_input_normalizer import normalize_report_inputs


class E2EReporter:
    def __init__(self, green_threshold: float = 0.85, yellow_threshold: float = 0.65) -> None:
        if not (0.0 <= yellow_threshold < green_threshold <= 1.0):
            raise ValueError("thresholds must satisfy 0.0 <= yellow < green <= 1.0")
        self._reports: list[dict[str, Any]] = []
        self._green_threshold = float(green_threshold)
        self._yellow_threshold = float(yellow_threshold)

    def tune_status_thresholds(self, green_threshold: float, yellow_threshold: float) -> None:
        if not (0.0 <= yellow_threshold < green_threshold <= 1.0):
            raise ValueError("thresholds must satisfy 0.0 <= yellow < green <= 1.0")
        self._green_threshold = float(green_threshold)
        self._yellow_threshold = float(yellow_threshold)

    def build(
        self,
        delivery_summary: Any,
        compliance_report: Any,
        recorder_summary: Any,
        perf_report: Any,
        traffic_summary: Any | None = None,
        meta: dict[str, Any] | None = None,
        scenario_summary: Any | None = None,
        perf_window_sec: float | None = None,
    ) -> dict[str, Any]:
        normalized = normalize_report_inputs(
            delivery_summary=delivery_summary,
            compliance_report=compliance_report,
            recorder_summary=recorder_summary,
            perf_report=perf_report,
            traffic_summary=traffic_summary,
            meta=meta,
            scenario_summary=scenario_summary,
            perf_window_sec=perf_window_sec,
        )
        scenario = dict(normalized["scenario"])
        delivery = dict(normalized["delivery"])
        compliance = dict(normalized["compliance"])
        recorder = dict(normalized["recorder"])
        performance = dict(normalized["performance"])
        traffic = dict(normalized["traffic"])

        delivered = int(delivery.get("delivered", 0))
        total_violations = int(compliance.get("total_violations", 0))
        success_rate = float(performance.get("success_rate", 1.0))
        events = int(recorder.get("events", 0))
        traffic_pressure = float(traffic.get("avg_congestion", delivery.get("avg_dispatch_congestion", 0.0)))
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
            "meta": self._normalize_meta(normalized["meta"]),
            "delivery": delivery,
            "compliance": compliance,
            "recorder": recorder,
            "performance": performance,
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
        if scenario:
            report["scenario"] = scenario
        report["sections"] = self._section_status(report)
        report["diagnostics"] = self._section_diagnostics(report)
        report["status"] = self._overall_status(report)
        self._reports.append(report)
        return report

    def build_with_observability(
        self,
        delivery_summary: dict[str, Any],
        compliance_report: dict[str, Any],
        recorder: Any,
        benchmark: Any,
        traffic_summary: dict[str, Any] | None = None,
        window_sec: float = 60.0,
        meta: dict[str, Any] | None = None,
        scenario_summary: Any | None = None,
    ) -> dict[str, Any]:
        recorder_summary = dict(recorder.summary())
        perf_report = dict(benchmark.report(window_sec=window_sec))
        next_meta = dict(meta or {})
        next_meta.setdefault("observability_linked", True)
        report = self.build(
            delivery_summary=delivery_summary,
            compliance_report=compliance_report,
            recorder_summary=recorder_summary,
            perf_report=perf_report,
            traffic_summary=traffic_summary,
            meta=next_meta,
            scenario_summary=scenario_summary,
        )
        report["observability"] = {
            "linked": True,
            "window_sec": float(window_sec),
            "events": int(recorder_summary.get("events", 0)),
            "samples": int(perf_report.get("samples", 0)),
        }
        report["sections"]["observability"] = True
        return report

    def render_markdown(self, report: dict[str, Any]) -> str:
        meta = dict(report.get("meta", {}))
        kpi = dict(report.get("kpi", {}))
        diagnostics = dict(report.get("diagnostics", {}))
        status = str(report.get("status", "UNKNOWN"))
        scenario = str(meta.get("scenario", "unspecified"))

        lines = [
            "# SDACS E2E Report",
            "",
            f"- Scenario: `{scenario}`",
            f"- Status: `{status}`",
            f"- Health Score: `{float(kpi.get('health_score', 0.0)):.4f}`",
            f"- Schema: `{meta.get('schema_version', 'unknown')}`",
            f"- Input Contract: `{meta.get('input_contract_version', 'unknown')}`",
            "",
            "## KPI",
            "",
            "| Metric | Value |",
            "|---|---:|",
            f"| Delivered | {int(kpi.get('delivered', 0))} |",
            f"| Violations | {int(kpi.get('violations', 0))} |",
            f"| Success Rate | {float(kpi.get('success_rate', 0.0)):.4f} |",
            f"| Events | {int(kpi.get('events', 0))} |",
            f"| Traffic Pressure | {float(kpi.get('traffic_pressure', 0.0)):.4f} |",
            "",
            "## Diagnostics",
            "",
        ]

        blockers = list(diagnostics.get("blockers", []))
        warnings = list(diagnostics.get("warnings", []))
        lines.append(
            f"- Blockers: {', '.join(f'`{name}`' for name in blockers) if blockers else 'none'}"
        )
        lines.append(
            f"- Warnings: {', '.join(f'`{name}`' for name in warnings) if warnings else 'none'}"
        )
        lines.extend(
            [
                "",
                "## Section Status",
                "",
                "| Section | State |",
                "|---|---|",
            ]
        )

        section_states = diagnostics.get("sections", {})
        for name in sorted(section_states):
            state = str(section_states[name].get("state", "UNKNOWN"))
            lines.append(f"| {name} | `{state}` |")

        return "\n".join(lines) + "\n"

    def export_bundle(
        self,
        report: dict[str, Any],
        output_dir: str | Path = "data/e2e_reports",
        stem: str | None = None,
    ) -> dict[str, str | float]:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        base_stem = self._slugify(stem or self._default_stem(report))
        artifact_stem = self._next_available_stem(out_dir, base_stem)
        json_path = out_dir / f"{artifact_stem}.json"
        markdown_path = out_dir / f"{artifact_stem}.md"
        manifest_path = out_dir / f"{artifact_stem}.manifest.json"

        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump(report, fh, indent=2, ensure_ascii=False)
        with open(markdown_path, "w", encoding="utf-8") as fh:
            fh.write(self.render_markdown(report))

        manifest = {
            "stem": artifact_stem,
            "scenario": report.get("meta", {}).get("scenario"),
            "status": str(report.get("status", "UNKNOWN")),
            "health_score": round(float(report.get("kpi", {}).get("health_score", 0.0)), 4),
            "schema_version": report.get("meta", {}).get("schema_version"),
            "input_contract_version": report.get("meta", {}).get("input_contract_version"),
            "files": {
                "json": json_path.name,
                "markdown": markdown_path.name,
            },
        }
        with open(manifest_path, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2, ensure_ascii=False)

        return {
            "stem": artifact_stem,
            "json_path": str(json_path),
            "markdown_path": str(markdown_path),
            "manifest_path": str(manifest_path),
            "status": manifest["status"],
            "health_score": manifest["health_score"],
        }

    @staticmethod
    def _normalize_meta(meta: dict[str, Any] | None) -> dict[str, Any]:
        out = dict(meta or {})
        out.setdefault("schema_version", "phase172.v1")
        return out

    @staticmethod
    def _slugify(value: str) -> str:
        text = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(value).strip().lower()).strip("-")
        return text or "e2e-report"

    @staticmethod
    def _default_stem(report: dict[str, Any]) -> str:
        meta = dict(report.get("meta", {}))
        scenario = meta.get("scenario")
        if scenario:
            return f"{scenario}-e2e-report"
        status = str(report.get("status", "report")).lower()
        return f"{status}-e2e-report"

    @staticmethod
    def _next_available_stem(output_dir: Path, stem: str) -> str:
        candidate = stem
        idx = 2
        while (
            (output_dir / f"{candidate}.json").exists()
            or (output_dir / f"{candidate}.md").exists()
            or (output_dir / f"{candidate}.manifest.json").exists()
        ):
            candidate = f"{stem}-{idx}"
            idx += 1
        return candidate

    @staticmethod
    def _section_status(report: dict[str, Any]) -> dict[str, bool]:
        return {
            "scenario": bool(report.get("scenario")),
            "delivery": bool(report.get("delivery")),
            "compliance": bool(report.get("compliance")),
            "recorder": bool(report.get("recorder")),
            "performance": bool(report.get("performance")),
            "traffic": bool(report.get("traffic")),
            "kpi": bool(report.get("kpi")),
            "observability": bool(report.get("observability")),
        }

    def _overall_status(self, report: dict[str, Any]) -> str:
        kpi = report.get("kpi", {})
        health = float(kpi.get("health_score", 0.0))
        if health >= self._green_threshold:
            return "GREEN"
        if health >= self._yellow_threshold:
            return "YELLOW"
        return "RED"

    @staticmethod
    def _section_diagnostics(report: dict[str, Any]) -> dict[str, Any]:
        scenario = report.get("scenario", {})
        delivery = report.get("delivery", {})
        compliance = report.get("compliance", {})
        recorder = report.get("recorder", {})
        performance = report.get("performance", {})
        traffic = report.get("traffic", {})

        dispatches = int(delivery.get("dispatches", 0))
        delivered = int(delivery.get("delivered", 0))
        delivery_state = "GREEN" if dispatches >= delivered else "RED"

        total_violations = int(compliance.get("total_violations", 0))
        if total_violations == 0:
            compliance_state = "GREEN"
        elif total_violations <= 3:
            compliance_state = "YELLOW"
        else:
            compliance_state = "RED"

        events = int(recorder.get("events", 0))
        recorder_state = "GREEN" if events >= 2 else ("YELLOW" if events == 1 else "RED")

        success_rate = float(performance.get("success_rate", 0.0))
        if success_rate >= 0.95:
            perf_state = "GREEN"
        elif success_rate >= 0.80:
            perf_state = "YELLOW"
        else:
            perf_state = "RED"

        congestion = float(traffic.get("avg_congestion", 0.0))
        traffic_state = "GREEN" if congestion < 0.5 else ("YELLOW" if congestion < 0.8 else "RED")

        sections: dict[str, dict[str, Any]] = {}
        if scenario:
            collision_count = int(scenario.get("collision_count", 0))
            scenario_state = "RED" if scenario.get("error") or collision_count > 0 else "GREEN"
            sections["scenario"] = {
                "state": scenario_state,
                "collision_count": collision_count,
                "seed": scenario.get("seed"),
            }
        sections["delivery"] = {"state": delivery_state, "dispatches": dispatches, "delivered": delivered}
        sections["compliance"] = {"state": compliance_state, "violations": total_violations}
        sections["recorder"] = {"state": recorder_state, "events": events}
        sections["performance"] = {"state": perf_state, "success_rate": round(success_rate, 4)}
        sections["traffic"] = {"state": traffic_state, "avg_congestion": round(congestion, 4)}

        blockers = [name for name, info in sections.items() if info["state"] == "RED"]
        warnings = [name for name, info in sections.items() if info["state"] == "YELLOW"]
        return {
            "sections": sections,
            "blockers": blockers,
            "warnings": warnings,
        }

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
            "thresholds": {
                "green": round(self._green_threshold, 4),
                "yellow": round(self._yellow_threshold, 4),
            },
            "avg_blockers": round(
                sum(len(r.get("diagnostics", {}).get("blockers", [])) for r in self._reports)
                / len(self._reports),
                4,
            ),
        }

    def clear(self) -> None:
        self._reports.clear()
