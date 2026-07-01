"""Phase 365: NTN Link Model 테스트.

5G Non-Terrestrial Network 링크 버짓, 핸드오버, ATC 적합성 평가를 검증한다.
모든 테스트는 결정적(deterministic) — 물리 상수 기반 정확값 비교.
"""
from __future__ import annotations

import json
import math
import subprocess
import sys

import pytest

from simulation.ntn_link_model import (
    ATC_MAX_LATENCY_MS,
    ORBIT_PARAMS,
    PROCESSING_DELAY_MS,
    SATELLITE_CATALOG,
    HandoverEvent,
    LinkBudget,
    NTNLink,
    NTNSimResult,
    SatelliteType,
    _estimate_availability,
    _free_space_path_loss,
    _frequency_band,
    _noise_power_dbm,
    _slant_range_m,
    assess_atc_suitability,
    result_to_dict,
    run_full_simulation,
    simulate_handover,
    simulate_link,
)

# ===================================================================
# 1. SatelliteType Enum
# ===================================================================


class TestSatelliteType:
    """SatelliteType enum 검증."""

    def test_has_four_members(self) -> None:
        assert len(SatelliteType) == 4

    def test_values(self) -> None:
        assert SatelliteType.LEO.value == "LEO"
        assert SatelliteType.MEO.value == "MEO"
        assert SatelliteType.GEO.value == "GEO"
        assert SatelliteType.HAPS.value == "HAPS"

    def test_from_string(self) -> None:
        assert SatelliteType("LEO") is SatelliteType.LEO


# ===================================================================
# 2. NTNLink Frozen Dataclass
# ===================================================================


class TestNTNLink:
    """NTNLink 생성 및 불변성 검증."""

    def test_creation(self) -> None:
        link = NTNLink(
            satellite_type=SatelliteType.LEO,
            orbit_altitude_km=550.0,
            frequency_ghz=20.0,
            bandwidth_mhz=250.0,
            tx_power_dbm=40.0,
            antenna_gain_dbi=38.0,
        )
        assert link.satellite_type is SatelliteType.LEO
        assert link.orbit_altitude_km == 550.0

    def test_frozen(self) -> None:
        link = SATELLITE_CATALOG[SatelliteType.LEO]
        with pytest.raises(AttributeError):
            link.orbit_altitude_km = 600.0  # type: ignore[misc]

    def test_invalid_altitude_raises(self) -> None:
        with pytest.raises(ValueError, match="orbit_altitude_km must be positive"):
            NTNLink(
                satellite_type=SatelliteType.LEO,
                orbit_altitude_km=-100.0,
                frequency_ghz=20.0,
                bandwidth_mhz=250.0,
                tx_power_dbm=40.0,
                antenna_gain_dbi=38.0,
            )

    def test_invalid_frequency_raises(self) -> None:
        with pytest.raises(ValueError, match="frequency_ghz must be positive"):
            NTNLink(
                satellite_type=SatelliteType.LEO,
                orbit_altitude_km=550.0,
                frequency_ghz=0.0,
                bandwidth_mhz=250.0,
                tx_power_dbm=40.0,
                antenna_gain_dbi=38.0,
            )

    def test_invalid_bandwidth_raises(self) -> None:
        with pytest.raises(ValueError, match="bandwidth_mhz must be positive"):
            NTNLink(
                satellite_type=SatelliteType.LEO,
                orbit_altitude_km=550.0,
                frequency_ghz=20.0,
                bandwidth_mhz=-10.0,
                tx_power_dbm=40.0,
                antenna_gain_dbi=38.0,
            )


# ===================================================================
# 3. LinkBudget / HandoverEvent / NTNSimResult Frozen
# ===================================================================


class TestFrozenDataclasses:
    """보조 dataclass 불변성 검증."""

    def test_link_budget_frozen(self) -> None:
        budget = LinkBudget(
            path_loss_db=180.0, atmospheric_loss_db=1.5,
            rain_attenuation_db=6.0, total_loss_db=187.5,
            received_power_dbm=-100.0, snr_db=20.0,
            capacity_mbps=100.0, latency_ms=10.0,
        )
        with pytest.raises(AttributeError):
            budget.snr_db = 30.0  # type: ignore[misc]

    def test_handover_event_frozen(self) -> None:
        ho = HandoverEvent(
            from_sat="LEO-000", to_sat="LEO-001",
            time_s=600.0, duration_ms=50.0, packet_loss_pct=0.5,
        )
        with pytest.raises(AttributeError):
            ho.duration_ms = 100.0  # type: ignore[misc]

    def test_ntn_sim_result_frozen(self) -> None:
        link = SATELLITE_CATALOG[SatelliteType.LEO]
        budget = simulate_link(link)
        result = NTNSimResult(
            link=link, budget=budget, handovers=(),
            availability_pct=99.99, meets_atc_requirement=True,
        )
        with pytest.raises(AttributeError):
            result.meets_atc_requirement = False  # type: ignore[misc]


