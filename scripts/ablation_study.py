#!/usr/bin/env python3
"""Phase 286 — Safety-Net Ablation Study Runner.

각 안전망 계층(APF 회피 · CBS 다중 에이전트 계획)을 선택적으로 제거하고
충돌·근접경고·충돌 해결률에 미치는 영향을 정량화한다.
논문 §Ablation 표에 직접 삽입 가능한 markdown + JSON 을 생성한다.

충돌 해결률 공식 (CLAUDE.md 규약):
    resolution_rate = 1 - collisions / (conflicts + collisions)

Usage:
    python scripts/ablation_study.py
    python scripts/ablation_study.py --seeds 10 --drones 30 --duration 120
    python scripts/ablation_study.py --out-dir results/ablation

Exit codes:
    0 — report generated.
    1 — no successful runs.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from simulation.analytics import SimulationResult  # noqa: E402
from simulation.simulator import SwarmSimulator  # noqa: E402

# 제거 대상 안전망 계층. baseline = 모든 계층 활성.
ABLATIONS: dict[str, dict] = {
    "baseline": {},
    "no_apf": {"disable_apf": True},
    "no_cbs": {"disable_cbs": True},
    "no_apf_no_cbs": {"disable_apf": True, "disable_cbs": True},
}

# 집계 대상 안전 지표 (낮을수록 안전).
SAFETY_METRICS = ("collision_count", "near_miss_count", "conflict_resolution_rate_pct")


@dataclass(frozen=True)
class AblationRun:
    """단일 (ablation, seed) 실행 결과."""

    ablation: str
    seed: int
    collision_count: int
    near_miss_count: int
    conflicts_total: int
    conflict_resolution_rate_pct: float


@dataclass
class AblationSummary:
    """ablation 별 시드 평균 집계."""

    ablation: str
    n_runs: int = 0
    collision_count_mean: float = 0.0
    near_miss_count_mean: float = 0.0
    conflicts_total_mean: float = 0.0
    resolution_rate_mean: float = 0.0


def resolution_rate(conflicts: int, collisions: int) -> float:
    """충돌 해결률(%) — CLAUDE.md 공식. 충돌·갈등 없으면 100%."""
    denom = conflicts + collisions
    if denom <= 0:
        return 100.0
    return (1.0 - collisions / denom) * 100.0


def run_single(ablation: str, overrides: dict, seed: int, n_drones: int, duration_s: float) -> AblationRun:
    """단일 ablation 구성을 1개 시드로 실행한다."""
    scenario_cfg = {
        "drones": {"default_count": n_drones, "count": n_drones},
        "weather": {"wind_models": []},
        "failure_injection": {"drone_failure_rate": 0.0, "comms_loss_rate": 0.0},
        "logging": {"save_trajectory": False, "save_events": False},
        "ablation": overrides,
    }
    sim = SwarmSimulator(scenario_cfg=scenario_cfg, seed=seed)
    result: SimulationResult = sim.run(duration_s=duration_s)
    return AblationRun(
        ablation=ablation,
        seed=seed,
        collision_count=result.collision_count,
        near_miss_count=result.near_miss_count,
        conflicts_total=result.conflicts_total,
        conflict_resolution_rate_pct=result.conflict_resolution_rate_pct,
    )


def aggregate(runs: list[AblationRun]) -> list[AblationSummary]:
    """ablation 별 시드 평균을 계산한다."""
    summaries: list[AblationSummary] = []
    for name in ABLATIONS:
        group = [r for r in runs if r.ablation == name]
        if not group:
            continue
        summaries.append(
            AblationSummary(
                ablation=name,
                n_runs=len(group),
                collision_count_mean=float(np.mean([r.collision_count for r in group])),
                near_miss_count_mean=float(np.mean([r.near_miss_count for r in group])),
                conflicts_total_mean=float(np.mean([r.conflicts_total for r in group])),
                resolution_rate_mean=float(
                    np.mean([r.conflict_resolution_rate_pct for r in group])
                ),
            )
        )
    return summaries


def generate_markdown(summaries: list[AblationSummary], meta: dict) -> str:
    """논문 §Ablation 삽입용 markdown 표를 생성한다."""
    lines = [
        "# Safety-Net Ablation Study (Phase 286)",
        "",
        f"- Seeds: {meta['seeds']} | Drones: {meta['drones']} | Duration: {meta['duration_s']:.0f}s",
        "- 각 행은 해당 안전망 계층을 제거한 구성의 시드 평균.",
        "- 충돌 해결률 = 1 − collisions / (conflicts + collisions).",
        "",
        "| Configuration | Collisions | Near-misses | Conflicts | Resolution Rate (%) |",
        "|---|---:|---:|---:|---:|",
    ]
    for s in summaries:
        lines.append(
            f"| {s.ablation} "
            f"| {s.collision_count_mean:.2f} "
            f"| {s.near_miss_count_mean:.2f} "
            f"| {s.conflicts_total_mean:.2f} "
            f"| {s.resolution_rate_mean:.2f} |"
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Safety-net ablation study (Phase 286)")
    p.add_argument("--seeds", type=int, default=5, help="시드 개수 (0..N-1)")
    p.add_argument("--drones", type=int, default=30, help="드론 수")
    p.add_argument("--duration", type=float, default=120.0, help="시뮬레이션 길이(초)")
    p.add_argument("--out-dir", type=str, default="results/ablation", help="출력 디렉터리")
    args = p.parse_args(argv)

    runs: list[AblationRun] = []
    for name, overrides in ABLATIONS.items():
        for seed in range(args.seeds):
            print(f"[ablation] {name} seed={seed} ...", flush=True)
            runs.append(run_single(name, overrides, seed, args.drones, args.duration))

    if not runs:
        print("no successful runs", file=sys.stderr)
        return 1

    summaries = aggregate(runs)
    meta = {"seeds": args.seeds, "drones": args.drones, "duration_s": args.duration}

    out_dir = REPO_ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "ablation_report.md").write_text(generate_markdown(summaries, meta), encoding="utf-8")
    (out_dir / "ablation_results.json").write_text(
        json.dumps(
            {"meta": meta, "runs": [asdict(r) for r in runs], "summaries": [asdict(s) for s in summaries]},
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[ablation] report written to {out_dir}")
    print(generate_markdown(summaries, meta))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
