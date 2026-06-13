"""ODYSSEY Phase 446 — 충돌 해결률 공식 통계적 검정력 분석 테스트."""
import pytest

from simulation.power_analysis import (
    PowerResult,
    cohens_h,
    proportion_power,
    required_sample_size,
    resolution_rate_power_report,
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


class TestResolutionRatePowerReport:
    def test_report_contains_design_summary(self):
        report = resolution_rate_power_report(
            baseline=0.80, target=0.90, n_runs=100, alpha=0.05
        )
        assert "0.80" in report or "0.800" in report
        assert "0.90" in report or "0.900" in report
        assert "%" in report
        assert "|" in report  # 마크다운 표
