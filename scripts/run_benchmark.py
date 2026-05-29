#!/usr/bin/env python3
"""P706 — Cross-method benchmark runner.

Runs SDACS vs ORCA vs VO vs CBS across all (or selected) scenarios and seeds,
then writes per-run JSON traces + a summary CSV / printed table.

Usage examples
--------------
# Full sweep: 4 methods × 10 scenarios × 5 seeds
python scripts/run_benchmark.py --methods sdacs_hybrid orca vo cbs --seeds 0 1 2 3 4

# Ablation: SDACS layers removed one at a time
python scripts/run_benchmark.py --methods sdacs_hybrid --ablation no_reactive no_global

# Single scenario quick check
python scripts/run_benchmark.py --scenarios 01_corridor_crossing --seeds 0 1 2

Exit codes
----------
0  — all runs completed (some may have per-run failures, check the summary).
1  — fatal configuration error.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

SCENARIOS_DIR = REPO_ROOT / "benchmarks" / "scenarios"
BASELINES_DIR = REPO_ROOT / "benchmarks" / "baselines"
RESULTS_DIR = REPO_ROOT / "results"

ALL_SCENARIOS = sorted(p.name for p in SCENARIOS_DIR.iterdir() if p.is_dir())

# Map user-facing method name → baselines subdirectory name
_METHOD_DIR: dict[str, str] = {
    "sdacs_hybrid": "sdacs",
}
ALL_METHODS = ["sdacs_hybrid", "orca", "vo", "cbs"]
DEFAULT_SEEDS = list(range(5))


# ---------------------------------------------------------------------------
# Adapter loading
# ---------------------------------------------------------------------------

def _load_adapter_class(method: str):
    """동적으로 어댑터 클래스를 로드한다."""
    # Allow user-facing names to differ from baselines directory names
    dir_name = _METHOD_DIR.get(method, method)
    mod_path = f"benchmarks.baselines.{dir_name}.adapter"
    try:
        mod = importlib.import_module(mod_path)
        return mod.Adapter
    except (ImportError, AttributeError) as exc:
        raise RuntimeError(f"Cannot load adapter '{method}' (dir={dir_name}): {exc}") from exc


def _load_manifest(scenario_id: str) -> dict[str, Any]:
    """시나리오 매니페스트를 로드한다."""
    path = SCENARIOS_DIR / scenario_id / "manifest.yaml"
    if not path.exists():
        raise FileNotFoundError(f"No manifest at {path}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Single run
# ---------------------------------------------------------------------------

def _run_one(
    scenario_id: str,
    method: str,
    seed: int,
    out_dir: Path,
    wall_limit_s: float,
) -> dict[str, Any]:
    """(scenario, method, seed) 조합 1회를 실행한다."""
    os.environ["PYTHONHASHSEED"] = "0"
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"

    out_path = out_dir / f"{scenario_id}__{method}__seed{seed:03d}.json"
    if out_path.exists():
        # Resume: skip already-completed runs.
        try:
            with open(out_path, encoding="utf-8") as f:
                data = json.load(f)
            return {"status": "cached", "path": str(out_path), **_extract_summary(data)}
        except Exception:
            pass

    manifest = _load_manifest(scenario_id)
    AdapterClass = _load_adapter_class(method)
    adapter = AdapterClass(manifest, seed)

    t0 = time.perf_counter()
    try:
        trace = adapter.run(hard_wall_time_s=wall_limit_s)
        wall = time.perf_counter() - t0
        trace_dict = _trace_to_dict(trace)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(trace_dict, f, indent=2)
        summary = _extract_summary(trace_dict)
        return {"status": "ok", "path": str(out_path), "wall_s": wall, **summary}
    except Exception as exc:
        return {"status": "error", "error": str(exc), "scenario": scenario_id, "method": method, "seed": seed}


def _trace_to_dict(trace) -> dict[str, Any]:
    """SimulationTrace를 직렬화 가능한 dict로 변환한다."""
    import dataclasses
    if dataclasses.is_dataclass(trace):
        return dataclasses.asdict(trace)
    return vars(trace) if hasattr(trace, "__dict__") else {}


def _extract_summary(data: dict[str, Any]) -> dict[str, Any]:
    """trace dict에서 핵심 메트릭을 추출한다."""
    agents = data.get("agents", [])
    n_agents = len(agents)
    n_goals = sum(1 for a in agents if a.get("goal_reached_at_s") is not None)
    tick_ms = data.get("tick_latencies_ms", [])
    avg_tick = sum(tick_ms) / len(tick_ms) if tick_ms else 0.0

    rid_valid = data.get("remote_id_valid_seconds_per_agent", {})
    horizon = float(data.get("horizon_seconds", 1.0))
    rid_cr = (sum(rid_valid.values()) / max(1, n_agents * horizon)) if rid_valid else None

    return {
        "scenario": data.get("scenario_id", "?"),
        "method": data.get("method", "?"),
        "seed": data.get("seed", -1),
        "n_agents": n_agents,
        "goals_reached": n_goals,
        "goal_rate": round(n_goals / max(1, n_agents), 4),
        "avg_tick_ms": round(avg_tick, 3),
        "horizon_s": horizon,
        "rid_cr": round(rid_cr, 4) if rid_cr is not None else None,
    }


# ---------------------------------------------------------------------------
# Ablation wrappers
# ---------------------------------------------------------------------------

_ABLATION_ADAPTERS: dict[str, str] = {}


def _register_ablation(name: str, source_method: str, patch_fn) -> None:
    """어블레이션용 임시 어댑터를 동적으로 등록한다."""
    import types

    src_cls = _load_adapter_class(source_method)

    new_cls = types.new_class(
        name,
        bases=(src_cls,),
        exec_body=lambda ns: ns.update({"name": name, "run": patch_fn}),
    )
    # Inject into a fake module so importlib can find it.
    fake_mod = types.ModuleType(f"benchmarks.baselines.{name}.adapter")
    fake_mod.Adapter = new_cls
    sys.modules[fake_mod.__name__] = fake_mod
    _ABLATION_ADAPTERS[name] = name


def _setup_ablations(ablations: list[str]) -> list[str]:
    """어블레이션 어댑터들을 설정하고 실행할 메서드 목록을 반환한다."""
    extra: list[str] = []

    for abl in ablations:
        if abl == "no_reactive":
            # CBS-only: no APF/ORCA reactive layer
            def _no_reactive_run(self, hard_wall_time_s=300.0):
                from benchmarks.baselines.cbs.adapter import Adapter as CBS
                cbs = CBS(self.manifest, self.seed)
                t = cbs.run(hard_wall_time_s)
                import dataclasses
                return dataclasses.replace(t, method="sdacs_no_reactive")
            _register_ablation("sdacs_no_reactive", "sdacs_hybrid", _no_reactive_run)
            extra.append("sdacs_no_reactive")

        elif abl == "no_global":
            # ORCA-only: no CBS pre-planning
            def _no_global_run(self, hard_wall_time_s=300.0):
                from benchmarks.baselines.orca.adapter import Adapter as ORCA
                orca = ORCA(self.manifest, self.seed)
                t = orca.run(hard_wall_time_s)
                import dataclasses
                return dataclasses.replace(t, method="sdacs_no_global")
            _register_ablation("sdacs_no_global", "sdacs_hybrid", _no_global_run)
            extra.append("sdacs_no_global")

        elif abl == "no_regulatory":
            # SDACS without Remote-ID/LAANC/geofence
            def _no_reg_run(self, hard_wall_time_s=300.0):
                from benchmarks.baselines.sdacs.adapter import Adapter as SDACS
                sdacs = SDACS(self.manifest, self.seed)
                t = sdacs.run(hard_wall_time_s)
                import dataclasses
                return dataclasses.replace(
                    t,
                    method="sdacs_no_regulatory",
                    remote_id_valid_seconds_per_agent={},
                    laanc_request_latencies_ms=[],
                )
            _register_ablation("sdacs_no_regulatory", "sdacs_hybrid", _no_reg_run)
            extra.append("sdacs_no_regulatory")
        else:
            print(f"[warn] unknown ablation '{abl}', skipping", file=sys.stderr)

    return extra


# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------

def _print_table(rows: list[dict[str, Any]]) -> None:
    """결과를 ASCII 표로 출력한다."""
    from collections import defaultdict

    # Group by (scenario, method) -> aggregate over seeds
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    errors = 0
    for r in rows:
        if r.get("status") == "error":
            errors += 1
            continue
        key = (r.get("scenario", "?"), r.get("method", "?"))
        grouped[key].append(r)

    print("\n" + "=" * 80)
    print(f"  BENCHMARK RESULTS  (runs={len(rows)}  errors={errors})")
    print("=" * 80)
    header = f"{'Scenario':<30} {'Method':<22} {'Seeds':>5} {'GoalRate':>9} {'TickMs':>8} {'RID-CR':>7}"
    print(header)
    print("-" * 80)

    for (scenario, method), runs in sorted(grouped.items()):
        n = len(runs)
        goal_rate = sum(r.get("goal_rate", 0.0) for r in runs) / n
        tick_ms = sum(r.get("avg_tick_ms", 0.0) for r in runs) / n
        rid_vals = [r["rid_cr"] for r in runs if r.get("rid_cr") is not None]
        rid_cr = (sum(rid_vals) / len(rid_vals)) if rid_vals else float("nan")
        print(
            f"{scenario:<30} {method:<22} {n:>5} "
            f"{goal_rate:>9.4f} {tick_ms:>8.2f} "
            f"{rid_cr:>7.4f}" if not (rid_cr != rid_cr) else  # NaN check
            f"{scenario:<30} {method:<22} {n:>5} "
            f"{goal_rate:>9.4f} {tick_ms:>8.2f} {'n/a':>7}"
        )

    print("=" * 80 + "\n")


def _write_csv(rows: list[dict[str, Any]], out_path: Path) -> None:
    """결과를 CSV로 저장한다."""
    import csv

    fields = ["status", "scenario", "method", "seed", "n_agents",
              "goals_reached", "goal_rate", "avg_tick_ms", "horizon_s", "rid_cr", "wall_s", "error"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"[summary] CSV written → {out_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """CLI 파서를 구성한다."""
    p = argparse.ArgumentParser(
        description="P706 cross-method benchmark runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--scenarios", nargs="+", default=ALL_SCENARIOS,
        help=f"Scenario IDs to run (default: all {len(ALL_SCENARIOS)})",
    )
    p.add_argument(
        "--methods", nargs="+", default=ALL_METHODS,
        help="Methods to compare (default: sdacs_hybrid orca vo cbs)",
    )
    p.add_argument(
        "--ablation", nargs="+", default=[],
        choices=["no_reactive", "no_global", "no_regulatory"],
        metavar="NAME",
        help="Ablation variants to add (choices: no_reactive no_global no_regulatory)",
    )
    p.add_argument(
        "--seeds", nargs="+", type=int, default=DEFAULT_SEEDS,
        help="Random seeds (default: 0–4)",
    )
    p.add_argument(
        "--out-dir", type=Path, default=RESULTS_DIR / "benchmark",
        help="Directory for per-run JSON traces",
    )
    p.add_argument(
        "--csv", type=Path, default=RESULTS_DIR / "benchmark_summary.csv",
        help="Output CSV path for aggregated results",
    )
    p.add_argument(
        "--wall-limit", type=float, default=120.0,
        help="Per-run wall-clock limit in seconds (default: 120)",
    )
    p.add_argument(
        "--jobs", type=int, default=min(4, os.cpu_count() or 1),
        help="Parallel worker processes (default: min(4, cpu_count))",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="Print the run matrix without executing",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    """엔트리 포인트."""
    args = build_parser().parse_args(argv)

    # Validate scenarios
    unknown = [s for s in args.scenarios if s not in ALL_SCENARIOS]
    if unknown:
        print(f"[error] Unknown scenarios: {unknown}", file=sys.stderr)
        print(f"        Available: {ALL_SCENARIOS}", file=sys.stderr)
        return 1

    # Register ablation adapters and extend method list
    methods = list(args.methods)
    if args.ablation:
        methods += _setup_ablations(args.ablation)

    # Build run matrix
    runs = [
        (scenario, method, seed)
        for scenario in args.scenarios
        for method in methods
        for seed in args.seeds
    ]

    print(f"[benchmark] {len(runs)} runs  "
          f"({len(args.scenarios)} scenarios × {len(methods)} methods × {len(args.seeds)} seeds)")
    print(f"[benchmark] out_dir={args.out_dir}  jobs={args.jobs}  wall_limit={args.wall_limit}s")

    if args.dry_run:
        for r in runs:
            print(f"  {r[0]}  {r[1]}  seed={r[2]}")
        return 0

    args.out_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    done = 0
    t_start = time.perf_counter()

    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        futures = {
            pool.submit(_run_one, sc, meth, seed, args.out_dir, args.wall_limit): (sc, meth, seed)
            for sc, meth, seed in runs
        }
        for fut in as_completed(futures):
            sc, meth, seed = futures[fut]
            done += 1
            try:
                result = fut.result()
            except Exception as exc:
                result = {"status": "error", "error": str(exc), "scenario": sc, "method": meth, "seed": seed}

            results.append(result)
            elapsed = time.perf_counter() - t_start
            eta = (elapsed / done) * (len(runs) - done) if done else 0
            status_icon = "✓" if result.get("status") in ("ok", "cached") else "✗"
            print(
                f"  [{done}/{len(runs)}] {status_icon} {sc:30s} {meth:20s} seed={seed}"
                f"  ({elapsed:.0f}s elapsed, ~{eta:.0f}s remaining)"
            )
            if result.get("status") == "error":
                print(f"    ERROR: {result.get('error', '?')}", file=sys.stderr)

    _print_table(results)
    _write_csv(results, args.csv)

    n_ok = sum(1 for r in results if r.get("status") in ("ok", "cached"))
    n_err = len(results) - n_ok
    print(f"[benchmark] Done: {n_ok} ok, {n_err} errors  (total {time.perf_counter() - t_start:.1f}s)")
    return 0 if n_err == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
