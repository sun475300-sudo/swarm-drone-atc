"""
시나리오 러너 — YAML 시나리오 로드 및 반복 실행
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import yaml

logger = logging.getLogger("sdacs.scenario")

_ROOT = Path(__file__).resolve().parent.parent
SCENARIO_DIR = _ROOT / "config" / "scenario_params"


def list_scenarios() -> list[dict]:
    """사용 가능한 시나리오 목록 반환"""
    scenarios = []
    for f in sorted(SCENARIO_DIR.glob("*.yaml")):
        with open(f, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        scenarios.append({
            "name": f.stem,
            "scenario_id": data.get("scenario", f.stem),
            "description": data.get("description", ""),
            "file": str(f),
        })
    return scenarios


def load_scenario(name: str) -> dict:
    """시나리오 YAML 로드 (이름 = 파일 stem)"""
    path = SCENARIO_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"시나리오 '{name}' 없음: {path}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_scenario(
    name: str,
    runs: int = 1,
    base_seed: int = 42,
    duration_s: Optional[float] = None,
    # legacy compat
    n_runs: int | None = None,
    seed: int | None = None,
    **kwargs,
) -> list:
    """시나리오를 N회 반복 실행"""
    from simulation.engine import SimulationEngine
    from simulation.metrics import SimulationMetrics

    # legacy arg compat
    if n_runs is not None:
        runs = n_runs
    if seed is not None:
        base_seed = seed

    params = load_scenario(name)
    results = []

    for i in range(runs):
        s = base_seed + i
        logger.info("━━ 시나리오 [%s] 실행 #%d (seed=%d) ━━", name, i + 1, s)

        engine = SimulationEngine(
            seed=s,
            duration_s=duration_s or params.get(
                "simulation_duration_s",
                params.get("simulation_duration_min", 10) * 60
            ),
            scenario_overrides=params,
        )
        engine.apply_scenario(params)
        metrics = engine.run()
        results.append(metrics)

        logger.info("  결과: 충돌=%d, 근접위반=%d, 경로효율=%.3f",
                     metrics.collision_count, metrics.near_miss_count,
                     metrics.route_efficiency)

    return results


def aggregate_results(results: list) -> dict:
    """다중 실행 결과 집계"""
    n = len(results)
    return {
        "runs": n,
        "avg_collision": sum(r.collision_count for r in results) / n,
        "avg_near_miss": sum(r.near_miss_count for r in results) / n,
        "avg_route_efficiency": sum(r.route_efficiency for r in results) / n,
        "avg_conflict_resolution_rate": sum(
            r.conflict_resolution_rate for r in results
        ) / n,
        "avg_battery_remaining_pct": float(np.mean(
            [r.avg_battery_remaining_pct for r in results]
        )),
        "total_routes_completed": sum(r.routes_completed for r in results),
    }
