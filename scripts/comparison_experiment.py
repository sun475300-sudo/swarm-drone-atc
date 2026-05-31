#!/usr/bin/env python3
"""P706 — Contribution Comparison Experiment Runner.

Runs SDACS vs baselines (ORCA, VO, CBS) across all benchmark scenarios,
evaluates metrics, computes aggregate statistics with significance tests,
and generates a comparison report.

Usage:
    python scripts/comparison_experiment.py
    python scripts/comparison_experiment.py --seeds 5 --scenarios 01_corridor_crossing 02_dense_intersection
    python scripts/comparison_experiment.py --out-dir results/comparison --seeds 30

Exit codes:
    0 — report generated.
    1 — no successful runs.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import yaml  # type: ignore

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from benchmarks.baselines._base import make_adapter
from src.analytics.metrics import Evaluator, EvaluatorConfig
from src.analytics.types import SimulationTrace

ALL_METHODS = ("orca", "vo", "cbs", "sdacs_hybrid")

HEADLINE_METRICS = ("NMR", "MSD", "PE", "MS_s", "FT_drone_s", "AU", "RTF")

HIGHER_IS_BETTER = {"MSD", "PE", "AU", "RTF", "RID_CR"}
LOWER_IS_BETTER = {"NMR", "MS_s", "FT_drone_s", "geofence_violations"}


@dataclass(frozen=True)
class RunResult:
    scenario: str
    method: str
    seed: int
    metrics: dict[str, float]
    wall_seconds: float
    trace_path: str | None = None


@dataclass
class ComparisonReport:
    runs: list[RunResult] = field(default_factory=list)
    aggregate: dict[str, Any] = field(default_factory=dict)
    significance: list[dict[str, Any]] = field(default_factory=list)
    generated_at: str = ""


def discover_scenarios() -> list[str]:
    """Find all scenario IDs from benchmarks/scenarios/."""
    scenario_dir = REPO_ROOT / "benchmarks" / "scenarios"
    if not scenario_dir.exists():
        return []
    return sorted(
        d.name for d in scenario_dir.iterdir()
        if d.is_dir() and (d / "manifest.yaml").exists()
    )


def load_manifest(scenario_id: str) -> dict:
    path = REPO_ROOT / "benchmarks" / "scenarios" / scenario_id / "manifest.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_single(
    scenario_id: str,
    method: str,
    seed: int,
    manifest: dict,
    evaluator: Evaluator,
    hard_wall_s: float = 120.0,
    out_dir: Path | None = None,
) -> RunResult | None:
    """Run one (scenario, method, seed) and return metrics."""
    try:
        adapter = make_adapter(method, manifest, seed)
    except (ValueError, RuntimeError) as exc:
        print(f"  [SKIP] {scenario_id}/{method}/seed{seed}: adapter error: {exc}")
        return None

    t0 = time.perf_counter()
    try:
        trace = adapter.run(hard_wall_time_s=hard_wall_s)
    except Exception as exc:
        print(f"  [FAIL] {scenario_id}/{method}/seed{seed}: {exc}")
        return None
    wall = time.perf_counter() - t0

    metrics = evaluator.evaluate(trace)

    trace_path: str | None = None
    if out_dir is not None:
        p = out_dir / scenario_id / method / f"seed{seed}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(trace.to_dict(), f, indent=2, default=list, sort_keys=True)
        trace_path = str(p)

    return RunResult(
        scenario=scenario_id,
        method=method,
        seed=seed,
        metrics=metrics,
        wall_seconds=wall,
        trace_path=trace_path,
    )


def aggregate_results(
    runs: list[RunResult],
) -> dict[str, Any]:
    """Group by (scenario, method) and compute mean +/- std for headline metrics."""
    from collections import defaultdict

    grouped: dict[tuple[str, str], list[dict[str, float]]] = defaultdict(list)
    for r in runs:
        grouped[(r.scenario, r.method)].append(r.metrics)

    agg: dict[str, Any] = {}
    for (scenario, method), metric_list in sorted(grouped.items()):
        key = f"{scenario}__{method}"
        entry: dict[str, Any] = {
            "scenario": scenario,
            "method": method,
            "n_runs": len(metric_list),
        }
        for m in HEADLINE_METRICS:
            values = [d[m] for d in metric_list if not _is_nan(d.get(m))]
            if values:
                arr = np.array(values, dtype=float)
                entry[f"{m}_mean"] = float(arr.mean())
                entry[f"{m}_std"] = float(arr.std(ddof=1)) if len(arr) > 1 else 0.0
            else:
                entry[f"{m}_mean"] = float("nan")
                entry[f"{m}_std"] = float("nan")
        agg[key] = entry
    return agg


def significance_tests(
    runs: list[RunResult],
    reference: str = "sdacs_hybrid",
) -> list[dict[str, Any]]:
    """Mann-Whitney U test: SDACS vs each baseline, per scenario per metric."""
    from collections import defaultdict

    grouped: dict[tuple[str, str], list[dict[str, float]]] = defaultdict(list)
    for r in runs:
        grouped[(r.scenario, r.method)].append(r.metrics)

    results: list[dict[str, Any]] = []
    scenarios = sorted({r.scenario for r in runs})

    for scenario in scenarios:
        ref_metrics = grouped.get((scenario, reference), [])
        if not ref_metrics:
            continue
        baselines = [m for m in ALL_METHODS if m != reference]
        for baseline in baselines:
            base_metrics = grouped.get((scenario, baseline), [])
            if not base_metrics:
                continue
            for metric_name in HEADLINE_METRICS:
                ref_vals = [d[metric_name] for d in ref_metrics if not _is_nan(d.get(metric_name))]
                base_vals = [d[metric_name] for d in base_metrics if not _is_nan(d.get(metric_name))]
                if len(ref_vals) < 2 or len(base_vals) < 2:
                    continue
                ref_arr = np.array(ref_vals, dtype=float)
                base_arr = np.array(base_vals, dtype=float)
                u_stat, p_value = _mann_whitney_u(ref_arr, base_arr)
                better_direction = "higher" if metric_name in HIGHER_IS_BETTER else "lower"
                ref_mean = float(ref_arr.mean())
                base_mean = float(base_arr.mean())
                if better_direction == "higher":
                    sdacs_wins = ref_mean > base_mean
                else:
                    sdacs_wins = ref_mean < base_mean

                results.append({
                    "scenario": scenario,
                    "metric": metric_name,
                    "sdacs_vs": baseline,
                    "sdacs_mean": ref_mean,
                    "baseline_mean": base_mean,
                    "u_statistic": u_stat,
                    "p_value": p_value,
                    "significant_005": p_value < 0.05,
                    "sdacs_wins": sdacs_wins,
                    "better_direction": better_direction,
                })
    return results


def _mann_whitney_u(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Pure-NumPy Mann-Whitney U test (two-sided, normal approximation)."""
    nx, ny = len(x), len(y)
    combined = np.concatenate([x, y])
    ranks = _rank_data(combined)
    r1 = ranks[:nx].sum()
    u1 = r1 - nx * (nx + 1) / 2
    u2 = nx * ny - u1
    u_stat = min(u1, u2)
    mu = nx * ny / 2
    n_total = nx + ny
    sigma = np.sqrt(nx * ny * (n_total + 1) / 12)
    if sigma == 0:
        return float(u_stat), 1.0
    z = (u_stat - mu) / sigma
    p_value = 2 * _normal_cdf(-abs(z))
    return float(u_stat), float(p_value)


