"""GENESIS Phase 303 — 비행계획 신고/승인 신청서 자동 생성 테스트.

근거: 항공안전법 §127(비행승인) + 시행규칙 §306(비행계획 제출, Drone One-Stop).
"""
from __future__ import annotations

import pytest

from src.certification.flight_plan_submission import (
    Aircraft,
    Applicant,
    ApprovalRequirement,
    FlightMethod,
    FlightPlan,
    Pilot,
    build_flight_plan_submission,
)


def _valid_inputs():
    applicant = Applicant(
        name="홍길동",
        organization="SDACS 드론팀",
        address="서울특별시 강남구 테헤란로 1",
        phone="010-1234-5678",
    )
    aircraft = Aircraft(
        registration_number="K-2026-0001",
        model="SDACS-Q4",
        weight_kg=4.2,
        purpose="연구·실증",
    )
    plan = FlightPlan(
        start="2026-07-01T09:00",
        end="2026-07-01T11:00",
        center_lat=37.5665,
        center_lon=126.9780,
        radius_m=300.0,
        altitude_max_m=120.0,
        method=FlightMethod.VISUAL_DAY,
        purpose="군집 비행 실증",
    )
    pilot = Pilot(name="홍길동", license_grade=2, experience_hours=150.0)
    return applicant, aircraft, plan, pilot


# ── 정상 생성 ──────────────────────────────────────────────

def test_build_returns_form_with_all_sections():
    applicant, aircraft, plan, pilot = _valid_inputs()

    sub = build_flight_plan_submission(applicant, aircraft, plan, pilot)
    form = sub.to_dict()

    assert "신청인" in form
    assert "비행장치" in form
    assert "비행계획" in form
    assert "조종자" in form
    assert form["신청인"]["성명"] == "홍길동"
    assert form["비행장치"]["신고번호"] == "K-2026-0001"


def test_to_text_includes_korean_labels():
    applicant, aircraft, plan, pilot = _valid_inputs()

    text = build_flight_plan_submission(applicant, aircraft, plan, pilot).to_text()

    assert "비행계획 승인 신청서" in text
    assert "K-2026-0001" in text
    assert "홍길동" in text


# ── 승인 요건 판정 ─────────────────────────────────────────

def test_altitude_over_150m_requires_approval():
    applicant, aircraft, plan, pilot = _valid_inputs()
    plan = FlightPlan(
        start=plan.start, end=plan.end, center_lat=plan.center_lat,
        center_lon=plan.center_lon, radius_m=plan.radius_m,
        altitude_max_m=160.0, method=plan.method, purpose=plan.purpose,
    )

    sub = build_flight_plan_submission(applicant, aircraft, plan, pilot)

    assert ApprovalRequirement.ALTITUDE_OVER_150M in sub.requirements


def test_bvlos_and_night_require_special_approval():
    applicant, aircraft, plan, pilot = _valid_inputs()
    plan = FlightPlan(
        start=plan.start, end=plan.end, center_lat=plan.center_lat,
        center_lon=plan.center_lon, radius_m=plan.radius_m,
        altitude_max_m=100.0, method=FlightMethod.BVLOS_NIGHT, purpose=plan.purpose,
    )

    sub = build_flight_plan_submission(applicant, aircraft, plan, pilot)

    assert ApprovalRequirement.SPECIAL_FLIGHT_APPROVAL in sub.requirements


def test_heavy_aircraft_requires_safety_certification():
    applicant, _aircraft, plan, pilot = _valid_inputs()
    heavy = Aircraft(
        registration_number="K-2026-0002",
        model="SDACS-Heavy",
        weight_kg=30.0,
        purpose="화물 배송",
    )

    sub = build_flight_plan_submission(applicant, heavy, plan, pilot)

    assert ApprovalRequirement.SAFETY_CERTIFICATION in sub.requirements


def test_light_visual_day_flight_under_150m_has_no_special_requirement():
    applicant, aircraft, plan, pilot = _valid_inputs()

    sub = build_flight_plan_submission(applicant, aircraft, plan, pilot)

    assert ApprovalRequirement.SPECIAL_FLIGHT_APPROVAL not in sub.requirements
    assert ApprovalRequirement.ALTITUDE_OVER_150M not in sub.requirements


def test_altitude_exactly_150m_has_no_requirement():
    # 150m "초과"가 기준 — 정확히 150m는 승인 불요.
    applicant, aircraft, _plan, pilot = _valid_inputs()
    plan = FlightPlan(
        start="2026-07-01T09:00", end="2026-07-01T11:00",
        center_lat=37.5, center_lon=127.0, radius_m=100.0,
        altitude_max_m=150.0, method=FlightMethod.VISUAL_DAY, purpose="t",
    )

    sub = build_flight_plan_submission(applicant, aircraft, plan, pilot)

    assert ApprovalRequirement.ALTITUDE_OVER_150M not in sub.requirements


def test_weight_exactly_25kg_has_no_safety_certification():
    # 25kg "초과"가 기준 — 정확히 25kg는 안전성 인증 불요.
    applicant, _aircraft, plan, pilot = _valid_inputs()
    boundary = Aircraft("K-1", "X", 25.0, "t")

    sub = build_flight_plan_submission(applicant, boundary, plan, pilot)

    assert ApprovalRequirement.SAFETY_CERTIFICATION not in sub.requirements


def test_end_before_start_rejected():
    with pytest.raises(ValueError):
        FlightPlan(
            start="2026-07-01T11:00", end="2026-07-01T09:00",
            center_lat=37.5, center_lon=127.0, radius_m=100.0,
            altitude_max_m=100.0, method=FlightMethod.VISUAL_DAY, purpose="t",
        )


# ── 입력 검증 ─────────────────────────────────────────────

def test_negative_weight_rejected():
    with pytest.raises(ValueError):
        Aircraft(registration_number="K-1", model="X", weight_kg=-1.0, purpose="t")


def test_invalid_license_grade_rejected():
    with pytest.raises(ValueError):
        Pilot(name="x", license_grade=5, experience_hours=10.0)


def test_negative_radius_rejected():
    with pytest.raises(ValueError):
        FlightPlan(
            start="2026-07-01T09:00", end="2026-07-01T11:00",
            center_lat=37.5, center_lon=127.0, radius_m=-10.0,
            altitude_max_m=100.0, method=FlightMethod.VISUAL_DAY, purpose="t",
        )


def test_latitude_out_of_range_rejected():
    with pytest.raises(ValueError):
        FlightPlan(
            start="2026-07-01T09:00", end="2026-07-01T11:00",
            center_lat=200.0, center_lon=127.0, radius_m=100.0,
            altitude_max_m=100.0, method=FlightMethod.VISUAL_DAY, purpose="t",
        )


def test_to_dict_is_json_serializable():
    import json

    applicant, aircraft, plan, pilot = _valid_inputs()
    sub = build_flight_plan_submission(applicant, aircraft, plan, pilot)

    dumped = json.dumps(sub.to_dict(), ensure_ascii=False)

    assert "K-2026-0001" in dumped
