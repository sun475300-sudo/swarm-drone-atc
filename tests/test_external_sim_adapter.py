"""
외부 시뮬레이터 어댑터 테스트 (GENESIS Phase 323)
=================================================
SDACS ↔ BlueSky/U-TRAFMAN 호환 import/export 변환기 검증.
결정적·오프라인·재현성을 단언한다.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from simulation.external_sim_adapter import (
    DEFAULT_REF_LAT,
    DEFAULT_REF_LON,
    ExchangeAircraft,
    ScenarioExchange,
    bluesky_to_exchange,
    exchange_to_bluesky,
    exchange_to_sdacs,
    exchange_to_utrafman,
    latlon_to_local_km,
    local_km_to_latlon,
    sdacs_to_exchange,
    utrafman_to_exchange,
)
from simulation.scenario_schema import validate_scenario

_SCENARIO_DIR = Path(__file__).resolve().parent.parent / "config" / "scenario_params"


# ── 좌표 투영 (왕복 항등) ────────────────────────────────────────────────────
def test_local_km_origin_maps_to_reference():
    lat, lon = local_km_to_latlon(0.0, 0.0, DEFAULT_REF_LAT, DEFAULT_REF_LON)
    assert lat == pytest.approx(DEFAULT_REF_LAT)
    assert lon == pytest.approx(DEFAULT_REF_LON)


def test_local_km_north_increases_latitude():
    lat, _ = local_km_to_latlon(0.0, 11.132, DEFAULT_REF_LAT, DEFAULT_REF_LON)
    assert lat > DEFAULT_REF_LAT


def test_km_latlon_roundtrip_recovers_offset():
    x0, y0 = 3.5, -2.25
    lat, lon = local_km_to_latlon(x0, y0, DEFAULT_REF_LAT, DEFAULT_REF_LON)
    x1, y1 = latlon_to_local_km(lat, lon, DEFAULT_REF_LAT, DEFAULT_REF_LON)
    assert x1 == pytest.approx(x0, abs=1e-6)
    assert y1 == pytest.approx(y0, abs=1e-6)


# ── SDACS → IR 물질화 ───────────────────────────────────────────────────────
def _sample_scenario() -> dict:
    return {
        "scenario": "unit_sample",
        "description": "단위 테스트 시나리오",
        "drone_count": 12,
        "simulation_duration_min": 10,
        "area_km2": 64.0,
        "drone_profile_distribution": {"COMMERCIAL_DELIVERY": 0.6, "SURVEILLANCE": 0.4},
    }


def test_sdacs_to_exchange_materializes_drone_count_aircraft():
    ex = sdacs_to_exchange(_sample_scenario(), seed=7)
    assert len(ex.aircraft) == 12


def test_sdacs_to_exchange_is_deterministic_for_same_seed():
    a = sdacs_to_exchange(_sample_scenario(), seed=7)
    b = sdacs_to_exchange(_sample_scenario(), seed=7)
    assert a == b


def test_sdacs_to_exchange_differs_for_different_seed():
    a = sdacs_to_exchange(_sample_scenario(), seed=1)
    b = sdacs_to_exchange(_sample_scenario(), seed=2)
    assert a.aircraft != b.aircraft


def test_materialized_aircraft_within_area_bounds():
    scenario = _sample_scenario()
    ex = sdacs_to_exchange(scenario, seed=3)
    half = (scenario["area_km2"] ** 0.5) / 2.0
    for ac in ex.aircraft:
        x, y = latlon_to_local_km(ac.lat, ac.lon, ex.ref_lat, ex.ref_lon)
        assert -half - 1e-6 <= x <= half + 1e-6
        assert -half - 1e-6 <= y <= half + 1e-6


def test_duration_minutes_converted_to_seconds():
    ex = sdacs_to_exchange(_sample_scenario(), seed=0)
    assert ex.duration_s == pytest.approx(600.0)


def test_profile_distribution_types_drawn_from_keys():
    ex = sdacs_to_exchange(_sample_scenario(), seed=5)
    allowed = {"COMMERCIAL_DELIVERY", "SURVEILLANCE"}
    assert {ac.type_code for ac in ex.aircraft} <= allowed


def test_missing_distribution_falls_back_to_default_type():
    scenario = {"scenario": "x", "drone_count": 3, "area_km2": 16.0}
    ex = sdacs_to_exchange(scenario, seed=0)
    assert {ac.type_code for ac in ex.aircraft} == {"MULTIROTOR"}


# ── IR → SDACS (스키마 호환) ────────────────────────────────────────────────
def test_exchange_to_sdacs_passes_schema_validation():
    ex = sdacs_to_exchange(_sample_scenario(), seed=0)
    scenario = exchange_to_sdacs(ex)
    result = validate_scenario(scenario)
    assert result.is_valid, result.errors


def test_exchange_to_sdacs_preserves_drone_count():
    ex = sdacs_to_exchange(_sample_scenario(), seed=0)
    assert exchange_to_sdacs(ex)["drone_count"] == 12


# ── BlueSky export/import ───────────────────────────────────────────────────
def test_bluesky_export_has_cre_and_dest_per_aircraft():
    ex = sdacs_to_exchange(_sample_scenario(), seed=0)
    scn = exchange_to_bluesky(ex)
    assert scn.count(">CRE ") == 12
    assert scn.count(">DEST ") == 12


def test_bluesky_export_lines_are_time_stamped():
    ex = sdacs_to_exchange(_sample_scenario(), seed=0)
    scn = exchange_to_bluesky(ex)
    cmd_lines = [ln for ln in scn.splitlines() if ln and not ln.startswith("#")]
    assert all(ln.startswith("00:00:00.00>") for ln in cmd_lines)


def test_bluesky_roundtrip_preserves_aircraft_count():
    ex = sdacs_to_exchange(_sample_scenario(), seed=0)
    back = bluesky_to_exchange(exchange_to_bluesky(ex))
    assert len(back.aircraft) == len(ex.aircraft)


def test_bluesky_roundtrip_preserves_coordinates():
    ex = sdacs_to_exchange(_sample_scenario(), seed=0)
    back = bluesky_to_exchange(exchange_to_bluesky(ex))
    orig = ex.aircraft[0]
    rt = back.aircraft[0]
    assert rt.lat == pytest.approx(orig.lat, abs=1e-5)
    assert rt.lon == pytest.approx(orig.lon, abs=1e-5)
    assert rt.dest_lat == pytest.approx(orig.dest_lat, abs=1e-5)


def test_bluesky_roundtrip_preserves_altitude_and_speed():
    ex = sdacs_to_exchange(_sample_scenario(), seed=0)
    back = bluesky_to_exchange(exchange_to_bluesky(ex))
    assert back.aircraft[0].alt_m == pytest.approx(ex.aircraft[0].alt_m, abs=0.1)
    assert back.aircraft[0].spd_ms == pytest.approx(ex.aircraft[0].spd_ms, abs=0.05)


def test_bluesky_import_ignores_comments_and_blank_lines():
    scn = (
        "# header comment\n"
        "\n"
        "00:00:00.00>CRE SD0000,MULTIROTOR,34.790000,126.390000,90.00,328.1,29.16\n"
        "00:00:00.00>DEST SD0000,34.800000,126.400000\n"
    )
    ex = bluesky_to_exchange(scn)
    assert len(ex.aircraft) == 1
    assert ex.aircraft[0].acid == "SD0000"


def test_bluesky_import_preserves_cre_order():
    scn = (
        "00:00:00.00>CRE BBB,MULTIROTOR,34.7,126.3,0,328,29\n"
        "00:00:00.00>CRE AAA,MULTIROTOR,34.8,126.4,0,328,29\n"
    )
    ex = bluesky_to_exchange(scn)
    assert [ac.acid for ac in ex.aircraft] == ["BBB", "AAA"]


def test_bluesky_import_aircraft_without_dest_uses_origin():
    scn = "00:00:00.00>CRE SOLO,MULTIROTOR,34.75,126.35,45,328,29\n"
    ex = bluesky_to_exchange(scn)
    ac = ex.aircraft[0]
    assert ac.dest_lat == pytest.approx(ac.lat)
    assert ac.dest_lon == pytest.approx(ac.lon)


def test_bluesky_import_skips_malformed_coordinate_lines():
    scn = (
        "00:00:00.00>CRE BAD,MULTIROTOR,not_a_number,126.3,0,328,29\n"
        "00:00:00.00>CRE OK,MULTIROTOR,34.8,126.4,0,328,29\n"
    )
    ex = bluesky_to_exchange(scn)
    assert [ac.acid for ac in ex.aircraft] == ["OK"]


def test_bluesky_import_skips_short_cre_lines():
    scn = (
        "00:00:00.00>CRE SHORT,MULTIROTOR,34.8,126.4\n"  # 4 필드 < 7
        "00:00:00.00>CRE FULL,MULTIROTOR,34.8,126.4,0,328,29\n"
    )
    ex = bluesky_to_exchange(scn)
    assert [ac.acid for ac in ex.aircraft] == ["FULL"]


# ── U-TRAFMAN export/import ─────────────────────────────────────────────────
def test_utrafman_export_one_plan_per_aircraft():
    ex = sdacs_to_exchange(_sample_scenario(), seed=0)
    doc = exchange_to_utrafman(ex)
    assert len(doc["flight_plans"]) == 12
    assert doc["format"] == "u-trafman/flight-plan"


def test_utrafman_roundtrip_preserves_aircraft():
    ex = sdacs_to_exchange(_sample_scenario(), seed=0)
    back = utrafman_to_exchange(exchange_to_utrafman(ex))
    assert len(back.aircraft) == len(ex.aircraft)
    assert back.aircraft[0].acid == ex.aircraft[0].acid
    assert back.aircraft[0].lat == pytest.approx(ex.aircraft[0].lat, abs=1e-6)
    assert back.aircraft[0].spd_ms == pytest.approx(ex.aircraft[0].spd_ms)


def test_utrafman_roundtrip_preserves_reference_origin():
    ex = sdacs_to_exchange(_sample_scenario(), seed=0)
    back = utrafman_to_exchange(exchange_to_utrafman(ex))
    assert back.ref_lat == pytest.approx(ex.ref_lat)
    assert back.ref_lon == pytest.approx(ex.ref_lon)


def test_utrafman_import_missing_destination_raises():
    doc = {"flight_plans": [{"flight_id": "X", "origin": [34.8, 126.4]}]}
    with pytest.raises(ValueError, match="missing origin/destination"):
        utrafman_to_exchange(doc)


def test_utrafman_import_without_reference_origin_uses_default():
    doc = {
        "flight_plans": [
            {"flight_id": "X", "origin": [34.8, 126.4], "destination": [34.81, 126.41]}
        ]
    }
    ex = utrafman_to_exchange(doc)
    assert ex.ref_lat == pytest.approx(DEFAULT_REF_LAT)
    assert ex.ref_lon == pytest.approx(DEFAULT_REF_LON)


# ── 경계: 빈 교환 ───────────────────────────────────────────────────────────
def test_exchange_to_sdacs_rejects_empty_aircraft():
    empty = bluesky_to_exchange("# comments only\n")
    assert empty.aircraft == ()
    with pytest.raises(ValueError, match="empty exchange"):
        exchange_to_sdacs(empty)


# ── 실 시나리오 파일 통합 (오프라인) ────────────────────────────────────────
def test_real_scenario_files_export_to_both_formats():
    import yaml

    for path in sorted(_SCENARIO_DIR.glob("*.yaml")):
        scenario = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(scenario, dict):
            continue
        ex = sdacs_to_exchange(scenario, seed=0)
        # 양 포맷 모두 예외 없이 생성되어야 한다
        scn = exchange_to_bluesky(ex)
        doc = exchange_to_utrafman(ex)
        assert isinstance(scn, str)
        assert doc["scenario"] == ex.name


def test_high_density_roundtrip_recovers_drone_count():
    import yaml

    path = _SCENARIO_DIR / "high_density.yaml"
    scenario = yaml.safe_load(path.read_text(encoding="utf-8"))
    ex = sdacs_to_exchange(scenario, seed=0)
    back = bluesky_to_exchange(exchange_to_bluesky(ex))
    assert len(back.aircraft) == scenario["drone_count"]
