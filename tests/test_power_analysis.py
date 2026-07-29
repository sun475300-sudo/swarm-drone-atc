"""ODYSSEY Phase 446 — 충돌 해결률 공식 통계적 검정력 분석 테스트."""
import pytest

from simulation.power_analysis import (
    PowerResult,
    ProportionComparison,
    cohens_h,
    compare_resolution_rates,
    proportion_power,
    required_sample_size,
    resolution_rate,
    resolution_rate_comparison_report,
    resolution_rate_power_report,
    two_proportion_power,
    wilson_interval,
)

pytestmark = pytest.mark.unit


class TestCohensH:
    def test_zero_when_equal(self):
        assert cohens_h(0.8, 0.8) == pytest.approx(0.0, abs=1e-9)

    def test_known_value(self):
        # 2*asin(sqrt(0.9)) - 2*asin(sqrt(0.8)) ≈ 0.2838
        assert cohens_h(0.8, 0.9) == pytest.approx(0.2838, abs=1e-3)

    def test_sign_follows_direction(self):
        assert cohens_h(0.8, 0.9) > 0
        assert cohens_h(0.9, 0.8) < 0

    def test_invalid_proportion_raises(self):
        with pytest.raises(ValueError):
            cohens_h(-0.1, 0.5)
        with pytest.raises(ValueError):
            cohens_h(0.5, 1.5)


class TestProportionPower:
    def test_power_in_unit_range(self):
        res = proportion_power(p0=0.8, p1=0.9, n=98)
        assert isinstance(res, PowerResult)
        assert 0.0 <= res.power <= 1.0

    def test_no_effect_gives_alpha_level_power(self):
        # 효과 없음 → 검정력 ≈ 유의수준
        res = proportion_power(p0=0.8, p1=0.8, n=100, alpha=0.05)
        assert res.power == pytest.approx(0.05, abs=1e-6)

    def test_power_increases_with_n(self):
        small = proportion_power(p0=0.8, p1=0.9, n=20)
        large = proportion_power(p0=0.8, p1=0.9, n=400)
        assert large.power > small.power

    def test_standard_design_reaches_80pct(self):
        # n=98 설계는 p0=0.8 vs p1=0.9, alpha=0.05 에서 ~0.8 검정력
        res = proportion_power(p0=0.8, p1=0.9, n=98, alpha=0.05)
        assert res.power == pytest.approx(0.80, abs=0.05)

    def test_invalid_proportion_raises_at_boundary(self):
        with pytest.raises(ValueError):
            proportion_power(p0=-0.1, p1=0.9, n=100)
        with pytest.raises(ValueError):
            proportion_power(p0=0.8, p1=1.5, n=100)


class TestRequiredSampleSize:
    def test_standard_design(self):
        # p0=0.8, p1=0.9, alpha=0.05, power=0.8 → n≈98
        n = required_sample_size(p0=0.8, p1=0.9, alpha=0.05, power=0.8)
        assert 90 <= n <= 105

    def test_smaller_effect_needs_more_samples(self):
        n_big = required_sample_size(p0=0.8, p1=0.9)
        n_small = required_sample_size(p0=0.8, p1=0.83)
        assert n_small > n_big

    def test_achieves_target_power(self):
        n = required_sample_size(p0=0.8, p1=0.9, alpha=0.05, power=0.8)
        # 계산된 n 으로 검정력 ≥ 목표
        res = proportion_power(p0=0.8, p1=0.9, n=n, alpha=0.05)
        assert res.power >= 0.80

    def test_zero_effect_raises(self):
        with pytest.raises(ValueError):
            required_sample_size(p0=0.8, p1=0.8)

    def test_invalid_proportion_raises_at_boundary(self):
        with pytest.raises(ValueError):
            required_sample_size(p0=0.8, p1=1.2)


class TestObservedResolutionRate:
    def test_rate_uses_project_formula(self):
        assert resolution_rate(conflicts=95, collisions=5) == pytest.approx(0.95)

    def test_no_events_is_treated_as_safe(self):
        assert resolution_rate(conflicts=0, collisions=0) == 1.0

    def test_negative_counts_are_rejected(self):
        with pytest.raises(ValueError):
            resolution_rate(conflicts=-1, collisions=0)


class TestWilsonInterval:
    def test_interval_contains_observed_rate(self):
        low, high = wilson_interval(successes=95, total=100)
        assert 0.0 <= low <= 0.95 <= high <= 1.0

    def test_zero_total_returns_uninformative_interval(self):
        assert wilson_interval(successes=0, total=0) == (0.0, 1.0)

    def test_successes_cannot_exceed_total(self):
        with pytest.raises(ValueError):
            wilson_interval(successes=11, total=10)


class TestObservedComparison:
    def test_clear_improvement_is_significant(self):
        result = compare_resolution_rates(
            baseline_conflicts=70,
            baseline_collisions=30,
            candidate_conflicts=96,
            candidate_collisions=4,
        )
        assert isinstance(result, ProportionComparison)
        assert result.candidate_rate > result.baseline_rate
        assert result.significant
        assert result.p_value < 0.001

    def test_identical_rates_are_not_significant(self):
        result = compare_resolution_rates(90, 10, 90, 10)
        assert result.difference == pytest.approx(0.0)
        assert result.p_value == pytest.approx(1.0)
        assert not result.significant

    def test_power_increases_with_event_count(self):
        small = two_proportion_power(0.8, 0.9, 50)
        large = two_proportion_power(0.8, 0.9, 500)
        assert large > small

    def test_comparison_report_contains_inference(self):
        report = resolution_rate_comparison_report(70, 30, 96, 4)
        assert "Wilson" in report
        assert "p-value" in report
        assert "유의함" in report


class TestResolutionRatePowerReport:
    def test_report_contains_design_summary(self):
        report = resolution_rate_power_report(
            baseline=0.80, target=0.90, n_runs=100, alpha=0.05
        )
        assert "0.80" in report or "0.800" in report
        assert "0.90" in report or "0.900" in report
        assert "%" in report
        assert "|" in report  # 마크다운 표
