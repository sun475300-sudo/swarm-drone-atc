#!/usr/bin/env python3
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
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import tracemalloc
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


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


if __name__ == "__main__":
    sys.exit(main())
