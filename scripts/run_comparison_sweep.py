#!/usr/bin/env python3
"""P706 비교 실험 스윕 — 전체 (scenario × method × seed) 셀 실행.

Usage:
    # 전체 스윕 (10 scenarios × 4 methods × 30 seeds = 1200 runs)
    python scripts/run_comparison_sweep.py

    # 빠른 검증 (scenario 1개 × 2 methods × 3 seeds = 6 runs)
    python scripts/run_comparison_sweep.py --quick

    # 특정 시나리오만
    python scripts/run_comparison_sweep.py --scenarios 01_corridor_crossing 02_dense_intersection

    # 병렬 워커 수 조정 (기본: CPU 코어 수)
    python scripts/run_comparison_sweep.py --workers 4

Output:
    results/<scenario>/<method>/seed<N>.json  (per-run trace)
    results/summary.csv                        (aggregated metrics table)
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

ALL_SCENARIOS = [
    "01_corridor_crossing",
    "02_dense_intersection",
    "03_emergency_landing",
    "04_no_fly_zone",
    "05_weather_diversion",
    "06_priority_aircraft",
    "07_communication_loss",
    "08_stress_high_density",
    "09_stress_failure_cascade",
    "10_stress_adversarial_swarm",
]
ALL_METHODS = ["orca", "vo", "cbs", "sdacs_hybrid"]
QUICK_SCENARIOS = ["01_corridor_crossing"]
QUICK_METHODS = ["orca", "sdacs_hybrid"]
QUICK_SEEDS = [0, 1, 2]
ALL_SEEDS = list(range(30))

METRIC_KEYS = [
    "near_miss_rate",
    "min_separation_m",
    "path_efficiency",
    "makespan_s",
    "flowtime_s",
    "airspace_utilization",
    "rid_compliance_rate",
    "rtf",
]


@dataclass
class RunSpec:
    scenario: str
    method: str
    seed: int
    out_path: Path
    hard_wall_s: float = 120.0


@dataclass
class RunResult:
    spec: RunSpec
    success: bool
    wall_s: float
    metrics: dict[str, Any] = field(default_factory=dict)
    error: str = ""


def _run_one(spec: RunSpec) -> RunResult:
    """단일 (scenario, method, seed) 셀 실행 — subprocess worker."""
    import yaml  # type: ignore

    from benchmarks.baselines._base import make_adapter
    from src.analytics.metrics import Evaluator

    t0 = time.perf_counter()
    manifest_path = REPO_ROOT / "benchmarks" / "scenarios" / spec.scenario / "manifest.yaml"
    if not manifest_path.exists():
        return RunResult(spec, False, 0.0, error=f"manifest not found: {manifest_path}")

    with open(manifest_path, encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    try:
        adapter = make_adapter(spec.method, manifest, spec.seed)
        trace = adapter.run(hard_wall_time_s=spec.hard_wall_s)
    except Exception as exc:
        return RunResult(spec, False, time.perf_counter() - t0, error=str(exc))

    wall_s = time.perf_counter() - t0

    try:
        metrics = Evaluator().evaluate(trace)
    except Exception as exc:
        metrics = {"eval_error": str(exc)}

    spec.out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {**metrics, "scenario": spec.scenario, "method": spec.method, "seed": spec.seed}
    with open(spec.out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=float, sort_keys=True)

    return RunResult(spec, True, wall_s, metrics)


def _build_specs(
    scenarios: list[str],
    methods: list[str],
    seeds: list[int],
    results_dir: Path,
    hard_wall_s: float,
    skip_existing: bool,
) -> list[RunSpec]:
    specs = []
    for sc in scenarios:
        for method in methods:
            for seed in seeds:
                out = results_dir / sc / method / f"seed{seed}.json"
                if skip_existing and out.exists():
                    continue
                specs.append(RunSpec(sc, method, seed, out, hard_wall_s))
    return specs


def _write_summary(results: list[RunResult], out_path: Path) -> None:
    rows = []
    for r in results:
        if not r.success:
            continue
        row = {
            "scenario": r.spec.scenario,
            "method": r.spec.method,
            "seed": r.spec.seed,
            "wall_s": round(r.wall_s, 3),
        }
        for k in METRIC_KEYS:
            row[k] = r.metrics.get(k, "")
        rows.append(row)

    if not rows:
        return

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["scenario", "method", "seed", "wall_s"] + METRIC_KEYS
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    """``main`` 동작을 수행한다."""
    p = argparse.ArgumentParser(description="P706 비교 실험 스윕")
    p.add_argument("--quick", action="store_true",
                   help=f"빠른 검증: {QUICK_SCENARIOS} × {QUICK_METHODS} × seeds 0-2")
    p.add_argument("--scenarios", nargs="+", default=None,
                   help="실행할 시나리오 ID 목록 (기본: 전체)")
    p.add_argument("--methods", nargs="+", default=None,
                   help="실행할 방법 목록 (기본: 전체)")
    p.add_argument("--seeds", nargs="+", type=int, default=None,
                   help="실행할 시드 목록 (기본: 0-29)")
    p.add_argument("--workers", type=int, default=None,
                   help="병렬 워커 수 (기본: CPU 코어 수)")
    p.add_argument("--results-dir", default="results",
                   help="결과 저장 디렉토리 (기본: results)")
    p.add_argument("--hard-wall-s", type=float, default=120.0,
                   help="셀당 벽시계 시간 상한 (초, 기본: 120)")
    p.add_argument("--skip-existing", action="store_true",
                   help="이미 결과 파일이 있는 셀은 건너뜀")
    p.add_argument("--summary-out", default=None,
                   help="요약 CSV 경로 (기본: <results-dir>/summary.csv)")
    args = p.parse_args(argv)

    if args.quick:
        scenarios = QUICK_SCENARIOS
        methods = QUICK_METHODS
        seeds = QUICK_SEEDS
    else:
        scenarios = args.scenarios or ALL_SCENARIOS
        methods = args.methods or ALL_METHODS
        seeds = args.seeds or ALL_SEEDS

    results_dir = REPO_ROOT / args.results_dir
    summary_out = Path(args.summary_out) if args.summary_out else results_dir / "summary.csv"

    specs = _build_specs(scenarios, methods, seeds, results_dir, args.hard_wall_s, args.skip_existing)
    total = len(specs)
    if total == 0:
        print("[sweep] 실행할 셀 없음 (--skip-existing 이거나 빈 조합)")
        return 0

    print(f"[sweep] {total}개 셀 실행 시작 (scenarios={len(scenarios)}, methods={len(methods)}, seeds={len(seeds)})")
    print(f"[sweep] workers={args.workers or 'auto'}, hard_wall_s={args.hard_wall_s}")

    results: list[RunResult] = []
    done = 0
    failed = 0
    t_sweep = time.perf_counter()

    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(_run_one, spec): spec for spec in specs}
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            done += 1
            if result.success:
                nmr = result.metrics.get("near_miss_rate", "?")
                rtf = result.metrics.get("rtf", "?")
                print(
                    f"  [{done:4d}/{total}] {result.spec.scenario}/{result.spec.method}/seed{result.spec.seed}"
                    f"  nmr={nmr}  rtf={rtf}  ({result.wall_s:.1f}s)"
                )
            else:
                failed += 1
                print(
                    f"  [{done:4d}/{total}] FAIL {result.spec.scenario}/{result.spec.method}/seed{result.spec.seed}"
                    f"  {result.error}",
                    file=sys.stderr,
                )

    elapsed = time.perf_counter() - t_sweep
    print(f"\n[sweep] 완료: {done - failed}/{total} 성공, {failed} 실패, {elapsed:.1f}s")

    _write_summary(results, summary_out)
    print(f"[sweep] 요약 → {summary_out}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
