#!/usr/bin/env python3
"""Regenerate the 3 headline figures for PAPER_DRAFT §5 from the sweep CSV.

Input : results/<sweep-name>/summary.csv (produced by scripts/reproduce/aggregate.py)
Output: docs/paper/figs/fig{2,3,4}.pdf

Usage:
    python docs/paper/figs/generate_figures.py \
        --csv results/full_sweep/summary.csv \
        --out docs/paper/figs

Reproducibility:
    * The three figures are deterministic given the input CSV.
    * Font: DejaVu Sans (matplotlib default) -- do NOT depend on Times New Roman
      because CI containers may lack it.
"""
from __future__ import annotations

import argparse
import csv
import math
import os
from collections import defaultdict

import matplotlib

matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt
import numpy as np


METHODS = ["orca", "vo", "cbs", "sdacs_hybrid"]
METHOD_LABEL = {
    "orca": "ORCA",
    "vo": "VO",
    "cbs": "CBS",
    "sdacs_hybrid": "SDACS (ours)",
}
METHOD_COLOR = {
    "orca": "#4c72b0",
    "vo": "#dd8452",
    "cbs": "#55a467",
    "sdacs_hybrid": "#c44e52",
}


def _load(csv_path: str) -> list[dict]:
    """Read CSV; coerce numeric columns to float."""
    numeric_keys = {
        "NMR", "MSD", "PE", "MS_s", "FT_drone_s", "AU",
        "RID_CR", "LAANC_latency_ms", "RTF",
        "tick_p50_ms", "tick_p95_ms", "tick_p99_ms",
        "geofence_violations", "wall_clock_seconds",
        "n_agents",
    }
    out = []
    with open(csv_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            for k in list(row):
                if k in numeric_keys:
                    try:
                        row[k] = float(row[k]) if row[k] != "" else float("nan")
                    except (TypeError, ValueError):
                        row[k] = float("nan")
            out.append(row)
    return out


# ------------------------------------------------------------------
# Fig 2 -- NMR heatmap (scenario x method)
# ------------------------------------------------------------------


def fig2_heatmap(rows: list[dict], out_pdf: str) -> None:
    scenarios = sorted({r["scenario"] for r in rows})
    grid = np.full((len(scenarios), len(METHODS)), np.nan)
    for i, sc in enumerate(scenarios):
        for j, m in enumerate(METHODS):
            vals = [r["NMR"] for r in rows
                    if r["scenario"] == sc and r["method"] == m and not math.isnan(r["NMR"])]
            if vals:
                grid[i, j] = np.mean(vals) * 1e4  # display in 10^-4 units

    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    im = ax.imshow(grid, cmap="RdYlGn_r", aspect="auto", vmin=0, vmax=np.nanmax(grid))
    ax.set_xticks(range(len(METHODS)))
    ax.set_xticklabels([METHOD_LABEL[m] for m in METHODS], rotation=20, ha="right")
    ax.set_yticks(range(len(scenarios)))
    ax.set_yticklabels([sc.replace("_", " ") for sc in scenarios], fontsize=9)
    for i in range(len(scenarios)):
        for j in range(len(METHODS)):
            v = grid[i, j]
            if not math.isnan(v):
                color = "white" if v > np.nanmax(grid) * 0.55 else "black"
                ax.text(j, i, f"{v:.2f}", ha="center", va="center",
                        color=color, fontsize=8)
    cbar = plt.colorbar(im, ax=ax, fraction=0.04, pad=0.03)
    cbar.set_label(r"NMR $\times 10^{-4}$  (lower is safer)", fontsize=9)
    ax.set_title("Fig. 2  Near-Miss Rate across scenarios and methods\n"
                 "(7 standard scenarios, 30 seeds each, mean per cell)",
                 fontsize=10, pad=10)
    plt.tight_layout()
    plt.savefig(out_pdf, format="pdf", bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------
# Fig 3 -- Ablation-style bar chart per method
# ------------------------------------------------------------------


def fig3_bars(rows: list[dict], out_pdf: str) -> None:
    """Grouped bars: NMR, MSD (normalized), PE, MS_s (normalized) per method."""
    stats = {m: {k: [] for k in ("NMR", "MSD", "PE", "MS_s")} for m in METHODS}
    for r in rows:
        if r["method"] not in stats:
            continue
        for k in ("NMR", "MSD", "PE", "MS_s"):
            v = r.get(k, float("nan"))
            if not math.isnan(v) and math.isfinite(v):
                stats[r["method"]][k].append(v)

    means = {}
    stds = {}
    for m, d in stats.items():
        means[m] = {k: (np.mean(v) if v else float("nan")) for k, v in d.items()}
        stds[m] = {k: (np.std(v) if v else 0.0) for k, v in d.items()}

    metrics = ["NMR", "MSD", "PE", "MS_s"]
    # normalize each metric across methods so bars are comparable
    def _norm(vals):
        vmax = max(v for v in vals if not math.isnan(v))
        if vmax == 0:
            return [0.0 for _ in vals]
        return [v / vmax for v in vals]

    fig, ax = plt.subplots(figsize=(7, 4))
    width = 0.20
    x = np.arange(len(metrics))
    for i, m in enumerate(METHODS):
        heights = _norm([means[m][k] for k in metrics])
        ax.bar(x + i * width - 1.5 * width, heights, width,
               label=METHOD_LABEL[m], color=METHOD_COLOR[m])
    ax.set_xticks(x)
    ax.set_xticklabels([f"{k}\n(↓ NMR/MS; ↑ MSD/PE)" if k in ("NMR", "MS_s")
                        else f"{k}\n(↑ better)"
                        for k in metrics], fontsize=9)
    ax.set_ylabel("Normalized to worst per metric (0–1)")
    ax.legend(loc="upper right", fontsize=8)
    ax.set_title("Fig. 3  Per-method metric summary (normalized)\n"
                 "(n=30 seeds × 7 scenarios = 210 runs per method)",
                 fontsize=10, pad=10)
    ax.grid(axis="y", alpha=0.3)
    ax.set_ylim(0, 1.15)
    plt.tight_layout()
    plt.savefig(out_pdf, format="pdf", bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------
# Fig 4 -- RTF vs N (approximate scaling), or wall clock vs n_agents
# ------------------------------------------------------------------


def fig4_scaling(rows: list[dict], out_pdf: str) -> None:
    """RTF scaling per method vs agent count (scenario-driven).

    Uses Real-Time Factor (higher = better, RTF > 1 means faster than real time).
    Original plan was wall-clock but summary.csv does not carry that column;
    RTF is a cleaner scaling proxy anyway.
    """
    per_method: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for r in rows:
        n = r.get("n_agents", float("nan"))
        rtf = r.get("RTF", float("nan"))
        if isinstance(n, str):
            try:
                n = float(n)
            except ValueError:
                n = float("nan")
        if not (math.isnan(n) or math.isnan(rtf) or rtf <= 0 or math.isinf(rtf)):
            per_method[r["method"]].append((int(n), rtf))

    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    plotted = False
    for m in METHODS:
        pts = per_method.get(m, [])
        if not pts:
            continue
        ns = np.array([p[0] for p in pts])
        rs = np.array([p[1] for p in pts])
        uniq = sorted(set(int(n) for n in ns))
        means = [rs[ns == u].mean() for u in uniq]
        ax.plot(uniq, means, marker="o", label=METHOD_LABEL[m], color=METHOD_COLOR[m])
        plotted = True

    ax.set_xlabel("Number of agents N (per scenario)")
    ax.set_ylabel("Real-Time Factor (higher = faster than real time)")
    ax.set_yscale("log")
    ax.set_title("Fig. 4  Runtime scaling — RTF vs. N\n"
                 "(RTF > 1 means the simulator runs faster than real time)",
                 fontsize=10, pad=10)
    if plotted:
        ax.legend(loc="upper right", fontsize=8)
    ax.grid(True, alpha=0.3, which="both")
    plt.tight_layout()
    plt.savefig(out_pdf, format="pdf", bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--csv", default="results/full_sweep/summary.csv")
    p.add_argument("--out", default="docs/paper/figs")
    args = p.parse_args()

    if not os.path.exists(args.csv):
        print(f"ERROR: {args.csv} not found. Run aggregate.py first.")
        return 1

    rows = _load(args.csv)
    print(f"loaded {len(rows)} rows from {args.csv}")
    os.makedirs(args.out, exist_ok=True)

    fig2_heatmap(rows, os.path.join(args.out, "fig2_nmr_heatmap.pdf"))
    print(f"  wrote {args.out}/fig2_nmr_heatmap.pdf")

    fig3_bars(rows, os.path.join(args.out, "fig3_per_method_bars.pdf"))
    print(f"  wrote {args.out}/fig3_per_method_bars.pdf")

    fig4_scaling(rows, os.path.join(args.out, "fig4_scaling.pdf"))
    print(f"  wrote {args.out}/fig4_scaling.pdf")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
