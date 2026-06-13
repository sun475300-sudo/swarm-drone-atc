"""Phase 303 — 드론 원스톱 비행승인 신청서 자동 생성 단위 검증.

항공안전법 시행규칙 별지 제122호서식(무인비행장치 비행승인신청서) 매핑.
"""
from __future__ import annotations

import pytest

from src.certification.flight_plan_declaration import (
    Aircraft,
    Applicant,
    FlightPlan,
    FlightPlanRequest,
    OperationProfile,
    assess_approval_requirement,
    generate_declaration,
    render_text,
    validate_request,
)

# ─────────────────────────────────────────────────────────────
# Fixtures — 표준 요청 (관제권 밖·주간·가시권·25kg 이하)
# ─────────────────────────────────────────────────────────────


def _base_request(**overrides) -> FlightPlanRequest:
    applicant = Applicant(
        name="홍길동",
        address="전남 무안군 청계면",
        phone="010-1234-5678",
    )
    aircraft = Aircraft(
        model="SDACS-Q20",
        registration="DRN-2026-0001",
        purpose="연구·실증",
        max_takeoff_weight_kg=4.0,
    )
    plan = FlightPlan(
        date="2026-07-01",
        start_time="10:00",
        end_time="12:00",
        area_name="무안 실증 회랑",
        center_lat=34.94,
        center_lon=126.43,
        radius_m=500.0,
        max_altitude_m_agl=120.0,
    )
    profile = OperationProfile(
        in_controlled_airspace=False,
        in_prohibited_zone=False,
        is_night=False,
        is_bvlos=False,
    )
    fields = dict(applicant=applicant, aircraft=aircraft, plan=plan, profile=profile)
    fields.update(overrides)
    return FlightPlanRequest(**fields)


# ─── 승인 필요 판정 ──────────────────────────────────────────


def test_baseline_flight_needs_no_approval() -> None:
    """관제권 밖·150m 이하·25kg 이하·주간·가시권 → 승인 불요."""
    req = _base_request()
    result = assess_approval_requirement(req)
    assert result.approval_required is False
    assert result.special_approval_required is False
    assert result.reasons == []


def test_controlled_airspace_requires_approval() -> None:
    req = _base_request(
        profile=OperationProfile(
            in_controlled_airspace=True,
            in_prohibited_zone=False,
            is_night=False,
            is_bvlos=False,
        )
    )
    result = assess_approval_requirement(req)
    assert result.approval_required is True
    assert any("관제권" in r for r in result.reasons)


def test_altitude_over_150m_requires_approval() -> None:
    req = _base_request(
        plan=FlightPlan(
            date="2026-07-01",
            start_time="10:00",
            end_time="12:00",
            area_name="고고도 실증",
            center_lat=34.94,
            center_lon=126.43,
            radius_m=500.0,
            max_altitude_m_agl=160.0,
        )
    )
    result = assess_approval_requirement(req)
    assert result.approval_required is True
    assert any("150" in r for r in result.reasons)


def test_weight_over_25kg_requires_approval() -> None:
    req = _base_request(
        aircraft=Aircraft(
            model="SDACS-Heavy",
            registration="DRN-2026-0009",
            purpose="방제",
            max_takeoff_weight_kg=30.0,
        )
    )
    result = assess_approval_requirement(req)
    assert result.approval_required is True
    assert any("25" in r for r in result.reasons)


def test_night_flight_requires_special_approval() -> None:
    req = _base_request(
        profile=OperationProfile(
            in_controlled_airspace=False,
            in_prohibited_zone=False,
            is_night=True,
            is_bvlos=False,
        )
    )
    result = assess_approval_requirement(req)
    assert result.special_approval_required is True
    assert any("야간" in r for r in result.reasons)


def test_bvlos_requires_special_approval() -> None:
    req = _base_request(
        profile=OperationProfile(
            in_controlled_airspace=False,
            in_prohibited_zone=False,
            is_night=False,
            is_bvlos=True,
        )
    )
    result = assess_approval_requirement(req)
    assert result.special_approval_required is True
    assert any("비가시권" in r for r in result.reasons)


# ─── 입력 검증 ───────────────────────────────────────────────


def test_validate_passes_for_complete_request() -> None:
    assert validate_request(_base_request()) == []


def test_validate_flags_missing_applicant_name() -> None:
    req = _base_request(
        applicant=Applicant(name="", address="주소", phone="010-0000-0000")
    )
    errors = validate_request(req)
    assert any("신청인" in e for e in errors)


def test_validate_flags_negative_radius() -> None:
    req = _base_request(
        plan=FlightPlan(
            date="2026-07-01",
            start_time="10:00",
            end_time="12:00",
            area_name="x",
            center_lat=34.0,
            center_lon=126.0,
            radius_m=-1.0,
            max_altitude_m_agl=100.0,
        )
    )
    errors = validate_request(req)
    assert any("반경" in e for e in errors)


def test_validate_flags_end_before_start() -> None:
    req = _base_request(
        plan=FlightPlan(
            date="2026-07-01",
            start_time="12:00",
            end_time="10:00",
            area_name="x",
            center_lat=34.0,
            center_lon=126.0,
            radius_m=100.0,
            max_altitude_m_agl=100.0,
        )
    )
    errors = validate_request(req)
    assert any("시간" in e for e in errors)


# ─── 신청서 생성 ─────────────────────────────────────────────


def test_generate_declaration_has_official_sections() -> None:
    form = generate_declaration(_base_request())
    assert form["form_id"] == "별지 제122호서식"
    for section in ("신청인", "비행장치", "비행계획", "승인판정"):
        assert section in form


def test_generate_declaration_embeds_assessment() -> None:
    req = _base_request(
        profile=OperationProfile(
            in_controlled_airspace=True,
            in_prohibited_zone=False,
            is_night=False,
            is_bvlos=False,
        )
    )
    form = generate_declaration(req)
    assert form["승인판정"]["approval_required"] is True


def test_generate_declaration_raises_on_invalid_request() -> None:
    bad = _base_request(
        applicant=Applicant(name="", address="", phone="")
    )
    with pytest.raises(ValueError):
        generate_declaration(bad)


def test_render_text_contains_applicant_and_area() -> None:
    text = render_text(generate_declaration(_base_request()))
    assert "홍길동" in text
    assert "무안 실증 회랑" in text
    assert "별지 제122호서식" in text


def test_render_text_is_deterministic() -> None:
    req = _base_request()
    assert render_text(generate_declaration(req)) == render_text(
        generate_declaration(req)
    )
