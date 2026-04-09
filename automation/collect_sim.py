"""
시뮬레이션 데이터 수집 모듈
==========================
Monte Carlo 스윕 및 시나리오 벤치마크를 실행하고
구조화된 결과를 반환한다.
"""
from __future__ import annotations

import logging
import sys
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import numpy as np

# 프로젝트 루트를 sys.path에 추가
_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

logger = logging.getLogger("automation.collect_sim")


# ── Monte Carlo 수집 ──────────────────────────────────────────

def collect_monte_carlo(
    mode: str = "quick",
    override_params: Optional[dict] = None,
) -> dict[str, Any]:
    """
    Monte Carlo 스윕을 실행하고 결과를 구조화된 dict로 반환.

    Args:
        mode: "quick" 또는 "full"
        override_params: MC 설정 오버라이드 (선택)

    Returns:
        {
            "type": "monte_carlo",
            "mode": str,
            "timestamp": str (ISO),
            "elapsed_s": float,
            "total_runs": int,
            "raw_results": list[dict],
            "summary": dict,      # 집계 통계
        }
    """
    from simulation.monte_carlo import run_monte_carlo

    logger.info("Monte Carlo [%s] 수집 시작", mode)
    t0 = time.monotonic()

    results = run_monte_carlo(mode=mode)

    elapsed = time.monotonic() - t0
    logger.info("Monte Carlo 완료: %d runs, %.1f초", len(results), elapsed)

    # 집계 통계 계산
    summary = _summarize_mc(results)

    return {
        "type": "monte_carlo",
        "mode": mode,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "elapsed_s": round(elapsed, 2),
        "total_runs": len(results),
        "raw_results": results,
        "summary": summary,
    }


def _summarize_mc(results: list[dict]) -> dict:
    """MC 결과 집계 통계."""
    if not results:
        return {}

    import pandas as pd

    df = pd.DataFrame(results)
    metric_cols = [
        "collision_count", "near_miss_count",
        "conflict_resolution_rate", "route_efficiency",
        "total_flight_time_s", "total_distance_km",
        "energy_efficiency_wh_per_km",
    ]
    existing = [c for c in metric_cols if c in df.columns]

    stats = {}
    for col in existing:
        vals = df[col].dropna()
        stats[col] = {
            "mean": round(float(vals.mean()), 4),
            "std": round(float(vals.std()), 4),
            "min": round(float(vals.min()), 4),
            "max": round(float(vals.max()), 4),
            "p50": round(float(vals.median()), 4),
            "p95": round(float(vals.quantile(0.95)), 4),
        }

    # SLA 통과율
    if "sla_pass" in df.columns:
        stats["sla_pass_rate"] = round(float(df["sla_pass"].mean()), 4)

    return stats


# ── 시나리오 벤치마크 수집 ────────────────────────────────────

def collect_scenario_benchmarks(
    scenarios: Optional[list[str]] = None,
    n_runs: int = 3,
    seed: int = 42,
) -> dict[str, Any]:
    """
    모든 (또는 지정된) 시나리오를 실행하고 결과를 반환.

    Args:
        scenarios: 실행할 시나리오 이름 목록 (None=전체)
        n_runs: 시나리오당 반복 횟수
        seed: 기본 시드

    Returns:
        {
            "type": "scenario_benchmark",
            "timestamp": str,
            "elapsed_s": float,
            "scenarios": {
                "scenario_name": {
                    "runs": list[dict],
                    "summary": dict,
                }
            }
        }
    """
    from simulation.scenario_runner import list_scenarios, run_scenario

    logger.info("시나리오 벤치마크 수집 시작 (n_runs=%d)", n_runs)
    t0 = time.monotonic()

    # 시나리오 목록 결정
    if scenarios is None:
        all_scenarios = list_scenarios()
        scenarios = []
        for s in all_scenarios:
            if isinstance(s, dict):
                scenarios.append(s.get("name", str(s)))
            else:
                scenarios.append(str(s))

    results = {}
    for name in scenarios:
        logger.info("  시나리오 [%s] 실행 중...", name)
        try:
            runs = run_scenario(name, n_runs=n_runs, seed=seed)
            summary = _summarize_scenario(runs)
            results[name] = {"runs": runs, "summary": summary}
        except Exception as e:
            logger.error("  시나리오 [%s] 실패: %s", name, e)
            results[name] = {"runs": [], "summary": {}, "error": str(e)}

    elapsed = time.monotonic() - t0
    logger.info("시나리오 벤치마크 완료: %d개, %.1f초", len(results), elapsed)

    return {
        "type": "scenario_benchmark",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "elapsed_s": round(elapsed, 2),
        "scenarios": results,
    }


def _summarize_scenario(runs: list[dict]) -> dict:
    """시나리오 실행 결과 집계."""
    if not runs:
        return {}

    numeric_keys = [
        k for k, v in runs[0].items()
        if isinstance(v, (int, float)) and k != "run_idx"
    ]
    summary = {}
    for k in numeric_keys:
        vals = [r[k] for r in runs if k in r and r[k] is not None]
        if vals:
            arr = np.array(vals, dtype=float)
            summary[k] = {
                "mean": round(float(arr.mean()), 4),
                "std": round(float(arr.std()), 4),
                "min": round(float(arr.min()), 4),
                "max": round(float(arr.max()), 4),
            }
    return summary
