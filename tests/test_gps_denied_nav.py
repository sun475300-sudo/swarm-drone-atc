"""GENESIS Phase 366 -- GPS-Denied Navigation Fallback Model 테스트.

검증 항목:
- NavSource enum 완전성
- NavAccuracy / NavFusion / GPSDeniedScenario / NavAssessment frozen
- NAV_SOURCE_CATALOG 카탈로그 값 검증
- select_nav_sources 결정적 선택 로직
- fuse_accuracy 역분산 가중 퓨전
- safe_flight_duration 드리프트 기반 안전 시간
- assess_scenario 시나리오 종합 평가
- SCENARIOS 사전 정의 시나리오
- CLI: --sources, --scenarios, --assess, --fuse, --json
"""
from __future__ import annotations

import json
import math
import subprocess
import sys

import pytest

from simulation.gps_denied_nav import (
    NAV_SOURCE_CATALOG,
    SCENARIOS,
    GPSDeniedScenario,
    NavFusion,
    NavSource,
    assess_scenario,
    fuse_accuracy,
    safe_flight_duration,
    select_nav_sources,
)

# ── NavSource enum ─────────────────────────────────────────────────────

class TestNavSource:
    def test_all_seven_members(self) -> None:
        expected = {
            "GPS", "RTK_GPS", "VIO", "UWB",
            "BAROMETER", "IMU_DEAD_RECKONING", "TERRAIN_MATCHING",
        }
        assert {s.value for s in NavSource} == expected

    def test_member_count(self) -> None:
        assert len(NavSource) == 7


# ── Frozen dataclasses ─────────────────────────────────────────────────

class TestFrozenDataclasses:
    def test_nav_accuracy_frozen(self) -> None:
        acc = NAV_SOURCE_CATALOG[NavSource.GPS]
        with pytest.raises(AttributeError):
            acc.horizontal_m = 999.0  # type: ignore[misc]

    def test_nav_fusion_frozen(self) -> None:
        fusion = NavFusion(
            sources=(NavSource.GPS,),
            fused_horizontal_m=1.0,
            fused_vertical_m=1.0,
            degradation_factor=1.0,
        )
        with pytest.raises(AttributeError):
            fusion.fused_horizontal_m = 0.0  # type: ignore[misc]

    def test_gps_denied_scenario_frozen(self) -> None:
        s = SCENARIOS["jamming"]
        with pytest.raises(AttributeError):
            s.gps_available = True  # type: ignore[misc]

    def test_nav_assessment_frozen(self) -> None:
        assessment = assess_scenario(SCENARIOS["jamming"])
        with pytest.raises(AttributeError):
            assessment.recommendation = "x"  # type: ignore[misc]


# ── Source catalog ─────────────────────────────────────────────────────

class TestNavSourceCatalog:
    def test_catalog_covers_all_sources(self) -> None:
        for src in NavSource:
            assert src in NAV_SOURCE_CATALOG

    def test_gps_accuracy(self) -> None:
        gps = NAV_SOURCE_CATALOG[NavSource.GPS]
        assert gps.horizontal_m == 2.5
        assert gps.vertical_m == 5.0
        assert gps.update_rate_hz == 10.0
        assert gps.drift_rate_m_per_s == 0.0
        assert gps.max_range_m is None

    def test_rtk_accuracy(self) -> None:
        rtk = NAV_SOURCE_CATALOG[NavSource.RTK_GPS]
        assert rtk.horizontal_m == 0.02
        assert rtk.vertical_m == 0.03
        assert rtk.update_rate_hz == 20.0
        assert rtk.drift_rate_m_per_s == 0.0

    def test_vio_has_drift(self) -> None:
        vio = NAV_SOURCE_CATALOG[NavSource.VIO]
        assert vio.drift_rate_m_per_s == 0.01

    def test_uwb_has_range_limit(self) -> None:
        uwb = NAV_SOURCE_CATALOG[NavSource.UWB]
        assert uwb.max_range_m == 100.0

    def test_barometer_horizontal_is_inf(self) -> None:
        baro = NAV_SOURCE_CATALOG[NavSource.BAROMETER]
        assert math.isinf(baro.horizontal_m)
        assert baro.vertical_m == 0.5

    def test_imu_high_drift(self) -> None:
        imu = NAV_SOURCE_CATALOG[NavSource.IMU_DEAD_RECKONING]
        assert imu.drift_rate_m_per_s == 0.5
        assert imu.update_rate_hz == 200.0

    def test_terrain_matching_low_rate(self) -> None:
        tm = NAV_SOURCE_CATALOG[NavSource.TERRAIN_MATCHING]
        assert tm.update_rate_hz == 1.0
        assert tm.drift_rate_m_per_s == 0.0


