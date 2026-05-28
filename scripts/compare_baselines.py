#!/usr/bin/env python3
"""P706 — Baseline comparison sweep.

Runs every (scenario, method, seed) combination and produces a Markdown
table suitable for the AIAA SciTech 2027 paper (§ 4 Results).

Usage:
    python scripts/compare_baselines.py [--seeds N] [--workers W] [--out DIR]
    python scripts/compare_baselines.py --quick          # 1 seed, 3 scenarios
    python scripts/compare_baselines.py --scenarios 01 02 03

Outputs:
    results/comparison/          — per-run JSON traces
    results/comparison_table.md  — Markdown table (copy into paper)
    results/comparison_table.csv — raw CSV for further analysis
"""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import io
import json
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

METHODS = ["orca", "vo", "cbs", "sdacs_hybrid"]
ALL_SCENARIOS = [
    "01_corridor_crossing",
    "02_dense_intersection",
    "03_emergency_landing",
    "04_no_fly_zone",
    "05_weather_diversion",
    "06_priority_aircraft",
    "07_communication_loss",
    "08_stress_high_density",
    "09_stress_failure_cascade",
    "10_stress_adversarial_swarm",
]
QUICK_SCENARIOS = ["01_corridor_crossing", "02_dense_intersection", "08_stress_high_density"]

# Keys must match Evaluator.evaluate() output exactly
METRIC_KEYS = ["NMR", "PE", "AU", "RID_CR", "LAANC_latency_ms", "geofence_violations", "tick_p99_ms"]
METRIC_LABELS = {
    "NMR":                "Near-Miss Rate↓       (events/pair·s)",
    "PE":                 "Path Efficiency↑      [0-1]",
    "AU":                 "Airspace Util↑        [0-1]",
    "RID_CR":             "Remote-ID Compl↑      [0-1]",
    "LAANC_latency_ms":   "LAANC Latency↓        (ms)",
    "geofence_violations":"Geofence Viol↓        (count)",
    "tick_p99_ms":        "P99 Tick Latency↓     (ms)",
}


# ---------------------------------------------------------------------------
# Single-run worker
# ---------------------------------------------------------------------------


def _run_one(scenario_id: str, method: str, seed: int, out_dir: Path,
             hard_wall_s: float = 120.0) -> dict | None:
    """Run one (scenario, method, seed) and return the metrics dict."""
    out_path = out_dir / f"{scenario_id}__{method}__{seed}.json"

    # Re-use cached trace if present
    if out_path.exists():
        with open(out_path, encoding="utf-8") as f:
            raw = json.load(f)
        trace = _dict_to_trace(raw)
    else:
        manifest = _load_manifest(scenario_id)
        if manifest is None:
            return None

        from benchmarks.baselines._base import make_adapter

        try:
            adapter = make_adapter(method, manifest, seed)
        except (ValueError, RuntimeError) as exc:
            print(f"  [SKIP] {scenario_id}/{method}/s{seed}: {exc}", file=sys.stderr)
            return None

        t0 = time.perf_counter()
        try:
            trace = adapter.run(hard_wall_time_s=hard_wall_s)
        except Exception as exc:
            print(f"  [FAIL] {scenario_id}/{method}/s{seed}: {exc}", file=sys.stderr)
            return None
        elapsed = time.perf_counter() - t0

        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(trace.to_dict(), f, separators=(",", ":"))

        print(f"  [OK]   {scenario_id}/{method}/s{seed}  {elapsed:.1f}s  "
              f"{len(trace.agents)} agents")

    from src.analytics.metrics import Evaluator

    metrics = Evaluator().evaluate(trace)
    return {
        "scenario": scenario_id,
        "method": method,
        "seed": seed,
        **metrics,
    }


def _load_manifest(scenario_id: str) -> dict | None:
    path = REPO_ROOT / "benchmarks" / "scenarios" / scenario_id / "manifest.yaml"
    if not path.exists():
        print(f"  [MISS] manifest not found: {path}", file=sys.stderr)
        return None
    import yaml
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _dict_to_trace(raw: dict):
    from src.analytics.types import AgentTrajectory, NearMissEvent, SimulationTrace

    agents = [
        AgentTrajectory(
            agent_id=a["agent_id"],
            positions=[tuple(p) for p in a.get("positions", [])],
            goal_reached_at_s=a.get("goal_reached_at_s"),
            spawn_time_s=a.get("spawn_time_s", 0.0),
        )
        for a in raw.get("agents", [])
    ]
    predicted = [
        NearMissEvent(
            a_id=e["a_id"], b_id=e["b_id"],
            predicted_at_s=e["predicted_at_s"],
            lead_time_s=e["lead_time_s"],
            predicted_min_distance_m=e["predicted_min_distance_m"],
        )
        for e in raw.get("predicted_conflicts", [])
    ]
    return SimulationTrace(
        scenario_id=raw.get("scenario_id", "unknown"),
        method=raw.get("method", "unknown"),
        seed=raw.get("seed", 0),
        horizon_seconds=raw.get("horizon_seconds", 0.0),
        dt_s=raw.get("dt_s", 1.0),
        wall_clock_seconds=raw.get("wall_clock_seconds", 0.0),
        agents=agents,
        predicted_conflicts=predicted,
        voronoi_assignments=raw.get("voronoi_assignments", []),
        remote_id_valid_seconds_per_agent=raw.get("remote_id_valid_seconds_per_agent", {}),
        laanc_request_latencies_ms=raw.get("laanc_request_latencies_ms", []),
        geofence_violation_timestamps=raw.get("geofence_violation_timestamps", []),
        tick_latencies_ms=raw.get("tick_latencies_ms", []),
        peak_memory_mb=raw.get("peak_memory_mb"),
    )


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def _aggregate(rows: list[dict]) -> dict[str, dict[str, dict[str, float]]]:
    """Aggregate: scenario -> method -> {metric -> mean}."""
    import statistics

    # Group by (scenario, method)
    groups: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        key = (r["scenario"], r["method"])
        groups.setdefault(key, []).append(r)

    result: dict[str, dict[str, dict[str, float]]] = {}
    for (sc, m), runs in groups.items():
        result.setdefault(sc, {})
        agg: dict[str, float] = {}
        for k in METRIC_KEYS:
            vals = [r[k] for r in runs if k in r and r[k] is not None]
            agg[k] = statistics.mean(vals) if vals else float("nan")
        result[sc][m] = agg
    return result


