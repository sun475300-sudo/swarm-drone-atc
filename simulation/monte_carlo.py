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
    """단일 설정 실행 (joblib 워커용) — SwarmSimulator 기반"""
    from simulation.simulator import SwarmSimulator

    config_combo, seed = args
    drone_count = config_combo.get("drone_density", 100)

    # 시나리오 오버라이드 구성
    scenario_cfg: dict = {
        "drones": {"default_count": drone_count},
    }

    # 기상 오버라이드
    wind = config_combo.get("wind_speed_ms", 0)
    if wind > 0:
        scenario_cfg["weather"] = {
            "wind_models": [{"type": "constant", "speed_ms": wind, "direction_deg": 0}],
        }

    # 장애율 오버라이드
    failure_rate = config_combo.get("failure_rate_pct", 0)
    if failure_rate > 0:
        scenario_cfg.setdefault("failure_injection", {})["drone_failure_rate"] = failure_rate / 100.0

    # 통신 손실 오버라이드
    comms_loss = config_combo.get("comms_loss_rate", 0)
    if comms_loss > 0:
        scenario_cfg.setdefault("failure_injection", {})["comms_loss_rate"] = comms_loss

    sim = SwarmSimulator(seed=seed, scenario_cfg=scenario_cfg)
    result = sim.run(duration_s=600.0)

    return {
        **config_combo,
        "seed": seed,
        "collision_count": result.collision_count,
        "near_miss_count": result.near_miss_count,
        "conflict_resolution_rate": result.conflict_resolution_rate_pct,
        "route_efficiency": result.route_efficiency_mean,
        "total_flight_time_s": result.total_flight_time_s,
        "total_distance_km": result.total_distance_km,
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

    # 파라미터 조합 생성
    param_names = ["drone_density", "area_size_km2", "failure_rate_pct",
                   "comms_loss_rate", "wind_speed_ms"]
    param_values = [sweep_cfg.get(p, [0]) for p in param_names]
    n_per_config = sweep_cfg.get("n_per_config", 30)

    combos = list(itertools.product(*param_values))
    total_configs = len(combos)
    total_runs = total_configs * n_per_config

    logger.info(
        "Monte Carlo [%s]: %d configs × %d runs = %d 총 실행",
        mode, total_configs, n_per_config, total_runs,
    )

    # 실행 작업 목록 생성
    tasks = []
    rng = np.random.default_rng(master_seed)
    for combo in combos:
        combo_dict = dict(zip(param_names, combo))
        for run_i in range(n_per_config):
            seed = int(rng.integers(0, 2**31))
            tasks.append((combo_dict, seed))

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

    agg_cols = {}
    for col, aggs in [
        ("collision_count", ["mean", "std", "max"]),
        ("near_miss_count", ["mean", "max"]),
        ("conflict_resolution_rate", ["mean"]),
        ("route_efficiency", ["mean"]),
        ("total_flight_time_s", ["mean"]),
        ("total_distance_km", ["mean"]),
    ]:
        if col in df.columns:
            agg_cols[col] = aggs

    if not agg_cols:
        return df.describe().to_string()

    summary = df.groupby(existing_cols).agg(agg_cols).round(4)

    return summary.to_string()
