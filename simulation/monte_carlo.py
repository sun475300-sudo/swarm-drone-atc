"""
Monte Carlo 파라미터 스윕
config/monte_carlo.yaml의 quick/full 설정 로드 → 조합 생성 → 병렬 실행
"""
from __future__ import annotations

import itertools
import logging
import time
from pathlib import Path

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
    wind_dir = config_combo.get("wind_direction_deg", 0)
    if wind > 0:
        scenario_cfg["weather"] = {
            "wind_models": [{"type": "constant", "speed_ms": wind, "direction_deg": wind_dir}],
        }

    # 장애율 오버라이드
    failure_rate = config_combo.get("failure_rate_pct", 0)
    if failure_rate > 0:
        scenario_cfg.setdefault("failure_injection", {})["drone_failure_rate"] = failure_rate / 100.0

    # 통신 손실 오버라이드
    comms_loss = config_combo.get("comms_loss_rate", 0)
    if comms_loss > 0:
        scenario_cfg.setdefault("failure_injection", {})["comms_loss_rate"] = comms_loss

    duration = config_combo.get("duration_s", 600)
    sim = SwarmSimulator(seed=seed, scenario_cfg=scenario_cfg)
    result = sim.run(duration_s=float(duration))

    # SLA 임계값 검증
    thresholds = _load_mc_config().get("acceptance_thresholds", {})
    sla_checks = result.check_acceptance(thresholds) if thresholds else {}
    sla_pass = all(sla_checks.values()) if sla_checks else True

    return {
        **config_combo,
        "seed": seed,
        "collision_count": result.collision_count,
        "near_miss_count": result.near_miss_count,
        "conflict_resolution_rate": result.conflict_resolution_rate_pct,
        "route_efficiency": result.route_efficiency_mean,
        "total_flight_time_s": result.total_flight_time_s,
        "total_distance_km": result.total_distance_km,
        "energy_efficiency_wh_per_km": result.energy_efficiency_wh_per_km,
        "failures_injected": result.failures_injected,
        "sla_pass": sla_pass,
        "sla_details": sla_checks,
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
                   "comms_loss_rate", "wind_speed_ms", "wind_direction_deg",
                   "duration_s"]
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
        combo_dict = dict(zip(param_names, combo, strict=False))
        for _run_i in range(n_per_config):
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


# 신뢰구간 리포트 기본 대상 지표 (Phase 445)
CI_DEFAULT_METRICS = (
    "collision_count",
    "near_miss_count",
    "conflict_resolution_rate",
    "route_efficiency",
)
CI_GROUP_COLS = (
    "drone_density",
    "area_size_km2",
    "failure_rate_pct",
    "comms_loss_rate",
    "wind_speed_ms",
)


def compute_confidence_intervals(
    results: list[dict],
    metrics: tuple[str, ...] = CI_DEFAULT_METRICS,
    confidence: float = 0.95,
) -> list[dict]:
    """
    Monte Carlo 결과의 설정 그룹별·지표별 신뢰구간 산출 (Phase 445)

    각 설정 조합(drone_density 등)으로 묶은 뒤, 지표마다 표본 평균과
    Student-t 기반 신뢰구간을 계산한다. 표본이 1개뿐이면 분산을 추정할 수
    없으므로 반폭(half_width)을 0.0 으로 둔다 (구간 = 점추정).

    Args:
        results: run_monte_carlo() 가 반환한 실행 결과 리스트
        metrics: 신뢰구간을 계산할 지표 이름들
        confidence: 신뢰수준 (0 < confidence < 1, 기본 0.95)

    Returns:
        그룹×지표별 통계 dict 리스트. 각 항목 키:
        group(설정값 dict), metric, n, mean, std, sem, half_width, ci_low, ci_high
    """
    if not 0.0 < confidence < 1.0:
        raise ValueError(f"confidence must be in (0, 1), got {confidence}")
    if not results:
        return []

    import pandas as pd
    from scipy import stats

    df = pd.DataFrame(results)
    group_cols = [c for c in CI_GROUP_COLS if c in df.columns]
    active_metrics = [m for m in metrics if m in df.columns]
    if not active_metrics:
        return []

    # 그룹 컬럼이 없으면 전체를 단일 그룹으로 취급
    groups = df.groupby(group_cols) if group_cols else [((), df)]
    alpha = 1.0 - confidence

    rows: list[dict] = []
    for key, sub in groups:
        key_tuple = key if isinstance(key, tuple) else (key,)
        group_label = dict(zip(group_cols, key_tuple, strict=False))
        for metric in active_metrics:
            values = sub[metric].to_numpy(dtype=float)
            # NaN(예: 실패 런)은 통계 왜곡을 피하기 위해 제외
            values = values[~np.isnan(values)]
            n = int(len(values))
            mean = float(np.mean(values)) if n > 0 else 0.0
            # ddof=1 표본표준편차, n<2 면 nan → 0.0 으로 정규화
            std = float(np.std(values, ddof=1)) if n > 1 else 0.0
            sem = std / np.sqrt(n) if n > 0 else 0.0
            if n > 1 and sem > 0.0:
                t_crit = float(stats.t.ppf(1.0 - alpha / 2.0, df=n - 1))
                half_width = t_crit * sem
            else:
                half_width = 0.0
            # 반올림된 값으로 구간을 도출해 ci_high - ci_low == 2*half_width 불변식 유지
            mean_r = round(mean, 4)
            half_r = round(half_width, 4)
            rows.append({
                "group": group_label,
                "metric": metric,
                "n": n,
                "mean": mean_r,
                "std": round(std, 4),
                "sem": round(sem, 4),
                "half_width": half_r,
                "ci_low": round(mean_r - half_r, 4),
                "ci_high": round(mean_r + half_r, 4),
            })
    return rows


def confidence_interval_report(
    results: list[dict],
    metrics: tuple[str, ...] = CI_DEFAULT_METRICS,
    confidence: float = 0.95,
) -> str:
    """compute_confidence_intervals() 결과를 사람이 읽는 표 형태 문자열로 포맷 (Phase 445)"""
    rows = compute_confidence_intervals(results, metrics=metrics, confidence=confidence)
    if not rows:
        return "신뢰구간 리포트: 데이터 없음"

    pct = int(round(confidence * 100))
    lines = [f"Monte Carlo {pct}% 신뢰구간 리포트 (설정 그룹 × 지표)"]
    last_group: dict | None = None
    for row in rows:
        if row["group"] != last_group:
            label = ", ".join(f"{k}={v}" for k, v in row["group"].items()) or "(전체)"
            lines.append(f"\n[{label}]")
            last_group = row["group"]
        lines.append(
            f"  {row['metric']:<26} "
            f"mean={row['mean']:>10.4f}  "
            f"{pct}%CI=[{row['ci_low']:>10.4f}, {row['ci_high']:>10.4f}]  "
            f"±{row['half_width']:<8.4f} (n={row['n']})"
        )
    return "\n".join(lines)


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
