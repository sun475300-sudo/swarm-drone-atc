#!/usr/bin/env python3
"""Run one (scenario, method, seed) combination and write a SimulationTrace JSON.

Usage:
    python scripts/run_one_scenario.py <scenario_id> <method> <seed> [--out <path>]

Example:
    python scripts/run_one_scenario.py 01_corridor_crossing sdacs_hybrid 42 \
        --out results/01_corridor_crossing__sdacs_hybrid__42.json

Exit codes:
    0 — trace written.
    1 — scenario / method not found.
    2 — adapter failed beyond hard wall time.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import yaml  # type: ignore


REPO_ROOT = Path(__file__).resolve().parent.parent


def load_manifest(scenario_id: str) -> dict:
    manifest_path = REPO_ROOT / "benchmarks" / "scenarios" / scenario_id / "manifest.yaml"
    if not manifest_path.exists():
        raise FileNotFoundError(f"No manifest at {manifest_path}")
    with open(manifest_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="run_one_scenario")
    p.add_argument("scenario", help="e.g. 01_corridor_crossing")
    p.add_argument("method", help="orca | vo | cbs | sdacs_hybrid")
    p.add_argument("seed", type=int)
    p.add_argument("--out", default=None,
                   help="Output path. Default: results/<sc>__<m>__<seed>.json")
    p.add_argument("--hard-wall-s", type=float, default=120.0,
                   help="Per-run wall time ceiling. Default 120 s.")
    args = p.parse_args(argv)

    sys.path.insert(0, str(REPO_ROOT))
    from benchmarks.baselines._base import make_adapter

    try:
        manifest = load_manifest(args.scenario)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print(f"[{time.strftime('%H:%M:%S')}] {args.scenario} / {args.method} / seed={args.seed}")

    try:
        adapter = make_adapter(args.method, manifest, args.seed)
    except (ValueError, RuntimeError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    t0 = time.perf_counter()
    trace = adapter.run(hard_wall_time_s=args.hard_wall_s)
    elapsed = time.perf_counter() - t0
    print(f"  -> {len(trace.agents)} agents, {len(trace.tick_latencies_ms)} ticks, {elapsed:.2f}s wall")

    out_path = Path(args.out) if args.out else (
        REPO_ROOT / "results" / f"{args.scenario}__{args.method}__{args.seed}.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(trace.to_dict(), f, indent=2, default=list, sort_keys=True)
    print(f"  -> wrote {out_path}")

    if elapsed >= args.hard_wall_s:
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