# ── select_nav_sources ─────────────────────────────────────────────────

class TestSelectNavSources:
    def test_gps_available_outdoor(self) -> None:
        scenario = GPSDeniedScenario(
            name="test", gps_available=True, rtk_available=False,
            indoor=False, duration_s=60.0,
        )
        sources = select_nav_sources(scenario)
        assert sources[0] == NavSource.GPS

    def test_rtk_available_is_primary(self) -> None:
        scenario = GPSDeniedScenario(
            name="test", gps_available=True, rtk_available=True,
            indoor=False, duration_s=60.0,
        )
        sources = select_nav_sources(scenario)
        assert sources[0] == NavSource.RTK_GPS
        assert NavSource.GPS not in sources

    def test_indoor_includes_vio_and_uwb(self) -> None:
        scenario = GPSDeniedScenario(
            name="test", gps_available=False, rtk_available=False,
            indoor=True, duration_s=60.0,
        )
        sources = select_nav_sources(scenario)
        assert NavSource.VIO in sources
        assert NavSource.UWB in sources
        assert NavSource.GPS not in sources

    def test_indoor_excludes_terrain_matching(self) -> None:
        scenario = GPSDeniedScenario(
            name="test", gps_available=False, rtk_available=False,
            indoor=True, duration_s=60.0,
        )
        sources = select_nav_sources(scenario)
        assert NavSource.TERRAIN_MATCHING not in sources

    def test_outdoor_includes_terrain_matching(self) -> None:
        scenario = GPSDeniedScenario(
            name="test", gps_available=False, rtk_available=False,
            indoor=False, duration_s=60.0,
        )
        sources = select_nav_sources(scenario)
        assert NavSource.TERRAIN_MATCHING in sources

    def test_always_includes_barometer_and_imu(self) -> None:
        for scenario in SCENARIOS.values():
            sources = select_nav_sources(scenario)
            assert NavSource.BAROMETER in sources
            assert NavSource.IMU_DEAD_RECKONING in sources


# ── fuse_accuracy ──────────────────────────────────────────────────────

class TestFuseAccuracy:
    def test_empty_sources_returns_inf(self) -> None:
        fusion = fuse_accuracy(())
        assert math.isinf(fusion.fused_horizontal_m)
        assert math.isinf(fusion.fused_vertical_m)
        assert fusion.degradation_factor == 1.0

    def test_single_source(self) -> None:
        gps_acc = NAV_SOURCE_CATALOG[NavSource.GPS]
        fusion = fuse_accuracy((gps_acc,))
        assert fusion.fused_horizontal_m == gps_acc.horizontal_m
        assert fusion.sources == (NavSource.GPS,)

    def test_fusion_better_than_worst(self) -> None:
        gps_acc = NAV_SOURCE_CATALOG[NavSource.GPS]
        vio_acc = NAV_SOURCE_CATALOG[NavSource.VIO]
        fusion = fuse_accuracy((gps_acc, vio_acc))
        worst_h = max(gps_acc.horizontal_m, vio_acc.horizontal_m)
        assert fusion.fused_horizontal_m < worst_h

    def test_fusion_better_than_or_equal_to_best(self) -> None:
        gps_acc = NAV_SOURCE_CATALOG[NavSource.GPS]
        vio_acc = NAV_SOURCE_CATALOG[NavSource.VIO]
        fusion = fuse_accuracy((gps_acc, vio_acc))
        best_h = min(gps_acc.horizontal_m, vio_acc.horizontal_m)
        assert fusion.fused_horizontal_m <= best_h

    def test_barometer_inf_horizontal_ignored_in_fusion(self) -> None:
        baro = NAV_SOURCE_CATALOG[NavSource.BAROMETER]
        gps = NAV_SOURCE_CATALOG[NavSource.GPS]
        fusion = fuse_accuracy((gps, baro))
        assert math.isfinite(fusion.fused_horizontal_m)

    def test_degradation_factor_leq_one(self) -> None:
        accs = tuple(
            NAV_SOURCE_CATALOG[s] for s in NavSource
            if s != NavSource.BAROMETER
        )
        fusion = fuse_accuracy(accs)
        assert fusion.degradation_factor <= 1.0

    def test_deterministic(self) -> None:
        accs = tuple(NAV_SOURCE_CATALOG.values())
        f1 = fuse_accuracy(accs)
        f2 = fuse_accuracy(accs)
        assert f1 == f2


# ── safe_flight_duration ───────────────────────────────────────────────

