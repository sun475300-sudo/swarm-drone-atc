"""GENESIS Phase 323 — 외부 시뮬레이터 어댑터 테스트.

BlueSky ``.scn`` / U-TRAFMAN JSON 상호 변환의 *왕복 항등*·*결정성*·*검증*을
확인한다. 외부 시뮬레이터 구동이 아니라 포맷 변환기 계약을 검증한다.
"""
from __future__ import annotations

import json
import math

import pytest

from simulation.external_sim_adapter import (
    AdapterScenario,
    Aircraft,
    Waypoint,
    _demo_scenario,
    _self_test,
    enu_to_geodetic,
    from_bluesky_scn,
    from_utrafman_dict,
    from_utrafman_json,
    geodetic_to_enu,
    main,
    scenario_to_enu,
    to_bluesky_scn,
    to_utrafman_dict,
    to_utrafman_json,
)


# ── 픽스처 ────────────────────────────────────────────────────────────────
@pytest.fixture
def scenario() -> AdapterScenario:
    return _demo_scenario()


# ── 데이터 모델 검증 ──────────────────────────────────────────────────────
class TestModelValidation:
    def test_waypoint_normalizes_to_float(self):
        wp = Waypoint(34, 126, 50)
        assert isinstance(wp.lat_deg, float)
        assert wp.spd_mps is None

    def test_waypoint_rejects_out_of_range_lat(self):
        with pytest.raises(ValueError, match="lat_deg"):
            Waypoint(91.0, 126.0, 50.0)

    def test_waypoint_rejects_out_of_range_lon(self):
        with pytest.raises(ValueError, match="lon_deg"):
            Waypoint(34.0, 181.0, 50.0)

    def test_waypoint_rejects_negative_speed(self):
        with pytest.raises(ValueError, match="spd_mps"):
            Waypoint(34.0, 126.0, 50.0, spd_mps=-1.0)

    def test_waypoint_rejects_non_finite(self):
        with pytest.raises(ValueError, match="alt_m"):
            Waypoint(34.0, 126.0, math.inf)

    def test_aircraft_rejects_empty_acid(self):
        with pytest.raises(ValueError, match="acid"):
            Aircraft("", "M600", 34.0, 126.0, 50.0, 0.0, 5.0)

    def test_aircraft_rejects_empty_actype(self):
        with pytest.raises(ValueError, match="actype"):
            Aircraft("SD1", "  ", 34.0, 126.0, 50.0, 0.0, 5.0)

    def test_aircraft_heading_wraps_modulo_360(self):
        ac = Aircraft("SD1", "M600", 34.0, 126.0, 50.0, 450.0, 5.0)
        assert ac.hdg_deg == pytest.approx(90.0)

    def test_aircraft_negative_heading_wraps(self):
        ac = Aircraft("SD1", "M600", 34.0, 126.0, 50.0, -90.0, 5.0)
        assert ac.hdg_deg == pytest.approx(270.0)

    def test_aircraft_rejects_negative_speed(self):
        with pytest.raises(ValueError, match="spd_mps"):
            Aircraft("SD1", "M600", 34.0, 126.0, 50.0, 0.0, -5.0)

    def test_scenario_rejects_empty_name(self):
        with pytest.raises(ValueError, match="name"):
            AdapterScenario("", 34.0, 126.0, 0.0, ())

    def test_scenario_rejects_duplicate_acid(self):
        a = Aircraft("DUP", "M600", 34.0, 126.0, 50.0, 0.0, 5.0)
        b = Aircraft("DUP", "M300", 34.1, 126.1, 50.0, 0.0, 5.0)
        with pytest.raises(ValueError, match="중복"):
            AdapterScenario("s", 34.0, 126.0, 0.0, (a, b))

    def test_frozen_dataclass_immutable(self):
        wp = Waypoint(34.0, 126.0, 50.0)
        with pytest.raises(Exception):
            wp.lat_deg = 35.0  # type: ignore[misc]


