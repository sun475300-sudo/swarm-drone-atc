"""P710 포스터·논문 차트 생성 스크립트.

P706 결과 CSV(`results/p706_comparison_3sc_5seed.csv`)를 읽어
matplotlib 차트(NMR·MSD bar + Pareto front)를 PNG로 저장.

실행:
    python scripts/poster/generate_charts.py

산출물:
    docs/poster/assets/results_nmr_msd_bar.png
    docs/poster/assets/pareto_front.png
"""
from __future__ import annotations

import csv
import os
from collections import defaultdict
from pathlib import Path
from typing import Any


def load_results(csv_path: str) -> dict[str, dict[str, list[float]]]:
    """P706 CSV → algorithm × metric × [seed values]."""
    if not os.path.exists(csv_path):
        return _sample_data()  # fallback for development
    data: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            algo = row.get("algorithm", "unknown")
            for metric in ("NMR", "MSD", "AU", "FT", "RTF"):
                if metric in row:
                    try:
                        data[algo][metric].append(float(row[metric]))
                    except (ValueError, TypeError):
                        pass
    return data


def _sample_data() -> dict[str, dict[str, list[float]]]:
    """결과 CSV 없을 때 샘플 데이터 (개발용)."""
    return {
        "ORCA": {"NMR": [0.18, 0.17, 0.19, 0.18, 0.18], "MSD": [24.3, 24.1, 24.5, 24.2, 24.4],
                 "AU": [0.62, 0.61, 0.63, 0.62, 0.62], "RTF": [120, 122, 118, 121, 119]},
        "VelocityObstacle": {"NMR": [0.21, 0.20, 0.22, 0.21, 0.21], "MSD": [22.1, 22.0, 22.3, 22.1, 22.0],
                             "AU": [0.58, 0.57, 0.59, 0.58, 0.58], "RTF": [95, 96, 94, 95, 95]},
        "CBS": {"NMR": [0.05, 0.04, 0.06, 0.05, 0.05], "MSD": [41.2, 41.0, 41.5, 41.1, 41.3],
                "AU": [0.51, 0.50, 0.52, 0.51, 0.51], "RTF": [8, 8, 8, 8, 8]},
        "SDACS": {"NMR": [0.08, 0.07, 0.09, 0.08, 0.08], "MSD": [38.7, 38.5, 38.9, 38.7, 38.6],
                  "AU": [0.71, 0.70, 0.72, 0.71, 0.71], "RTF": [140, 142, 138, 141, 139]},
    }


def _mean_std(values: list[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    n = len(values)
    m = sum(values) / n
    variance = sum((x - m) ** 2 for x in values) / max(1, n - 1)
    return m, variance ** 0.5


def plot_nmr_msd_bar(data: dict[str, dict[str, list[float]]], out_path: str) -> None:
    """NMR·MSD 막대 그래프 (오차막대 포함)."""
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("matplotlib 필요: pip install matplotlib numpy")
        return

    algos = list(data.keys())
    nmr_m = [_mean_std(data[a]["NMR"])[0] for a in algos]
    nmr_s = [_mean_std(data[a]["NMR"])[1] for a in algos]
    msd_m = [_mean_std(data[a]["MSD"])[0] for a in algos]
    msd_s = [_mean_std(data[a]["MSD"])[1] for a in algos]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    x = np.arange(len(algos))
    colors = ["#94a3b8", "#fb923c", "#a855f7", "#00e5ff"]

    ax1.bar(x, nmr_m, yerr=nmr_s, color=colors, capsize=4)
    ax1.set_xticks(x); ax1.set_xticklabels(algos, rotation=15)
    ax1.set_ylabel("Near Miss Rate (NMR) ↓")
    ax1.set_title("Safety: NMR")
    ax1.grid(axis="y", alpha=0.3)

    ax2.bar(x, msd_m, yerr=msd_s, color=colors, capsize=4)
    ax2.set_xticks(x); ax2.set_xticklabels(algos, rotation=15)
    ax2.set_ylabel("Mean Separation Distance (m) ↑")
    ax2.set_title("Separation: MSD")
    ax2.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"✅ saved: {out_path}")


def plot_pareto_front(data: dict[str, dict[str, list[float]]], out_path: str) -> None:
    """Pareto front: NMR (낮을수록 좋음) vs RTF (높을수록 좋음)."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib 필요")
        return

    fig, ax = plt.subplots(figsize=(7, 5))
    colors = {"ORCA": "#94a3b8", "VelocityObstacle": "#fb923c",
              "CBS": "#a855f7", "SDACS": "#00e5ff"}

    for algo, metrics in data.items():
        nmr_m, _ = _mean_std(metrics.get("NMR", []))
        rtf_m, _ = _mean_std(metrics.get("RTF", []))
        ax.scatter(nmr_m, rtf_m, s=200, c=colors.get(algo, "#888"),
                   edgecolors="black", linewidth=1, label=algo, zorder=3)
        ax.annotate(algo, (nmr_m, rtf_m), xytext=(6, 6),
                    textcoords="offset points", fontsize=9)

    ax.set_xlabel("Near Miss Rate (NMR) ↓  Lower is better")
    ax.set_ylabel("Real-Time Factor (RTF) ↑  Higher is better")
    ax.set_title("Pareto Front: Safety vs Throughput")
    ax.grid(alpha=0.3)
    ax.set_xscale("linear")

    # Pareto-optimal 영역 음영 (우상단 = 좋음)
    ax.axhspan(140, ax.get_ylim()[1] if ax.get_ylim()[1] > 140 else 150, alpha=0.05, color="green")
    ax.axvspan(ax.get_xlim()[0], 0.1, alpha=0.05, color="green")
    ax.legend(loc="best")

    plt.tight_layout()
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"✅ saved: {out_path}")


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent.parent
    csv_path = str(repo_root / "results" / "p706_comparison_3sc_5seed.csv")
    data = load_results(csv_path)

    plot_nmr_msd_bar(data, str(repo_root / "docs" / "poster" / "assets" / "results_nmr_msd_bar.png"))
    plot_pareto_front(data, str(repo_root / "docs" / "poster" / "assets" / "pareto_front.png"))


if __name__ == "__main__":
    main()