class TestSafeFlightDuration:
    def test_no_drift_sources_infinite(self) -> None:
        fusion = NavFusion(
            sources=(NavSource.GPS, NavSource.RTK_GPS),
            fused_horizontal_m=0.02,
            fused_vertical_m=0.03,
            degradation_factor=1.0,
        )
        assert math.isinf(safe_flight_duration(fusion))

    def test_high_drift_short_duration(self) -> None:
        fusion = NavFusion(
            sources=(NavSource.IMU_DEAD_RECKONING,),
            fused_horizontal_m=1.0,
            fused_vertical_m=1.0,
            degradation_factor=1.0,
        )
        duration = safe_flight_duration(fusion, max_position_error_m=5.0)
        assert duration == pytest.approx(8.0, abs=0.1)

    def test_error_already_exceeded_returns_zero(self) -> None:
        fusion = NavFusion(
            sources=(NavSource.IMU_DEAD_RECKONING,),
            fused_horizontal_m=10.0,
            fused_vertical_m=1.0,
            degradation_factor=1.0,
        )
        assert safe_flight_duration(fusion, max_position_error_m=5.0) == 0.0

    def test_higher_threshold_longer_duration(self) -> None:
        fusion = NavFusion(
            sources=(NavSource.VIO,),
            fused_horizontal_m=0.1,
            fused_vertical_m=0.5,
            degradation_factor=1.0,
        )
        d5 = safe_flight_duration(fusion, max_position_error_m=5.0)
        d10 = safe_flight_duration(fusion, max_position_error_m=10.0)
        assert d10 > d5


# ── assess_scenario ────────────────────────────────────────────────────

class TestAssessScenario:
    def test_urban_canyon_primary_is_gps(self) -> None:
        a = assess_scenario(SCENARIOS["urban_canyon"])
        assert a.primary == NavSource.GPS

    def test_indoor_warehouse_no_gps(self) -> None:
        a = assess_scenario(SCENARIOS["indoor_warehouse"])
        assert a.primary != NavSource.GPS
        assert a.primary != NavSource.RTK_GPS

    def test_jamming_no_gps(self) -> None:
        a = assess_scenario(SCENARIOS["jamming"])
        assert NavSource.GPS not in (a.primary, *a.fallbacks)

    def test_assessment_has_recommendation(self) -> None:
        for name in SCENARIOS:
            a = assess_scenario(SCENARIOS[name])
            assert len(a.recommendation) > 0

    def test_rtk_lost_falls_back_to_gps(self) -> None:
        a = assess_scenario(SCENARIOS["rtk_lost"])
        assert a.primary == NavSource.GPS


# ── SCENARIOS registry ─────────────────────────────────────────────────

class TestScenarios:
    def test_five_predefined(self) -> None:
        expected = {
            "urban_canyon", "indoor_warehouse", "jamming",
            "spoofing_detected", "rtk_lost",
        }
        assert set(SCENARIOS) == expected

    def test_all_scenarios_assessable(self) -> None:
        for name, scenario in SCENARIOS.items():
            a = assess_scenario(scenario)
            assert a.scenario.name == name


# ── CLI ────────────────────────────────────────────────────────────────

_MODULE = "simulation.gps_denied_nav"


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", _MODULE, *args],
        capture_output=True, text=True, timeout=30,
    )


class TestCLI:
    def test_sources(self) -> None:
        r = _run_cli("--sources")
        assert r.returncode == 0
        assert "GPS" in r.stdout

    def test_sources_json(self) -> None:
        r = _run_cli("--sources", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert len(data) == 7
        assert all("source" in d for d in data)

    def test_scenarios(self) -> None:
        r = _run_cli("--scenarios")
        assert r.returncode == 0
        assert "urban_canyon" in r.stdout

    def test_scenarios_json(self) -> None:
        r = _run_cli("--scenarios", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert len(data) == 5

    def test_assess_urban_canyon(self) -> None:
        r = _run_cli("--assess", "urban_canyon")
        assert r.returncode == 0
        assert "Primary" in r.stdout

    def test_assess_json(self) -> None:
        r = _run_cli("--assess", "indoor_warehouse", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["scenario"] == "indoor_warehouse"
        assert "primary" in data

    def test_fuse(self) -> None:
        r = _run_cli("--fuse", "GPS", "VIO")
        assert r.returncode == 0
        assert "Fused" in r.stdout

    def test_fuse_json(self) -> None:
        r = _run_cli("--fuse", "GPS", "VIO", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "fused_horizontal_m" in data

    def test_invalid_scenario(self) -> None:
        r = _run_cli("--assess", "nonexistent")
        assert r.returncode != 0

    def test_invalid_fuse_source(self) -> None:
        r = _run_cli("--fuse", "INVALID_SOURCE")
        assert r.returncode != 0

    def test_no_args_shows_help(self) -> None:
        r = _run_cli()
        assert r.returncode == 0
        assert "Phase 366" in r.stdout or "usage" in r.stdout.lower()