# ── BlueSky .scn 왕복 ─────────────────────────────────────────────────────
class TestBlueSkyRoundTrip:
    def test_roundtrip_preserves_aircraft_count(self, scenario):
        rt = from_bluesky_scn(to_bluesky_scn(scenario))
        assert len(rt.aircraft) == len(scenario.aircraft)

    def test_roundtrip_preserves_name_and_ref(self, scenario):
        rt = from_bluesky_scn(to_bluesky_scn(scenario))
        assert rt.name == scenario.name
        assert rt.ref_lat_deg == pytest.approx(scenario.ref_lat_deg, abs=1e-7)
        assert rt.ref_lon_deg == pytest.approx(scenario.ref_lon_deg, abs=1e-7)

    def test_roundtrip_preserves_positions(self, scenario):
        rt = from_bluesky_scn(to_bluesky_scn(scenario))
        for a, b in zip(scenario.aircraft, rt.aircraft):
            assert a.acid == b.acid
            assert a.actype == b.actype
            assert b.lat_deg == pytest.approx(a.lat_deg, abs=1e-7)
            assert b.lon_deg == pytest.approx(a.lon_deg, abs=1e-7)
            assert b.alt_m == pytest.approx(a.alt_m, abs=1e-2)
            assert b.hdg_deg == pytest.approx(a.hdg_deg, abs=1e-3)
            assert b.spd_mps == pytest.approx(a.spd_mps, abs=1e-2)

    def test_roundtrip_preserves_waypoints(self, scenario):
        rt = from_bluesky_scn(to_bluesky_scn(scenario))
        for a, b in zip(scenario.aircraft, rt.aircraft):
            assert len(a.waypoints) == len(b.waypoints)
            for wa, wb in zip(a.waypoints, b.waypoints):
                assert wb.lat_deg == pytest.approx(wa.lat_deg, abs=1e-7)
                assert wb.alt_m == pytest.approx(wa.alt_m, abs=1e-2)

    def test_roundtrip_preserves_leg_speed(self, scenario):
        rt = from_bluesky_scn(to_bluesky_scn(scenario))
        # SD001 둘째 경로점은 leg 속도 8.0 m/s.
        wp = rt.aircraft[0].waypoints[1]
        assert wp.spd_mps == pytest.approx(8.0, abs=1e-2)

    def test_output_uses_cre_and_addwpt(self, scenario):
        scn = to_bluesky_scn(scenario)
        assert "CRE SD001,M600," in scn
        assert "ADDWPT SD001," in scn
        assert scn.count(">CRE ") == 2

    def test_output_carries_time_prefix(self, scenario):
        scn = to_bluesky_scn(scenario)
        for line in scn.splitlines():
            if "CRE" in line or "ADDWPT" in line:
                assert line.startswith("00:00:00.00>")

    def test_altitude_converted_to_feet(self, scenario):
        scn = to_bluesky_scn(scenario)
        # 80 m ≈ 262.4672 ft → SD001 의 CRE 줄에 등장.
        cre = next(l for l in scn.splitlines() if l.startswith("00:00:00.00>CRE SD001"))
        assert "262.4672" in cre

    def test_deterministic_output(self, scenario):
        assert to_bluesky_scn(scenario) == to_bluesky_scn(scenario)

    def test_comma_and_space_separators_parse(self):
        scn = (
            "00:00:00.00>CRE SD9 M600 34.0 126.0 90.0 100.0 20.0\n"
            "00:00:00.00>ADDWPT SD9 34.01 126.01 100.0\n"
        )
        sc = from_bluesky_scn(scn)
        assert sc.aircraft[0].acid == "SD9"
        assert len(sc.aircraft[0].waypoints) == 1

    def test_import_ignores_unknown_commands(self):
        scn = (
            "00:00:00.00>CRE SD1,M600,34.0,126.0,90.0,100.0,20.0\n"
            "00:00:00.00>DEST SD1,34.5,126.5\n"
            "00:00:00.00>ASAS ON\n"
        )
        sc = from_bluesky_scn(scn)
        assert len(sc.aircraft) == 1

    def test_import_defaults_when_meta_absent(self):
        scn = "00:00:00.00>CRE SD1,M600,34.0,126.0,90.0,100.0,20.0\n"
        sc = from_bluesky_scn(scn)
        assert sc.name == "imported"
        assert sc.ref_lat_deg == 0.0

    def test_cre_missing_args_raises(self):
        with pytest.raises(ValueError, match="CRE"):
            from_bluesky_scn("00:00:00.00>CRE SD1,M600,34.0\n")

    def test_addwpt_orphan_raises(self):
        with pytest.raises(ValueError, match="ADDWPT"):
            from_bluesky_scn("00:00:00.00>ADDWPT GHOST,34.0,126.0,100.0\n")

    def test_addwpt_missing_altitude_raises_valueerror_not_indexerror(self):
        scn = (
            "00:00:00.00>CRE SD1,M600,34.0,126.0,90.0,100.0,20.0\n"
            "00:00:00.00>ADDWPT SD1,34.01,126.01\n"  # 고도 누락 → 3개 인자
        )
        with pytest.raises(ValueError, match="ADDWPT"):
            from_bluesky_scn(scn)

    def test_duplicate_cre_acid_raises(self):
        scn = (
            "00:00:00.00>CRE DUP,M600,34.0,126.0,90.0,100.0,20.0\n"
            "00:00:00.00>CRE DUP,M300,34.1,126.1,90.0,100.0,20.0\n"
        )
        with pytest.raises(ValueError, match="중복"):
            from_bluesky_scn(scn)

    def test_blank_and_comment_lines_skipped(self):
        scn = (
            "# just a comment\n\n"
            "00:00:00.00>CRE SD1,M600,34.0,126.0,90.0,100.0,20.0\n"
        )
        sc = from_bluesky_scn(scn)
        assert len(sc.aircraft) == 1

    def test_aircraft_order_preserved(self, scenario):
        rt = from_bluesky_scn(to_bluesky_scn(scenario))
        assert [a.acid for a in rt.aircraft] == ["SD001", "SD002"]


