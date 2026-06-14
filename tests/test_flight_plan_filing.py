"""Phase 303 (GENESIS): 비행계획 신고 양식 자동 생성 테스트.

Drone One-Stop 비행승인 신청서 생성·판정·검증·export 의 결정성을 검증한다.
"""

import json
from datetime import datetime

import pytest

from simulation.flight_plan_filing import (
    CONTROL_ZONE_RADIUS_M,
    ControlZone,
    FlightPlan,
    FlightPlanAircraft,
    FlightPlanApplicant,
    assess_filing,
    build_filing,
    export_json,
    export_text,
)


def _applicant(is_business: bool = False) -> FlightPlanApplicant:
    return FlightPlanApplicant(
        name="홍길동",
        phone="010-1234-5678",
        address="서울특별시 강남구",
        is_business=is_business,
        business_reg_no="123-45-67890" if is_business else "",
    )


def _aircraft(empty_weight_kg: float = 2.5, reg: str = "") -> FlightPlanAircraft:
    return FlightPlanAircraft(
        model="SDACS-Quad-X",
        registration_no=reg,
        empty_weight_kg=empty_weight_kg,
        mtow_kg=max(empty_weight_kg + 1.0, 4.0),
        purpose="교육/연구",
    )


def _plan(**kwargs) -> FlightPlan:
    base = dict(
        area_name="한강 시민공원",
        center_lat=37.5,
        center_lon=127.0,
        radius_m=300.0,
        max_altitude_agl_m=120.0,
        start=datetime(2026, 7, 1, 9, 0),
        end=datetime(2026, 7, 1, 11, 0),
    )
    base.update(kwargs)
    return FlightPlan(**base)


# ── 판정 로직 ─────────────────────────────────────────────


def test_low_altitude_visual_flight_needs_no_approval():
    # Arrange / Act
    decision = assess_filing(_plan(), _aircraft(), _applicant(), control_zones=[])

    # Assert
    assert decision.needs_approval is False
    assert decision.needs_special_approval is False


def test_altitude_above_150m_requires_approval():
    decision = assess_filing(
        _plan(max_altitude_agl_m=180.0), _aircraft(), _applicant(), control_zones=[]
    )

    assert decision.needs_approval is True
    assert any("150" in r for r in decision.reasons)


def test_flight_inside_control_zone_requires_approval():
    # 비행 중심이 관제권 중심과 동일 → 무조건 진입
    zone = ControlZone(name="김포공항", center_lat=37.5, center_lon=127.0)

    decision = assess_filing(_plan(), _aircraft(), _applicant(), control_zones=[zone])

    assert decision.needs_approval is True
    assert any("관제권" in r for r in decision.reasons)


def test_flight_far_from_control_zone_no_approval():
    # 위도 1도 ≈ 111 km 떨어진 공항 → 관제권 밖
    zone = ControlZone(name="원거리공항", center_lat=38.5, center_lon=127.0)

    decision = assess_filing(_plan(), _aircraft(), _applicant(), control_zones=[zone])

    assert decision.needs_approval is False


def test_prohibited_zone_labeled_in_reason():
    zone = ControlZone(
        name="P-73", center_lat=37.5, center_lon=127.0, radius_m=2000.0,
        is_prohibited=True,
    )

    decision = assess_filing(_plan(), _aircraft(), _applicant(), control_zones=[zone])

    assert decision.needs_approval is True
    assert any("비행금지구역" in r for r in decision.reasons)


def test_bvlos_and_night_require_special_approval():
    decision = assess_filing(
        _plan(is_bvlos=True, is_night=True), _aircraft(), _applicant(), control_zones=[]
    )

    assert decision.needs_special_approval is True
    assert any("BVLOS" in r for r in decision.reasons)
    assert any("야간" in r for r in decision.reasons)


def test_business_operator_always_needs_aircraft_report():
    decision = assess_filing(
        _plan(), _aircraft(empty_weight_kg=1.0), _applicant(is_business=True),
        control_zones=[],
    )

    assert decision.needs_aircraft_report is True


def test_heavy_aircraft_needs_report():
    decision = assess_filing(
        _plan(), _aircraft(empty_weight_kg=15.0), _applicant(), control_zones=[]
    )

    assert decision.needs_aircraft_report is True


def test_exact_12kg_weight_does_not_need_report():
    # 정확히 12 kg은 임계값을 초과(>)하지 않으므로 신고 불요
    decision = assess_filing(
        _plan(), _aircraft(empty_weight_kg=12.0), _applicant(), control_zones=[]
    )

    assert decision.needs_aircraft_report is False


def test_exact_150m_altitude_does_not_need_approval():
    # 정확히 150 m AGL은 초과(>)가 아니므로 비행승인 불요
    decision = assess_filing(
        _plan(max_altitude_agl_m=150.0), _aircraft(), _applicant(), control_zones=[]
    )

    assert decision.needs_approval is False


# ── 양식 생성 / 검증 ──────────────────────────────────────


def test_build_filing_structure_and_determinism():
    args = (_plan(), _aircraft(reg="UAS-2026-0001"), _applicant())

    first = build_filing(*args)
    second = build_filing(*args)

    assert first == second  # 결정성
    assert first["form_type"] == "drone_onestop_flight_approval"
    assert first["flight"]["duration_h"] == 2.0
    assert first["aircraft"]["registration_no"] == "UAS-2026-0001"


def test_missing_registration_shows_placeholder():
    filing = build_filing(_plan(), _aircraft(reg=""), _applicant())

    assert filing["aircraft"]["registration_no"] == "(미신고)"


def test_invalid_end_before_start_raises():
    bad_plan = _plan(
        start=datetime(2026, 7, 1, 11, 0), end=datetime(2026, 7, 1, 9, 0)
    )

    with pytest.raises(ValueError, match="종료 일시"):
        build_filing(bad_plan, _aircraft(), _applicant())


def test_business_without_reg_no_raises():
    applicant = FlightPlanApplicant(
        name="에이전트", phone="010-0000-0000", address="대전",
        is_business=True, business_reg_no="",
    )

    with pytest.raises(ValueError, match="사업자등록번호"):
        build_filing(_plan(), _aircraft(), applicant)


def test_mtow_below_empty_weight_raises():
    aircraft = FlightPlanAircraft(
        model="Bad", registration_no="", empty_weight_kg=5.0, mtow_kg=3.0
    )

    with pytest.raises(ValueError, match="최대이륙중량"):
        build_filing(_plan(), aircraft, _applicant())


# ── export ────────────────────────────────────────────────


def test_export_json_roundtrip():
    filing = build_filing(_plan(), _aircraft(reg="UAS-1"), _applicant())

    text = export_json(filing)
    parsed = json.loads(text)

    assert parsed == filing


def test_export_text_contains_key_fields():
    filing = build_filing(
        _plan(max_altitude_agl_m=200.0), _aircraft(reg="UAS-1"), _applicant()
    )

    text = export_text(filing)

    assert "드론 원스톱 비행승인 신청서" in text
    assert "홍길동" in text
    assert "비행승인:     필요" in text


def test_control_zone_default_radius():
    zone = ControlZone(name="기본", center_lat=0.0, center_lon=0.0)
    assert zone.radius_m == CONTROL_ZONE_RADIUS_M
