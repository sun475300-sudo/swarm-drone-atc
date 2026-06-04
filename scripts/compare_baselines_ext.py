"""다중 알고리즘 KPI 비교 + 표/JSON 출력.

`scripts/compare_baselines.py`(P703/P706 호환)를 확장하여 P736 RL
정책까지 추가 비교 가능. 알고리즘별 결과 CSV → 통합 표.

실행:
    python scripts/compare_baselines_ext.py \
        --results results/orca.csv results/cbs.csv results/sdacs.csv results/ppo.csv \
        --metrics NMR MSD AU RTF \
        --output results/comparison.json
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


def load_csv(path: str) -> dict[str, list[float]]:
    """KPI CSV → metric → [seed values]."""
    data: dict[str, list[float]] = {}
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for k, v in row.items():
                if k in ("seed", "scenario", "algorithm"):
                    continue
                try:
                    data.setdefault(k, []).append(float(v))
                except (ValueError, TypeError):
                    pass
    return data


def _mean_std(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    n = len(values)
    m = sum(values) / n
    var = sum((x - m) ** 2 for x in values) / max(1, n - 1)
    return m, var ** 0.5


def compare(paths: list[str], metrics: list[str]) -> dict[str, dict[str, dict[str, float]]]:
    """알고리즘 × 메트릭 → {mean, std} 통합."""
    out: dict[str, dict[str, dict[str, float]]] = {}
    for path in paths:
        algo = Path(path).stem
        kpi = load_csv(path)
        out[algo] = {}
        for m in metrics:
            mean, std = _mean_std(kpi.get(m, []))
            out[algo][m] = {"mean": round(mean, 4), "std": round(std, 4)}
    return out


def format_table(comparison: dict[str, dict[str, dict[str, float]]], metrics: list[str]) -> str:
    """Markdown 표 출력."""
    header = "| Algorithm | " + " | ".join(metrics) + " |"
    sep = "|" + "|".join(["---"] * (len(metrics) + 1)) + "|"
    lines = [header, sep]
    for algo, mvs in comparison.items():
        row = [algo]
        for m in metrics:
            mean = mvs.get(m, {}).get("mean", 0.0)
            std = mvs.get(m, {}).get("std", 0.0)
            row.append(f"{mean:.3f} ± {std:.3f}")
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="P703/P706/P736 알고리즘 비교")
    ap.add_argument("--results", nargs="+", required=True, help="알고리즘별 KPI CSV 경로")
    ap.add_argument("--metrics", nargs="+", default=["NMR", "MSD", "AU", "RTF"])
    ap.add_argument("--output", default=None, help="JSON 출력 경로")
    ap.add_argument("--table", action="store_true", help="Markdown 표 출력")
    args = ap.parse_args()

    comparison = compare(args.results, args.metrics)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(comparison, f, indent=2, ensure_ascii=False)
        print(f"✅ saved: {args.output}")

    if args.table or not args.output:
        print()
        print(format_table(comparison, args.metrics))

    return 0


if __name__ == "__main__":
    sys.exit(main())
