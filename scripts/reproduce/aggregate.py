"""Aggregate per-run JSONs into a single parquet for the paper.

Usage:
    python scripts/reproduce/aggregate.py --root results --out results/summary.parquet
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from typing import Any


def collect(root: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    pattern = os.path.join(root, "*", "*", "seed*.json")
    for path in sorted(glob.glob(pattern)):
        parts = path.replace("\\", "/").split("/")
        # results / <scenario> / <method> / seed<N>.json
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
        for metric in (
            "near_miss_rate",
            "min_separation_m",
            "path_efficiency",
            "makespan_s",
            "flowtime_s",
            "airspace_utilization",
            "rid_compliance_rate",
            "rtf",
        ):
            row[metric] = data.get(metric)
        rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="results", help="directory tree with per-run JSONs")
    parser.add_argument("--out", default="results/summary.parquet")
    args = parser.parse_args()

    rows = collect(args.root)
    if not rows:
        print(f"[aggregate] no rows under {args.root}", file=sys.stderr)
        return 1

    try:
        import pandas as pd  # type: ignore
    except ImportError:
        print("[aggregate] pandas not installed; writing CSV instead", file=sys.stderr)
        import csv

        fallback = args.out.replace(".parquet", ".csv")
        with open(fallback, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        print(f"[aggregate] wrote {len(rows)} rows -> {fallback}")
        return 0

    df = pd.DataFrame(rows)
    df.to_parquet(args.out, index=False)
    print(f"[aggregate] wrote {len(df)} rows -> {args.out}")

    summary = df.groupby(["scenario", "method"]).agg(
        {
            "near_miss_rate": ["mean", "std"],
            "makespan_s": ["mean", "std"],
            "path_efficiency": ["mean", "std"],
        }
    )
    print(summary.to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
