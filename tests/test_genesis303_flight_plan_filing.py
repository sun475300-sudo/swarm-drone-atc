"""GENESIS Phase 303 — 비행계획 신고 양식(Drone One-Stop) 테스트."""
from __future__ import annotations

import json

import pytest

from src.compliance.flight_plan_filing import (
    MAX_UNCONTROLLED_ALTITUDE_M_AGL,
    Aircraft,
    FilingForm,
    FlightPlan,
    Operator,
    build_filing,
    required_forms,
    requires_flight_approval,
    requires_special_approval,
)


# ── Arrange 헬퍼 ─────────────────────────────────────────────
def _operator() -> Operator:
    return Operator(name="홍길동", contact="010-0000-0000", address="서울시 강남구")


def _aircraft() -> Aircraft:
    return Aircraft(
        model="SDACS-X1",
        registration="ABC-1234",
        empty_weight_kg=3.0,
        max_takeoff_weight_kg=7.0,
    )


def _plan(**overrides) -> FlightPlan:
    base = dict(
        purpose="군집 비행 실증",
        area_name="목포 해상 시험구역",
        start_ts=1_000.0,
        end_ts=4_600.0,
        max_altitude_m_agl=100.0,
    )
    return FlightPlan(**{**base, **overrides})


# ── 비행승인 판정 (§127 ①) ──────────────────────────────────
class TestFlightApproval:
    def test_class_g_low_altitude_needs_no_approval(self):
        assert requires_flight_approval(_plan(max_altitude_m_agl=120.0)) is False

    def test_exactly_150m_needs_no_approval(self):
        # 경계값: 150m 이하는 비통제(Class G).
        assert requires_flight_approval(
            _plan(max_altitude_m_agl=MAX_UNCONTROLLED_ALTITUDE_M_AGL)
        ) is False

    def test_above_150m_needs_approval(self):
        assert requires_flight_approval(_plan(max_altitude_m_agl=151.0)) is True

    def test_controlled_airspace_needs_approval(self):
        assert requires_flight_approval(_plan(controlled_airspace=True)) is True

    def test_restricted_area_needs_approval(self):
        assert requires_flight_approval(_plan(restricted_area=True)) is True


# ── 특별비행승인 판정 (§129 ②) ──────────────────────────────
class TestSpecialApproval:
    def test_daytime_vlos_no_special_approval(self):
        assert requires_special_approval(_plan()) is False

    def test_night_needs_special_approval(self):
        assert requires_special_approval(_plan(night=True)) is True

    def test_bvlos_needs_special_approval(self):
        assert requires_special_approval(_plan(bvlos=True)) is True


# ── 필요 양식 목록 ───────────────────────────────────────────
class TestRequiredForms:
    def test_simple_flight_needs_no_forms(self):
        assert required_forms(_plan()) == []

    def test_all_conditions_produce_three_forms_in_order(self):
        forms = required_forms(
            _plan(controlled_airspace=True, bvlos=True, aerial_photography=True)
        )
        assert forms == [
            FilingForm.FLIGHT_APPROVAL,
            FilingForm.SPECIAL_APPROVAL,
            FilingForm.AERIAL_PHOTOGRAPHY,
        ]

    def test_aerial_photography_only(self):
        assert required_forms(_plan(aerial_photography=True)) == [
            FilingForm.AERIAL_PHOTOGRAPHY
        ]


# ── 양식 생성 + export ───────────────────────────────────────
class TestBuildFiling:
    def test_build_returns_serializable_dict(self):
        filing = build_filing(_operator(), _aircraft(), _plan(night=True))
        d = filing.to_dict()
        assert d["신청양식"] == [FilingForm.SPECIAL_APPROVAL.value]
        assert d["신청인"]["성명"] == "홍길동"
        assert d["비행계획"]["최대고도_m_AGL"] == 100.0
        # 시각은 사람이 읽을 수 있는 ISO-8601 문자열이어야 함 (epoch float 아님).
        assert d["비행계획"]["시작시각"] == "1970-01-01T00:16:40+00:00"
        assert isinstance(d["비행계획"]["종료시각"], str)
        # JSON 직렬화 가능해야 함 (한글 포함).
        json.dumps(d, ensure_ascii=False)

    def test_forms_populated_on_filing(self):
        filing = build_filing(
            _operator(), _aircraft(), _plan(max_altitude_m_agl=200.0)
        )
        assert FilingForm.FLIGHT_APPROVAL in filing.forms


# ── 입력 검증 ────────────────────────────────────────────────
class TestValidation:
    def test_empty_operator_name_raises(self):
        with pytest.raises(ValueError, match="성명"):
            build_filing(
                Operator(name="  ", contact="010", address="서울"),
                _aircraft(),
                _plan(),
            )

    def test_empty_operator_address_raises(self):
        with pytest.raises(ValueError, match="주소"):
            build_filing(
                Operator(name="홍길동", contact="010", address="   "),
                _aircraft(),
                _plan(),
            )

    def test_empty_registration_raises(self):
        bad = Aircraft(
            model="X", registration="  ", empty_weight_kg=1.0, max_takeoff_weight_kg=2.0
        )
        with pytest.raises(ValueError, match="신고번호"):
            build_filing(_operator(), bad, _plan())

    def test_non_positive_empty_weight_raises(self):
        bad = Aircraft(
            model="X", registration="R", empty_weight_kg=0.0, max_takeoff_weight_kg=1.0
        )
        with pytest.raises(ValueError, match="자체중량"):
            build_filing(_operator(), bad, _plan())

    def test_mtow_below_empty_weight_raises(self):
        bad = Aircraft(
            model="X", registration="R", empty_weight_kg=5.0, max_takeoff_weight_kg=3.0
        )
        with pytest.raises(ValueError, match="최대이륙중량"):
            build_filing(_operator(), bad, _plan())

    def test_negative_altitude_raises(self):
        with pytest.raises(ValueError, match="고도"):
            build_filing(_operator(), _aircraft(), _plan(max_altitude_m_agl=-1.0))

    def test_end_before_start_raises(self):
        with pytest.raises(ValueError, match="종료시각"):
            build_filing(
                _operator(), _aircraft(), _plan(start_ts=5_000.0, end_ts=1_000.0)
            )

    def test_zero_duration_raises(self):
        # 경계값: 시작 == 종료(0초 비행)는 거부.
        with pytest.raises(ValueError, match="종료시각"):
            build_filing(
                _operator(), _aircraft(), _plan(start_ts=1_000.0, end_ts=1_000.0)
            )

    def test_equal_weight_accepted(self):
        # 경계값: 최대이륙중량 == 자체중량 (탑재 0kg)은 허용.
        ac = Aircraft(
            model="X", registration="R", empty_weight_kg=2.0, max_takeoff_weight_kg=2.0
        )
        filing = build_filing(_operator(), ac, _plan())
        assert filing.aircraft.max_takeoff_weight_kg == 2.0
