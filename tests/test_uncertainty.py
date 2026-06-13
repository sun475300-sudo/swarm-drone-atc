"""ODYSSEY Phase 445 — 불확실성 정량화(Monte Carlo 신뢰구간) 테스트."""
import numpy as np
import pytest

from simulation.uncertainty import (
    ConfidenceInterval,
    bootstrap_ci,
    confidence_report,
    normal_ci,
    proportion_ci,
    summarize_metric_ci,
)

pytestmark = pytest.mark.unit


class TestConfidenceInterval:
    def test_margin_and_contains(self):
        ci = ConfidenceInterval(
            point=0.9, lower=0.8, upper=1.0, confidence=0.95, method="normal", n=30
        )
        assert ci.margin == pytest.approx(0.1)
        assert ci.contains(0.85)
        assert not ci.contains(0.5)

    def test_as_dict_roundtrip(self):
        ci = ConfidenceInterval(
            point=0.5, lower=0.4, upper=0.6, confidence=0.95, method="normal", n=10
        )
        d = ci.as_dict()
        assert d["point"] == 0.5
        assert d["lower"] == 0.4
        assert d["confidence"] == 0.95

    def test_format_human_readable(self):
        ci = ConfidenceInterval(
            point=0.942, lower=0.910, upper=0.974, confidence=0.95, method="normal", n=30
        )
        s = ci.format()
        assert "0.942" in s
        assert "0.910" in s
        assert "0.974" in s


class TestNormalCI:
    def test_known_mean(self):
        # 평균 10, 분산 0 → CI 폭 0
        ci = normal_ci([10.0, 10.0, 10.0, 10.0])
        assert ci.point == pytest.approx(10.0)
        assert ci.lower == pytest.approx(10.0)
        assert ci.upper == pytest.approx(10.0)

    def test_interval_brackets_mean(self):
        rng = np.random.default_rng(42)
        samples = rng.normal(5.0, 2.0, 200).tolist()
        ci = normal_ci(samples, confidence=0.95)
        assert ci.lower < ci.point < ci.upper
        assert ci.point == pytest.approx(float(np.mean(samples)))
        # 참값 5.0이 95% 구간 안에 들어야 함
        assert ci.contains(5.0)

    def test_higher_confidence_wider(self):
        rng = np.random.default_rng(1)
        samples = rng.normal(0.0, 1.0, 100).tolist()
        ci90 = normal_ci(samples, confidence=0.90)
        ci99 = normal_ci(samples, confidence=0.99)
        assert ci99.margin > ci90.margin

    def test_single_sample_raises(self):
        with pytest.raises(ValueError):
            normal_ci([1.0])


class TestBootstrapCI:
    def test_deterministic_with_seed(self):
        rng = np.random.default_rng(7)
        samples = rng.normal(3.0, 1.0, 100).tolist()
        a = bootstrap_ci(samples, seed=123, n_resamples=2000)
        b = bootstrap_ci(samples, seed=123, n_resamples=2000)
        assert a.lower == b.lower
        assert a.upper == b.upper

    def test_brackets_point(self):
        rng = np.random.default_rng(11)
        samples = rng.normal(3.0, 1.0, 100).tolist()
        ci = bootstrap_ci(samples, seed=123, n_resamples=2000)
        assert ci.lower < ci.point < ci.upper
        assert ci.method == "bootstrap"

    def test_close_to_normal_ci(self):
        rng = np.random.default_rng(3)
        samples = rng.normal(50.0, 5.0, 300).tolist()
        nci = normal_ci(samples)
        bci = bootstrap_ci(samples, seed=99, n_resamples=4000)
        # 대표본에서 두 방법은 근접해야 함
        assert bci.lower == pytest.approx(nci.lower, abs=1.0)
        assert bci.upper == pytest.approx(nci.upper, abs=1.0)


class TestProportionCI:
    def test_wilson_score_brackets_estimate(self):
        ci = proportion_ci(successes=94, trials=100, confidence=0.95)
        assert ci.point == pytest.approx(0.94)
        assert ci.lower < 0.94 < ci.upper
        assert ci.method == "wilson"

    def test_bounds_clamped(self):
        ci = proportion_ci(successes=100, trials=100)
        assert ci.lower >= 0.0
        assert ci.upper <= 1.0

    def test_invalid_trials_raises(self):
        with pytest.raises(ValueError):
            proportion_ci(successes=5, trials=0)
        with pytest.raises(ValueError):
            proportion_ci(successes=11, trials=10)


class TestSummarizeMetricCI:
    def test_extracts_metric_from_results(self):
        results = [{"collision_count": float(x)} for x in [1, 2, 3, 4, 5]]
        ci = summarize_metric_ci(results, "collision_count")
        assert ci.point == pytest.approx(3.0)
        assert ci.n == 5

    def test_missing_metric_raises(self):
        with pytest.raises(KeyError):
            summarize_metric_ci([{"a": 1.0}], "b")


class TestConfidenceReport:
    def test_markdown_table_lists_metrics(self):
        results = [
            {"collision_count": 1.0, "conflict_resolution_rate": 0.9},
            {"collision_count": 2.0, "conflict_resolution_rate": 0.95},
            {"collision_count": 0.0, "conflict_resolution_rate": 1.0},
        ]
        report = confidence_report(
            results, ["collision_count", "conflict_resolution_rate"]
        )
        assert "collision_count" in report
        assert "conflict_resolution_rate" in report
        assert "95%" in report
        # 마크다운 표 헤더
        assert "|" in report