# ── U-TRAFMAN JSON 왕복 ───────────────────────────────────────────────────
class TestUTrafmanRoundTrip:
    def test_roundtrip_exact_positions(self, scenario):
        rt = from_utrafman_json(to_utrafman_json(scenario))
        for a, b in zip(scenario.aircraft, rt.aircraft):
            assert b.lat_deg == pytest.approx(a.lat_deg, abs=1e-12)
            assert b.lon_deg == pytest.approx(a.lon_deg, abs=1e-12)
            assert b.alt_m == pytest.approx(a.alt_m, abs=1e-12)
            assert b.spd_mps == pytest.approx(a.spd_mps, abs=1e-12)

    def test_roundtrip_preserves_meta(self, scenario):
        rt = from_utrafman_json(to_utrafman_json(scenario))
        assert rt.name == scenario.name
        assert rt.ref_lat_deg == pytest.approx(scenario.ref_lat_deg)

    def test_roundtrip_preserves_waypoints_and_leg_speed(self, scenario):
        rt = from_utrafman_json(to_utrafman_json(scenario))
        wp = rt.aircraft[0].waypoints[1]
        assert wp.spd_mps == pytest.approx(8.0)
        assert rt.aircraft[1].waypoints[0].spd_mps is None

    def test_format_tag_and_version(self, scenario):
        d = to_utrafman_dict(scenario)
        assert d["format"] == "utrafman-compat"
        assert d["format_version"] == "1.0"
        assert len(d["operations"]) == 2

    def test_json_is_deterministic_sorted(self, scenario):
        assert to_utrafman_json(scenario) == to_utrafman_json(scenario)
        parsed = json.loads(to_utrafman_json(scenario))
        assert list(parsed.keys()) == sorted(parsed.keys())

    def test_rejects_wrong_format_tag(self):
        with pytest.raises(ValueError, match="format"):
            from_utrafman_dict({"format": "other", "operations": []})

    def test_rejects_non_dict(self):
        with pytest.raises(TypeError):
            from_utrafman_dict([1, 2, 3])  # type: ignore[arg-type]

    def test_rejects_non_list_operations(self):
        with pytest.raises(ValueError, match="operations"):
            from_utrafman_dict({"format": "utrafman-compat", "operations": {}})

    def test_missing_op_key_raises_valueerror(self):
        data = {
            "format": "utrafman-compat",
            "operations": [{
                "uav_id": "X", "uav_type": "M600",
                # heading_deg 누락
                "cruise_spd_mps": 5.0,
                "flight_plan": [{"lat": 34.0, "lon": 126.0, "alt_m": 90.0}],
            }],
        }
        with pytest.raises(ValueError, match="heading_deg"):
            from_utrafman_dict(data)

    def test_missing_leg_key_raises_valueerror(self):
        data = {
            "format": "utrafman-compat",
            "operations": [{
                "uav_id": "X", "uav_type": "M600",
                "heading_deg": 0.0, "cruise_spd_mps": 5.0,
                "flight_plan": [{"lat": 34.0, "lon": 126.0}],  # alt_m 누락
            }],
        }
        with pytest.raises(ValueError, match="alt_m"):
            from_utrafman_dict(data)

    def test_rejects_empty_flight_plan(self):
        data = {
            "format": "utrafman-compat",
            "operations": [{
                "uav_id": "X", "uav_type": "M600",
                "heading_deg": 0.0, "cruise_spd_mps": 5.0, "flight_plan": [],
            }],
        }
        with pytest.raises(ValueError, match="flight_plan"):
            from_utrafman_dict(data)

    def test_spawn_leg_becomes_aircraft_state(self):
        data = {
            "format": "utrafman-compat",
            "scenario": "s",
            "reference": {"lat": 0.0, "lon": 0.0, "alt_m": 0.0},
            "operations": [{
                "uav_id": "X", "uav_type": "M600",
                "heading_deg": 45.0, "cruise_spd_mps": 7.0,
                "flight_plan": [{"lat": 34.0, "lon": 126.0, "alt_m": 90.0, "spd_mps": 7.0}],
            }],
        }
        sc = from_utrafman_dict(data)
        assert sc.aircraft[0].alt_m == 90.0
        assert sc.aircraft[0].waypoints == ()