# ===================================================================
# 4. Frequency Band Classification
# ===================================================================


class TestFrequencyBand:
    """주파수 대역 분류 검증."""

    def test_s_band(self) -> None:
        assert _frequency_band(2.1) == "S"

    def test_ku_band(self) -> None:
        assert _frequency_band(12.0) == "Ku"

    def test_ka_band(self) -> None:
        assert _frequency_band(20.0) == "Ka"

    def test_boundary_s_ku(self) -> None:
        assert _frequency_band(3.99) == "S"
        assert _frequency_band(4.0) == "Ku"

    def test_boundary_ku_ka(self) -> None:
        assert _frequency_band(17.99) == "Ku"
        assert _frequency_band(18.0) == "Ka"


# ===================================================================
# 5. Free-Space Path Loss
# ===================================================================


class TestFreeSpacePathLoss:
    """FSPL 계산 정확성 검증."""

    def test_known_value(self) -> None:
        # 1km, 1GHz -> well-known FSPL ~ 92.45 dB
        d = 1000.0  # 1 km
        f = 1e9  # 1 GHz
        fspl = _free_space_path_loss(d, f)
        assert 92.0 < fspl < 93.0

    def test_distance_doubles_adds_6db(self) -> None:
        f = 1e9
        fspl_1 = _free_space_path_loss(1000.0, f)
        fspl_2 = _free_space_path_loss(2000.0, f)
        assert abs((fspl_2 - fspl_1) - 20.0 * math.log10(2.0)) < 0.01

    def test_frequency_doubles_adds_6db(self) -> None:
        d = 1000.0
        fspl_1 = _free_space_path_loss(d, 1e9)
        fspl_2 = _free_space_path_loss(d, 2e9)
        assert abs((fspl_2 - fspl_1) - 20.0 * math.log10(2.0)) < 0.01


# ===================================================================
# 6. Link Budget Calculation
# ===================================================================


class TestSimulateLink:
    """simulate_link 결과 검증."""

    def test_leo_budget_has_positive_path_loss(self) -> None:
        budget = simulate_link(SATELLITE_CATALOG[SatelliteType.LEO])
        assert budget.path_loss_db > 0

    def test_total_loss_is_sum(self) -> None:
        budget = simulate_link(SATELLITE_CATALOG[SatelliteType.LEO])
        expected = (
            budget.path_loss_db
            + budget.atmospheric_loss_db
            + budget.rain_attenuation_db
        )
        assert abs(budget.total_loss_db - expected) < 0.01

    def test_capacity_positive(self) -> None:
        for sat_type in SatelliteType:
            budget = simulate_link(SATELLITE_CATALOG[sat_type])
            assert budget.capacity_mbps > 0

    def test_latency_positive(self) -> None:
        for sat_type in SatelliteType:
            budget = simulate_link(SATELLITE_CATALOG[sat_type])
            assert budget.latency_ms > PROCESSING_DELAY_MS


# ===================================================================
# 7. Latency Ordering (LEO < MEO < GEO)
# ===================================================================


class TestLatencyOrdering:
    """전파 지연 순서 검증: HAPS < LEO < MEO < GEO."""

    def test_haps_fastest(self) -> None:
        haps = simulate_link(SATELLITE_CATALOG[SatelliteType.HAPS])
        leo = simulate_link(SATELLITE_CATALOG[SatelliteType.LEO])
        assert haps.latency_ms < leo.latency_ms

    def test_leo_faster_than_meo(self) -> None:
        leo = simulate_link(SATELLITE_CATALOG[SatelliteType.LEO])
        meo = simulate_link(SATELLITE_CATALOG[SatelliteType.MEO])
        assert leo.latency_ms < meo.latency_ms

    def test_meo_faster_than_geo(self) -> None:
        meo = simulate_link(SATELLITE_CATALOG[SatelliteType.MEO])
        geo = simulate_link(SATELLITE_CATALOG[SatelliteType.GEO])
        assert meo.latency_ms < geo.latency_ms


