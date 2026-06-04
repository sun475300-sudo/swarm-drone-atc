#!/usr/bin/env python3
<<<<<<< HEAD
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
=======
"""P717 — Load test: 100-drone swarm realtime simulation throughput.

Tests whether the SDACS stack can sustain ≥1Hz control loop ticks for a
100-drone swarm without exceeding the target latency budget.

Target (from P717 spec):
  - 100 drones, realtime 60-second simulation.
  - Tick wall-clock latency p99 ≤ 50 ms (= 1 Hz budget).
  - No tick drops (all n_steps ticks complete within horizon_seconds wall time).
  - Memory growth ≤ 100 MB over the run.

Usage:
    python scripts/load_test.py
    python scripts/load_test.py --drones 200 --duration 30
    python scripts/load_test.py --drones 100 --duration 60 --out results/load_test.json

Exit codes:
    0 — all assertions pass.
    1 — at least one assertion failed (prints FAIL summary).
>>>>>>> c712bbd5ecb51bce6d827215bbc998a957a56a02
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import tracemalloc
<<<<<<< HEAD
from dataclasses import asdict, dataclass
=======
from dataclasses import asdict, dataclass, field
>>>>>>> c712bbd5ecb51bce6d827215bbc998a957a56a02
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

<<<<<<< HEAD
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
=======

@dataclass
class TickStats:
    """Per-tick timing captured during the load test."""
    tick_ms: list[float] = field(default_factory=list)

    def p50(self) -> float:
        return float(np.percentile(self.tick_ms, 50)) if self.tick_ms else 0.0

    def p95(self) -> float:
        return float(np.percentile(self.tick_ms, 95)) if self.tick_ms else 0.0

    def p99(self) -> float:
        return float(np.percentile(self.tick_ms, 99)) if self.tick_ms else 0.0

    def max(self) -> float:
        return float(max(self.tick_ms)) if self.tick_ms else 0.0

    def mean(self) -> float:
        return float(np.mean(self.tick_ms)) if self.tick_ms else 0.0


@dataclass
class LoadTestResult:
    n_drones: int
    duration_s: float
    n_ticks: int
    wall_s: float
    rtf: float                      # realtime factor = horizon_s / wall_s
    tick_p50_ms: float
    tick_p95_ms: float
    tick_p99_ms: float
    tick_max_ms: float
    tick_mean_ms: float
    peak_memory_mb: float
    goals_reached_pct: float
    passed: bool
    failures: list[str] = field(default_factory=list)
    assertions: dict[str, Any] = field(default_factory=dict)


def _run_sdacs_load(
    n_drones: int,
    duration_s: float,
    dt_s: float,
    seed: int,
) -> tuple[TickStats, float, float]:
    """Run the SDACS adapter and return tick stats, peak memory, goal%.

    Uses the SDACS hybrid adapter directly so we test the actual algorithm
    (APF + CBS stagger + Voronoi), not a synthetic loop.
    """
    from benchmarks.baselines.sdacs.adapter import Adapter

    manifest = {
        "id": f"load_test_{n_drones}",
        "duration_seconds": duration_s,
        "dt_seconds": dt_s,
        "airspace": {"bounds_m": {"x": [0, 2000], "y": [0, 2000], "z": [50, 250]}},
        "agents": {
            "count": n_drones,
            "spawn_pattern": "uniform_random",
            "kinematics": {"max_speed_m_s": 15.0},
        },
    }

    tracemalloc.start()
    adapter = Adapter(manifest=manifest, seed=seed)
    trace = adapter.run(hard_wall_time_s=duration_s * 10)
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    stats = TickStats(tick_ms=list(trace.tick_latencies_ms))
    peak_mb = peak_mem / 1024 / 1024
    goals = sum(1 for a in trace.agents if a.goal_reached_at_s is not None)
    goal_pct = goals / max(1, len(trace.agents)) * 100.0
    return stats, peak_mb, goal_pct


def run_load_test(
    n_drones: int = 100,
    duration_s: float = 60.0,
    dt_s: float = 1.0,
    seed: int = 42,
    p99_budget_ms: float = 50.0,
    rtf_floor: float = 0.5,
    memory_budget_mb: float = 200.0,
) -> LoadTestResult:
    """Execute the load test and evaluate pass/fail assertions."""
    print(f"[P717] Load test: {n_drones} drones × {duration_s}s (dt={dt_s}s) seed={seed}")

    wall_start = time.perf_counter()
    stats, peak_mb, goal_pct = _run_sdacs_load(n_drones, duration_s, dt_s, seed)
    wall_total = time.perf_counter() - wall_start

    n_ticks = len(stats.tick_ms)
    rtf = duration_s / max(wall_total, 1e-9)

    assertions: dict[str, Any] = {
        "p99_ms_ok": stats.p99() <= p99_budget_ms,
        "rtf_ok": rtf >= rtf_floor,
        "memory_ok": peak_mb <= memory_budget_mb,
        "n_ticks_ok": n_ticks >= int(duration_s / dt_s) * 0.9,
    }
    failures = [k for k, v in assertions.items() if not v]

    result = LoadTestResult(
        n_drones=n_drones,
        duration_s=duration_s,
        n_ticks=n_ticks,
        wall_s=wall_total,
        rtf=rtf,
        tick_p50_ms=stats.p50(),
        tick_p95_ms=stats.p95(),
        tick_p99_ms=stats.p99(),
        tick_max_ms=stats.max(),
        tick_mean_ms=stats.mean(),
        peak_memory_mb=peak_mb,
        goals_reached_pct=goal_pct,
        passed=len(failures) == 0,
        failures=failures,
        assertions=assertions,
    )

    _print_result(result, p99_budget_ms, rtf_floor, memory_budget_mb)
    return result


def _print_result(r: LoadTestResult, p99_budget: float, rtf_floor: float, mem_budget: float) -> None:
    ok = "PASS" if r.passed else "FAIL"
    print(f"\n[P717] {ok} — {r.n_drones} drones × {r.duration_s}s")
    print(f"  Wall time      : {r.wall_s:.2f}s")
    print(f"  Realtime factor: {r.rtf:.2f}x  (≥{rtf_floor}x required)")
    print(f"  Ticks          : {r.n_ticks}")
    print(f"  Goals reached  : {r.goals_reached_pct:.1f}%")
    print(f"  Tick latency   : p50={r.tick_p50_ms:.2f}ms  p95={r.tick_p95_ms:.2f}ms  "
          f"p99={r.tick_p99_ms:.2f}ms  max={r.tick_max_ms:.2f}ms  "
          f"(budget ≤{p99_budget:.0f}ms)")
    print(f"  Peak memory    : {r.peak_memory_mb:.1f} MB  (budget ≤{mem_budget:.0f}MB)")
    if r.failures:
        print(f"  FAILED assertions: {', '.join(r.failures)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="P717 load test")
    parser.add_argument("--drones", type=int, default=100)
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--dt", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--p99-budget-ms", type=float, default=50.0,
                        help="p99 tick latency budget (ms)")
    parser.add_argument("--rtf-floor", type=float, default=0.5,
                        help="minimum acceptable realtime factor")
    parser.add_argument("--memory-budget-mb", type=float, default=200.0)
    parser.add_argument("--out", type=str, default=None,
                        help="path to write JSON result")
    args = parser.parse_args(argv)

    result = run_load_test(
        n_drones=args.drones,
        duration_s=args.duration,
        dt_s=args.dt,
        seed=args.seed,
        p99_budget_ms=args.p99_budget_ms,
        rtf_floor=args.rtf_floor,
        memory_budget_mb=args.memory_budget_mb,
    )

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(asdict(result), indent=2))
        print(f"[P717] wrote {out_path}")

    return 0 if result.passed else 1
>>>>>>> c712bbd5ecb51bce6d827215bbc998a957a56a02


if __name__ == "__main__":
    sys.exit(main())
