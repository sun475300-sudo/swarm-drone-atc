"""
Phase 366: GPS-Denied Navigation Fallback Model
================================================
GPS 불가 환경에서의 대체 항법 소스 선택, 센서 퓨전 정확도 추정,
안전 비행 가능 시간 산출.

분석 모델이며, 실측값이 아닌 카탈로그 기반 이론치.

사용법::

    python -m simulation.gps_denied_nav --scenarios
    python -m simulation.gps_denied_nav --assess urban_canyon
    python -m simulation.gps_denied_nav --assess indoor_warehouse --json
    python -m simulation.gps_denied_nav --sources
    python -m simulation.gps_denied_nav --fuse GPS RTK_GPS
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class NavSource(Enum):
    """항법 소스 종류."""
    GPS = "GPS"
    RTK_GPS = "RTK_GPS"
    VIO = "VIO"
    UWB = "UWB"
    BAROMETER = "BAROMETER"
    IMU_DEAD_RECKONING = "IMU_DEAD_RECKONING"
    TERRAIN_MATCHING = "TERRAIN_MATCHING"


# ---------------------------------------------------------------------------
# Frozen dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class NavAccuracy:
    """단일 항법 소스의 정확도 사양."""
    source: NavSource
    horizontal_m: float
    vertical_m: float
    update_rate_hz: float
    drift_rate_m_per_s: float
    max_range_m: float | None


@dataclass(frozen=True)
class NavFusion:
    """다중 소스 퓨전 정확도."""
    sources: tuple[NavSource, ...]
    fused_horizontal_m: float
    fused_vertical_m: float
    degradation_factor: float


@dataclass(frozen=True)
class GPSDeniedScenario:
    """GPS 거부 시나리오 정의."""
    name: str
    gps_available: bool
    rtk_available: bool
    indoor: bool
    duration_s: float


@dataclass(frozen=True)
class NavAssessment:
    """시나리오 평가 결과."""
    scenario: GPSDeniedScenario
    primary: NavSource
    fallbacks: tuple[NavSource, ...]
    fused: NavFusion
    safe_flight_duration_s: float
    recommendation: str


# ---------------------------------------------------------------------------
# Source accuracy catalog (deterministic)
# ---------------------------------------------------------------------------

NAV_SOURCE_CATALOG: dict[NavSource, NavAccuracy] = {
    NavSource.GPS: NavAccuracy(
        source=NavSource.GPS,
        horizontal_m=2.5, vertical_m=5.0,
        update_rate_hz=10.0, drift_rate_m_per_s=0.0,
        max_range_m=None,
    ),
    NavSource.RTK_GPS: NavAccuracy(
        source=NavSource.RTK_GPS,
        horizontal_m=0.02, vertical_m=0.03,
        update_rate_hz=20.0, drift_rate_m_per_s=0.0,
        max_range_m=None,
    ),
    NavSource.VIO: NavAccuracy(
        source=NavSource.VIO,
        horizontal_m=0.1, vertical_m=0.5,
        update_rate_hz=30.0, drift_rate_m_per_s=0.01,
        max_range_m=None,
    ),
    NavSource.UWB: NavAccuracy(
        source=NavSource.UWB,
        horizontal_m=0.3, vertical_m=0.5,
        update_rate_hz=100.0, drift_rate_m_per_s=0.0,
        max_range_m=100.0,
    ),
    NavSource.BAROMETER: NavAccuracy(
        source=NavSource.BAROMETER,
        horizontal_m=float("inf"), vertical_m=0.5,
        update_rate_hz=50.0, drift_rate_m_per_s=0.001,
        max_range_m=None,
    ),
    NavSource.IMU_DEAD_RECKONING: NavAccuracy(
        source=NavSource.IMU_DEAD_RECKONING,
        horizontal_m=1.0, vertical_m=1.0,
        update_rate_hz=200.0, drift_rate_m_per_s=0.5,
        max_range_m=None,
    ),
    NavSource.TERRAIN_MATCHING: NavAccuracy(
        source=NavSource.TERRAIN_MATCHING,
        horizontal_m=5.0, vertical_m=3.0,
        update_rate_hz=1.0, drift_rate_m_per_s=0.0,
        max_range_m=None,
    ),
}


# ---------------------------------------------------------------------------
# Predefined scenarios
# ---------------------------------------------------------------------------

SCENARIOS: dict[str, GPSDeniedScenario] = {
    "urban_canyon": GPSDeniedScenario(
        name="urban_canyon",
        gps_available=True, rtk_available=False,
        indoor=False, duration_s=300.0,
    ),
    "indoor_warehouse": GPSDeniedScenario(
        name="indoor_warehouse",
        gps_available=False, rtk_available=False,
        indoor=True, duration_s=600.0,
    ),
    "jamming": GPSDeniedScenario(
        name="jamming",
        gps_available=False, rtk_available=False,
        indoor=False, duration_s=120.0,
    ),
    "spoofing_detected": GPSDeniedScenario(
        name="spoofing_detected",
        gps_available=False, rtk_available=False,
        indoor=False, duration_s=180.0,
    ),
    "rtk_lost": GPSDeniedScenario(
        name="rtk_lost",
        gps_available=True, rtk_available=False,
        indoor=False, duration_s=600.0,
    ),
}


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def select_nav_sources(scenario: GPSDeniedScenario) -> tuple[NavSource, ...]:
    """시나리오 가용성에 따라 사용 가능한 항법 소스를 결정적으로 선택한다."""
    sources: list[NavSource] = []

    if scenario.rtk_available:
        sources.append(NavSource.RTK_GPS)
    if scenario.gps_available and not scenario.rtk_available:
        sources.append(NavSource.GPS)

    if scenario.indoor:
        sources.append(NavSource.VIO)
        sources.append(NavSource.UWB)
    else:
        sources.append(NavSource.VIO)

    sources.append(NavSource.BAROMETER)
    sources.append(NavSource.IMU_DEAD_RECKONING)

    if not scenario.indoor:
        sources.append(NavSource.TERRAIN_MATCHING)

    return tuple(sources)


def _inverse_variance_weight(values: Sequence[float]) -> float:
    """유한 값들에 대해 역분산 가중 결합 (deterministic)."""
    finite = [v for v in values if math.isfinite(v) and v > 0]
    if not finite:
        return float("inf")
    inv_var_sum = sum(1.0 / (v * v) for v in finite)
    return 1.0 / math.sqrt(inv_var_sum)


def fuse_accuracy(sources: tuple[NavAccuracy, ...]) -> NavFusion:
    """역분산 가중으로 다중 소스 퓨전 정확도를 계산한다."""
    if not sources:
        return NavFusion(
            sources=(),
            fused_horizontal_m=float("inf"),
            fused_vertical_m=float("inf"),
            degradation_factor=1.0,
        )

    h_vals = [s.horizontal_m for s in sources]
    v_vals = [s.vertical_m for s in sources]

    fused_h = _inverse_variance_weight(h_vals)
    fused_v = _inverse_variance_weight(v_vals)

    finite_h = [v for v in h_vals if math.isfinite(v)]
    best_h = min(finite_h) if finite_h else float("inf")
    degradation = fused_h / best_h if best_h > 0 and math.isfinite(best_h) else 1.0

    nav_sources = tuple(s.source for s in sources)
    return NavFusion(
        sources=nav_sources,
        fused_horizontal_m=round(fused_h, 6),
        fused_vertical_m=round(fused_v, 6),
        degradation_factor=round(degradation, 6),
    )


def safe_flight_duration(
    fusion: NavFusion,
    max_position_error_m: float = 5.0,
) -> float:
    """누적 드리프트가 허용 오차를 초과하기까지의 안전 비행 시간(초)."""
    source_accuracies = tuple(
        NAV_SOURCE_CATALOG[s] for s in fusion.sources
        if s in NAV_SOURCE_CATALOG
    )

    max_drift = max(
        (a.drift_rate_m_per_s for a in source_accuracies),
        default=0.0,
    )

    if max_drift <= 0.0:
        return float("inf")

    remaining = max_position_error_m - fusion.fused_horizontal_m
    if remaining <= 0.0:
        return 0.0

    return round(remaining / max_drift, 2)


def _generate_recommendation(
    scenario: GPSDeniedScenario,
    primary: NavSource,
    safe_duration: float,
) -> str:
    """시나리오 평가에 대한 운용 권고문을 생성한다."""
    if math.isinf(safe_duration):
        return f"드리프트 없음: {primary.value} 기반 지속 비행 가능"
    if safe_duration >= scenario.duration_s:
        return (
            f"안전: {safe_duration:.0f}초 비행 가능 "
            f"(임무 {scenario.duration_s:.0f}초)"
        )
    return (
        f"주의: 안전 비행 {safe_duration:.0f}초, "
        f"임무 {scenario.duration_s:.0f}초 - 조기 복귀 권고"
    )


def assess_scenario(scenario: GPSDeniedScenario) -> NavAssessment:
    """시나리오를 분석하고 항법 평가 결과를 반환한다."""
    nav_sources = select_nav_sources(scenario)
    primary = nav_sources[0]
    fallbacks = nav_sources[1:]

    accuracies = tuple(NAV_SOURCE_CATALOG[s] for s in nav_sources)
    fusion = fuse_accuracy(accuracies)
    duration = safe_flight_duration(fusion)
    recommendation = _generate_recommendation(scenario, primary, duration)

    return NavAssessment(
        scenario=scenario,
        primary=primary,
        fallbacks=fallbacks,
        fused=fusion,
        safe_flight_duration_s=duration,
        recommendation=recommendation,
    )


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _accuracy_to_dict(acc: NavAccuracy) -> dict:
    """NavAccuracy -> dict."""
    return {
        "source": acc.source.value,
        "horizontal_m": acc.horizontal_m,
        "vertical_m": acc.vertical_m,
        "update_rate_hz": acc.update_rate_hz,
        "drift_rate_m_per_s": acc.drift_rate_m_per_s,
        "max_range_m": acc.max_range_m,
    }


def _fusion_to_dict(fusion: NavFusion) -> dict:
    """NavFusion -> dict."""
    return {
        "sources": [s.value for s in fusion.sources],
        "fused_horizontal_m": fusion.fused_horizontal_m,
        "fused_vertical_m": fusion.fused_vertical_m,
        "degradation_factor": fusion.degradation_factor,
    }


def _assessment_to_dict(assessment: NavAssessment) -> dict:
    """NavAssessment -> dict."""
    return {
        "scenario": assessment.scenario.name,
        "primary": assessment.primary.value,
        "fallbacks": [s.value for s in assessment.fallbacks],
        "fused": _fusion_to_dict(assessment.fused),
        "safe_flight_duration_s": assessment.safe_flight_duration_s,
        "recommendation": assessment.recommendation,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """CLI 파서를 생성한다."""
    parser = argparse.ArgumentParser(
        description="GPS-Denied Navigation Fallback Model (Phase 366)",
    )
    parser.add_argument(
        "--assess", metavar="SCENARIO",
        help="시나리오 평가 (예: urban_canyon, indoor_warehouse)",
    )
    parser.add_argument(
        "--sources", action="store_true",
        help="항법 소스 카탈로그 출력",
    )
    parser.add_argument(
        "--fuse", nargs="+", metavar="SOURCE",
        help="지정 소스 퓨전 정확도 계산 (예: GPS VIO BAROMETER)",
    )
    parser.add_argument(
        "--scenarios", action="store_true",
        help="등록된 시나리오 목록 출력",
    )
    parser.add_argument(
        "--json", action="store_true", dest="as_json",
        help="JSON 형식 출력",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """CLI 진입점."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.sources:
        _cmd_sources(args.as_json)
    elif args.scenarios:
        _cmd_scenarios(args.as_json)
    elif args.fuse:
        _cmd_fuse(args.fuse, args.as_json)
    elif args.assess:
        _cmd_assess(args.assess, args.as_json)
    else:
        parser.print_help()


