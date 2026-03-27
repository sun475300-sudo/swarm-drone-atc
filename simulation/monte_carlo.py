"""
Monte Carlo 파라미터 스윕
config/monte_carlo.yaml의 quick/full 설정 로드 → 조합 생성 → 병렬 실행
"""
from __future__ import annotations

import itertools
import logging
import time
from pathlib import Path
from typing import Optional

import numpy as np
import yaml

logger = logging.getLogger("sdacs.monte_carlo")

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "monte_carlo.yaml"


def _load_mc_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _run_single(args: tuple) -> dict:
    """단일 설정 실행 (joblib 워커용)"""
    from simulation.simulator import SwarmSimulator

    config_combo, seed, duration_s = args
    wind = config_combo.get("wind_speed_ms", 0)

    scenario_cfg: dict = {
        "simulation": {
            "duration_s": duration_s,
            "n_drones": config_combo.get("drone_density", 100),
        },
    }
    if wind > 0:
        scenario_cfg["wind_models"] = [
            {"type": "constant", "speed_ms": wind, "direction_deg": 0}
        ]

    sim = SwarmSimulator(seed=seed, scenario_cfg=scenario_cfg)
    result = sim.run()

    return {
        **config_combo,
        "seed": seed,
        "collision_count": result.collision_count,
        "near_miss_count": result.near_miss_count,
        "conflict_resolution_rate": result.conflict_resolution_rate_pct,
        "route_efficiency": result.route_efficiency_mean,
        "avg_battery_pct": result.avg_battery_remaining_pct,
        "routes_completed": result.clearances_approved,
    }


def run_monte_carlo(mode: str = "quick") -> list[dict]:
    """
    Monte Carlo 파라미터 스윕 실행

    Args:
        mode: "quick" 또는 "full"

    Returns:
        결과 리스트 (각 항목 = 1회 실행)
    """
    mc_cfg = _load_mc_config()
    sweep_cfg = mc_cfg.get(f"{mode}_sweep", mc_cfg.get("quick_sweep"))
    parallel_cfg = mc_cfg.get("parallel", {})
    master_seed = mc_cfg.get("master_seed", 42)

    # duration_s: 스윕별 설정 → 공통 설정 → 기본값 600s
    duration_s = float(
        sweep_cfg.get("duration_s",
        mc_cfg.get("simulation", {}).get("duration_s", 600.0))
    )

    # 파라미터 조합 생성
    param_names = ["drone_density", "area_size_km2", "failure_rate_pct",
                   "comms_loss_rate", "wind_speed_ms"]
    param_values = [sweep_cfg.get(p, [0]) for p in param_names]
    n_per_config = sweep_cfg.get("n_per_config", 30)

    combos = list(itertools.product(*param_values))
    total_configs = len(combos)
    total_runs = total_configs * n_per_config

    logger.info(
        "Monte Carlo [%s]: %d configs × %d runs = %d 총 실행 (duration=%.0fs)",
        mode, total_configs, n_per_config, total_runs, duration_s,
    )

    # 실행 작업 목록 생성
    tasks = []
    rng = np.random.default_rng(master_seed)
    for combo in combos:
        combo_dict = dict(zip(param_names, combo))
        for run_i in range(n_per_config):
            seed = int(rng.integers(0, 2**31))
            tasks.append((combo_dict, seed, duration_s))

    # 병렬 실행
    n_workers = parallel_cfg.get("n_workers", -1)
    t0 = time.time()

    try:
        from joblib import Parallel, delayed
        results = Parallel(n_jobs=n_workers, backend="loky")(
            delayed(_run_single)(t) for t in tasks
        )
    except ImportError:
        logger.warning("joblib 미설치 — 순차 실행합니다")
        results = [_run_single(t) for t in tasks]

    elapsed = time.time() - t0
    logger.info("Monte Carlo 완료: %.1f초 (%d runs)", elapsed, total_runs)

    return results


def summarize_results(results: list[dict]) -> str:
    """Monte Carlo 결과 테이블 요약"""
    import pandas as pd

    df = pd.DataFrame(results)
    group_cols = ["drone_density", "area_size_km2", "failure_rate_pct",
                  "comms_loss_rate", "wind_speed_ms"]
    existing_cols = [c for c in group_cols if c in df.columns]

    if not existing_cols:
        return df.describe().to_string()

    summary = df.groupby(existing_cols).agg({
        "collision_count": ["mean", "std", "max"],
        "near_miss_count": ["mean", "max"],
        "conflict_resolution_rate": "mean",
        "route_efficiency": "mean",
        "avg_battery_pct": "mean",
    }).round(4)

    return summary.to_string()
