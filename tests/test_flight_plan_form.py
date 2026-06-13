"""GENESIS Phase 303 — 비행승인 신청서(Drone One-Stop) 자동 생성 테스트.

항공안전법 시행규칙 §306 별지 제122호서식 기계 작성 필드의 결정성·정합성 검증.
"""

from __future__ import annotations

import json

import pytest

from scripts.generate_flight_plan import (
    PII_PLACEHOLDER,
    FlightPlanForm,
    build_flight_plan,
    build_geobox,
    render_json,
    render_markdown,
)

# ── Arrange: 공통 픽스처 ──────────────────────────────────────────────


@pytest.fixture
def default_config() -> dict:
    return {
        "simulation": {"duration_minutes": 10},
        "airspace": {
            "home": {"lat": 35.1595, "lon": 126.8526},
            "bounds_km": {"x": [-5.0, 5.0], "y": [-5.0, 5.0], "z": [0.0, 0.12]},
        },
        "drones": {"default_count": 100, "max_altitude_m": 120.0},
        "separation_standards": {"lateral_min_m": 50.0, "vertical_min_m": 15.0},
    }


@pytest.fixture
def scenario_config() -> dict:
    return {
        "scenario": "s01_high_density",
        "description": "고밀도 군집 비행",
        "drone_count": 200,
        "simulation_duration_min": 15,
    }


# ── 필드 추출 ────────────────────────────────────────────────────────


def test_builds_form_from_default_config(default_config):
    form = build_flight_plan(default_config, "default")
    assert isinstance(form, FlightPlanForm)
    assert form.aircraft_count == 100
    assert form.flight_duration_min == 10.0
    assert form.max_altitude_m == 120.0


def test_scenario_drone_count_overrides_default(scenario_config):
    form = build_flight_plan(scenario_config, "high_density")
    assert form.aircraft_count == 200
    assert form.flight_duration_min == 15.0
    assert form.generated_for == "s01_high_density"


def test_total_drone_count_key_is_recognized():
    form = build_flight_plan({"total_drone_count": 240}, "multi_city")
    assert form.aircraft_count == 240


def test_duration_from_seconds_is_converted_to_minutes():
    form = build_flight_plan({"simulation_duration_s": 600}, "comms_loss")
    assert form.flight_duration_min == 10.0


def test_max_altitude_falls_back_to_bounds_z():
    config = {"airspace": {"bounds_km": {"z": [0.0, 0.09]}}}
    form = build_flight_plan(config, "z_only")
    assert form.max_altitude_m == 90.0


# ── PII 필드는 placeholder 유지 ──────────────────────────────────────


def test_pii_fields_are_placeholders(default_config):
    form = build_flight_plan(default_config, "default")
    assert form.applicant_name == PII_PLACEHOLDER
    assert form.pilot_license_no == PII_PLACEHOLDER
    assert form.registration_no == PII_PLACEHOLDER
    assert form.insurance_policy_no == PII_PLACEHOLDER


# ── 비행구역 좌표 ────────────────────────────────────────────────────


def test_geobox_center_matches_home(default_config):
    box = build_geobox(default_config)
    assert box.center_lat == 35.1595
    assert box.center_lon == 126.8526


def test_geobox_corners_bracket_center(default_config):
    box = build_geobox(default_config)
    assert box.sw_lat < box.center_lat < box.ne_lat
    assert box.sw_lon < box.center_lon < box.ne_lon
    # 외접원 반경(half-diagonal) = hypot(10,10)/2 ≈ 7.071 km — 과소신고 방지
    assert box.radius_km == pytest.approx(7.071, abs=0.01)


def test_geobox_defaults_when_missing_airspace():
    box = build_geobox({})
    assert box.center_lat == 35.1595
    assert box.radius_km == pytest.approx(7.071, abs=0.01)


# ── 결정성 ───────────────────────────────────────────────────────────


def test_build_is_deterministic(default_config):
    a = build_flight_plan(default_config, "default")
    b = build_flight_plan(default_config, "default")
    assert a == b


def test_json_render_is_deterministic(default_config):
    form = build_flight_plan(default_config, "default")
    assert render_json(form) == render_json(form)


# ── 렌더링 ───────────────────────────────────────────────────────────


def test_markdown_contains_required_sections(default_config):
    md = render_markdown(build_flight_plan(default_config, "default"))
    for section in ["신청인", "비행장치", "비행계획", "비행구역", "조종자", "안전대책", "보험"]:
        assert section in md


def test_markdown_includes_legal_basis(default_config):
    md = render_markdown(build_flight_plan(default_config, "default"))
    assert "시행규칙 §306" in md


def test_json_is_valid_and_has_safety_measures(default_config):
    data = json.loads(render_json(build_flight_plan(default_config, "default")))
    assert data["aircraft_count"] == 100
    assert len(data["safety_measures"]) == 4
    assert any("5계층" in m for m in data["safety_measures"])


def test_json_serializes_nested_geobox(default_config):
    data = json.loads(render_json(build_flight_plan(default_config, "default")))
    assert data["area"]["center_lat"] == 35.1595
    assert data["area"]["radius_km"] == pytest.approx(7.071, abs=0.01)


def test_bvlos_inferred_for_wide_area(default_config):
    # ±5km 운영 구역(>0.5km) → BVLOS(특별승인 필요)로 추론
    form = build_flight_plan(default_config, "default")
    assert form.is_bvlos is True


def test_bvlos_false_for_small_area():
    config = {"airspace": {"bounds_km": {"x": [-0.3, 0.3], "y": [-0.3, 0.3]}}}
    form = build_flight_plan(config, "small")
    assert form.is_bvlos is False


def test_explicit_bvlos_config_overrides_inference():
    config = {"bvlos": False, "airspace": {"bounds_km": {"x": [-5.0, 5.0], "y": [-5.0, 5.0]}}}
    form = build_flight_plan(config, "explicit")
    assert form.is_bvlos is False


def test_config_path_outside_root_is_rejected():
    import argparse

    from scripts.generate_flight_plan import _resolve_input

    args = argparse.Namespace(scenario=None, config="../../../etc/passwd")
    with pytest.raises(ValueError, match="프로젝트 루트"):
        _resolve_input(args)


def test_scenario_name_with_separators_is_sanitized():
    import argparse

    from scripts.generate_flight_plan import _resolve_input

    args = argparse.Namespace(scenario="../evil", config=None)
    # 경로 이탈 시 ValueError, 아니면 sanitize된 이름 반환 — 어느 쪽이든 분리자 미포함
    try:
        _path, name = _resolve_input(args)
    except ValueError:
        return
    assert "/" not in name and ".." not in name
