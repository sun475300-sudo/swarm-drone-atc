"""GENESIS Phase 308 — 드론 배상책임보험 요율 산정 API 검증.

Phase 67 mock(toy 공식)을 격상한 표준 요율표 기반 견적 엔진이 결정적이고
단조적으로 동작하는지, 무사고 할인·사고 할증·경력 할인·위험 가산·의무가입
한도 검증이 실 보험사 스펙대로 적용되는지 검증한다.
"""
from __future__ import annotations

import pytest

from simulation.insurance_rate_quote import (
    MANDATORY_MIN_LIMIT_KRW,
    QuoteRequest,
    quote,
)

# 마지막 명세 running 과 최종 보험료의 허용 오차(원) — 반올림 단위.
_ROUND_GUARD = 100


def _req(**kw) -> QuoteRequest:
    """기준 요청 — 테스트별로 일부 필드만 덮어쓴다."""
    base = dict(
        mtow_kg=5.0,
        operation_type="survey",
        annual_flight_hours=100.0,
        pilot_experience_years=2.0,
        claims_in_3yr=0,
        coverage_limit_krw=200_000_000,
    )
    base.update(kw)
    return QuoteRequest(**base)


class TestDeterminism:
    """동일 입력은 동일 견적을 낸다."""

    def test_same_request_yields_identical_quote(self):
        # Arrange
        req = _req()
        # Act
        q1, q2 = quote(req), quote(req)
        # Assert
        assert q1 == q2
        assert q1.annual_premium_krw == q2.annual_premium_krw


class TestRounding:
    """최종 보험료는 100원 단위로 반올림된다."""

    def test_premium_rounded_to_100_won(self):
        q = quote(_req(annual_flight_hours=137.0, pilot_experience_years=3.0))
        assert q.annual_premium_krw % 100 == 0


class TestMtowMonotonic:
    """중량 등급이 무거울수록 기본료가 높다."""

    @pytest.mark.parametrize(
        "mtow, expected_base",
        [(1.5, 80_000), (5.0, 150_000), (20.0, 300_000), (100.0, 700_000), (200.0, 1_500_000)],
    )
    def test_base_premium_by_mtow_tier(self, mtow, expected_base):
        assert quote(_req(mtow_kg=mtow)).base_premium_krw == expected_base

    def test_heavier_drone_costs_more(self):
        light = quote(_req(mtow_kg=1.5)).annual_premium_krw
        heavy = quote(_req(mtow_kg=100.0)).annual_premium_krw
        assert heavy > light


class TestClaimsHistory:
    """무사고는 할인, 사고는 건당 할증."""

    def test_no_claims_cheaper_than_one_claim(self):
        clean = quote(_req(claims_in_3yr=0)).annual_premium_krw
        one = quote(_req(claims_in_3yr=1)).annual_premium_krw
        assert clean < one

    def test_more_claims_more_expensive(self):
        one = quote(_req(claims_in_3yr=1)).annual_premium_krw
        three = quote(_req(claims_in_3yr=3)).annual_premium_krw
        assert three > one


class TestExperienceDiscount:
    """경력이 길수록 저렴하며, 할인은 15%에서 포화한다."""

    def test_experienced_pilot_cheaper(self):
        novice = quote(_req(pilot_experience_years=0.0)).annual_premium_krw
        veteran = quote(_req(pilot_experience_years=5.0)).annual_premium_krw
        assert veteran < novice

    def test_discount_caps_at_15_percent(self):
        five = quote(_req(pilot_experience_years=5.0)).annual_premium_krw
        twenty = quote(_req(pilot_experience_years=20.0)).annual_premium_krw
        assert five == twenty


