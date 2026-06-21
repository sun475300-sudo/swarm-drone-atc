"""ODYSSEY Phase 405 — 국제 벤치마크 비교 (BlueSky·U-TRAFMAN) 단위 테스트."""
from __future__ import annotations

import os

import pytest

from simulation.benchmark_comparison import (
    BENCHMARK_DIMENSIONS,
    BENCHMARK_SYSTEM_CATALOG,
    BENCHMARK_SYSTEMS,
    SUPPORT_LEVELS,
    SUPPORT_WEIGHT,
    BenchmarkDimension,
    BenchmarkSystem,
    ComparisonReport,
    categories,
    comparison_matrix,
    dimensions_by_category,
    find_dimension,
    find_system,
    gaps,
    system_score,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _dim(**kw) -> BenchmarkDimension:
    """검증 테스트용 기본 비교 축 (필요 필드만 덮어쓴다)."""
    base = dict(
        dim_id="d",
        name="D",
        category="conflict",
        citation="cite",
        sdacs_support="full",
        sdacs_module="simulation/metrics.py",
        bluesky_support="full",
        u_trafman_support="partial",
        summary="s",
    )
    base.update(kw)
    return BenchmarkDimension(**base)  # type: ignore[arg-type]


# --- BenchmarkDimension 검증 ----------------------------------------------

def test_dimension_rejects_empty_id():
    with pytest.raises(ValueError):
        _dim(dim_id="")


def test_dimension_rejects_padded_id():
    with pytest.raises(ValueError):
        _dim(dim_id=" d ")


def test_dimension_rejects_empty_name():
    with pytest.raises(ValueError):
        _dim(name="  ")


def test_dimension_rejects_empty_category():
    with pytest.raises(ValueError):
        _dim(category="")


def test_dimension_rejects_empty_citation():
    with pytest.raises(ValueError):
        _dim(citation="")


def test_dimension_rejects_empty_summary():
    with pytest.raises(ValueError):
        _dim(summary="")


def test_dimension_rejects_unknown_support_level():
    with pytest.raises(ValueError):
        _dim(bluesky_support="maybe")


def test_dimension_rejects_unknown_sdacs_level():
    with pytest.raises(ValueError):
        _dim(sdacs_support="some")


def test_dimension_rejects_blank_module_path():
    with pytest.raises(ValueError):
        _dim(sdacs_support="full", sdacs_module="   ")


def test_dimension_honesty_binding_none_requires_null_module():
    # sdacs_support=='none' 이면 module 은 None 이어야 한다.
    with pytest.raises(ValueError):
        _dim(sdacs_support="none", sdacs_module="simulation/metrics.py")


def test_dimension_honesty_binding_supported_requires_module():
    # sdacs_support!='none' 이면 module 은 None 이 아니어야 한다.
    with pytest.raises(ValueError):
        _dim(sdacs_support="partial", sdacs_module=None)


def test_dimension_none_with_null_module_is_valid():
    d = _dim(sdacs_support="none", sdacs_module=None)
    assert d.sdacs_support == "none"
    assert d.sdacs_module is None


def test_support_for_returns_correct_level():
    d = _dim(sdacs_support="full", bluesky_support="partial", u_trafman_support="none")
    assert d.support_for("sdacs") == "full"
    assert d.support_for("bluesky") == "partial"
    assert d.support_for("u_trafman") == "none"


def test_support_for_rejects_unknown_system():
    with pytest.raises(ValueError):
        _dim().support_for("skyguide")


# --- BenchmarkSystem 검증 --------------------------------------------------

def test_system_rejects_unknown_id():
    with pytest.raises(ValueError):
        BenchmarkSystem("other", "n", "o", "l", "c")


def test_system_rejects_empty_field():
    with pytest.raises(ValueError):
        BenchmarkSystem("sdacs", "n", "o", "l", "  ")


def test_catalog_covers_all_systems():
    assert {s.system_id for s in BENCHMARK_SYSTEM_CATALOG} == set(BENCHMARK_SYSTEMS)


def test_catalog_ids_unique():
    ids = [s.system_id for s in BENCHMARK_SYSTEM_CATALOG]
    assert len(ids) == len(set(ids))


def test_find_system_returns_match():
    assert find_system("bluesky").name.startswith("BlueSky")


def test_find_system_unknown_raises():
    with pytest.raises(KeyError):
        find_system("nope")


# --- 카탈로그 무결성 -------------------------------------------------------

def test_dimension_ids_are_unique():
    ids = [d.dim_id for d in BENCHMARK_DIMENSIONS]
    assert len(ids) == len(set(ids))


def test_all_support_levels_valid():
    for d in BENCHMARK_DIMENSIONS:
        for system in BENCHMARK_SYSTEMS:
            assert d.support_for(system) in SUPPORT_LEVELS


def test_cited_modules_exist_on_disk():
    """SDACS 가 인용하는 모든 모듈 경로는 리포에 실재해야 한다 (정직성)."""
    for d in BENCHMARK_DIMENSIONS:
        if d.sdacs_module is not None:
            full = os.path.join(REPO_ROOT, d.sdacs_module)
            assert os.path.isfile(full), f"{d.dim_id} cites missing {d.sdacs_module}"


def test_honesty_binding_holds_across_catalog():
    for d in BENCHMARK_DIMENSIONS:
        assert (d.sdacs_support == "none") == (d.sdacs_module is None)


def test_manned_integration_is_known_gap():
    assert "manned_integration" in {d.dim_id for d in gaps()}


def test_support_weights_cover_all_levels():
    assert set(SUPPORT_WEIGHT) == set(SUPPORT_LEVELS)


def test_support_weight_is_read_only():
    # 가중치 표는 모듈 전역 — 변조되면 모든 점수가 조용히 틀어진다.
    with pytest.raises(TypeError):
        SUPPORT_WEIGHT["full"] = 0.0  # type: ignore[index]


# --- 조회 함수 -------------------------------------------------------------

def test_find_dimension_returns_match():
    d = find_dimension("pairwise_cdr")
    assert d.category == "conflict"


def test_find_dimension_unknown_raises():
    with pytest.raises(KeyError):
        find_dimension("does_not_exist")


def test_categories_sorted_and_unique():
    cats = categories()
    assert cats == tuple(sorted(set(cats)))


def test_dimensions_by_category_returns_only_that_category():
    for cat in categories():
        members = dimensions_by_category(cat)
        assert all(d.category == cat for d in members)


def test_dimensions_by_category_sorted_by_id():
    members = dimensions_by_category("analysis")
    ids = [d.dim_id for d in members]
    assert ids == sorted(ids)


def test_dimensions_by_category_unknown_raises():
    with pytest.raises(ValueError):
        dimensions_by_category("nonexistent")


def test_every_dimension_in_exactly_one_category_bucket():
    collected = []
    for cat in categories():
        collected.extend(dimensions_by_category(cat))
    assert len(collected) == len(BENCHMARK_DIMENSIONS)
    assert {d.dim_id for d in collected} == {d.dim_id for d in BENCHMARK_DIMENSIONS}


def test_gaps_are_unsupported_only():
    assert all(d.sdacs_support == "none" for d in gaps())


# --- system_score / ComparisonReport --------------------------------------

def test_system_score_rejects_unknown_system():
    with pytest.raises(ValueError):
        system_score("other")


def test_system_score_counts_sum_to_total():
    for system in BENCHMARK_SYSTEMS:
        r = system_score(system)
        assert r.full + r.partial + r.none == r.total
        assert r.total == len(BENCHMARK_DIMENSIONS)


def test_system_score_weighted_matches_manual():
    r = system_score("sdacs")
    expected = sum(
        SUPPORT_WEIGHT[d.sdacs_support] for d in BENCHMARK_DIMENSIONS
    )
    assert r.weighted_score == pytest.approx(expected)


def test_system_score_coverage_in_range():
    for system in BENCHMARK_SYSTEMS:
        r = system_score(system)
        assert 0.0 <= r.coverage_pct <= 100.0


def test_system_score_is_deterministic():
    # 데이터 전용 순수 함수 — 모듈 전역 가변 상태가 새로 끼어들면 깨지는 회귀 가드.
    assert system_score("bluesky") == system_score("bluesky")


def test_report_none_count_matches_gaps_helper():
    # ComparisonReport.none 은 gaps() 헬퍼와 교차 일치해야 한다 (브리틀 하드코딩 회피).
    r = system_score("sdacs")
    assert r.none == len(gaps())


def test_report_type():
    assert isinstance(system_score("sdacs"), ComparisonReport)


def test_report_rejects_inconsistent_counts():
    with pytest.raises(ValueError):
        ComparisonReport("sdacs", 10, 3, 3, 3, 5.0)  # 3+3+3 != 10


def test_report_rejects_weighted_overflow():
    with pytest.raises(ValueError):
        ComparisonReport("sdacs", 10, 5, 3, 2, 99.0)  # weighted >> any bound


def test_report_rejects_weighted_inconsistent_with_counts():
    # full*1.0 + partial*0.5 = 5 + 2.5 = 7.5; 8.0 은 counts 와 모순 → 거부.
    with pytest.raises(ValueError):
        ComparisonReport("sdacs", 10, 5, 5, 0, 8.0)


def test_report_accepts_max_possible_weighted():
    # 경계값: full*1.0 + partial*0.5 정확히 = 7.5 는 허용.
    r = ComparisonReport("sdacs", 10, 5, 5, 0, 7.5)
    assert r.weighted_score == pytest.approx(7.5)


def test_report_rejects_unknown_system():
    with pytest.raises(ValueError):
        ComparisonReport("other", 1, 1, 0, 0, 1.0)


def test_empty_report_coverage_is_zero():
    r = ComparisonReport("sdacs", 0, 0, 0, 0, 0.0)
    assert r.coverage_pct == 0.0


# --- comparison_matrix -----------------------------------------------------

def test_matrix_covers_all_dimensions():
    rows = comparison_matrix()
    assert len(rows) == len(BENCHMARK_DIMENSIONS)
    assert {r["dim_id"] for r in rows} == {d.dim_id for d in BENCHMARK_DIMENSIONS}


def test_matrix_sorted_by_category_then_id():
    rows = comparison_matrix()
    keys = [(r["category"], r["dim_id"]) for r in rows]
    assert keys == sorted(keys)


def test_matrix_rows_are_read_only():
    rows = comparison_matrix()
    with pytest.raises(TypeError):
        rows[0]["sdacs"] = "none"  # type: ignore[index]


def test_matrix_is_deterministic():
    assert comparison_matrix() == comparison_matrix()


def test_matrix_module_matches_honesty_binding():
    for row in comparison_matrix():
        assert (row["sdacs"] == "none") == (row["sdacs_module"] is None)


# --- main() CLI 진입점 -----------------------------------------------------

def test_main_report_exits_zero():
    from simulation.benchmark_comparison import main
    assert main(["--report"]) == 0


def test_main_matrix_exits_zero():
    from simulation.benchmark_comparison import main
    assert main(["--matrix"]) == 0


def test_main_gaps_exits_zero():
    from simulation.benchmark_comparison import main
    assert main(["--gaps"]) == 0


def test_main_system_exits_zero():
    from simulation.benchmark_comparison import main
    assert main(["--system", "bluesky"]) == 0


def test_main_category_exits_zero():
    from simulation.benchmark_comparison import main
    assert main(["--category", "analysis"]) == 0


def test_main_systems_exits_zero():
    from simulation.benchmark_comparison import main
    assert main(["--systems"]) == 0


def test_main_default_exits_zero():
    from simulation.benchmark_comparison import main
    assert main([]) == 0
