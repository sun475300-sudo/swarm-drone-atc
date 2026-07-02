"""Aggregate per-run SimulationTrace JSONs into a summary parquet.

Handles two input layouts:

1. **Flat (modern, from scripts/run_one_scenario.py):**
     ``<root>/<scenario>__<method>__<seed>.json`` or ``<root>/<method>.json``
   Each file is a SimulationTrace dict. We run the Evaluator on it to
   derive the 14 metrics.

2. **Nested (legacy):**
     ``<root>/<scenario>/<method>/seed<N>.json``
   Each file has metric fields directly (near_miss_rate, ...).

Both layouts are auto-detected and merged into a single DataFrame.

Usage:
    python scripts/reproduce/aggregate.py --root results
    python scripts/reproduce/aggregate.py --root results/dryrun --csv -o results/dryrun/summary.csv
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from typing import Any

_FLAT_RE = re.compile(r"^(?P<sc>[0-9a-zA-Z]+(?:_[0-9a-zA-Z]+)*)__(?P<m>[a-z_]+)__(?P<s>-?\d+)\.json$")


def _try_import_evaluator():
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    try:
        from src.analytics.metrics import Evaluator  # type: ignore
        from src.analytics.types import SimulationTrace  # type: ignore
        return Evaluator(), SimulationTrace
    except Exception as exc:  # pragma: no cover
        print(f"[aggregate] Evaluator unavailable: {exc}", file=sys.stderr)
        return None, None


def _collect_flat(root: str, evaluator, TraceCls) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if evaluator is None:
        return rows
    for path in sorted(glob.glob(os.path.join(root, "*.json"))):
        name = os.path.basename(path)
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            print(f"[skip] {path}: {exc}", file=sys.stderr)
            continue
        if "agents" not in data or "scenario_id" not in data:
            continue
        trace = TraceCls.from_dict(data)
        m = _FLAT_RE.match(name)
        if m:
            scenario, method, seed = m["sc"], m["m"], int(m["s"])
        else:
            scenario = trace.scenario_id
            method = trace.method or name[:-5]
            seed = trace.seed
        metrics = evaluator.evaluate(trace)
        rows.append({
            "scenario": scenario,
            "method": method,
            "seed": seed,
            **metrics,
            "wall_clock_seconds": trace.wall_clock_seconds,
        })
    return rows


def _collect_nested(root: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    pattern = os.path.join(root, "*", "*", "seed*.json")
    for path in sorted(glob.glob(pattern)):
        parts = path.replace("\\", "/").split("/")
        scenario = parts[-3]
        method = parts[-2]
        seed_str = os.path.basename(path).removeprefix("seed").removesuffix(".json")
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            print(f"[skip] {path}: {exc}", file=sys.stderr)
            continue
        row: dict[str, Any] = {
            "scenario": scenario,
            "method": method,
            "seed": int(seed_str),
        }
        for metric in ("near_miss_rate", "min_separation_m", "path_efficiency",
                       "makespan_s", "flowtime_s", "airspace_utilization",
                       "rid_compliance_rate", "rtf"):
            row[metric] = data.get(metric)
        rows.append(row)
    return rows


def collect(root: str) -> list[dict[str, Any]]:
    """Try both layouts, return combined rows."""
    evaluator, TraceCls = _try_import_evaluator()
    flat = _collect_flat(root, evaluator, TraceCls)
    nested = _collect_nested(root)
    return flat + nested


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="results")
    parser.add_argument("-o", "--out", default="results/summary.parquet")
    parser.add_argument("--csv", action="store_true")
    args = parser.parse_args()

    rows = collect(args.root)
    if not rows:
        print(f"[aggregate] no rows under {args.root}", file=sys.stderr)
        return 1

    if args.csv or not args.out.endswith(".parquet"):
        import csv
        out_path = args.out if not args.out.endswith(".parquet") else args.out.replace(".parquet", ".csv")
        keys = sorted({k for r in rows for k in r.keys()})
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(rows)
        print(f"[aggregate] wrote {len(rows)} rows -> {out_path}")
    else:
        try:
            import pandas as pd
        except ImportError:
            print("[aggregate] pandas not installed", file=sys.stderr)
            return 2
        df = pd.DataFrame(rows)
        df.to_parquet(args.out, index=False)
        print(f"[aggregate] wrote {len(df)} rows -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
