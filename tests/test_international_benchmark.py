"""ODYSSEY Phase 405 — 국제 벤치마크 비교 매트릭스 단위 테스트."""
from __future__ import annotations

from pathlib import Path
from types import MappingProxyType

import pytest

from simulation.international_benchmark import (
    BENCHMARK_CATEGORIES,
    BENCHMARK_METRICS,
    BENCHMARK_SCENARIOS,
    PLATFORMS,
    BenchmarkComparisonReport,
    BenchmarkScenario,
    comparison_matrix,
    comparison_report,
    find_scenario,
    scenarios_by_category,
    scenarios_for_platform,
    sdacs_unique_scenarios,
    main,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------- #
# 카탈로그 정합성
# --------------------------------------------------------------------------- #
def test_catalog_non_empty():
    assert len(BENCHMARK_SCENARIOS) >= 10


def test_scenario_ids_unique():
    ids = [s.scenario_id for s in BENCHMARK_SCENARIOS]
    assert len(ids) == len(set(ids))


def test_all_categories_referenced_exist():
    for s in BENCHMARK_SCENARIOS:
        assert s.category in BENCHMARK_CATEGORIES


def test_all_metrics_valid():
    for s in BENCHMARK_SCENARIOS:
        assert s.primary_metric in BENCHMARK_METRICS


def test_all_comparable_platforms_known():
    for s in BENCHMARK_SCENARIOS:
        for code in s.comparable:
            assert code in PLATFORMS


# --------------------------------------------------------------------------- #
# 정직성 결속 (핵심 불변식)
# --------------------------------------------------------------------------- #
def test_cited_manifests_exist_on_disk():
    """모든 시나리오가 인용한 매니페스트는 디스크에 실재해야 한다."""
    for s in BENCHMARK_SCENARIOS:
        path = _REPO_ROOT / s.manifest
        assert path.is_file(), f"{s.scenario_id} cites missing manifest {s.manifest}"


def test_has_at_least_one_sdacs_unique_gap():
    """외부 교차 검증 기준선이 없는 SDACS 고유 시나리오를 정직히 표면화한다."""
    assert len(sdacs_unique_scenarios()) >= 1


def test_sdacs_unique_has_empty_comparable():
    for s in sdacs_unique_scenarios():
        assert s.comparable == ()
        assert s.is_cross_validatable is False


def test_has_at_least_one_cross_validatable():
    assert any(s.is_cross_validatable for s in BENCHMARK_SCENARIOS)


# --------------------------------------------------------------------------- #
# BenchmarkScenario 검증 (__post_init__)
# --------------------------------------------------------------------------- #
def _valid_kwargs(**over):
    base = dict(
        scenario_id="01_x", name="X", category="CDR", primary_metric="MSD",
        manifest="benchmarks/scenarios/01_corridor_crossing/manifest.yaml",
        comparable=("bluesky",), summary="s",
    )
    base.update(over)
    return base


def test_rejects_empty_scenario_id():
    with pytest.raises(ValueError):
        BenchmarkScenario(**_valid_kwargs(scenario_id=""))


def test_rejects_padded_scenario_id():
    with pytest.raises(ValueError):
        BenchmarkScenario(**_valid_kwargs(scenario_id=" x "))


def test_rejects_scenario_id_with_space():
    with pytest.raises(ValueError):
        BenchmarkScenario(**_valid_kwargs(scenario_id="a b"))


def test_rejects_scenario_id_with_tab():
    with pytest.raises(ValueError):
        BenchmarkScenario(**_valid_kwargs(scenario_id="a\tb"))


def test_rejects_empty_name():
    with pytest.raises(ValueError):
        BenchmarkScenario(**_valid_kwargs(name="  "))


def test_rejects_empty_summary():
    with pytest.raises(ValueError):
        BenchmarkScenario(**_valid_kwargs(summary=""))


def test_rejects_empty_manifest():
    with pytest.raises(ValueError):
        BenchmarkScenario(**_valid_kwargs(manifest="  "))


def test_rejects_unknown_category():
    with pytest.raises(ValueError):
        BenchmarkScenario(**_valid_kwargs(category="ZZZ"))


def test_rejects_unknown_metric():
    with pytest.raises(ValueError):
        BenchmarkScenario(**_valid_kwargs(primary_metric="BOGUS"))


def test_rejects_unknown_comparable_platform():
    with pytest.raises(ValueError):
        BenchmarkScenario(**_valid_kwargs(comparable=("nope",)))


def test_rejects_duplicate_comparable_platform():
    with pytest.raises(ValueError):
        BenchmarkScenario(**_valid_kwargs(comparable=("bluesky", "bluesky")))


def test_accepts_empty_comparable_as_unique():
    s = BenchmarkScenario(**_valid_kwargs(comparable=()))
    assert s.is_cross_validatable is False
    assert s.cross_platform_count == 0


def test_cross_platform_count():
    s = BenchmarkScenario(**_valid_kwargs(comparable=("bluesky", "utrafman")))
    assert s.cross_platform_count == 2
    assert s.is_cross_validatable is True


def test_scenario_is_frozen():
    s = BENCHMARK_SCENARIOS[0]
    with pytest.raises(Exception):
        s.category = "DENS"  # type: ignore[misc]


# --------------------------------------------------------------------------- #
# 조회 API
# --------------------------------------------------------------------------- #
def test_find_scenario_found():
    s = find_scenario("01_corridor_crossing")
    assert s.name == "Corridor Crossing"


def test_find_scenario_missing():
    with pytest.raises(KeyError):
        find_scenario("nope")


def test_scenarios_by_category_sorted():
    items = scenarios_by_category("CDR")
    assert all(s.category == "CDR" for s in items)
    assert list(items) == sorted(items, key=lambda s: s.scenario_id)


def test_scenarios_by_category_invalid():
    with pytest.raises(ValueError):
        scenarios_by_category("ZZZ")


def test_scenarios_for_platform_sorted():
    items = scenarios_for_platform("bluesky")
    assert all("bluesky" in s.comparable for s in items)
    assert list(items) == sorted(items, key=lambda s: s.scenario_id)


def test_scenarios_for_platform_invalid():
    with pytest.raises(ValueError):
        scenarios_for_platform("nope")


def test_sdacs_unique_sorted():
    items = sdacs_unique_scenarios()
    assert list(items) == sorted(items, key=lambda s: s.scenario_id)


# --------------------------------------------------------------------------- #
# BenchmarkComparisonReport
# --------------------------------------------------------------------------- #
def test_report_counts_sum_to_total():
    r = comparison_report()
    assert r.cross_validatable + r.sdacs_unique == r.total
    assert r.total == len(BENCHMARK_SCENARIOS)


def test_report_coverage_in_range():
    r = comparison_report()
    assert 0.0 <= r.coverage <= 1.0
    assert r.coverage_pct == pytest.approx(100.0 * r.coverage)


def test_report_by_platform_within_cross_validatable():
    r = comparison_report()
    for platform, count in r.by_platform.items():
        assert platform in PLATFORMS
        assert 0 <= count <= r.cross_validatable


def test_report_by_category_total_matches():
    r = comparison_report()
    cat_total = sum(tot for _xv, tot in r.by_category.values())
    assert cat_total == r.total


def test_report_by_platform_is_readonly():
    r = comparison_report()
    with pytest.raises(TypeError):
        r.by_platform["bluesky"] = 0  # type: ignore[index]


def test_report_by_category_is_readonly():
    r = comparison_report()
    with pytest.raises(TypeError):
        r.by_category["CDR"] = (0, 0)  # type: ignore[index]


def test_report_coverage_matches_count():
    r = comparison_report()
    expected = r.cross_validatable / r.total
    assert r.coverage == pytest.approx(expected)


def test_report_rejects_inconsistent_counts():
    with pytest.raises(ValueError):
        BenchmarkComparisonReport(
            total=5, cross_validatable=1, sdacs_unique=1, coverage=0.5,
            by_platform=MappingProxyType({}), by_category=MappingProxyType({}),
        )


def test_report_rejects_out_of_range_coverage():
    with pytest.raises(ValueError):
        BenchmarkComparisonReport(
            total=1, cross_validatable=1, sdacs_unique=0, coverage=2.0,
            by_platform=MappingProxyType({"bluesky": 1}),
            by_category=MappingProxyType({"CDR": (1, 1)}),
        )


def test_report_rejects_unknown_platform():
    with pytest.raises(ValueError):
        BenchmarkComparisonReport(
            total=1, cross_validatable=1, sdacs_unique=0, coverage=1.0,
            by_platform=MappingProxyType({"ghost": 1}),
            by_category=MappingProxyType({"CDR": (1, 1)}),
        )


def test_report_rejects_platform_exceeds_cross_validatable():
    with pytest.raises(ValueError):
        BenchmarkComparisonReport(
            total=2, cross_validatable=1, sdacs_unique=1, coverage=0.5,
            by_platform=MappingProxyType({"bluesky": 99}),
            by_category=MappingProxyType({"CDR": (1, 2)}),
        )


def test_report_rejects_category_total_mismatch():
    with pytest.raises(ValueError):
        BenchmarkComparisonReport(
            total=2, cross_validatable=2, sdacs_unique=0, coverage=1.0,
            by_platform=MappingProxyType({"bluesky": 2}),
            by_category=MappingProxyType({"CDR": (1, 1)}),
        )


def test_report_rejects_category_cross_validatable_sum_mismatch():
    # 범주 총계는 일치하지만(2==2) 범주별 교차검증 합(1) != cross_validatable(2).
    with pytest.raises(ValueError):
        BenchmarkComparisonReport(
            total=2, cross_validatable=2, sdacs_unique=0, coverage=1.0,
            by_platform=MappingProxyType({"bluesky": 2}),
            by_category=MappingProxyType({"CDR": (1, 2)}),
        )


def test_report_by_category_cross_validatable_sum_matches():
    r = comparison_report()
    cat_xv = sum(xv for xv, _tot in r.by_category.values())
    assert cat_xv == r.cross_validatable


# --------------------------------------------------------------------------- #
# comparison_matrix (도구 간 교환)
# --------------------------------------------------------------------------- #
def test_matrix_row_count():
    assert len(comparison_matrix()) == len(BENCHMARK_SCENARIOS)


def test_matrix_keys():
    expected = {"scenario_id", "name", "category", "primary_metric",
                "comparable", "cross_validatable", "manifest"}
    for row in comparison_matrix():
        assert set(row) == expected


def test_matrix_sorted_by_id():
    rows = comparison_matrix()
    ids = [str(r["scenario_id"]) for r in rows]
    assert ids == sorted(ids)


def test_matrix_unique_has_empty_comparable():
    for row in comparison_matrix():
        if not row["comparable"]:
            assert row["cross_validatable"] is False


def test_matrix_rows_are_readonly():
    for row in comparison_matrix():
        with pytest.raises(TypeError):
            row["scenario_id"] = "hacked"  # type: ignore[index]


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def test_cli_default(capsys):
    assert main([]) == 0
    assert "커버리지" in capsys.readouterr().out


def test_cli_matrix(capsys):
    assert main(["--matrix"]) == 0
    assert "매트릭스" in capsys.readouterr().out


def test_cli_report(capsys):
    assert main(["--report"]) == 0
    assert "커버리지" in capsys.readouterr().out


def test_cli_category(capsys):
    assert main(["--category", "CDR"]) == 0
    assert "corridor" in capsys.readouterr().out


def test_cli_platform(capsys):
    assert main(["--platform", "bluesky"]) == 0
    out = capsys.readouterr().out
    assert out.strip()


def test_cli_unique(capsys):
    assert main(["--unique"]) == 0
    out = capsys.readouterr().out
    assert out.strip()


def test_cli_platforms(capsys):
    assert main(["--platforms"]) == 0
    out = capsys.readouterr().out
    for platform in PLATFORMS:
        assert platform in out