# ── 좌표 변환 (측지 ↔ ENU) ────────────────────────────────────────────────
class TestCoordinateBridge:
    REF = (34.7936, 126.3886, 0.0)

    def test_origin_maps_to_zero_enu(self):
        e, n, u = geodetic_to_enu(*self.REF, *self.REF)
        assert e == pytest.approx(0.0, abs=1e-6)
        assert n == pytest.approx(0.0, abs=1e-6)
        assert u == pytest.approx(0.0, abs=1e-6)

    def test_enu_geodetic_roundtrip(self):
        lat, lon, alt = 34.7970, 126.3950, 120.0
        e, n, u = geodetic_to_enu(lat, lon, alt, *self.REF)
        lat2, lon2, alt2 = enu_to_geodetic(e, n, u, *self.REF)
        assert lat2 == pytest.approx(lat, abs=1e-9)
        assert lon2 == pytest.approx(lon, abs=1e-9)
        assert alt2 == pytest.approx(alt, abs=1e-4)

    def test_east_is_positive_for_increasing_lon(self):
        e, _, _ = geodetic_to_enu(34.7936, 126.3986, 0.0, *self.REF)
        assert e > 0.0

    def test_north_is_positive_for_increasing_lat(self):
        _, n, _ = geodetic_to_enu(34.8036, 126.3886, 0.0, *self.REF)
        assert n > 0.0

    def test_up_tracks_altitude(self):
        _, _, u = geodetic_to_enu(34.7936, 126.3886, 100.0, *self.REF)
        assert u == pytest.approx(100.0, abs=1e-3)

    def test_scenario_to_enu_origin_aircraft_near_zero(self, scenario):
        states = scenario_to_enu(scenario)
        # SD001 은 기준점과 동일 위경도 → east/north ≈ 0.
        sd001 = next(s for s in states if s["acid"] == "SD001")
        assert sd001["east_m"] == pytest.approx(0.0, abs=1e-3)
        assert sd001["north_m"] == pytest.approx(0.0, abs=1e-3)
        assert sd001["up_m"] == pytest.approx(80.0, abs=1e-2)

    def test_one_degree_lat_is_about_111km(self):
        _, n, _ = geodetic_to_enu(35.7936, 126.3886, 0.0, *self.REF)
        assert n == pytest.approx(111_000.0, rel=0.01)

    def test_high_latitude_roundtrip_stable(self):
        # 고극 위도(북극권)에서도 alt 역해가 안정적이어야 함 (sin 분기).
        ref = (89.5, 30.0, 0.0)
        lat, lon, alt = 89.6, 31.0, 250.0
        e, n, u = geodetic_to_enu(lat, lon, alt, *ref)
        lat2, lon2, alt2 = enu_to_geodetic(e, n, u, *ref)
        assert lat2 == pytest.approx(lat, abs=1e-8)
        assert lon2 == pytest.approx(lon, abs=1e-7)
        assert alt2 == pytest.approx(alt, abs=1e-3)

    def test_southern_high_latitude_roundtrip_stable(self):
        ref = (-70.0, -60.0, 0.0)
        lat, lon, alt = -70.2, -59.5, 180.0
        e, n, u = geodetic_to_enu(lat, lon, alt, *ref)
        lat2, lon2, alt2 = enu_to_geodetic(e, n, u, *ref)
        assert lat2 == pytest.approx(lat, abs=1e-8)
        assert alt2 == pytest.approx(alt, abs=1e-3)


