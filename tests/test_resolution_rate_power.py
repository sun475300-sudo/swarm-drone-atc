"""Phase 446 — 충돌 해결률 통계적 검정력 분석 테스트."""
from __future__ import annotations

import math

import pytest

from simulation.resolution_rate_power import (
    norm_cdf,
    norm_ppf,
    power_report,
    power_two_proportion,
    required_sample_size,
    resolution_rate,
    two_proportion_ztest,
    wilson_interval,
)


class TestResolutionRate:
    def test_no_events_is_fully_safe(self):
        assert resolution_rate(0, 0) == 1.0

    def test_all_resolved(self):
        assert resolution_rate(100, 0) == 1.0

    def test_known_formula(self):
        # 1 - 5/(95+5) = 0.95
        assert resolution_rate(95, 5) == pytest.approx(0.95)

    def test_all_collisions(self):
        assert resolution_rate(0, 10) == 0.0


class TestNormalFunctions:
    def test_cdf_at_zero_is_half(self):
        assert norm_cdf(0.0) == pytest.approx(0.5)

    def test_cdf_symmetry(self):
        assert norm_cdf(1.5) + norm_cdf(-1.5) == pytest.approx(1.0)

    def test_ppf_is_inverse_of_cdf(self):
        for p in (0.025, 0.1, 0.5, 0.9, 0.975):
            assert norm_cdf(norm_ppf(p)) == pytest.approx(p, abs=1e-6)

    def test_ppf_known_quantile(self):
        # 양측 95% z ≈ 1.95996
        assert norm_ppf(0.975) == pytest.approx(1.959964, abs=1e-4)

    def test_ppf_rejects_out_of_range(self):
        with pytest.raises(ValueError):
            norm_ppf(0.0)
        with pytest.raises(ValueError):
            norm_ppf(1.0)


class TestWilsonInterval:
    def test_bounds_within_unit(self):
        lo, hi = wilson_interval(10, 10)
        assert 0.0 <= lo <= hi <= 1.0

    def test_contains_point_estimate(self):
        lo, hi = wilson_interval(95, 100)
        assert lo <= 0.95 <= hi

    def test_zero_n_returns_full_range(self):
        assert wilson_interval(0, 0) == (0.0, 1.0)

    def test_extreme_proportion_stays_bounded(self):
        # 100/100 -> 상한 1.0, 하한 > 0 (Wald와 달리 붕괴하지 않음)
        lo, hi = wilson_interval(100, 100)
        assert hi == pytest.approx(1.0)
        assert lo > 0.0

    def test_larger_sample_narrows_interval(self):
        lo_small, hi_small = wilson_interval(9, 10)
        lo_big, hi_big = wilson_interval(900, 1000)
        assert (hi_big - lo_big) < (hi_small - lo_small)


class TestTwoProportionZtest:
    def test_identical_proportions_not_significant(self):
        result = two_proportion_ztest(50, 100, 50, 100)
        assert result.diff == pytest.approx(0.0)
        assert not result.significant
        assert result.p_value == pytest.approx(1.0)

    def test_large_difference_is_significant(self):
        # 50% vs 95% with n=200 each -> clearly significant
        result = two_proportion_ztest(100, 200, 190, 200)
        assert result.significant
        assert result.p_value < 0.001
        assert result.diff > 0

    def test_rejects_zero_sample(self):
        with pytest.raises(ValueError):
            two_proportion_ztest(0, 0, 5, 10)


class TestPower:
    def test_power_increases_with_sample_size(self):
        low = power_two_proportion(0.80, 0.90, 50)
        high = power_two_proportion(0.80, 0.90, 500)
        assert high > low

    def test_no_difference_gives_power_near_alpha(self):
        # 효과가 없으면 검정력은 유의수준 수준
        assert power_two_proportion(0.9, 0.9, 100, alpha=0.05) == pytest.approx(
            0.05, abs=1e-9
        )

    def test_power_in_unit_range(self):
        p = power_two_proportion(0.7, 0.95, 80)
        assert 0.0 <= p <= 1.0

    def test_rejects_bad_probability(self):
        with pytest.raises(ValueError):
            power_two_proportion(1.2, 0.5, 100)


class TestRequiredSampleSize:
    def test_returns_positive_integer(self):
        n = required_sample_size(0.80, 0.90)
        assert isinstance(n, int)
        assert n > 0

    def test_smaller_effect_needs_more_samples(self):
        small_effect = required_sample_size(0.80, 0.82)
        large_effect = required_sample_size(0.80, 0.95)
        assert small_effect > large_effect

    def test_achieves_target_power(self):
        # 산정된 n으로 실제 검정력이 목표 이상이어야 한다 (반올림 오차 허용)
        p1, p2, target = 0.80, 0.90, 0.80
        n = required_sample_size(p1, p2, target)
        achieved = power_two_proportion(p1, p2, n, alpha=0.05)
        assert achieved >= target - 0.02

    def test_rejects_equal_proportions(self):
        with pytest.raises(ValueError):
            required_sample_size(0.9, 0.9)


class TestPowerReport:
    def test_report_contains_key_sections(self):
        report = power_report(
            baseline_conflicts=70,
            baseline_collisions=30,
            sdacs_conflicts=96,
            sdacs_collisions=4,
        )
        assert "충돌 해결률 통계적 검정력 분석" in report
        assert "Wilson CI" in report
        assert "z-검정" in report
        assert "p-value" in report

    def test_report_flags_significant_improvement(self):
        report = power_report(70, 30, 96, 4)
        assert "유의함" in report

    def test_report_suggests_sample_size_when_underpowered(self):
        # 거의 차이 없고 표본 작음 -> 비유의 + 필요 표본 권고
        report = power_report(80, 20, 82, 18)
        assert "필요한 그룹당 이벤트 수" in report
