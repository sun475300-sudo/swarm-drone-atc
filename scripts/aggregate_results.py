#!/usr/bin/env python3
"""Re-aggregate existing trace JSON files into comparison tables.

Use this when you want to re-render the Markdown/CSV without re-running sims.

Usage:
    python scripts/aggregate_results.py [--dir results/comparison] [--out results]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


def main(argv: list[str] | None = None) -> int:
    """결과 집계 메인 루틴."""
    import argparse

    p = argparse.ArgumentParser(prog="aggregate_results")
    p.add_argument("--dir", default=str(REPO_ROOT / "results" / "comparison"),
                   help="Directory containing trace JSON files.")
    p.add_argument("--out", default=str(REPO_ROOT / "results"),
                   help="Output directory for table files.")
    args = p.parse_args(argv)

    trace_dir = Path(args.dir)
    json_files = sorted(trace_dir.glob("*.json"))

    if not json_files:
        print(f"No JSON files found in {trace_dir}", file=sys.stderr)
        return 1

    print(f"[aggregate] {len(json_files)} trace files")

    from compare_baselines import (  # noqa: PLC0415
        METRIC_KEYS,
        ALL_SCENARIOS,
        _aggregate,
        _dict_to_trace,
        _write_csv,
        _write_markdown,
    )
    from src.analytics.metrics import Evaluator

    evaluator = Evaluator()
    rows: list[dict] = []

    for jf in json_files:
        with open(jf, encoding="utf-8") as f:
            raw = json.load(f)
        trace = _dict_to_trace(raw)
        metrics = evaluator.evaluate(trace)
        rows.append({
            "scenario": trace.scenario_id,
            "method": trace.method,
            "seed": trace.seed,
            **metrics,
        })

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    _write_csv(rows, out_dir / "comparison_table.csv")

    agg = _aggregate(rows)
    # Determine which scenarios are actually present
    scenarios_present = []
    for sc in ALL_SCENARIOS:
        if sc in agg:
            scenarios_present.append(sc)

    # Count seeds from the data
    seed_counts = {}
    for r in rows:
        k = (r["scenario"], r["method"])
        seed_counts[k] = seed_counts.get(k, 0) + 1
    n_seeds = max(seed_counts.values()) if seed_counts else 1

    _write_markdown(agg, out_dir / "comparison_table.md", scenarios_present, n_seeds)
    return 0


if __name__ == "__main__":
    sys.exit(main())
