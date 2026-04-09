"""
Monte Carlo 파라미터 스윕 실행기

config/monte_carlo.yaml 의 full_sweep / quick_sweep 설정을 읽어
지정된 조합을 joblib 병렬로 실행하고 결과를 parquet/csv로 저장한다.

CLI:
    python simulation/monte_carlo_runner.py --mode quick
    python simulation/monte_carlo_runner.py --mode full --workers 8
"""
from __future__ import annotations

import argparse
import itertools
import logging
import os
import time
from pathlib import Path
from typing import Any

import numpy as np
import yaml

logger = logging.getLogger(__name__)


# ── 단일 실행 (joblib 직렬화 가능 최상위 함수) ──────────────────────────

def run_one(params: dict[str, Any]) -> dict[str, Any]:
    """
    단일 시뮬레이션 실행.
    joblib 워커에서 호출되므로 최상위 함수여야 한다.

    Parameters
    ----------
    params : dict
        seed, drone_density, area_size_km2, failure_rate_pct,
        comms_loss_rate, wind_speed_ms, duration_s, config_path
    """
    from simulation.simulator import SwarmSimulator

    seed          = int(params["seed"])
    n_drones      = int(params["drone_density"])
    area_km2      = float(params["area_size_km2"])
    fail_rate     = float(params["failure_rate_pct"]) / 100.0
    comms_loss    = float(params["comms_loss_rate"])
    wind_ms       = float(params["wind_speed_ms"])
    duration_s    = float(params.get("duration_s", 600.0))
    config_path   = str(params.get("config_path", "config/default_simulation.yaml"))

    # 시나리오 오버라이드 딕셔너리
    side_m   = float(np.sqrt(area_km2) * 1000.0)
    half     = side_m / 2.0
    scenario: dict[str, Any] = {
        "airspace": {
            "bounds_km": {
                "x": [-half / 1000, half / 1000],
                "y": [-half / 1000, half / 1000],
                "z": [0, 0.15],
            }
        },
        "drones": {"count": n_drones},
        "weather": {
            "wind_models": [
                {"type": "constant", "speed_ms": wind_ms, "direction_deg": 45.0}
            ]
        },
        "failure_injection": {
            "drone_failure_rate": fail_rate,
            "comms_loss_rate":    comms_loss,
        },
    }

    try:
        sim = SwarmSimulator(
            config_path=config_path,
            scenario_cfg=scenario,
            seed=seed,
        )
        result = sim.run(duration_s=duration_s)
        row = result.to_dict()
    except Exception as exc:  # noqa: BLE001
        logger.warning("run_one failed seed=%d: %s", seed, exc)
        row = {
            "seed": seed, "scenario": "monte_carlo",
            "duration_s": duration_s, "n_drones": n_drones,
            "collision_count": -1,  # 실패 표시
            "error": str(exc),
        }

    # 파라미터 열 추가
    row.update({
        "param_drone_density":   n_drones,
        "param_area_size_km2":   area_km2,
        "param_failure_rate_pct": params["failure_rate_pct"],
        "param_comms_loss_rate": comms_loss,
        "param_wind_speed_ms":   wind_ms,
    })
    return row


# ── 파라미터 그리드 생성 ─────────────────────────────────────────────────

def build_param_grid(
    sweep_cfg: dict[str, Any],
    master_seed: int,
    config_path: str,
    duration_s: float,
) -> list[dict[str, Any]]:
    """
    sweep_cfg 의 레벨 값들로 Cartesian product를 만들고
    n_per_config 개의 독립 시드를 할당한다.
    """
    level_keys = [
        "drone_density",
        "area_size_km2",
        "failure_rate_pct",
        "comms_loss_rate",
        "wind_speed_ms",
    ]
    levels = [sweep_cfg[k] for k in level_keys]
    n_per  = int(sweep_cfg.get("n_per_config", 10))

    rng    = np.random.default_rng(master_seed)
    params_list: list[dict[str, Any]] = []

    for combo in itertools.product(*levels):
        combo_dict = dict(zip(level_keys, combo))
        seeds = rng.integers(0, 2**31, size=n_per)
        for s in seeds:
            params_list.append({
                **combo_dict,
                "seed":        int(s),
                "config_path": config_path,
                "duration_s":  duration_s,
            })

    return params_list