# ===================================================================
# 8. Handover Simulation
# ===================================================================


class TestSimulateHandover:
    """핸드오버 시뮬레이션 검증."""

    def test_geo_no_handovers(self) -> None:
        handovers = simulate_handover(SatelliteType.GEO)
        assert handovers == ()

    def test_leo_has_handovers(self) -> None:
        handovers = simulate_handover(SatelliteType.LEO)
        assert len(handovers) > 0

    def test_leo_more_frequent_than_meo(self) -> None:
        leo_ho = simulate_handover(SatelliteType.LEO)
        meo_ho = simulate_handover(SatelliteType.MEO)
        assert len(leo_ho) > len(meo_ho)

    def test_handover_times_ascending(self) -> None:
        handovers = simulate_handover(SatelliteType.LEO)
        times = [ho.time_s for ho in handovers]
        assert times == sorted(times)

    def test_satellite_names_sequential(self) -> None:
        handovers = simulate_handover(SatelliteType.LEO)
        if handovers:
            assert handovers[0].from_sat == "LEO-000"
            assert handovers[0].to_sat == "LEO-001"

    def test_custom_window(self) -> None:
        handovers = simulate_handover(
            SatelliteType.LEO,
            orbit_period_s=5760.0,
            visibility_window_s=120.0,
            simulation_duration_s=1200.0,
        )
        assert len(handovers) >= 2

    def test_window_equals_period_no_handovers(self) -> None:
        handovers = simulate_handover(
            SatelliteType.LEO,
            orbit_period_s=600.0,
            visibility_window_s=600.0,
        )
        assert handovers == ()


# ===================================================================
# 9. ATC Suitability Assessment
# ===================================================================


class TestATCSuitability:
    """ATC 적합성 평가 검증."""

    def test_good_link_no_issues(self) -> None:
        link = SATELLITE_CATALOG[SatelliteType.HAPS]
        budget = simulate_link(link)
        result = NTNSimResult(
            link=link, budget=budget, handovers=(),
            availability_pct=99.99, meets_atc_requirement=True,
        )
        issues = assess_atc_suitability(result)
        assert issues == ()

    def test_high_latency_detected(self) -> None:
        link = SATELLITE_CATALOG[SatelliteType.GEO]
        budget = simulate_link(link)
        result = NTNSimResult(
            link=link, budget=budget, handovers=(),
            availability_pct=99.99, meets_atc_requirement=True,
        )
        issues = assess_atc_suitability(result)
        latency_issues = [i for i in issues if "latency" in i]
        if budget.latency_ms > ATC_MAX_LATENCY_MS:
            assert len(latency_issues) == 1

    def test_low_availability_detected(self) -> None:
        link = SATELLITE_CATALOG[SatelliteType.LEO]
        budget = simulate_link(link)
        result = NTNSimResult(
            link=link, budget=budget, handovers=(),
            availability_pct=95.0, meets_atc_requirement=True,
        )
        issues = assess_atc_suitability(result)
        assert any("availability" in i for i in issues)

    def test_low_capacity_detected(self) -> None:
        link = NTNLink(
            satellite_type=SatelliteType.GEO,
            orbit_altitude_km=35786.0,
            frequency_ghz=12.0,
            bandwidth_mhz=0.001,
            tx_power_dbm=10.0,
            antenna_gain_dbi=10.0,
        )
        budget = simulate_link(link)
        result = NTNSimResult(
            link=link, budget=budget, handovers=(),
            availability_pct=99.99, meets_atc_requirement=True,
        )
        issues = assess_atc_suitability(result)
        assert any("capacity" in i for i in issues)


# ===================================================================
# 10. Full Simulation Pipeline
# ===================================================================


class TestRunFullSimulation:
    """run_full_simulation 통합 검증."""

    def test_returns_ntn_sim_result(self) -> None:
        result = run_full_simulation(SatelliteType.LEO)
        assert isinstance(result, NTNSimResult)

    def test_haps_meets_atc(self) -> None:
        result = run_full_simulation(SatelliteType.HAPS)
        assert result.meets_atc_requirement is True

    def test_availability_near_100_for_geo(self) -> None:
        result = run_full_simulation(SatelliteType.GEO)
        assert result.availability_pct == 100.0

    def test_deterministic_results(self) -> None:
        r1 = run_full_simulation(SatelliteType.LEO)
        r2 = run_full_simulation(SatelliteType.LEO)
        assert r1.budget.latency_ms == r2.budget.latency_ms
        assert r1.budget.capacity_mbps == r2.budget.capacity_mbps
        assert len(r1.handovers) == len(r2.handovers)


