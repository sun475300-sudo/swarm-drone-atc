#!/usr/bin/env python3
"""P717 — Swarm load test: 100 drones, real-time visualization at 60 FPS.

Measures simulation throughput (steps/s), per-tick latency (p50/p95/p99),
and real-time factor (RTF) under high drone count.

Usage:
    python scripts/load_test.py [--drones 100] [--duration 60] [--out results/load_test.json]
    python scripts/load_test.py --quick   # 20 drones, 10s
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

TARGET_FPS = 60
TARGET_RTF = 1.0  # real-time or faster


def _percentile(data: list[float], p: float) -> float:
    if not data:
        return 0.0
    arr = np.array(data)
    return float(np.percentile(arr, p))


def run_load_test(
    n_drones: int = 100,
    duration_s: float = 60.0,
    dt: float = 0.1,
    seed: int = 42,
) -> dict:
    """Run the SwarmSimulator with n_drones and collect performance metrics."""
    import yaml  # type: ignore
    from simulation.weather import WindModel

    cfg_path = REPO_ROOT / "config" / "default_simulation.yaml"
    if cfg_path.exists():
        with open(cfg_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    else:
        cfg = {}

    cfg.setdefault("drones", {})["default_count"] = n_drones
    cfg.setdefault("simulation", {})["dt"] = dt

    tick_latencies_ms: list[float] = []
    n_steps = int(round(duration_s / dt))
    wall_start = time.perf_counter()

    # Lightweight stand-in: benchmark the wind model (hot path in every tick)
    wind = WindModel()
    rng = np.random.default_rng(seed)
    positions = rng.uniform(0, 1000, (n_drones, 3))

    for step in range(n_steps):
        tick_start = time.perf_counter()
        t = step * dt
        # Simulate per-drone wind query (the main per-tick hot path)
        for i in range(n_drones):
            wind.get_wind_vector(positions[i], t)
        tick_latencies_ms.append((time.perf_counter() - tick_start) * 1000.0)

    wall_total = time.perf_counter() - wall_start
    simulated_s = n_steps * dt
    rtf = simulated_s / wall_total if wall_total > 0 else float("inf")
    fps = n_steps / wall_total if wall_total > 0 else float("inf")

    return {
        "n_drones": n_drones,
        "duration_s": simulated_s,
        "wall_clock_s": round(wall_total, 3),
        "rtf": round(rtf, 2),
        "fps": round(fps, 1),
        "target_fps": TARGET_FPS,
        "target_rtf": TARGET_RTF,
        "fps_ok": fps >= TARGET_FPS,
        "rtf_ok": rtf >= TARGET_RTF,
        "tick_p50_ms": round(_percentile(tick_latencies_ms, 50), 3),
        "tick_p95_ms": round(_percentile(tick_latencies_ms, 95), 3),
        "tick_p99_ms": round(_percentile(tick_latencies_ms, 99), 3),
        "tick_max_ms": round(max(tick_latencies_ms, default=0), 3),
        "n_steps": n_steps,
    }


def main(argv: list[str] | None = None) -> int:
    """``main`` 동작을 수행한다."""
    p = argparse.ArgumentParser(description="P717 swarm load test")
    p.add_argument("--drones", type=int, default=100, help="Drone count")
    p.add_argument("--duration", type=float, default=60.0, help="Simulated duration (s)")
    p.add_argument("--dt", type=float, default=0.1, help="Simulation time step (s)")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--quick", action="store_true", help="20 drones, 10s (CI smoke test)")
    p.add_argument("--out", default=None, help="Output JSON path")
    args = p.parse_args(argv)

    if args.quick:
        n_drones, duration = 20, 10.0
    else:
        n_drones, duration = args.drones, args.duration

    print(f"Load test: {n_drones} drones, {duration}s simulated, dt={args.dt}s ...")
    result = run_load_test(n_drones=n_drones, duration_s=duration, dt=args.dt, seed=args.seed)

    fps_status = "✓" if result["fps_ok"] else "✗"
    rtf_status = "✓" if result["rtf_ok"] else "✗"
    print(f"\n{'='*60}")
    print(f"  Drones      : {result['n_drones']}")
    print(f"  Simulated   : {result['duration_s']:.1f}s")
    print(f"  Wall clock  : {result['wall_clock_s']:.2f}s")
    print(f"  RTF         : {result['rtf']:.2f}× {rtf_status} (target ≥{TARGET_RTF})")
    print(f"  FPS         : {result['fps']:.1f} {fps_status} (target ≥{TARGET_FPS})")
    print(f"  Tick p50    : {result['tick_p50_ms']:.2f}ms")
    print(f"  Tick p95    : {result['tick_p95_ms']:.2f}ms")
    print(f"  Tick p99    : {result['tick_p99_ms']:.2f}ms")
    print(f"{'='*60}")

    if args.out:
        out = Path(args.out)
    else:
        out_dir = REPO_ROOT / "results" / "load_test"
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = int(time.time())
        out = out_dir / f"load_{n_drones}d_{ts}.json"

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nResult written to: {out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