def _cmd_sources(as_json: bool) -> None:
    """항법 소스 카탈로그 출력."""
    data = [_accuracy_to_dict(a) for a in NAV_SOURCE_CATALOG.values()]
    if as_json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return
    for acc in NAV_SOURCE_CATALOG.values():
        h = f"{acc.horizontal_m}m" if math.isfinite(acc.horizontal_m) else "N/A"
        print(
            f"  {acc.source.value:<20s}  H={h:<8s} V={acc.vertical_m}m  "
            f"rate={acc.update_rate_hz}Hz  drift={acc.drift_rate_m_per_s} m/s  "
            f"range={acc.max_range_m}",
        )


def _cmd_scenarios(as_json: bool) -> None:
    """시나리오 목록 출력."""
    data = [
        {
            "name": s.name, "gps": s.gps_available,
            "rtk": s.rtk_available, "indoor": s.indoor,
            "duration_s": s.duration_s,
        }
        for s in SCENARIOS.values()
    ]
    if as_json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return
    for s in SCENARIOS.values():
        print(
            f"  {s.name:<22s}  GPS={s.gps_available!s:<5s}  "
            f"RTK={s.rtk_available!s:<5s}  indoor={s.indoor!s:<5s}  "
            f"duration={s.duration_s}s",
        )


