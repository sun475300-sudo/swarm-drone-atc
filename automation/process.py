"""
데이터 가공 모듈
===============
수집된 원시 데이터를 필터링, 통계 계산, 포맷 변환한다.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np

logger = logging.getLogger("automation.process")


# ── 시뮬레이션 결과 가공 ──────────────────────────────────────

def process_sim_data(
    mc_data: Optional[dict] = None,
    scenario_data: Optional[dict] = None,
    filters: Optional[dict] = None,
) -> dict[str, Any]:
    """
    시뮬레이션 수집 결과를 필터링·집계·정리.

    Args:
        mc_data: collect_monte_carlo()의 반환값
        scenario_data: collect_scenario_benchmarks()의 반환값
        filters: 필터 조건 (선택)
            - min_collision_resolution_rate: float (0~100)
            - max_collision_count: int
            - drone_densities: list[int]

    Returns:
        {
            "type": "processed_sim",
            "timestamp": str,
            "mc": { ... },         # 가공된 MC 결과
            "scenarios": { ... },  # 가공된 시나리오 결과
        }
    """
    filters = filters or {}
    logger.info("시뮬레이션 데이터 가공 시작")

    result = {
        "type": "processed_sim",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mc": {},
        "scenarios": {},
    }

    # MC 결과 가공
    if mc_data and mc_data.get("raw_results"):
        result["mc"] = _process_mc(mc_data, filters)

    # 시나리오 결과 가공
    if scenario_data and scenario_data.get("scenarios"):
        result["scenarios"] = _process_scenarios(scenario_data, filters)

    return result


def _process_mc(mc_data: dict, filters: dict) -> dict:
    """Monte Carlo 결과 필터링 및 집계."""
    import pandas as pd

    raw = mc_data["raw_results"]
    df = pd.DataFrame(raw)

    original_count = len(df)

    # 필터 적용
    min_cr = filters.get("min_collision_resolution_rate")
    if min_cr is not None and "conflict_resolution_rate" in df.columns:
        df = df[df["conflict_resolution_rate"] >= min_cr]

    max_col = filters.get("max_collision_count")
    if max_col is not None and "collision_count" in df.columns:
        df = df[df["collision_count"] <= max_col]

    densities = filters.get("drone_densities")
    if densities and "drone_density" in df.columns:
        df = df[df["drone_density"].isin(densities)]

    filtered_count = len(df)
    logger.info("  MC 필터: %d → %d rows", original_count, filtered_count)

    # 드론 밀도별 집계
    group_stats = {}
    if "drone_density" in df.columns and len(df) > 0:
        for density, group in df.groupby("drone_density"):
            metrics = {}
            for col in ["collision_count", "near_miss_count",
                        "conflict_resolution_rate", "route_efficiency",
                        "energy_efficiency_wh_per_km"]:
                if col in group.columns:
                    vals = group[col].dropna()
                    metrics[col] = {
                        "mean": round(float(vals.mean()), 4),
                        "std": round(float(vals.std()), 4),
                        "p50": round(float(vals.median()), 4),
                        "p95": round(float(vals.quantile(0.95)), 4),
                    }
            group_stats[int(density)] = metrics

    # SLA 위반 분석
    sla_violations = []
    if "sla_pass" in df.columns:
        failures = df[~df["sla_pass"]]
        if len(failures) > 0:
            for _, row in failures.head(20).iterrows():
                violation = {
                    "drone_density": row.get("drone_density"),
                    "wind_speed_ms": row.get("wind_speed_ms"),
                    "failure_rate_pct": row.get("failure_rate_pct"),
                }
                if "sla_details" in row and isinstance(row["sla_details"], dict):
                    failed_checks = [k for k, v in row["sla_details"].items() if not v]
                    violation["failed_checks"] = failed_checks
                sla_violations.append(violation)

    return {
        "mode": mc_data.get("mode"),
        "total_runs": mc_data.get("total_runs"),
        "filtered_runs": filtered_count,
        "overall_summary": mc_data.get("summary", {}),
        "by_density": group_stats,
        "sla_pass_rate": round(float(df["sla_pass"].mean()), 4) if "sla_pass" in df.columns and len(df) > 0 else None,
        "sla_violations_sample": sla_violations,
    }


def _process_scenarios(scenario_data: dict, filters: dict) -> dict:
    """시나리오 벤치마크 결과 정리."""
    processed = {}
    for name, data in scenario_data.get("scenarios", {}).items():
        if data.get("error"):
            processed[name] = {"status": "error", "error": data["error"]}
            continue

        summary = data.get("summary", {})

        # 핵심 KPI 추출
        kpis = {}
        for key in ["collision_count", "near_miss_count",
                     "conflict_resolution_rate", "total_flight_time_s",
                     "route_efficiency"]:
            if key in summary:
                kpis[key] = summary[key]

        # 합격/불합격 판정
        cr_rate = summary.get("conflict_resolution_rate", {}).get("mean")
        status = "pass" if cr_rate and cr_rate >= 99.5 else "review"

        processed[name] = {
            "status": status,
            "n_runs": len(data.get("runs", [])),
            "kpis": kpis,
        }

    return processed


# ── 외부 데이터 가공 ──────────────────────────────────────────

def process_external_data(
    external_data: dict,
) -> dict[str, Any]:
    """
    외부 수집 데이터를 정리·가공.

    Returns:
        {
            "type": "processed_external",
            "timestamp": str,
            "crypto_summary": {...},
            "weather_summary": {...},
            "sc2_summary": {...},
            "sim_weather_params": {...},  # 날씨→시뮬 파라미터 변환
        }
    """
    logger.info("외부 데이터 가공 시작")

    result = {
        "type": "processed_external",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "crypto_summary": {},
        "weather_summary": {},
        "sc2_summary": {},
        "sim_weather_params": {},
    }

    # 암호화폐 요약
    crypto = external_data.get("crypto", {})
    if crypto.get("tickers"):
        tickers = crypto["tickers"]
        result["crypto_summary"] = {
            "count": len(tickers),
            "top_gainer": max(tickers, key=lambda t: t.get("signed_change_rate", 0) or 0),
            "top_loser": min(tickers, key=lambda t: t.get("signed_change_rate", 0) or 0),
            "total_volume_24h": sum(t.get("acc_trade_price_24h", 0) or 0 for t in tickers),
            "prices": {t["market"]: t["trade_price"] for t in tickers if t.get("market")},
        }

    # 날씨 요약 + 시뮬레이션 파라미터 변환
    weather = external_data.get("weather", {})
    current = weather.get("current", {})
    if current:
        wind_speed = current.get("wind_speed_ms", 0) or 0
        wind_dir = current.get("wind_direction_deg", 0) or 0
        wind_gusts = current.get("wind_gusts_ms", 0) or 0

        result["weather_summary"] = {
            "wind_speed_ms": wind_speed,
            "wind_direction_deg": wind_dir,
            "wind_gusts_ms": wind_gusts,
            "temperature_c": current.get("temperature_c"),
            "precipitation_mm": current.get("precipitation_mm"),
            "flight_condition": _assess_flight_condition(wind_speed, wind_gusts, current.get("precipitation_mm", 0) or 0),
        }

        # 실제 날씨 → SDACS 시뮬레이션 wind 파라미터로 변환
        # APF_PARAMS_WINDY는 풍속 >10 m/s에서 자동 전환됨
        result["sim_weather_params"] = {
            "wind_models": [{
                "type": "constant",
                "speed_ms": round(wind_speed, 1),
                "direction_deg": round(wind_dir, 0),
            }],
            "use_windy_apf": wind_speed > 10,
        }

    # SC2 요약
    sc2 = external_data.get("sc2", {})
    if sc2.get("rankings"):
        result["sc2_summary"] = {
            "top_players": sc2["rankings"][:5],
            "race_distribution": _count_races(sc2["rankings"]),
        }

    return result


def _assess_flight_condition(wind_ms: float, gusts_ms: float, precip_mm: float) -> str:
    """비행 조건 등급 판정."""
    if wind_ms > 20 or gusts_ms > 25 or precip_mm > 10:
        return "DANGEROUS"
    elif wind_ms > 10 or gusts_ms > 15 or precip_mm > 5:
        return "CAUTION"
    else:
        return "GOOD"


def _count_races(rankings: list[dict]) -> dict[str, int]:
    """종족 분포 카운트."""
    counts: dict[str, int] = {}
    for r in rankings:
        race = r.get("race", "?")
        counts[race] = counts.get(race, 0) + 1
    return counts


# ── 통합 가공 함수 ────────────────────────────────────────────

def process_all(
    mc_data: Optional[dict] = None,
    scenario_data: Optional[dict] = None,
    external_data: Optional[dict] = None,
    filters: Optional[dict] = None,
) -> dict[str, Any]:
    """
    모든 수집 데이터를 가공하여 통합 결과를 반환.
    """
    result = {
        "type": "processed_all",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sim": {},
        "external": {},
    }

    if mc_data or scenario_data:
        result["sim"] = process_sim_data(mc_data, scenario_data, filters)

    if external_data:
        result["external"] = process_external_data(external_data)

    return result
