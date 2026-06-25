"""Phase 365: 5G Non-Terrestrial Network (NTN) 링크 모델.

군집드론 ATC 통신을 위한 위성/HAPS 기반 비지상 네트워크 링크 버짓 분석
및 핸드오버 시뮬레이션. 3GPP TR 38.811 / TR 38.821 용어 기반.

정직 공시 (CLAUDE.md)
--------------------
1. 본 모듈은 해석적(analytical) 링크 버짓 모델이며 실측 데이터가 아니다.
   Free-space path loss, ITU-R P.838 강우 감쇠, Shannon 용량은 교과서 공식의
   결정적 구현이다. 실제 위성 링크 성능은 안테나 패턴, 대기 신틸레이션,
   도플러 효과 등 본 모델이 생략한 요인에 의해 달라진다.
2. 위성 카탈로그(LEO 550km, MEO 20200km, GEO 35786km, HAPS 20km)는
   대표값이며 특정 위성 시스템의 사양이 아니다.
3. 핸드오버 모델은 궤도 주기와 가시 창을 기반으로 한 결정적 근사이며,
   실제 핸드오버 지연은 네트워크 혼잡, 빔 스위칭 지연 등에 의존한다.

무작위성 0 · 결정적. 기존 모듈 무수정 순수 추가.

CLI:
    python simulation/ntn_link_model.py --simulate LEO        # LEO 링크 시뮬레이션
    python simulation/ntn_link_model.py --budget               # 전체 카탈로그 링크 버짓
    python simulation/ntn_link_model.py --handover LEO         # 핸드오버 시뮬레이션
    python simulation/ntn_link_model.py --assess LEO           # ATC 적합성 평가
    python simulation/ntn_link_model.py --json                 # JSON 출력
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from enum import Enum
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SPEED_OF_LIGHT_M_S: float = 299_792_458.0
BOLTZMANN_DB: float = -228.6  # dBW/(K·Hz), Boltzmann constant in dB scale
NOISE_TEMP_K: float = 290.0  # receiver noise temperature (K)
PROCESSING_DELAY_MS: float = 5.0  # baseband processing delay (ms)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SatelliteType(Enum):
    """위성/플랫폼 유형."""

    LEO = "LEO"    # Low Earth Orbit
    MEO = "MEO"    # Medium Earth Orbit
    GEO = "GEO"    # Geostationary Earth Orbit
    HAPS = "HAPS"  # High Altitude Platform Station


# ---------------------------------------------------------------------------
# Frozen Dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class NTNLink:
    """NTN 링크 파라미터 정의."""

    satellite_type: SatelliteType
    orbit_altitude_km: float
    frequency_ghz: float
    bandwidth_mhz: float
    tx_power_dbm: float
    antenna_gain_dbi: float

    def __post_init__(self) -> None:
        if self.orbit_altitude_km <= 0:
            raise ValueError("orbit_altitude_km must be positive")
        if self.frequency_ghz <= 0:
            raise ValueError("frequency_ghz must be positive")
        if self.bandwidth_mhz <= 0:
            raise ValueError("bandwidth_mhz must be positive")


@dataclass(frozen=True)
class LinkBudget:
    """링크 버짓 계산 결과."""

    path_loss_db: float
    atmospheric_loss_db: float
    rain_attenuation_db: float
    total_loss_db: float
    received_power_dbm: float
    snr_db: float
    capacity_mbps: float
    latency_ms: float


@dataclass(frozen=True)
class HandoverEvent:
    """위성 간 핸드오버 이벤트."""

    from_sat: str
    to_sat: str
    time_s: float
    duration_ms: float
    packet_loss_pct: float


@dataclass(frozen=True)
class NTNSimResult:
    """NTN 시뮬레이션 종합 결과."""

    link: NTNLink
    budget: LinkBudget
    handovers: tuple[HandoverEvent, ...]
    availability_pct: float
    meets_atc_requirement: bool


# ---------------------------------------------------------------------------
# Satellite Catalog
# ---------------------------------------------------------------------------

# 대표 위성 파라미터: (altitude_km, freq_ghz, bw_mhz, tx_dbm, gain_dbi)
SATELLITE_CATALOG: dict[SatelliteType, NTNLink] = {
    SatelliteType.LEO: NTNLink(
        satellite_type=SatelliteType.LEO,
        orbit_altitude_km=550.0,
        frequency_ghz=20.0,       # Ka-band downlink
        bandwidth_mhz=250.0,
        tx_power_dbm=40.0,
        antenna_gain_dbi=38.0,
    ),
    SatelliteType.MEO: NTNLink(
        satellite_type=SatelliteType.MEO,
        orbit_altitude_km=20_200.0,
        frequency_ghz=12.0,       # Ku-band
        bandwidth_mhz=36.0,
        tx_power_dbm=43.0,
        antenna_gain_dbi=42.0,
    ),
    SatelliteType.GEO: NTNLink(
        satellite_type=SatelliteType.GEO,
        orbit_altitude_km=35_786.0,
        frequency_ghz=12.0,       # Ku-band
        bandwidth_mhz=36.0,
        tx_power_dbm=46.0,
        antenna_gain_dbi=50.0,
    ),
    SatelliteType.HAPS: NTNLink(
        satellite_type=SatelliteType.HAPS,
        orbit_altitude_km=20.0,
        frequency_ghz=2.1,        # S-band
        bandwidth_mhz=20.0,
        tx_power_dbm=33.0,
        antenna_gain_dbi=18.0,
    ),
}

# 궤도 주기(초)와 가시 창(초) — 결정적 대표값
ORBIT_PARAMS: dict[SatelliteType, tuple[float, float]] = {
    SatelliteType.LEO: (5_760.0, 600.0),       # ~96분 주기, ~10분 가시
    SatelliteType.MEO: (43_080.0, 7_200.0),    # ~12시간 주기, ~2시간 가시
    SatelliteType.GEO: (86_400.0, 86_400.0),   # 정지궤도 — 항상 가시
    SatelliteType.HAPS: (86_400.0, 43_200.0),  # 준정지 — ~12시간 가시
}


# ---------------------------------------------------------------------------
# Atmospheric / Rain Loss Lookup Tables
# ---------------------------------------------------------------------------

# 주파수대별 대기 감쇠 (dB) — 맑은 날씨 기준 근사값
_ATMOSPHERIC_LOSS_TABLE: dict[str, float] = {
    "S": 0.1,   # 2 GHz 대
    "Ku": 0.5,  # 12 GHz 대
    "Ka": 1.5,  # 20 GHz 대
}

# ITU-R P.838 간이 강우 감쇠 (dB) — 중간 강우 (25 mm/h) 기준
_RAIN_ATTENUATION_TABLE: dict[str, float] = {
    "S": 0.1,
    "Ku": 2.0,
    "Ka": 6.0,
}


def _frequency_band(freq_ghz: float) -> str:
    """주파수를 대역명으로 분류한다."""
    if freq_ghz < 4.0:
        return "S"
    if freq_ghz < 18.0:
        return "Ku"
    return "Ka"


# ---------------------------------------------------------------------------
# Link Budget Calculation
# ---------------------------------------------------------------------------

def _free_space_path_loss(distance_m: float, frequency_hz: float) -> float:
    """자유 공간 경로 손실(dB)을 계산한다.

    FSPL = 20*log10(d) + 20*log10(f) + 20*log10(4*pi/c)
    """
    return (
        20.0 * math.log10(distance_m)
        + 20.0 * math.log10(frequency_hz)
        + 20.0 * math.log10(4.0 * math.pi / SPEED_OF_LIGHT_M_S)
    )


def _noise_power_dbm(bandwidth_hz: float) -> float:
    """수신기 열잡음 전력(dBm)을 계산한다.

    N = k*T*B -> dBm = BOLTZMANN_DB + 10*log10(T) + 10*log10(B) + 30
    (+30 은 dBW->dBm 변환)
    """
    return (
        BOLTZMANN_DB
        + 10.0 * math.log10(NOISE_TEMP_K)
        + 10.0 * math.log10(bandwidth_hz)
        + 30.0
    )


def _slant_range_m(altitude_km: float, drone_altitude_m: float) -> float:
    """위성-드론 간 경사 거리(m)를 계산한다.

    수직 직하점(nadir) 가정 — 최소 경사 거리.
    """
    return (altitude_km * 1000.0) - drone_altitude_m


def simulate_link(
    link: NTNLink,
    drone_altitude_m: float = 120.0,
) -> LinkBudget:
    """NTN 링크 버짓을 계산한다.

    Args:
        link: NTN 링크 파라미터.
        drone_altitude_m: 드론 고도(m). 기본값 120m (도심 운용 고도).

    Returns:
        LinkBudget 계산 결과.
    """
    distance_m = _slant_range_m(link.orbit_altitude_km, drone_altitude_m)
    freq_hz = link.frequency_ghz * 1e9
    bw_hz = link.bandwidth_mhz * 1e6

    # 경로 손실
    path_loss = _free_space_path_loss(distance_m, freq_hz)

    # 대기 / 강우 손실
    band = _frequency_band(link.frequency_ghz)
    atm_loss = _ATMOSPHERIC_LOSS_TABLE[band]
    rain_loss = _RAIN_ATTENUATION_TABLE[band]

    total_loss = path_loss + atm_loss + rain_loss

    # 수신 전력 (dBm) = Tx - 총손실 + 안테나 이득
    rx_power = link.tx_power_dbm - total_loss + link.antenna_gain_dbi

    # SNR
    noise = _noise_power_dbm(bw_hz)
    snr = rx_power - noise

    # Shannon 용량 (Mbps)
    snr_linear = 10.0 ** (snr / 10.0)
    capacity = (bw_hz * math.log2(1.0 + snr_linear)) / 1e6

    # 편도 전파 지연 + 왕복 + 처리 지연
    one_way_s = distance_m / SPEED_OF_LIGHT_M_S
    latency = (2.0 * one_way_s * 1000.0) + PROCESSING_DELAY_MS

    return LinkBudget(
        path_loss_db=round(path_loss, 2),
        atmospheric_loss_db=round(atm_loss, 2),
        rain_attenuation_db=round(rain_loss, 2),
        total_loss_db=round(total_loss, 2),
        received_power_dbm=round(rx_power, 2),
        snr_db=round(snr, 2),
        capacity_mbps=round(capacity, 4),
        latency_ms=round(latency, 4),
    )


# ---------------------------------------------------------------------------
# Handover Simulation
# ---------------------------------------------------------------------------

def simulate_handover(
    satellite_type: SatelliteType,
    orbit_period_s: float | None = None,
    visibility_window_s: float | None = None,
    simulation_duration_s: float = 3600.0,
) -> tuple[HandoverEvent, ...]:
    """위성 핸드오버 이벤트를 결정적으로 생성한다.

    Args:
        satellite_type: 위성 유형.
        orbit_period_s: 궤도 주기(초). None이면 카탈로그 기본값.
        visibility_window_s: 가시 창(초). None이면 카탈로그 기본값.
        simulation_duration_s: 시뮬레이션 기간(초). 기본 1시간.

    Returns:
        시간순 핸드오버 이벤트 튜플.
    """
    default_period, default_window = ORBIT_PARAMS[satellite_type]
    period = orbit_period_s if orbit_period_s is not None else default_period
    window = visibility_window_s if visibility_window_s is not None else default_window

    if window >= period:
        # 항상 가시 — 핸드오버 없음 (GEO 등)
        return ()

    events: list[HandoverEvent] = []
    sat_index = 0
    current_time = 0.0

    while current_time < simulation_duration_s:
        # 현재 위성 가시 종료 -> 핸드오버 발생
        handover_time = current_time + window
        if handover_time >= simulation_duration_s:
            break

        from_name = f"{satellite_type.value}-{sat_index:03d}"
        to_name = f"{satellite_type.value}-{sat_index + 1:03d}"

        ho_duration = _handover_duration_ms(satellite_type)
        ho_loss = _handover_packet_loss_pct(satellite_type)

        events.append(HandoverEvent(
            from_sat=from_name,
            to_sat=to_name,
            time_s=round(handover_time, 2),
            duration_ms=ho_duration,
            packet_loss_pct=ho_loss,
        ))

        sat_index += 1
        current_time = handover_time

    return tuple(events)


def _handover_duration_ms(sat_type: SatelliteType) -> float:
    """위성 유형별 핸드오버 소요 시간(ms)."""
    durations: dict[SatelliteType, float] = {
        SatelliteType.LEO: 50.0,
        SatelliteType.MEO: 100.0,
        SatelliteType.GEO: 0.0,
        SatelliteType.HAPS: 30.0,
    }
    return durations[sat_type]


def _handover_packet_loss_pct(sat_type: SatelliteType) -> float:
    """위성 유형별 핸드오버 시 패킷 손실률(%)."""
    losses: dict[SatelliteType, float] = {
        SatelliteType.LEO: 0.5,
        SatelliteType.MEO: 0.2,
        SatelliteType.GEO: 0.0,
        SatelliteType.HAPS: 0.3,
    }
    return losses[sat_type]


# ---------------------------------------------------------------------------
# ATC Suitability Assessment
# ---------------------------------------------------------------------------

ATC_MAX_LATENCY_MS: float = 500.0
ATC_MIN_AVAILABILITY_PCT: float = 99.0
ATC_MIN_CAPACITY_MBPS: float = 1.0


def assess_atc_suitability(result: NTNSimResult) -> tuple[str, ...]:
    """NTN 링크의 ATC 적합성을 평가한다.

    Returns:
        발견된 부적합 사유 튜플. 빈 튜플이면 적합.
    """
    issues: list[str] = []

    if result.budget.latency_ms > ATC_MAX_LATENCY_MS:
        issues.append(
            f"latency {result.budget.latency_ms:.1f}ms "
            f"exceeds ATC limit {ATC_MAX_LATENCY_MS:.0f}ms"
        )

    if result.availability_pct < ATC_MIN_AVAILABILITY_PCT:
        issues.append(
            f"availability {result.availability_pct:.1f}% "
            f"below ATC minimum {ATC_MIN_AVAILABILITY_PCT:.0f}%"
        )

    if result.budget.capacity_mbps < ATC_MIN_CAPACITY_MBPS:
        issues.append(
            f"capacity {result.budget.capacity_mbps:.2f}Mbps "
            f"below ATC minimum {ATC_MIN_CAPACITY_MBPS:.0f}Mbps"
        )

    return tuple(issues)


# ---------------------------------------------------------------------------
# Full Simulation Pipeline
# ---------------------------------------------------------------------------

def _estimate_availability(
    satellite_type: SatelliteType,
    handovers: tuple[HandoverEvent, ...],
    simulation_duration_s: float = 3600.0,
) -> float:
    """핸드오버 기반 가용성(%) 추정."""
    total_outage_ms = sum(ho.duration_ms for ho in handovers)
    total_outage_s = total_outage_ms / 1000.0
    if simulation_duration_s <= 0:
        return 100.0
    availability = (
        (simulation_duration_s - total_outage_s) / simulation_duration_s
    ) * 100.0
    return round(min(availability, 100.0), 4)


def run_full_simulation(
    satellite_type: SatelliteType,
    drone_altitude_m: float = 120.0,
    simulation_duration_s: float = 3600.0,
) -> NTNSimResult:
    """지정 위성 유형에 대해 전체 NTN 시뮬레이션을 수행한다."""
    link = SATELLITE_CATALOG[satellite_type]
    budget = simulate_link(link, drone_altitude_m)
    handovers = simulate_handover(
        satellite_type, simulation_duration_s=simulation_duration_s,
    )
    availability = _estimate_availability(
        satellite_type, handovers, simulation_duration_s,
    )
    # 임시 result 로 적합성 평가
    preliminary = NTNSimResult(
        link=link, budget=budget, handovers=handovers,
        availability_pct=availability, meets_atc_requirement=True,
    )
    issues = assess_atc_suitability(preliminary)
    meets = len(issues) == 0

    return NTNSimResult(
        link=link,
        budget=budget,
        handovers=handovers,
        availability_pct=availability,
        meets_atc_requirement=meets,
    )


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def _link_to_dict(link: NTNLink) -> dict[str, Any]:
    """NTNLink -> dict."""
    return {
        "satellite_type": link.satellite_type.value,
        "orbit_altitude_km": link.orbit_altitude_km,
        "frequency_ghz": link.frequency_ghz,
        "bandwidth_mhz": link.bandwidth_mhz,
        "tx_power_dbm": link.tx_power_dbm,
        "antenna_gain_dbi": link.antenna_gain_dbi,
    }


def _budget_to_dict(b: LinkBudget) -> dict[str, float]:
    """LinkBudget -> dict."""
    return {
        "path_loss_db": b.path_loss_db,
        "atmospheric_loss_db": b.atmospheric_loss_db,
        "rain_attenuation_db": b.rain_attenuation_db,
        "total_loss_db": b.total_loss_db,
        "received_power_dbm": b.received_power_dbm,
        "snr_db": b.snr_db,
        "capacity_mbps": b.capacity_mbps,
        "latency_ms": b.latency_ms,
    }


def _handover_to_dict(ho: HandoverEvent) -> dict[str, Any]:
    """HandoverEvent -> dict."""
    return {
        "from_sat": ho.from_sat,
        "to_sat": ho.to_sat,
        "time_s": ho.time_s,
        "duration_ms": ho.duration_ms,
        "packet_loss_pct": ho.packet_loss_pct,
    }


def result_to_dict(result: NTNSimResult) -> dict[str, Any]:
    """NTNSimResult -> dict (JSON 직렬화용)."""
    return {
        "link": _link_to_dict(result.link),
        "budget": _budget_to_dict(result.budget),
        "handovers": [_handover_to_dict(ho) for ho in result.handovers],
        "availability_pct": result.availability_pct,
        "meets_atc_requirement": result.meets_atc_requirement,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    """CLI 파서를 생성한다."""
    parser = argparse.ArgumentParser(
        description="Phase 365: 5G NTN Link Model",
    )
    parser.add_argument(
        "--simulate",
        choices=[st.value for st in SatelliteType],
        help="Run full simulation for satellite type",
    )
    parser.add_argument(
        "--budget", action="store_true",
        help="Print link budgets for all satellite types",
    )
    parser.add_argument(
        "--handover",
        choices=[st.value for st in SatelliteType],
        help="Simulate handovers for satellite type",
    )
    parser.add_argument(
        "--assess",
        choices=[st.value for st in SatelliteType],
        help="Assess ATC suitability for satellite type",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output in JSON format",
    )
    return parser


def _print_budget(sat_type: SatelliteType, budget: LinkBudget) -> None:
    """링크 버짓을 텍스트로 출력한다."""
    sep = "=" * 60
    print(f"\n{sep}")
    print(f"  {sat_type.value} Link Budget")
    print(sep)
    print(f"  Path Loss        : {budget.path_loss_db:.2f} dB")
    print(f"  Atmospheric Loss : {budget.atmospheric_loss_db:.2f} dB")
    print(f"  Rain Attenuation : {budget.rain_attenuation_db:.2f} dB")
    print(f"  Total Loss       : {budget.total_loss_db:.2f} dB")
    print(f"  Received Power   : {budget.received_power_dbm:.2f} dBm")
    print(f"  SNR              : {budget.snr_db:.2f} dB")
    print(f"  Capacity         : {budget.capacity_mbps:.4f} Mbps")
    print(f"  Latency          : {budget.latency_ms:.4f} ms")


def main() -> None:
    """CLI 진입점."""
    parser = _build_parser()
    args = parser.parse_args()

    use_json = args.json

    if args.simulate:
        sat_type = SatelliteType(args.simulate)
        result = run_full_simulation(sat_type)
        if use_json:
            print(json.dumps(result_to_dict(result), indent=2))
        else:
            _print_budget(sat_type, result.budget)
            print(f"\n  Handovers        : {len(result.handovers)}")
            print(f"  Availability     : {result.availability_pct:.2f}%")
            print(f"  ATC Suitable     : {result.meets_atc_requirement}")
            issues = assess_atc_suitability(result)
            if issues:
                print("  Issues           :")
                for issue in issues:
                    print(f"    - {issue}")

    elif args.budget:
        all_budgets: dict[str, Any] = {}
        for sat_type in SatelliteType:
            link = SATELLITE_CATALOG[sat_type]
            budget = simulate_link(link)
            if use_json:
                all_budgets[sat_type.value] = _budget_to_dict(budget)
            else:
                _print_budget(sat_type, budget)
        if use_json:
            print(json.dumps(all_budgets, indent=2))

    elif args.handover:
        sat_type = SatelliteType(args.handover)
        handovers = simulate_handover(sat_type)
        if use_json:
            print(json.dumps(
                [_handover_to_dict(ho) for ho in handovers], indent=2,
            ))
        else:
            print(f"\n{sat_type.value} Handovers (1h):")
            if not handovers:
                print("  No handovers (continuous coverage)")
            for ho in handovers:
                print(
                    f"  {ho.time_s:8.1f}s: {ho.from_sat} -> {ho.to_sat}"
                    f"  ({ho.duration_ms:.0f}ms, {ho.packet_loss_pct:.1f}% loss)"
                )

    elif args.assess:
        sat_type = SatelliteType(args.assess)
        result = run_full_simulation(sat_type)
        issues = assess_atc_suitability(result)
        if use_json:
            print(json.dumps({
                "satellite_type": sat_type.value,
                "meets_atc_requirement": result.meets_atc_requirement,
                "issues": list(issues),
                "latency_ms": result.budget.latency_ms,
                "availability_pct": result.availability_pct,
                "capacity_mbps": result.budget.capacity_mbps,
            }, indent=2))
        else:
            print(f"\nATC Suitability -- {sat_type.value}")
            print(f"  Meets requirement: {result.meets_atc_requirement}")
            if issues:
                for issue in issues:
                    print(f"  X {issue}")
            else:
                print("  OK All ATC requirements met")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