# ── 교차 포맷 일관성 ──────────────────────────────────────────────────────
class TestCrossFormatConsistency:
    def test_bluesky_and_utrafman_agree_on_geometry(self, scenario):
        via_bsky = from_bluesky_scn(to_bluesky_scn(scenario))
        via_utm = from_utrafman_json(to_utrafman_json(scenario))
        for a, b in zip(via_bsky.aircraft, via_utm.aircraft):
            assert a.acid == b.acid
            assert a.lat_deg == pytest.approx(b.lat_deg, abs=1e-6)
            assert a.spd_mps == pytest.approx(b.spd_mps, abs=1e-2)

    def test_self_test_passes(self):
        assert _self_test() is True


# ── CLI ───────────────────────────────────────────────────────────────────
class TestCli:
    def test_self_test_cli_returns_zero(self):
        assert main(["--self-test"]) == 0

    def test_demo_both_formats(self, capsys):
        assert main(["--demo"]) == 0
        out = capsys.readouterr().out
        assert "BlueSky" in out and "U-TRAFMAN" in out
        assert "CRE SD001" in out

    def test_demo_bluesky_only(self, capsys):
        assert main(["--demo", "--format", "bluesky"]) == 0
        out = capsys.readouterr().out
        assert "CRE SD001" in out
        assert "U-TRAFMAN" not in out

    def test_demo_utrafman_only(self, capsys):
        assert main(["--demo", "--format", "utrafman"]) == 0
        out = capsys.readouterr().out
        assert "utrafman-compat" in out
        assert "BlueSky .scn" not in out

    def test_no_args_prints_help(self, capsys):
        assert main([]) == 0
        assert "usage" in capsys.readouterr().out.lower()
