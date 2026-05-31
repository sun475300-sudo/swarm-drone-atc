#!/usr/bin/env python3
"""P717 — Load Test: Simulation Throughput at Scale.

Measures tick latency, real-time factor, memory usage, and collision rates
at increasing drone counts (20, 50, 100, 200, 500).

Usage:
    python scripts/load_test.py
    python scripts/load_test.py --drone-counts 20 50 100 --duration 30
    python scripts/load_test.py --seeds 3 --out-dir results/load_test

Exit codes:
    0 — report generated.
    1 — no successful runs.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import tracemalloc
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

DEFAULT_DRONE_COUNTS = [20, 50, 100, 200, 500]
DEFAULT_DURATION_S = 60


@dataclass(frozen=True)
class LoadTestResult:
    drone_count: int
    seed: int
    duration_s: float
    wall_seconds: float
    real_time_factor: float
    collision_count: int
    near_miss_count: int
    conflict_resolution_rate_pct: float
    clearances_per_sec: float
    route_efficiency_mean: float
    peak_memory_mb: float


def run_one(drone_count: int, duration_s: float, seed: int) -> LoadTestResult | None:
    """Run one simulation with the given drone count and measure performance."""
    from simulation.simulator import SwarmSimulator

    scenario_cfg = {
        "drones": {"default_count": drone_count},
        "simulation": {"duration_minutes": duration_s / 60.0},
    }

    tracemalloc.start()
    t0 = time.perf_counter()
    try:
        sim = SwarmSimulator(scenario_cfg=scenario_cfg, seed=seed)
        result = sim.run(duration_s=duration_s)
    except (KeyboardInterrupt, SystemExit):
        tracemalloc.stop()
        raise
    except Exception as exc:
        print(f"  [FAIL] {drone_count} drones, seed={seed}: {type(exc).__name__}: {exc}", file=sys.stderr)
        tracemalloc.stop()
        return None
    wall = time.perf_counter() - t0
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    peak_mb = peak_bytes / (1024 * 1024)

    rtf = duration_s / wall if wall > 0 else float("inf")

    return LoadTestResult(
        drone_count=drone_count,
        seed=seed,
        duration_s=duration_s,
        wall_seconds=round(wall, 3),
        real_time_factor=round(rtf, 2),
        collision_count=result.collision_count,
        near_miss_count=result.near_miss_count,
        conflict_resolution_rate_pct=round(result.conflict_resolution_rate_pct, 2),
        clearances_per_sec=round(result.clearances_per_sec, 2),
        route_efficiency_mean=round(result.route_efficiency_mean, 4),
        peak_memory_mb=round(peak_mb, 1),
    )


def _status_label(rtf_mean: float) -> str:
    if rtf_mean >= 100:
        return "Excellent"
    if rtf_mean >= 10:
        return "Good"
    if rtf_mean >= 1:
        return "Acceptable"
    return "Below real-time"


def aggregate_by_count(
    results: list[LoadTestResult],
) -> list[dict[str, Any]]:
    """Aggregate results by drone count across seeds."""
    from collections import defaultdict

    grouped: dict[int, list[LoadTestResult]] = defaultdict(list)
    for r in results:
        grouped[r.drone_count].append(r)

    agg: list[dict[str, Any]] = []
    for count in sorted(grouped.keys()):
        runs = grouped[count]
        walls = np.array([r.wall_seconds for r in runs])
        rtfs = np.array([r.real_time_factor for r in runs])
        collisions = np.array([r.collision_count for r in runs])
        near_misses = np.array([r.near_miss_count for r in runs])
        resolution = np.array([r.conflict_resolution_rate_pct for r in runs])
        clearances = np.array([r.clearances_per_sec for r in runs])
        memory = np.array([r.peak_memory_mb for r in runs])

        entry = {
            "drone_count": count,
            "n_seeds": len(runs),
            "wall_s_mean": round(float(walls.mean()), 3),
            "wall_s_std": round(float(walls.std(ddof=1)), 3) if len(walls) > 1 else 0.0,
            "rtf_mean": round(float(rtfs.mean()), 2),
            "rtf_std": round(float(rtfs.std(ddof=1)), 2) if len(rtfs) > 1 else 0.0,
            "collisions_mean": round(float(collisions.mean()), 1),
            "near_misses_mean": round(float(near_misses.mean()), 1),
            "resolution_rate_pct": round(float(resolution.mean()), 2),
            "clearances_per_sec_mean": round(float(clearances.mean()), 2),
            "peak_memory_mb_mean": round(float(memory.mean()), 1),
            "peak_memory_mb_max": round(float(memory.max()), 1),
            "status": _status_label(float(rtfs.mean())),
        }
        agg.append(entry)
    return agg


def generate_report(
    agg: list[dict[str, Any]],
    all_results: list[LoadTestResult],
    out_dir: Path,
    duration_s: float,
) -> None:
    """Generate JSON + Markdown load test reports."""
    json_path = out_dir / "load_test_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "duration_s": duration_s,
                "aggregate": agg,
                "per_run": [asdict(r) for r in all_results],
            },
            f,
            indent=2,
            sort_keys=True,
        )
    print(f"[load_test] wrote {json_path}")

    md_path = out_dir / "LOAD_TEST_REPORT.md"
    lines = [
        "# P717 Load Test Report",
        "",
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Duration: {duration_s}s per run",
        "",
        "## Throughput Summary",
        "",
        "| Drones | Wall Time | RTF | Collisions | Resolution | Memory | Status |",
        "|--------|-----------|-----|------------|------------|--------|--------|",
    ]
    for entry in agg:
        lines.append(
            f"| {entry['drone_count']:>6} "
            f"| {entry['wall_s_mean']:.1f}s +/- {entry['wall_s_std']:.1f}s "
            f"| {entry['rtf_mean']:.1f}x "
            f"| {entry['collisions_mean']:.0f} "
            f"| {entry['resolution_rate_pct']:.1f}% "
            f"| {entry['peak_memory_mb_mean']:.0f} MB "
            f"| {entry['status']} |"
        )
    lines.extend(["", "## Key Metrics", ""])

    for entry in agg:
        lines.append(f"### {entry['drone_count']} Drones")
        lines.append(f"- Real-time factor: **{entry['rtf_mean']}x** (+/- {entry['rtf_std']})")
        lines.append(f"- Collision count: {entry['collisions_mean']}")
        lines.append(f"- Conflict resolution rate: {entry['resolution_rate_pct']}%")
        lines.append(f"- Clearances/sec: {entry['clearances_per_sec_mean']}")
        lines.append(f"- Peak memory: {entry['peak_memory_mb_max']} MB")
        lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[load_test] wrote {md_path}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="load_test",
        description="P717: Simulation load test at scale",
    )
    p.add_argument(
        "--drone-counts", nargs="*", type=int, default=DEFAULT_DRONE_COUNTS,
        help=f"Drone counts to test. Default: {DEFAULT_DRONE_COUNTS}",
    )
    p.add_argument("--duration", type=float, default=DEFAULT_DURATION_S)
    p.add_argument("--seeds", type=int, default=3)
    p.add_argument("--seed-start", type=int, default=42)
    p.add_argument("--out-dir", default="results/load_test")
    args = p.parse_args(argv)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    counts = args.drone_counts
    seeds = list(range(args.seed_start, args.seed_start + args.seeds))
    total = len(counts) * len(seeds)
    print(f"[P717] {len(counts)} drone counts x {len(seeds)} seeds = {total} runs")
    print(f"[P717] Counts: {counts}")
    print(f"[P717] Duration: {args.duration}s per run")
    print()

    results: list[LoadTestResult] = []
    done = 0

    for count in counts:
        for seed in seeds:
            done += 1
            print(f"[{done}/{total}] {count} drones, seed={seed}", end=" ... ")
            r = run_one(count, args.duration, seed)
            if r is not None:
                results.append(r)
                print(f"{r.wall_seconds:.1f}s (RTF={r.real_time_factor:.1f}x, mem={r.peak_memory_mb:.0f}MB)")
            else:
                print("failed")

    if not results:
        print("ERROR: no successful runs", file=sys.stderr)
        return 1

    print(f"\n[P717] {len(results)}/{total} runs succeeded")

    agg = aggregate_by_count(results)
    generate_report(agg, results, out_dir, args.duration)

    print("\n[P717] Summary:")
    for entry in agg:
        print(
            f"  {entry['drone_count']:>4} drones: "
            f"RTF={entry['rtf_mean']:>7.1f}x, "
            f"collisions={entry['collisions_mean']:.0f}, "
            f"memory={entry['peak_memory_mb_mean']:.0f}MB -- "
            f"{entry['status']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
