"""Shared input normalization for ops report pipelines.

Phase 180 starts standardizing mixed scenario/delivery/compliance/benchmark
outputs into one report contract so bundle generation can consume a stable
shape regardless of source object or alias keys.
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any


INPUT_CONTRACT_VERSION = "phase180.report_inputs.v1"


def normalize_report_inputs(
    *,
    delivery_summary: Any,
    compliance_report: Any,
    recorder_summary: Any,
    perf_report: Any,
    traffic_summary: Any | None = None,
    meta: dict[str, Any] | None = None,
    scenario_summary: Any | None = None,
    perf_window_sec: float | None = None,
) -> dict[str, dict[str, Any]]:
    scenario = normalize_scenario(scenario_summary)
    delivery = normalize_delivery(delivery_summary)
    compliance = normalize_compliance(compliance_report)
    recorder = normalize_recorder(recorder_summary)
    performance = normalize_performance(perf_report, window_sec=perf_window_sec)
    traffic = normalize_traffic(traffic_summary)
    return {
        "meta": normalize_meta(meta, scenario=scenario),
        "scenario": scenario,
        "delivery": delivery,
        "compliance": compliance,
        "recorder": recorder,
        "performance": performance,
        "traffic": traffic,
    }


def normalize_meta(meta: dict[str, Any] | None, scenario: dict[str, Any] | None = None) -> dict[str, Any]:
    out = dict(meta or {})
    scenario = dict(scenario or {})
    if scenario:
        _setdefault_present(out, "scenario", scenario.get("scenario"))
        _setdefault_present(out, "seed", scenario.get("seed"))
        _setdefault_present(out, "run_idx", scenario.get("run_idx"))
        _setdefault_present(out, "duration_s", scenario.get("duration_s"))
        _setdefault_present(out, "n_drones", scenario.get("n_drones"))
        _setdefault_present(out, "scenario_source", scenario.get("source"))
    out.setdefault("schema_version", "phase172.v1")
    out.setdefault("input_contract_version", INPUT_CONTRACT_VERSION)
    return out


def normalize_scenario(value: Any) -> dict[str, Any]:
    raw = _coerce_mapping(value)
    if not raw:
        return {}
    scenario_name = _pick(raw, "scenario", "name")
    if scenario_name is None:
        return {}
    out = {
        "scenario": str(scenario_name),
        "seed": _to_int(_pick(raw, "seed")),
        "run_idx": _to_int(_pick(raw, "run_idx")),
        "duration_s": _to_float(_pick(raw, "duration_s", "duration_sec")),
        "n_drones": _to_int(_pick(raw, "n_drones", "drones")),
        "collision_count": _to_int(_pick(raw, "collision_count")),
        "near_miss_count": _to_int(_pick(raw, "near_miss_count")),
        "conflict_resolution_rate_pct": _to_float(
            _pick(raw, "conflict_resolution_rate_pct", "resolve_rate_pct")
        ),
        "route_efficiency_mean": _to_float(_pick(raw, "route_efficiency_mean")),
        "source": str(_pick(raw, "source")) if _pick(raw, "source") is not None else "normalized_input",
    }
    error = _pick(raw, "error")
    if error:
        out["error"] = str(error)
    return {key: value for key, value in out.items() if value is not None}


def normalize_delivery(value: Any) -> dict[str, Any]:
    raw = _coerce_mapping(value)
    if not raw and hasattr(value, "summary"):
        raw = _coerce_mapping(value.summary())
    if not raw:
        return {}
    return {
        "drones": _to_int(_pick(raw, "drones"), default=0),
        "pending_orders": _to_int(_pick(raw, "pending_orders", "pending", "open_orders"), default=0),
        "dispatches": _to_int(_pick(raw, "dispatches", "dispatch_count", "assignments"), default=0),
        "delivered": _to_int(
            _pick(raw, "delivered", "orders_delivered", "deliveries_completed", "completed_deliveries"),
            default=0,
        ),
        "busy_drones": _to_int(_pick(raw, "busy_drones"), default=0),
        "reserved_slots": _to_int(_pick(raw, "reserved_slots"), default=0),
        "avg_dispatch_congestion": round(
            _to_float(_pick(raw, "avg_dispatch_congestion", "avg_congestion", "traffic_pressure"), default=0.0),
            4,
        ),
        "avg_dispatch_demand": round(
            _to_float(_pick(raw, "avg_dispatch_demand", "avg_demand", "traffic_demand"), default=0.0),
            2,
        ),
        "slot_policy": _coerce_mapping(_pick(raw, "slot_policy", "policy")),
    }


def normalize_compliance(value: Any) -> dict[str, Any]:
    raw: dict[str, Any] = {}
    if hasattr(value, "violation_report"):
        raw.update(_coerce_mapping(value.violation_report()))
    if hasattr(value, "summary"):
        summary = _coerce_mapping(value.summary())
        for key, val in summary.items():
            raw.setdefault(key, val)
    if not raw:
        raw = _coerce_mapping(value)
    if not raw:
        return {}

    violations = raw.get("violations")
    derived_by_rule, derived_by_severity = _derive_violation_maps(violations)
    by_rule = _normalize_count_map(raw.get("by_rule")) or derived_by_rule
    by_severity = _normalize_count_map(raw.get("by_severity")) or derived_by_severity
    total_violations = _to_int(_pick(raw, "total_violations", "violations_total"), default=None)
    if total_violations is None:
        total_violations = sum(by_rule.values()) if by_rule else len(violations or [])
    hotspots = _normalize_hotspots(raw.get("hotspots"), by_rule=by_rule, by_severity=by_severity)
    return {
        "total_violations": int(total_violations),
        "by_severity": by_severity,
        "by_rule": by_rule,
        "hotspots": hotspots,
        "evaluations": _to_int(_pick(raw, "evaluations"), default=0),
    }


def normalize_recorder(value: Any) -> dict[str, Any]:
    if isinstance(value, list):
        by_type: dict[str, int] = {}
        duration = 0.0
        for row in value:
            event = _coerce_mapping(row)
            event_type = str(_pick(event, "event_type", "type") or "UNKNOWN")
            by_type[event_type] = by_type.get(event_type, 0) + 1
            duration = max(duration, _to_float(_pick(event, "t_sec", "time_sec"), default=0.0))
        return {
            "events": len(value),
            "duration_sec": round(duration, 3),
            "by_type": by_type,
        }

    raw = _coerce_mapping(value)
    if not raw and hasattr(value, "summary"):
        raw = _coerce_mapping(value.summary())
    if not raw:
        return {}
    return {
        "events": _to_int(_pick(raw, "events", "count", "total_events"), default=0),
        "duration_sec": round(_to_float(_pick(raw, "duration_sec", "duration_s"), default=0.0), 3),
        "by_type": _normalize_count_map(_pick(raw, "by_type", "events_by_type")),
    }


def normalize_performance(value: Any, window_sec: float | None = None) -> dict[str, Any]:
    raw = {}
    if hasattr(value, "report"):
        if window_sec is None:
            raw = _coerce_mapping(value.report())
        else:
            raw = _coerce_mapping(value.report(window_sec=float(window_sec)))
    if not raw:
        raw = _coerce_mapping(value)
    if not raw:
        return {}

    samples = _to_int(_pick(raw, "samples", "count", "iterations"), default=0)
    success_rate = _normalize_success_rate(raw, samples=samples)
    return {
        "samples": samples,
        "avg_ms": round(_to_float(_pick(raw, "avg_ms", "mean_ms", "latency_ms_avg"), default=0.0), 3),
        "p50_ms": round(_to_float(_pick(raw, "p50_ms", "latency_ms_p50"), default=0.0), 3),
        "p95_ms": round(_to_float(_pick(raw, "p95_ms", "latency_ms_p95", "latency_p95_ms"), default=0.0), 3),
        "p99_ms": round(_to_float(_pick(raw, "p99_ms", "latency_ms_p99"), default=0.0), 3),
        "throughput_rps": round(
            _to_float(_pick(raw, "throughput_rps", "throughput", "throughput_ops_s"), default=0.0),
            3,
        ),
        "success_rate": round(success_rate, 4),
    }


def normalize_traffic(value: Any) -> dict[str, Any]:
    raw = _coerce_mapping(value)
    if not raw and hasattr(value, "summary"):
        raw = _coerce_mapping(value.summary())
    if not raw:
        return {}
    avg_congestion = _pick(raw, "avg_congestion", "congestion", "traffic_pressure")
    avg_demand = _pick(raw, "avg_demand", "demand")
    peak_hour = _pick(raw, "peak_hour", "hour", "peak")
    states = _pick(raw, "states")
    if states is None and avg_demand is not None:
        states = 1
    return {
        "states": _to_int(states, default=0),
        "avg_demand": round(_to_float(avg_demand, default=0.0), 2),
        "avg_congestion": round(_to_float(avg_congestion, default=0.0), 4),
        "peak_hour": _to_int(peak_hour, default=None),
        "incident_probability": round(
            _to_float(_pick(raw, "incident_probability", "p_incident"), default=0.0),
            4,
        ),
    }


def _normalize_success_rate(raw: dict[str, Any], samples: int) -> float:
    for key in ("success_rate", "success_ratio", "pass_rate"):
        if key in raw and raw[key] is not None:
            rate = _to_float(raw[key], default=1.0)
            return max(0.0, min(1.0, rate / 100.0 if rate > 1.0 else rate))
    for key in ("success_pct", "success_percent"):
        if key in raw and raw[key] is not None:
            return max(0.0, min(1.0, _to_float(raw[key], default=100.0) / 100.0))
    successes = _pick(raw, "successes")
    failures = _pick(raw, "failures")
    if successes is not None:
        success_count = _to_int(successes, default=0)
        failure_count = _to_int(failures, default=max(0, samples - success_count))
        total = max(1, success_count + failure_count)
        return success_count / total
    return 1.0


def _normalize_hotspots(
    value: Any,
    *,
    by_rule: dict[str, int],
    by_severity: dict[str, int],
) -> list[dict[str, Any]]:
    if isinstance(value, list):
        out: list[dict[str, Any]] = []
        for row in value:
            raw = _coerce_mapping(row)
            rule = _pick(raw, "rule", "name")
            if rule is None:
                continue
            out.append(
                {
                    "rule": str(rule),
                    "count": _to_int(_pick(raw, "count", "violations"), default=0),
                    "severity": str(_pick(raw, "severity") or "UNKNOWN"),
                }
            )
        if out:
            return out
    ranked = sorted(by_rule.items(), key=lambda item: (-item[1], item[0]))
    return [
        {
            "rule": name,
            "count": count,
            "severity": _severity_for_rule(name, by_severity),
        }
        for name, count in ranked[:3]
    ]


def _severity_for_rule(rule_name: str, by_severity: dict[str, int]) -> str:
    if not by_severity:
        return "UNKNOWN"
    return max(by_severity.items(), key=lambda item: item[1])[0]


def _derive_violation_maps(value: Any) -> tuple[dict[str, int], dict[str, int]]:
    if not isinstance(value, list):
        return {}, {}
    by_rule: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    for row in value:
        raw = _coerce_mapping(row)
        rule = _pick(raw, "rule_name", "rule", "name")
        severity = _pick(raw, "severity")
        if rule is not None:
            key = str(rule)
            by_rule[key] = by_rule.get(key, 0) + 1
        if severity is not None:
            sev = str(severity)
            by_severity[sev] = by_severity.get(sev, 0) + 1
    return by_rule, by_severity


def _normalize_count_map(value: Any) -> dict[str, int]:
    raw = _coerce_mapping(value)
    out: dict[str, int] = {}
    for key, val in raw.items():
        count = _to_int(val, default=None)
        if count is not None:
            out[str(key)] = count
    return out


def _coerce_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if is_dataclass(value):
        data = asdict(value)
        if isinstance(data, dict):
            return data
    if hasattr(value, "items"):
        try:
            return dict(value.items())
        except Exception:
            return {}
    return {}


def _pick(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return None


def _setdefault_present(out: dict[str, Any], key: str, value: Any) -> None:
    if value is not None:
        out.setdefault(key, value)


def _to_int(value: Any, default: int | None = None) -> int | None:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value: Any, default: float | None = None) -> float | None:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