def _cmd_fuse(source_names: list[str], as_json: bool) -> None:
    """소스 퓨전 정확도 계산."""
    try:
        sources = tuple(NavSource[n.upper()] for n in source_names)
    except KeyError as exc:
        valid = ", ".join(s.value for s in NavSource)
        print(
            f"ERROR: 알 수 없는 소스 {exc}. 유효: {valid}",
            file=sys.stderr,
        )
        sys.exit(1)

    accuracies = tuple(NAV_SOURCE_CATALOG[s] for s in sources)
    fusion = fuse_accuracy(accuracies)

    if as_json:
        print(json.dumps(_fusion_to_dict(fusion), indent=2, ensure_ascii=False))
        return
    print(
        f"  Fused H={fusion.fused_horizontal_m}m  "
        f"V={fusion.fused_vertical_m}m  "
        f"degradation={fusion.degradation_factor}",
    )


def _cmd_assess(scenario_name: str, as_json: bool) -> None:
    """시나리오 평가."""
    scenario = SCENARIOS.get(scenario_name)
    if scenario is None:
        valid = ", ".join(SCENARIOS)
        print(
            f"ERROR: 알 수 없는 시나리오 '{scenario_name}'. 유효: {valid}",
            file=sys.stderr,
        )
        sys.exit(1)

    assessment = assess_scenario(scenario)

    if as_json:
        print(json.dumps(
            _assessment_to_dict(assessment), indent=2, ensure_ascii=False,
        ))
        return
    print(f"  Scenario: {assessment.scenario.name}")
    print(f"  Primary:  {assessment.primary.value}")
    print(f"  Fallbacks: {', '.join(s.value for s in assessment.fallbacks)}")
    print(
        f"  Fused H={assessment.fused.fused_horizontal_m}m  "
        f"V={assessment.fused.fused_vertical_m}m",
    )
    print(f"  Safe flight: {assessment.safe_flight_duration_s}s")
    print(f"  Recommendation: {assessment.recommendation}")


if __name__ == "__main__":
    main()
