"""ODYSSEY Phase 462 — ISO/TC 20/SC 16 (UAS) 표준 추적 매트릭스 단위 테스트."""
from __future__ import annotations

import os

import pytest

from simulation.iso_uas_standards_matrix import (
    CATEGORIES,
    ISO_STANDARDS,
    STATUSES,
    CoverageReport,
    IsoStandard,
    covered_standards,
    coverage_report,
    find_standard,
    gaps,
    standards_by_category,
    standards_by_status,
    standards_matrix,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# --- IsoStandard 검증 ------------------------------------------------------

def test_standard_rejects_empty_id():
    with pytest.raises(ValueError):
        IsoStandard("", "title", "General", "PUBLISHED", None, "r")


def test_standard_rejects_padded_id():
    with pytest.raises(ValueError):
        IsoStandard(" ISO 1 ", "title", "General", "PUBLISHED", None, "r")


def test_standard_rejects_empty_title():
    with pytest.raises(ValueError):
        IsoStandard("ISO 1", "  ", "General", "PUBLISHED", None, "r")


def test_standard_rejects_empty_relevance():
    with pytest.raises(ValueError):
        IsoStandard("ISO 1", "title", "General", "PUBLISHED", None, "  ")


def test_standard_rejects_unknown_category():
    with pytest.raises(ValueError):
        IsoStandard("ISO 1", "title", "Nope", "PUBLISHED", None, "r")


def test_standard_rejects_unknown_status():
    with pytest.raises(ValueError):
        IsoStandard("ISO 1", "title", "General", "DRAFT", None, "r")


def test_standard_rejects_blank_module_path():
    with pytest.raises(ValueError):
        IsoStandard("ISO 1", "title", "General", "PUBLISHED", "   ", "r")


def test_is_covered_reflects_module_presence():
    mapped = IsoStandard("ISO 1", "T", "UTM", "PUBLISHED", "simulation/remote_id.py", "r")
    gap = IsoStandard("ISO 2", "T", "Personnel", "PUBLISHED", None, "r")
    assert mapped.is_covered is True
    assert gap.is_covered is False


def test_is_published_reflects_status():
    pub = IsoStandard("ISO 1", "T", "UTM", "PUBLISHED", None, "r")
    dev = IsoStandard("ISO 2", "T", "UTM", "UNDER_DEVELOPMENT", None, "r")
    assert pub.is_published is True
    assert dev.is_published is False


# --- 카탈로그 무결성 -------------------------------------------------------

def test_standard_ids_are_unique():
    ids = [s.standard_id for s in ISO_STANDARDS]
    assert len(ids) == len(set(ids))


def test_all_categories_valid():
    assert all(s.category in CATEGORIES for s in ISO_STANDARDS)


def test_all_statuses_valid():
    assert all(s.status in STATUSES for s in ISO_STANDARDS)


def test_cited_modules_exist_on_disk():
    """매핑이 인용하는 모든 SDACS 모듈 경로는 리포에 실재해야 한다 (정직성)."""
    for std in ISO_STANDARDS:
        if std.sdacs_module is not None:
            full = os.path.join(REPO_ROOT, std.sdacs_module)
            assert os.path.isfile(full), f"{std.standard_id} cites missing {std.sdacs_module}"


def test_catalog_includes_iso_21384_series():
    ids = {s.standard_id for s in ISO_STANDARDS}
    assert {"ISO 21384-1", "ISO 21384-2", "ISO 21384-3"} <= ids


def test_catalog_includes_iso_23629_utm_series():
    utm = {s.standard_id for s in standards_by_category("UTM")}
    assert {"ISO 23629-5", "ISO 23629-7", "ISO 23629-8", "ISO 23629-12"} <= utm


def test_personnel_training_is_a_known_gap():
    assert "ISO 23665" in {s.standard_id for s in gaps()}


# --- 조회 함수 -------------------------------------------------------------

def test_find_standard_returns_match():
    std = find_standard("ISO 21384-3")
    assert std.category == "Operations"
    assert std.is_covered is True


def test_find_standard_unknown_raises():
    with pytest.raises(KeyError):
        find_standard("ISO 99999")


def test_standards_by_category_rejects_bad_category():
    with pytest.raises(ValueError):
        standards_by_category("Bogus")


def test_standards_by_category_returns_only_that_category():
    for category in CATEGORIES:
        members = standards_by_category(category)
        assert all(s.category == category for s in members)


def test_standards_by_category_is_sorted_by_id():
    members = standards_by_category("UTM")
    ids = [s.standard_id for s in members]
    assert ids == sorted(ids)


def test_every_standard_appears_in_exactly_one_category_bucket():
    collected = []
    for category in CATEGORIES:
        collected.extend(standards_by_category(category))
    assert len(collected) == len(ISO_STANDARDS)
    assert {s.standard_id for s in collected} == {s.standard_id for s in ISO_STANDARDS}


def test_standards_by_status_rejects_bad_status():
    with pytest.raises(ValueError):
        standards_by_status("DRAFT")


def test_standards_by_status_returns_only_that_status():
    for status in STATUSES:
        members = standards_by_status(status)
        assert all(s.status == status for s in members)


def test_remote_id_part8_is_under_development():
    dev = {s.standard_id for s in standards_by_status("UNDER_DEVELOPMENT")}
    assert "ISO 23629-8" in dev


def test_gaps_are_uncovered_only():
    assert all(not s.is_covered for s in gaps())


def test_covered_and_gaps_partition_catalog():
    cov = {s.standard_id for s in covered_standards()}
    gap = {s.standard_id for s in gaps()}
    assert cov.isdisjoint(gap)
    assert cov | gap == {s.standard_id for s in ISO_STANDARDS}


# --- CoverageReport --------------------------------------------------------

def test_coverage_report_totals_consistent():
    r = coverage_report()
    assert r.total == len(ISO_STANDARDS)
    assert r.covered + r.gaps == r.total


def test_coverage_report_type():
    assert isinstance(coverage_report(), CoverageReport)


def test_coverage_pct_in_range():
    r = coverage_report()
    assert 0.0 <= r.coverage_pct <= 100.0


def test_published_coverage_pct_in_range():
    r = coverage_report()
    assert 0.0 <= r.published_coverage_pct <= 100.0


def test_by_category_counts_sum_to_total():
    r = coverage_report()
    total_from_cat = sum(tot for _cov, tot in r.by_category.values())
    cov_from_cat = sum(cov for cov, _tot in r.by_category.values())
    assert total_from_cat == r.total
    assert cov_from_cat == r.covered


def test_by_category_covered_never_exceeds_total():
    r = coverage_report()
    for cov, tot in r.by_category.values():
        assert 0 <= cov <= tot


def test_coverage_report_is_deterministic():
    assert coverage_report() == coverage_report()


def test_published_total_never_exceeds_total():
    r = coverage_report()
    assert r.published_total <= r.total


def test_empty_coverage_pct_is_zero():
    r = CoverageReport(0, 0, 0, 0, 0, {})
    assert r.coverage_pct == 0.0
    assert r.published_coverage_pct == 0.0


def test_coverage_report_rejects_inconsistent_totals():
    with pytest.raises(ValueError):
        CoverageReport(5, 10, 0, 0, 0, {})  # covered+gaps != total


def test_coverage_report_rejects_published_overflow():
    with pytest.raises(ValueError):
        CoverageReport(5, 3, 2, 2, 9, {})  # published_covered > published_total


def test_coverage_report_rejects_published_exceeding_total():
    with pytest.raises(ValueError):
        CoverageReport(5, 3, 2, 9, 0, {})  # published_total > total


def test_coverage_report_by_category_is_read_only():
    r = coverage_report()
    with pytest.raises(TypeError):
        r.by_category["Bogus"] = (0, 0)  # type: ignore[index]


# --- standards_matrix ------------------------------------------------------

def test_matrix_covers_all_standards():
    rows = standards_matrix()
    assert len(rows) == len(ISO_STANDARDS)
    assert {r["standard_id"] for r in rows} == {s.standard_id for s in ISO_STANDARDS}


def test_matrix_sorted_by_category_then_id():
    rows = standards_matrix()
    keys = [(CATEGORIES.index(r["category"]), r["standard_id"]) for r in rows]
    assert keys == sorted(keys)


def test_matrix_covered_flag_matches_module():
    for row in standards_matrix():
        assert row["covered"] == (row["sdacs_module"] is not None)


def test_matrix_is_deterministic():
    assert standards_matrix() == standards_matrix()


# --- CLI -------------------------------------------------------------------

def test_cli_coverage_runs(capsys):
    from simulation.iso_uas_standards_matrix import main
    rc = main(["--coverage"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "커버리지" in out


def test_cli_matrix_runs(capsys):
    from simulation.iso_uas_standards_matrix import main
    rc = main(["--matrix"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "ISO 21384-1" in out


def test_cli_gaps_runs(capsys):
    from simulation.iso_uas_standards_matrix import main
    rc = main(["--gaps"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "ISO 23665" in out


def test_cli_category_runs(capsys):
    from simulation.iso_uas_standards_matrix import main
    rc = main(["--category", "UTM"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "ISO 23629-5" in out


def test_cli_published_runs(capsys):
    from simulation.iso_uas_standards_matrix import main
    rc = main(["--published"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "ISO 21384-1" in out


def test_cli_default_runs(capsys):
    from simulation.iso_uas_standards_matrix import main
    rc = main([])
    out = capsys.readouterr().out
    assert rc == 0
    assert "커버리지" in out