def _rank_data(data: np.ndarray) -> np.ndarray:
    """Average-rank method."""
    n = len(data)
    idx = np.argsort(data)
    ranks = np.empty(n, dtype=float)
    i = 0
    while i < n:
        j = i + 1
        while j < n and data[idx[j]] == data[idx[i]]:
            j += 1
        avg_rank = (i + j + 1) / 2
        for k in range(i, j):
            ranks[idx[k]] = avg_rank
        i = j
    return ranks


def _normal_cdf(z: float) -> float:
    """Standard normal CDF via error function."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _is_nan(v: Any) -> bool:
    if v is None:
        return True
    try:
        return math.isnan(float(v))
    except (TypeError, ValueError):
        return True


def generate_markdown_report(
    agg: dict[str, Any],
    sig: list[dict[str, Any]],
    out_path: Path,
) -> None:
    """Write a markdown comparison table."""
    scenarios = sorted({v["scenario"] for v in agg.values()})
    methods = sorted({v["method"] for v in agg.values()})

    lines: list[str] = [
        "# P706 Contribution Comparison Report",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]

    for metric in HEADLINE_METRICS:
        better = "higher" if metric in HIGHER_IS_BETTER else "lower"
        lines.append(f"## {metric} ({better} is better)")
        lines.append("")
        header = "| Scenario | " + " | ".join(methods) + " |"
        sep = "|" + "---|" * (len(methods) + 1)
        lines.append(header)
        lines.append(sep)

        for sc in scenarios:
            cells = [sc[:30]]
            best_val = None
            best_idx = -1
            vals: list[tuple[float, str]] = []

            for mi, m in enumerate(methods):
                key = f"{sc}__{m}"
                entry = agg.get(key, {})
                mean = entry.get(f"{metric}_mean", float("nan"))
                std = entry.get(f"{metric}_std", float("nan"))
                if _is_nan(mean):
                    vals.append((float("nan"), "N/A"))
                else:
                    vals.append((mean, f"{mean:.4f} +/- {std:.4f}"))
                    if best_val is None:
                        best_val = mean
                        best_idx = mi
                    elif better == "higher" and mean > best_val:
                        best_val = mean
                        best_idx = mi
                    elif better == "lower" and mean < best_val:
                        best_val = mean
                        best_idx = mi

            for mi, (_, text) in enumerate(vals):
                if mi == best_idx:
                    cells.append(f"**{text}**")
                else:
                    cells.append(text)
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")

    lines.append("## Statistical Significance (SDACS vs Baselines)")
    lines.append("")
    lines.append("| Scenario | Metric | vs | SDACS mean | Baseline mean | p-value | Sig. | Wins |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for s in sig:
        win = "Y" if s["sdacs_wins"] else "N"
        lines.append(
            f"| {s['scenario'][:25]} "
            f"| {s['metric']} "
            f"| {s['sdacs_vs']} "
            f"| {s['sdacs_mean']:.4f} "
            f"| {s['baseline_mean']:.4f} "
            f"| {s['p_value']:.4f} "
            f"| {'Yes' if s['significant_005'] else 'No'} "
            f"| {win} |"
        )
    lines.append("")

    win_count = sum(1 for s in sig if s["sdacs_wins"] and s["significant_005"])
    total_tests = len(sig)
    lines.append(f"**Summary:** SDACS significantly outperforms baselines in "
                 f"{win_count}/{total_tests} comparisons (p < 0.05).")
    lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[report] wrote {out_path}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="comparison_experiment",
        description="P706: SDACS contribution comparison experiment",
    )
    p.add_argument(
        "--scenarios", nargs="*", default=None,
        help="Scenario IDs. Default: all discovered.",
    )
    p.add_argument(
        "--methods", nargs="*", default=list(ALL_METHODS),
        help=f"Methods. Default: {' '.join(ALL_METHODS)}",
    )
    p.add_argument("--seeds", type=int, default=5, help="Number of seeds. Default: 5")
    p.add_argument("--seed-start", type=int, default=42, help="First seed. Default: 42")
    p.add_argument("--hard-wall-s", type=float, default=120.0)
    p.add_argument("--out-dir", default="results/comparison")
    p.add_argument("--save-traces", action="store_true", help="Save trace JSONs")
    args = p.parse_args(argv)

    scenarios = args.scenarios or discover_scenarios()
    if not scenarios:
        print("ERROR: no scenarios found", file=sys.stderr)
        return 1

    methods = args.methods
    seeds = list(range(args.seed_start, args.seed_start + args.seeds))
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    total = len(scenarios) * len(methods) * len(seeds)
    print(f"[P706] {len(scenarios)} scenarios x {len(methods)} methods x {len(seeds)} seeds = {total} runs")
    print(f"[P706] Scenarios: {', '.join(scenarios)}")
    print(f"[P706] Methods: {', '.join(methods)}")
    print()

    evaluator = Evaluator()
    runs: list[RunResult] = []
    done = 0

    for scenario in scenarios:
        try:
            manifest = load_manifest(scenario)
        except FileNotFoundError:
            print(f"[SKIP] scenario {scenario}: manifest not found")
            continue

        for method in methods:
            for seed in seeds:
                done += 1
                print(f"[{done}/{total}] {scenario} / {method} / seed={seed}", end=" ... ")
                result = run_single(
                    scenario,
                    method,
                    seed,
                    manifest,
                    evaluator,
                    hard_wall_s=args.hard_wall_s,
                    out_dir=out_dir if args.save_traces else None,
                )
                if result is not None:
                    runs.append(result)
                    print(f"{result.wall_seconds:.1f}s")
                else:
                    print("failed")

    if not runs:
        print("ERROR: no successful runs", file=sys.stderr)
        return 1

    print(f"\n[P706] {len(runs)}/{total} runs succeeded")

    agg = aggregate_results(runs)
    sig = significance_tests(runs)

    json_path = out_dir / "comparison_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "n_runs": len(runs),
                "aggregate": agg,
                "significance": sig,
                "per_run": [
                    {
                        "scenario": r.scenario,
                        "method": r.method,
                        "seed": r.seed,
                        "wall_seconds": r.wall_seconds,
                        "metrics": r.metrics,
                    }
                    for r in runs
                ],
            },
            f,
            indent=2,
            sort_keys=True,
            default=float,
        )
    print(f"[P706] wrote {json_path}")

    md_path = out_dir / "COMPARISON_REPORT.md"
    generate_markdown_report(agg, sig, md_path)

    win_count = sum(1 for s in sig if s["sdacs_wins"] and s["significant_005"])
    total_tests = len(sig)
    print(f"\n[P706] SDACS wins {win_count}/{total_tests} significant comparisons")
    return 0


if __name__ == "__main__":
    sys.exit(main())
