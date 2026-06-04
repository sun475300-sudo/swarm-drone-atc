#!/usr/bin/env python3
"""P706 — Comparison experiment: SDACS vs ORCA vs VO vs CBS.

Runs all (scenario, method, seed) combinations, evaluates 14 metrics,
and writes a CSV summary table suitable for Table 6 of the paper.

Usage:
    python scripts/compare_baselines.py [--seeds 3] [--out results/comparison.csv]
    python scripts/compare_baselines.py --quick   # 1 seed, fast
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

import yaml  # type: ignore

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

SCENARIOS_DIR = REPO_ROOT / "benchmarks" / "scenarios"
RESULTS_DIR = REPO_ROOT / "results" / "comparison"

METHODS = ["orca", "vo", "cbs", "sdacs_hybrid"]

# Metrics included in the comparison table (column order for paper)
TABLE_METRICS = [
    "NMR", "MSD", "PE", "MS", "FT",
    "AU", "RID_CR", "GFV", "RTF",
]


def _load_manifest(scenario_dir: Path) -> dict:
    with open(scenario_dir / "manifest.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _all_scenario_ids() -> list[str]:
    return sorted(d.name for d in SCENARIOS_DIR.iterdir() if d.is_dir())


def _run_one(scenario_id: str, method: str, seed: int, hard_wall_s: float = 60.0) -> dict:
    """Run one (scenario, method, seed) and return the metric dict."""
    from benchmarks.baselines._base import make_adapter
    from src.analytics.metrics import Evaluator

    manifest = _load_manifest(SCENARIOS_DIR / scenario_id)
    adapter = make_adapter(method, manifest, seed)

    t0 = time.perf_counter()
    trace = adapter.run(hard_wall_time_s=hard_wall_s)
    wall = time.perf_counter() - t0

    ev = Evaluator()
    metrics = ev.evaluate(trace)
    metrics["_wall_s"] = round(wall, 3)
    metrics["_scenario"] = scenario_id
    metrics["_method"] = method
    metrics["_seed"] = seed
    return metrics


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else float("nan")


def run_sweep(
    scenarios: list[str],
    methods: list[str],
    seeds: list[int],
    hard_wall_s: float = 60.0,
    out_dir: Path | None = None,
    verbose: bool = True,
) -> list[dict]:
    """Run all (scenario, method, seed) combos; return flat result rows."""
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    total = len(scenarios) * len(methods) * len(seeds)
    done = 0

    for scenario in scenarios:
        for method in methods:
            for seed in seeds:
                done += 1
                if verbose:
                    print(f"[{done}/{total}] {scenario} / {method} / seed={seed}", flush=True)
                try:
                    row = _run_one(scenario, method, seed, hard_wall_s=hard_wall_s)
                except Exception as exc:
                    print(f"  [ERROR] {exc}", file=sys.stderr)
                    row = {
                        "_scenario": scenario,
                        "_method": method,
                        "_seed": seed,
                        "_error": str(exc),
                    }
                rows.append(row)
                if out_dir:
                    out_path = out_dir / f"{scenario}__{method}__seed{seed}.json"
                    out_path.write_text(json.dumps(row, indent=2), encoding="utf-8")
    return rows


def build_summary_table(rows: list[dict]) -> list[dict]:
    """Aggregate per-seed rows into (scenario, method) mean ± std rows."""
    from collections import defaultdict

    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        if "_error" in row:
            continue
        key = (row["_scenario"], row["_method"])
        grouped[key].append(row)

    summary: list[dict] = []
    for (scenario, method), group in sorted(grouped.items()):
        entry: dict = {"scenario": scenario, "method": method, "n_seeds": len(group)}
        for metric in TABLE_METRICS:
            vals = [g[metric] for g in group if metric in g]
            entry[f"{metric}_mean"] = round(_mean(vals), 4) if vals else None
        summary.append(entry)
    return summary


def write_csv(summary: list[dict], path: Path) -> None:
    if not summary:
        return
    fieldnames = list(summary[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary)


def main(argv: list[str] | None = None) -> int:
    """``main`` 동작을 수행한다."""
    p = argparse.ArgumentParser(description="P706 baseline comparison sweep")
    p.add_argument("--seeds", type=int, default=3, help="Number of seeds per (scenario, method)")
    p.add_argument("--quick", action="store_true", help="1 seed, 10s wall time (CI smoke test)")
    p.add_argument("--out", default=None, help="Output CSV path")
    p.add_argument("--out-dir", default=None, help="Per-run JSON output directory")
    p.add_argument("--methods", nargs="+", default=METHODS, help="Methods to compare")
    p.add_argument("--scenarios", nargs="+", default=None, help="Scenario IDs (default: all)")
    args = p.parse_args(argv)

    scenarios = args.scenarios or _all_scenario_ids()
    seeds = [0] if args.quick else list(range(args.seeds))
    hard_wall_s = 10.0 if args.quick else 60.0

    print(f"Scenarios: {len(scenarios)}, Methods: {args.methods}, Seeds: {seeds}")

    out_dir = Path(args.out_dir) if args.out_dir else None
    rows = run_sweep(scenarios, args.methods, seeds, hard_wall_s=hard_wall_s, out_dir=out_dir)

    summary = build_summary_table(rows)

    out_csv = Path(args.out) if args.out else (RESULTS_DIR / "comparison_table.csv")
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    write_csv(summary, out_csv)

    # Print a quick preview
    print(f"\nComparison table ({len(summary)} rows) → {out_csv}")
    print(f"{'Scenario':<35} {'Method':<14} {'NMR_mean':>10} {'MSD_mean':>10} {'PE_mean':>10}")
    print("-" * 80)
    for row in summary:
        print(
            f"{row['scenario']:<35} {row['method']:<14}"
            f" {row.get('NMR_mean', '—'):>10}"
            f" {row.get('MSD_mean', '—'):>10}"
            f" {row.get('PE_mean', '—'):>10}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