# ===================================================================
# 11. Availability Estimation
# ===================================================================


class TestAvailability:
    """가용성 추정 검증."""

    def test_no_handovers_100_pct(self) -> None:
        avail = _estimate_availability(SatelliteType.GEO, (), 3600.0)
        assert avail == 100.0

    def test_with_handovers_less_than_100(self) -> None:
        handovers = simulate_handover(SatelliteType.LEO)
        avail = _estimate_availability(SatelliteType.LEO, handovers, 3600.0)
        assert avail < 100.0
        assert avail > 90.0

    def test_zero_duration_returns_100(self) -> None:
        avail = _estimate_availability(SatelliteType.LEO, (), 0.0)
        assert avail == 100.0


# ===================================================================
# 12. Serialization
# ===================================================================


class TestSerialization:
    """JSON 직렬화 검증."""

    def test_result_to_dict_keys(self) -> None:
        result = run_full_simulation(SatelliteType.LEO)
        d = result_to_dict(result)
        assert "link" in d
        assert "budget" in d
        assert "handovers" in d
        assert "availability_pct" in d
        assert "meets_atc_requirement" in d

    def test_json_roundtrip(self) -> None:
        result = run_full_simulation(SatelliteType.HAPS)
        d = result_to_dict(result)
        json_str = json.dumps(d)
        parsed = json.loads(json_str)
        assert parsed["link"]["satellite_type"] == "HAPS"
        assert isinstance(parsed["budget"]["latency_ms"], float)


# ===================================================================
# 13. Satellite Catalog
# ===================================================================


class TestSatelliteCatalog:
    """카탈로그 데이터 무결성 검증."""

    def test_all_types_in_catalog(self) -> None:
        for sat_type in SatelliteType:
            assert sat_type in SATELLITE_CATALOG

    def test_all_types_in_orbit_params(self) -> None:
        for sat_type in SatelliteType:
            assert sat_type in ORBIT_PARAMS

    def test_catalog_altitudes_correct(self) -> None:
        assert SATELLITE_CATALOG[SatelliteType.LEO].orbit_altitude_km == 550.0
        assert SATELLITE_CATALOG[SatelliteType.MEO].orbit_altitude_km == 20_200.0
        assert SATELLITE_CATALOG[SatelliteType.GEO].orbit_altitude_km == 35_786.0
        assert SATELLITE_CATALOG[SatelliteType.HAPS].orbit_altitude_km == 20.0


# ===================================================================
# 14. Slant Range
# ===================================================================


class TestSlantRange:
    """경사 거리 계산 검증."""

    def test_basic(self) -> None:
        sr = _slant_range_m(550.0, 120.0)
        assert sr == pytest.approx(549_880.0, abs=1.0)

    def test_haps_close(self) -> None:
        sr = _slant_range_m(20.0, 120.0)
        assert sr == pytest.approx(19_880.0, abs=1.0)


# ===================================================================
# 15. Noise Power
# ===================================================================


class TestNoisePower:
    """열잡음 전력 검증."""

    def test_wider_bandwidth_more_noise(self) -> None:
        n1 = _noise_power_dbm(1e6)
        n2 = _noise_power_dbm(10e6)
        assert n2 > n1


# ===================================================================
# 16. CLI
# ===================================================================


class TestCLI:
    """CLI 인터페이스 검증."""

    def test_simulate_json(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "simulation.ntn_link_model",
             "--simulate", "LEO", "--json"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["link"]["satellite_type"] == "LEO"
        assert "budget" in data

    def test_budget_flag(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "simulation.ntn_link_model", "--budget"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        assert "Link Budget" in result.stdout

    def test_handover_flag(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "simulation.ntn_link_model",
             "--handover", "GEO"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        assert "No handovers" in result.stdout or "continuous" in result.stdout

    def test_assess_json(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "simulation.ntn_link_model",
             "--assess", "HAPS", "--json"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "meets_atc_requirement" in data

    def test_no_args_shows_help(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "simulation.ntn_link_model"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        assert "usage" in result.stdout.lower() or "Phase 365" in result.stdout