class TestRiskLoadings:
    """야간·비가시 운용은 가산된다."""

    def test_night_ops_adds_loading(self):
        day = quote(_req()).annual_premium_krw
        night = quote(_req(night_ops=True)).annual_premium_krw
        assert night > day

    def test_bvlos_costs_more_than_night(self):
        night = quote(_req(night_ops=True)).annual_premium_krw
        bvlos = quote(_req(bvlos_ops=True)).annual_premium_krw
        assert bvlos > night

    def test_night_and_bvlos_stack_multiplicatively(self):
        plain = quote(_req()).annual_premium_krw
        both = quote(_req(night_ops=True, bvlos_ops=True)).annual_premium_krw
        # 두 가산은 곱(1.15×1.30≈1.495)으로 누적 — 더 높은 쪽만 적용되지 않는다.
        assert both == pytest.approx(plain * 1.15 * 1.30, rel=0.01)


class TestCoverageLimit:
    """보상한도가 높을수록 ILF로 보험료가 오른다."""

    def test_higher_limit_costs_more(self):
        low = quote(_req(coverage_limit_krw=150_000_000)).annual_premium_krw
        high = quote(_req(coverage_limit_krw=1_000_000_000)).annual_premium_krw
        assert high > low

    def test_non_standard_limit_rejected(self):
        with pytest.raises(ValueError, match="standard tier"):
            quote(_req(coverage_limit_krw=123_456_789))


class TestMandatory:
    """사용사업은 의무가입·최소한도, 취미비행은 비대상."""

    def test_commercial_is_mandatory(self):
        assert quote(_req(operation_type="delivery")).is_mandatory is True

    def test_recreational_not_mandatory(self):
        assert quote(_req(operation_type="recreational")).is_mandatory is False

    def test_mandatory_op_below_min_limit_rejected(self):
        with pytest.raises(ValueError, match="mandatory"):
            quote(_req(operation_type="delivery", coverage_limit_krw=50_000_000))

    def test_recreational_allows_low_limit(self):
        q = quote(_req(operation_type="recreational", coverage_limit_krw=50_000_000))
        assert q.annual_premium_krw > 0
        assert MANDATORY_MIN_LIMIT_KRW == 150_000_000


class TestBreakdown:
    """명세는 base로 시작하고 마지막 running이 견적과 정합한다."""

    def test_lines_start_with_base(self):
        q = quote(_req())
        assert q.lines[0].label == "base_premium"
        assert q.lines[0].running_krw == q.base_premium_krw

    def test_last_line_matches_premium_within_rounding(self):
        q = quote(_req(night_ops=True, bvlos_ops=True))
        assert abs(q.lines[-1].running_krw - q.annual_premium_krw) < _ROUND_GUARD


class TestValidation:
    """경계값 입력은 명확히 거부된다."""

    @pytest.mark.parametrize("field, value", [
        ("mtow_kg", 0.0),
        ("mtow_kg", -1.0),
        ("annual_flight_hours", -1.0),
        ("pilot_experience_years", -0.5),
        ("claims_in_3yr", -1),
    ])
    def test_invalid_numeric_rejected(self, field, value):
        with pytest.raises(ValueError):
            quote(_req(**{field: value}))

    def test_unknown_operation_rejected(self):
        with pytest.raises(ValueError, match="unknown operation_type"):
            quote(_req(operation_type="mining"))

    def test_physically_impossible_flight_hours_rejected(self):
        with pytest.raises(ValueError, match="cannot exceed"):
            quote(_req(annual_flight_hours=9_000.0))

    def test_max_flight_hours_boundary_accepted(self):
        # 정확히 1년치(8,760h)는 허용 — 경계값 통과.
        assert quote(_req(annual_flight_hours=8_760.0)).annual_premium_krw > 0

    def test_fractional_claims_rejected(self):
        with pytest.raises(TypeError, match="claims_in_3yr must be an int"):
            quote(_req(claims_in_3yr=0.5))

    def test_bool_claims_rejected(self):
        with pytest.raises(TypeError, match="claims_in_3yr must be an int"):
            quote(_req(claims_in_3yr=True))