def _write_csv(rows: list[dict], path: Path) -> None:
    if not rows:
        return
    fieldnames = ["scenario", "method", "seed"] + METRIC_KEYS
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"[CSV] {path}")


def _write_markdown(agg: dict, path: Path, scenarios: list[str], seeds: int) -> None:
    buf = io.StringIO()
    buf.write("# P706 — Baseline Comparison Results\n\n")
    buf.write(f"Seeds per combination: **{seeds}** (mean reported).\n\n")
    buf.write("↑ higher is better · ↓ lower is better\n\n")

    header = "| Scenario | Method | " + " | ".join(METRIC_KEYS) + " |\n"
    sep    = "|---|---|" + "|".join(["---"] * len(METRIC_KEYS)) + "|\n"

    buf.write(header)
    buf.write(sep)

    for sc in scenarios:
        sc_agg = agg.get(sc, {})
        first = True
        for method in METHODS:
            m_agg = sc_agg.get(method, {})
            sc_cell = sc if first else ""
            first = False
            vals = []
            for k in METRIC_KEYS:
                v = m_agg.get(k, float("nan"))
                if k in ("RIDC", "PE", "AU"):
                    vals.append(f"{v:.3f}" if v == v else "—")
                elif k in ("LAANC_ms", "P99_ms"):
                    vals.append(f"{v:.1f}" if v == v else "—")
                elif k == "NMR":
                    vals.append(f"{v:.2e}" if v == v else "—")
                else:
                    vals.append(f"{v:.1f}" if v == v else "—")
            buf.write(f"| {sc_cell} | {method} | " + " | ".join(vals) + " |\n")
        buf.write("|---|---|" + "|".join(["---"] * len(METRIC_KEYS)) + "|\n")

    buf.write("\n## Metric definitions\n\n")
    for k, label in METRIC_LABELS.items():
        buf.write(f"- **{k}**: {label}\n")

    buf.write("\n*Generated by `scripts/compare_baselines.py`*\n")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(buf.getvalue(), encoding="utf-8")
    print(f"[MD]  {path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """메인 실행 로직."""
    p = argparse.ArgumentParser(prog="compare_baselines")
    p.add_argument("--seeds", type=int, default=5,
                   help="Number of random seeds per (scenario, method). Default 5.")
    p.add_argument("--workers", type=int, default=4,
                   help="Parallel worker threads. Default 4.")
    p.add_argument("--out", default=str(REPO_ROOT / "results" / "comparison"),
                   help="Output directory for trace JSONs.")
    p.add_argument("--quick", action="store_true",
                   help="Quick mode: 3 scenarios, 1 seed — for CI smoke tests.")
    p.add_argument("--scenarios", nargs="+", default=None,
                   help="Restrict to listed scenario IDs (e.g. 01 02 08).")
    p.add_argument("--methods", nargs="+", default=None,
                   help="Restrict methods (e.g. orca sdacs_hybrid).")
    p.add_argument("--hard-wall-s", type=float, default=120.0)
    args = p.parse_args(argv)

    if args.quick:
        scenarios = QUICK_SCENARIOS
        seeds_list = [42]
    else:
        if args.scenarios:
            # Accept bare numbers ("01") or full names
            scenarios = [
                s if "_" in s else next(
                    (x for x in ALL_SCENARIOS if x.startswith(s + "_")), s
                )
                for s in args.scenarios
            ]
        else:
            scenarios = ALL_SCENARIOS
        seeds_list = list(range(args.seeds))

    methods = args.methods or METHODS
    out_dir = Path(args.out)

    combos = [
        (sc, m, seed)
        for sc in scenarios
        for m in methods
        for seed in seeds_list
    ]

    print(f"[sweep] {len(combos)} runs · {len(scenarios)} scenarios · "
          f"{len(methods)} methods · {len(seeds_list)} seeds")

    rows: list[dict] = []
    t_sweep = time.perf_counter()

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {
            pool.submit(_run_one, sc, m, seed, out_dir, args.hard_wall_s): (sc, m, seed)
            for sc, m, seed in combos
        }
        for fut in concurrent.futures.as_completed(futs):
            result = fut.result()
            if result is not None:
                rows.append(result)

    elapsed = time.perf_counter() - t_sweep
    print(f"[done] {len(rows)}/{len(combos)} runs succeeded in {elapsed:.1f}s")

    if not rows:
        print("ERROR: no results collected.", file=sys.stderr)
        return 1

    results_dir = REPO_ROOT / "results"
    results_dir.mkdir(exist_ok=True)

    _write_csv(rows, results_dir / "comparison_table.csv")

    agg = _aggregate(rows)
    _write_markdown(agg, results_dir / "comparison_table.md", scenarios, len(seeds_list))

    return 0


if __name__ == "__main__":
    sys.exit(main())
