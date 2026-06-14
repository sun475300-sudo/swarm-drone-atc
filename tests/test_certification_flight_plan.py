"""GENESIS Phase 303: 비행계획 신고 양식 자동 생성 모듈 테스트."""

from datetime import date

import pytest

from src.certification.flight_plan import (
    Aircraft,
    ApplicationInput,
    FlightPlan,
    Insurance,
    Operator,
    Pilot,
    build_application,
    render_markdown,
    required_approvals,
    validate,
)


def _valid_input(**overrides) -> ApplicationInput:
    """유효한 기본 신청 입력 생성 (개별 필드는 overrides로 교체)."""
    fp_kwargs = dict(
        purpose="농경지 방제",
        area_name="전남 해남 간척지",
        center_lat=34.57,
        center_lon=126.59,
        radius_m=300.0,
        altitude_max_m=80.0,
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 3),
    )
    fp_kwargs.update(overrides.pop("flight_plan", {}))
    ac_kwargs = dict(
        model="SDACS-X1",
        category="멀티콥터",
        purpose="방제",
        weight_kg=12.0,
        max_takeoff_weight_kg=20.0,
        registration_no="A1234",
    )
    ac_kwargs.update(overrides.pop("aircraft", {}))
    return ApplicationInput(
        operator=Operator("홍길동", "SDACS랩", "010-0000-0000", "서울시 관악구"),
        aircraft=Aircraft(**ac_kwargs),
        pilot=Pilot("김조종", "DR-2024-001", "010-1111-2222"),
        flight_plan=FlightPlan(**fp_kwargs),
        insurance=Insurance(insured=True, provider="삼성화재", policy_no="P-1"),
    )


# ── required_approvals ──────────────────────────────────────────────────
class TestRequiredApprovals:
    def test_no_approval_for_light_low_uncontrolled(self):
        data = _valid_input()
        assert required_approvals(data.flight_plan, data.aircraft) == []

    def test_flight_approval_when_over_weight(self):
        data = _valid_input(aircraft={"max_takeoff_weight_kg": 30.0})
        assert "비행승인" in required_approvals(data.flight_plan, data.aircraft)

    def test_flight_approval_when_high_altitude(self):
        data = _valid_input(flight_plan={"altitude_max_m": 150.0})
        assert "비행승인" in required_approvals(data.flight_plan, data.aircraft)

    def test_flight_approval_in_controlled_airspace(self):
        data = _valid_input(flight_plan={"in_controlled_airspace": True})
        assert "비행승인" in required_approvals(data.flight_plan, data.aircraft)

    def test_special_approval_for_night(self):
        data = _valid_input(flight_plan={"is_night": True})
        assert "특별비행승인" in required_approvals(data.flight_plan, data.aircraft)

    def test_special_approval_for_bvlos(self):
        data = _valid_input(flight_plan={"is_bvlos": True})
        assert "특별비행승인" in required_approvals(data.flight_plan, data.aircraft)


# ── validate ────────────────────────────────────────────────────────────
class TestValidate:
    def test_valid_input_has_no_errors(self):
        assert validate(_valid_input()) == []

    def test_missing_operator_name(self):
        data = _valid_input()
        data = ApplicationInput(
            operator=Operator("", data.operator.organization, data.operator.phone, data.operator.address),
            aircraft=data.aircraft, pilot=data.pilot,
            flight_plan=data.flight_plan, insurance=data.insurance,
        )
        errors = validate(data)
        assert any("신청인 성명" in e for e in errors)

    def test_zero_weight_rejected(self):
        data = _valid_input(aircraft={"weight_kg": 0.0})
        assert any("자체중량" in e for e in validate(data))

    def test_max_takeoff_below_empty_weight_rejected(self):
        data = _valid_input(aircraft={"weight_kg": 20.0, "max_takeoff_weight_kg": 10.0})
        assert any("최대이륙중량" in e for e in validate(data))

    def test_out_of_range_latitude_rejected(self):
        data = _valid_input(flight_plan={"center_lat": 100.0})
        assert any("위도" in e for e in validate(data))

    def test_end_before_start_rejected(self):
        data = _valid_input(
            flight_plan={"start_date": date(2026, 7, 5), "end_date": date(2026, 7, 1)}
        )
        assert any("종료일" in e for e in validate(data))

    def test_insured_without_provider_rejected(self):
        data = _valid_input()
        data = ApplicationInput(
            operator=data.operator, aircraft=data.aircraft, pilot=data.pilot,
            flight_plan=data.flight_plan, insurance=Insurance(insured=True, provider=""),
        )
        assert any("보험사" in e for e in validate(data))


# ── build_application ───────────────────────────────────────────────────
class TestBuildApplication:
    def test_build_returns_all_sections(self):
        app = build_application(_valid_input())
        for key in ("신청인", "비행장치", "조종자", "비행계획", "보험", "필요승인"):
            assert key in app

    def test_build_raises_on_invalid_input(self):
        data = _valid_input(aircraft={"weight_kg": -1.0})
        with pytest.raises(ValueError):
            build_application(data)

    def test_night_bvlos_high_altitude_lists_both_approvals(self):
        data = _valid_input(
            flight_plan={"is_night": True, "altitude_max_m": 200.0}
        )
        app = build_application(data)
        assert "비행승인" in app["필요승인"]
        assert "특별비행승인" in app["필요승인"]


# ── render_markdown ─────────────────────────────────────────────────────
class TestRenderMarkdown:
    def test_markdown_contains_header_and_fields(self):
        md = render_markdown(build_application(_valid_input()))
        assert md.startswith("# 드론 원스톱 비행승인 신청서")
        assert "홍길동" in md
        assert "SDACS-X1" in md
        assert "전남 해남 간척지" in md

    def test_markdown_is_deterministic(self):
        data = _valid_input()
        assert render_markdown(build_application(data)) == render_markdown(build_application(data))