# ── 병렬 실행 ────────────────────────────────────────────────────────────

def run_monte_carlo(
    config_path: str = "config/monte_carlo.yaml",
    sim_config_path: str = "config/default_simulation.yaml",
    mode: str = "quick",
    n_workers: int | None = None,
    duration_s: float = 600.0,
) -> "pd.DataFrame":
    """
    Monte Carlo 스윕 실행 → DataFrame 반환 (자동 저장 포함).

    Parameters
    ----------
    config_path     : monte_carlo.yaml 경로
    sim_config_path : default_simulation.yaml 경로
    mode            : "quick" | "full"
    n_workers       : None = yaml 설정값 사용
    duration_s      : 시뮬레이션 길이(초)
    """
    import pandas as pd
    try:
        from joblib import Parallel, delayed
        _has_joblib = True
    except ImportError:
        _has_joblib = False

    # ── YAML 로드 ────────────────────────────────────────────────────────
    cfg_path = Path(config_path)
    if not cfg_path.exists():
        raise FileNotFoundError(f"Monte Carlo 설정 파일 없음: {cfg_path}")

    with open(cfg_path, encoding="utf-8") as f:
        mc_cfg = yaml.safe_load(f)

    sweep_key = "quick_sweep" if mode == "quick" else "full_sweep"
    sweep_cfg = mc_cfg.get(sweep_key, mc_cfg.get("quick_sweep"))
    master_seed = int(mc_cfg.get("master_seed", 42))
    parallel_cfg = mc_cfg.get("parallel", {})
    output_cfg   = mc_cfg.get("output",   {})
    thresholds   = mc_cfg.get("acceptance_thresholds", {})

    workers = n_workers
    if workers is None:
        w = parallel_cfg.get("n_workers", -1)
        workers = None if w == -1 else int(w)
    backend = parallel_cfg.get("backend", "loky")

    # ── 파라미터 그리드 ──────────────────────────────────────────────────
    params_list = build_param_grid(
        sweep_cfg, master_seed, sim_config_path, duration_s
    )
    total = len(params_list)
    logger.info("[MC] mode=%s  runs=%d  workers=%s", mode, total, workers)
    print(f"[MC] {mode} sweep: {total} runs, workers={workers}")

    t0 = time.monotonic()

    # ── 실행 ─────────────────────────────────────────────────────────────
    if _has_joblib and (workers is None or workers != 1):
        results = Parallel(n_jobs=workers or -1, backend=backend, verbose=5)(
            delayed(run_one)(p) for p in params_list
        )
    else:
        # 순차 실행 (fallback / 단일 워커)
        results = []
        for i, p in enumerate(params_list):
            results.append(run_one(p))
            if (i + 1) % max(1, total // 20) == 0:
                pct = 100 * (i + 1) / total
                elapsed = time.monotonic() - t0
                print(f"  {pct:.0f}%  {i+1}/{total}  elapsed={elapsed:.1f}s")

    elapsed = time.monotonic() - t0
    print(f"[MC] 완료: {elapsed:.1f}s ({elapsed/total*1000:.1f} ms/run)")

    # ── 결과 DataFrame ───────────────────────────────────────────────────
    df = pd.DataFrame(results)

    # ── 합격 판정 열 추가 ────────────────────────────────────────────────
    if "collision_count" in df.columns:
        df["pass_no_collision"] = df["collision_count"] == 0

    if "conflict_resolution_rate_pct" in df.columns:
        thr = float(thresholds.get("conflict_resolution_rate_pct", 99.5))
        df["pass_conflict_res"] = df["conflict_resolution_rate_pct"] >= thr

    if "route_efficiency_mean" in df.columns:
        thr = float(thresholds.get("route_efficiency_max", 1.15))
        df["pass_route_eff"] = df["route_efficiency_mean"] <= thr

    # ── 저장 ─────────────────────────────────────────────────────────────
    out_dir = Path(output_cfg.get("directory", "data/results"))
    out_dir.mkdir(parents=True, exist_ok=True)
    fmt = output_cfg.get("format", "parquet")
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    stem = f"mc_{mode}_{timestamp}"

    if fmt == "parquet":
        try:
            out_path = out_dir / f"{stem}.parquet"
            df.to_parquet(out_path, index=False, compression="snappy"
                          if output_cfg.get("compress", True) else None)
            print(f"[MC] 저장: {out_path}")
        except Exception as exc:
            logger.warning("parquet 저장 실패 (%s), CSV로 전환", exc)
            fmt = "csv"

    if fmt != "parquet":
        out_path = out_dir / f"{stem}.csv"
        df.to_csv(out_path, index=False)
        print(f"[MC] 저장: {out_path}")

    # ── 요약 통계 ────────────────────────────────────────────────────────
    _print_summary(df, thresholds)

    return df


# ── 요약 출력 ────────────────────────────────────────────────────────────

def _print_summary(df: "pd.DataFrame", thresholds: dict) -> None:
    import pandas as pd  # noqa: F401

    print("\n" + "=" * 60)
    print("Monte Carlo 결과 요약")
    print("=" * 60)

    n_total = len(df)
    failed  = df["collision_count"].lt(0).sum() if "collision_count" in df.columns else 0
    n_valid = n_total - failed
    print(f"  총 실행: {n_total}  |  성공: {n_valid}  |  오류: {failed}")

    if n_valid == 0:
        print("  유효한 결과 없음")
        return

    valid = df[df["collision_count"] >= 0] if "collision_count" in df.columns else df

    for col, label in [
        ("collision_count",            "충돌 횟수"),
        ("near_miss_count",            "Near-miss 횟수"),
        ("conflict_resolution_rate_pct", "충돌 해결률 (%)"),
        ("route_efficiency_mean",      "경로 효율 (mean)"),
        ("advisory_latency_p50",       "어드바이저리 지연 P50 (s)"),
        ("advisory_latency_p99",       "어드바이저리 지연 P99 (s)"),
    ]:
        if col in valid.columns:
            s = valid[col].dropna()
            print(f"  {label:30s} mean={s.mean():.3f}  p50={s.median():.3f}"
                  f"  p99={s.quantile(0.99):.3f}  max={s.max():.3f}")

    # 합격률
    for col in ["pass_no_collision", "pass_conflict_res", "pass_route_eff"]:
        if col in valid.columns:
            rate = valid[col].mean() * 100
            print(f"  {col:30s}: {rate:.1f}% 합격")

    print("=" * 60 + "\n")


# ── CLI ──────────────────────────────────────────────────────────────────

def main() -> None:
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    parser = argparse.ArgumentParser(description="Monte Carlo 시뮬레이션 스윕")
    parser.add_argument("--mode",       default="quick", choices=["quick", "full"])
    parser.add_argument("--config",     default="config/monte_carlo.yaml")
    parser.add_argument("--sim-config", default="config/default_simulation.yaml")
    parser.add_argument("--workers",    type=int, default=None,
                        help="병렬 워커 수 (-1=all cores)")
    parser.add_argument("--duration",   type=float, default=600.0,
                        help="시뮬레이션 길이 (초)")
    args = parser.parse_args()

    run_monte_carlo(
        config_path=args.config,
        sim_config_path=args.sim_config,
        mode=args.mode,
        n_workers=args.workers,
        duration_s=args.duration,
    )


if __name__ == "__main__":
    main()
