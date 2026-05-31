#!/usr/bin/env python3
"""P706 — Cross-method benchmark sweep for the AIAA SciTech 2027 paper.

Runs every combination of (scenario, method, seed) and evaluates all
SDACS metrics (NMR, MSD, PE, MS, RID-CR, RTF, ...) defined in
docs/paper/EVALUATION_METRICS.md.

Usage:
    python scripts/p706_sweep.py                 # full sweep (200 runs, ~5-10 min)
    python scripts/p706_sweep.py --quick         # 2 seeds × 4 scenarios (32 runs)
    python scripts/p706_sweep.py --out my.json   # custom output path

Output:
    data/p706_results.json   — per-run raw results
    data/p706_summary.json   — mean ± 95 % CI table (paper §5 ready)
    docs/paper/p706_table.md — Markdown table for copy-paste into paper draft
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from benchmarks.baselines._base import make_adapter           # noqa: E402
from src.analytics.metrics import Evaluator                   # noqa: E402

SCENARIOS = [
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

QUICK_SCENARIOS = [
    "01_corridor_crossing",
    "02_dense_intersection",
    "03_emergency_landing",
    "08_stress_high_density",
]

METHODS = ["orca", "vo", "cbs", "sdacs_hybrid"]

# Metrics to collect in the paper table
PAPER_METRICS = ["NMR", "MSD", "PE", "MS", "AU", "RID_CR", "RTF"]

METRIC_LABEL = {
    "NMR": "NMR ×10⁻⁴ ev/(pair·s)  ↓",
    "MSD": "MSD (m)  ↑",
    "PE":  "PE  ↑",
    "MS":  "MS (s)  ↓",
    "AU":  "AU (ctx)  —",
    "RID_CR": "RID-CR  ↑",
    "RTF": "RTF (N=100)  ↑",
}

HARD_WALL_S = {
    "01_corridor_crossing":       30,
    "02_dense_intersection":      60,
    "03_emergency_landing":       30,
    "04_no_fly_zone":             60,
    "05_weather_diversion":       60,
    "06_priority_aircraft":       60,
    "07_communication_loss":      60,
    "08_stress_high_density":     90,
    "09_stress_failure_cascade":  60,
    "10_stress_adversarial_swarm": 60,
}


def load_manifest(scenario_id: str) -> dict:
    path = REPO_ROOT / "benchmarks" / "scenarios" / scenario_id / "manifest.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _run_one(args: tuple[str, str, int]) -> dict:
    """Top-level function for ProcessPoolExecutor (must be picklable)."""
    scenario_id, method, seed = args
    sys.path.insert(0, str(REPO_ROOT))

    try:
        manifest = load_manifest(scenario_id)
        adapter = make_adapter(method, manifest, seed)
        wall_s = HARD_WALL_S.get(scenario_id, 60)
        t0 = time.perf_counter()
        trace = adapter.run(hard_wall_time_s=float(wall_s))
        elapsed = time.perf_counter() - t0

        from src.analytics.metrics import Evaluator
        evaluator = Evaluator()
        metrics = evaluator.evaluate(trace)

        return {
            "scenario": scenario_id,
            "method": method,
            "seed": seed,
            "wall_s": elapsed,
            **metrics,
        }
    except Exception as e:  # noqa: BLE001
        return {
            "scenario": scenario_id,
            "method": method,
            "seed": seed,
            "error": str(e),
        }


def run_sweep(
    scenarios: list[str],
    n_seeds: int,
    max_workers: int = 4,
) -> list[dict]:
    """Run the full sweep and return per-run results."""
    seeds = list(range(42, 42 + n_seeds))
    jobs = [
        (sc, m, s)
        for sc in scenarios
        for m in METHODS
        for s in seeds
    ]
    total = len(jobs)
    results: list[dict] = []
    done = 0

    print(f"[p706] Starting sweep: {total} runs "
          f"({len(scenarios)} scenarios × {len(METHODS)} methods × {n_seeds} seeds)")

    # Use processes to avoid GIL on NumPy-heavy adapters
    with ProcessPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_run_one, job): job for job in jobs}
        for future in as_completed(futures):
            done += 1
            job = futures[future]
            try:
                row = future.result()
            except Exception as exc:  # noqa: BLE001
                row = {"scenario": job[0], "method": job[1], "seed": job[2],
                       "error": str(exc)}
            results.append(row)
            ok = "OK" if "error" not in row else f"ERR({row['error'][:30]})"
            print(f"  [{done:3d}/{total}] {job[0][:25]:25s} / {job[1]:15s} / "
                  f"seed={job[2]}  {ok}")

    return results


def build_summary(results: list[dict]) -> dict:
    """Compute mean ± 95 % CI for every (method, metric) pair across all seeds."""
    from collections import defaultdict

    bucket: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in results:
        if "error" in row:
            continue
        method = row["method"]
        for metric in PAPER_METRICS:
            val = row.get(metric)
            if isinstance(val, (int, float)) and not (val != val):  # not NaN
                bucket[(method, metric)].append(float(val))

    summary: dict = {}
    for method in METHODS:
        summary[method] = {}
        for metric in PAPER_METRICS:
            vals = bucket.get((method, metric), [])
            if not vals:
                summary[method][metric] = {"mean": None, "ci95": None, "n": 0}
                continue
            arr = np.array(vals)
            mean = float(arr.mean())
            # 95 % CI = 1.96 * std / sqrt(n)
            ci95 = float(1.96 * arr.std(ddof=1) / np.sqrt(len(arr))) if len(arr) > 1 else 0.0
            summary[method][metric] = {"mean": mean, "ci95": ci95, "n": len(arr)}

    return summary


def render_markdown_table(summary: dict) -> str:
    """Render the §5 headline results table for the paper draft."""
    # Header
    method_names = {
        "orca":         "ORCA",
        "vo":           "VO",
        "cbs":          "CBS",
        "sdacs_hybrid": "SDACS",
    }

    header_methods = [method_names[m] for m in METHODS]
    sep = "| :--- " + " | ---: " * len(METHODS) + "|"
    header = "| Metric | " + " | ".join(header_methods) + " |"

    rows = [
        "<!-- Auto-generated by scripts/p706_sweep.py — do not edit manually -->",
        "",
        header,
        sep,
    ]

    for metric in PAPER_METRICS:
        label = METRIC_LABEL.get(metric, metric)
        cells = []
        for m in METHODS:
            entry = summary.get(m, {}).get(metric, {})
            mean = entry.get("mean")
            ci = entry.get("ci95")
            if mean is None:
                cells.append("N/A")
            elif metric == "NMR":
                # Scale to ×10⁻⁴ for readability
                cells.append(f"{mean * 1e4:.2f} ± {ci * 1e4:.2f}")
            elif metric in ("PE", "AU", "RID_CR", "RTF"):
                cells.append(f"{mean:.3f} ± {ci:.3f}")
            else:
                cells.append(f"{mean:.1f} ± {ci:.1f}")
        rows.append("| " + label + " | " + " | ".join(cells) + " |")

    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="p706_sweep")
    p.add_argument("--quick", action="store_true",
                   help="Run 4 scenarios × 2 seeds only (32 runs, ~30 s).")
    p.add_argument("--seeds", type=int, default=5,
                   help="Number of seeds per (scenario, method). Default 5.")
    p.add_argument("--workers", type=int, default=4,
                   help="Parallel worker processes. Default 4.")
    p.add_argument("--out", default=None,
                   help="Override output directory (default: data/).")
    args = p.parse_args(argv)

    scenarios = QUICK_SCENARIOS if args.quick else SCENARIOS
    n_seeds = 2 if args.quick else args.seeds
    out_dir = Path(args.out) if args.out else REPO_ROOT / "data"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Run sweep
    t0 = time.perf_counter()
    results = run_sweep(scenarios, n_seeds=n_seeds, max_workers=args.workers)
    elapsed = time.perf_counter() - t0

    ok = sum(1 for r in results if "error" not in r)
    print(f"\n[p706] Sweep complete: {ok}/{len(results)} OK in {elapsed:.1f}s")

    # Save raw results
    raw_path = out_dir / "p706_results.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"[p706] Raw results → {raw_path}")

    # Build summary
    summary = build_summary(results)
    summary_path = out_dir / "p706_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"[p706] Summary      → {summary_path}")

    # Markdown table for paper
    table_md = render_markdown_table(summary)
    table_path = REPO_ROOT / "docs" / "paper" / "p706_table.md"
    table_path.parent.mkdir(parents=True, exist_ok=True)
    with open(table_path, "w", encoding="utf-8") as f:
        f.write(table_md + "\n")
    print(f"[p706] Paper table  → {table_path}")

    # Print headline numbers
    print("\n=== §5 Headline Results ===")
    print(table_md)

    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
