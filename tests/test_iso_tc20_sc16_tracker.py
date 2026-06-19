"""ODYSSEY Phase 462 — ISO/TC 20/SC 16 (UAS) 표준 추적 매트릭스 단위 테스트."""
from __future__ import annotations

import os

import pytest

from simulation.iso_tc20_sc16_tracker import (
    AS_OF,
    CATEGORIES,
    ISO_STANDARDS,
    STATUSES,
    ISOStandard,
    TrackingReport,
    aligned_standards,
    find_standard,
    gaps,
    published_standards,
    standards_by_category,
    standards_by_series,
    tracking_matrix,
    tracking_report,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# --- ISOStandard 검증 -----------------------------------------------------

def test_standard_rejects_empty_id():
    with pytest.raises(ValueError):
        ISOStandard("", "T", "ISO 21384", "Operational Procedures", "published", None, "s")


def test_standard_rejects_padded_id():
    with pytest.raises(ValueError):
        ISOStandard(" ISO 1 ", "T", "ISO 1", "Operational Procedures", "published", None, "s")


def test_standard_rejects_empty_title():
    with pytest.raises(ValueError):
        ISOStandard("ISO 1", "  ", "ISO 1", "Operational Procedures", "published", None, "s")


def test_standard_rejects_id_not_starting_with_series():
    with pytest.raises(ValueError):
        ISOStandard("ISO 99", "T", "ISO 21384", "Operational Procedures", "published", None, "s")


def test_standard_rejects_series_prefix_without_separator():
    # 'ISO 21' 은 'ISO 218' 의 bare 접두지만 구분자가 없으므로 거부돼야 한다.
    with pytest.raises(ValueError):
        ISOStandard("ISO 218", "T", "ISO 21", "Operational Procedures", "published", None, "s")


def test_standard_rejects_padded_series():
    with pytest.raises(ValueError):
        ISOStandard("ISO 1", "T", " ISO 1", "Operational Procedures", "published", None, "s")


def test_standard_rejects_empty_series():
    with pytest.raises(ValueError):
        ISOStandard("ISO 1", "T", "", "Operational Procedures", "published", None, "s")


def test_standard_rejects_unknown_category():
    with pytest.raises(ValueError):
        ISOStandard("ISO 1", "T", "ISO 1", "No Such", "published", None, "s")


def test_standard_rejects_unknown_status():
    with pytest.raises(ValueError):
        ISOStandard("ISO 1", "T", "ISO 1", "Operational Procedures", "withdrawn", None, "s")


def test_standard_rejects_blank_module_path():
    with pytest.raises(ValueError):
        ISOStandard("ISO 1", "T", "ISO 1", "Operational Procedures", "published", "  ", "s")


def test_standard_rejects_empty_summary():
    with pytest.raises(ValueError):
        ISOStandard("ISO 1", "T", "ISO 1", "Operational Procedures", "published", None, " ")


def test_is_aligned_reflects_module_presence():
    mapped = ISOStandard("ISO 1", "T", "ISO 1", "Operational Procedures",
                         "published", "simulation/compliance_checker.py", "s")
    gap = ISOStandard("ISO 2", "T", "ISO 2", "General & Vocabulary",
                      "under_development", None, "s")
    assert mapped.is_aligned is True
    assert gap.is_aligned is False


def test_is_published_reflects_status():
    pub = ISOStandard("ISO 1", "T", "ISO 1", "Operational Procedures", "published", None, "s")
    dev = ISOStandard("ISO 2", "T", "ISO 2", "UAS Components", "under_development", None, "s")
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


def test_all_ids_start_with_series():
    assert all(s.standard_id.startswith(s.series) for s in ISO_STANDARDS)


def test_as_of_snapshot_format():
    # YYYY-MM 스냅샷 형식 (연-월).
    year, _, month = AS_OF.partition("-")
    assert year.isdigit() and len(year) == 4
    assert month.isdigit() and 1 <= int(month) <= 12


def test_cited_modules_exist_on_disk():
    """매핑이 인용하는 모든 SDACS 모듈 경로는 리포에 실재해야 한다 (정직성)."""
    for std in ISO_STANDARDS:
        if std.sdacs_module is not None:
            full = os.path.join(REPO_ROOT, std.sdacs_module)
            assert os.path.isfile(full), (
                f"{std.standard_id} cites missing {std.sdacs_module}"
            )


def test_gap_iff_module_none():
    """정직성 결속: 갭 ⟺ sdacs_module is None."""
    for std in ISO_STANDARDS:
        assert (std.sdacs_module is None) == (not std.is_aligned)


# --- 조회 API -------------------------------------------------------------

def test_find_standard_returns_match():
    std = find_standard("ISO 21384-3")
    assert std.category == "Operational Procedures"
    assert std.is_published


def test_find_standard_unknown_raises():
    with pytest.raises(KeyError):
        find_standard("ISO 00000")


def test_standards_by_category_sorted():
    members = standards_by_category("UTM / Traffic Management")
    ids = [s.standard_id for s in members]
    assert ids == sorted(ids)
    assert all(s.category == "UTM / Traffic Management" for s in members)


def test_standards_by_category_rejects_unknown():
    with pytest.raises(ValueError):
        standards_by_category("Nope")


def test_standards_by_series_groups():
    members = standards_by_series("ISO 21384")
    assert {s.standard_id for s in members} == {
        "ISO 21384-1", "ISO 21384-2", "ISO 21384-3", "ISO 21384-4",
    }
    ids = [s.standard_id for s in members]
    assert ids == sorted(ids)


def test_standards_by_series_unknown_returns_empty():
    assert standards_by_series("ISO 00000") == ()


def test_gaps_and_aligned_partition_catalog():
    gap_ids = {s.standard_id for s in gaps()}
    aligned_ids = {s.standard_id for s in aligned_standards()}
    all_ids = {s.standard_id for s in ISO_STANDARDS}
    assert gap_ids.isdisjoint(aligned_ids)
    assert gap_ids | aligned_ids == all_ids


def test_published_standards_all_published():
    assert all(s.is_published for s in published_standards())


def test_gaps_sorted():
    ids = [s.standard_id for s in gaps()]
    assert ids == sorted(ids)


# --- TrackingReport -------------------------------------------------------

def test_report_counts_consistent():
    r = tracking_report()
    assert r.published + r.under_development == r.total
    assert r.aligned + r.gaps == r.total
    assert r.total == len(ISO_STANDARDS)


def test_report_alignment_pct_matches_counts():
    r = tracking_report()
    expected = 100.0 * r.aligned / r.total
    assert r.alignment_pct == pytest.approx(expected)


def test_report_by_category_sums_to_total():
    r = tracking_report()
    total_from_categories = sum(tot for _, tot in r.by_category.values())
    assert total_from_categories == r.total


def test_report_by_category_is_read_only():
    r = tracking_report()
    with pytest.raises(TypeError):
        r.by_category["UAS Components"] = (1, 1)  # type: ignore[index]


def test_report_rejects_inconsistent_status_split():
    with pytest.raises(ValueError):
        TrackingReport(total=8, published=5, under_development=2, aligned=4, gaps=4,
                       by_category={})


def test_report_rejects_inconsistent_alignment_split():
    with pytest.raises(ValueError):
        TrackingReport(total=8, published=6, under_development=2, aligned=5, gaps=4,
                       by_category={})


def test_report_rejects_negative_counts():
    with pytest.raises(ValueError):
        TrackingReport(total=-1, published=0, under_development=0, aligned=0, gaps=0,
                       by_category={})


def test_report_wraps_plain_dict_by_category_read_only():
    # 직접 생성 시 plain dict 도 MappingProxyType 로 동결돼야 한다 (불변 보장).
    r = TrackingReport(total=2, published=2, under_development=0, aligned=1, gaps=1,
                       by_category={"Operational Procedures": (1, 1),
                                    "UAS Components": (0, 1)})
    with pytest.raises(TypeError):
        r.by_category["UAS Components"] = (1, 1)  # type: ignore[index]


def test_report_rejects_by_category_sum_mismatch():
    # by_category 합이 상위 집계와 어긋나면 거부돼야 한다.
    with pytest.raises(ValueError):
        TrackingReport(total=2, published=2, under_development=0, aligned=1, gaps=1,
                       by_category={"Operational Procedures": (1, 1)})


# --- tracking_matrix ------------------------------------------------------

def test_matrix_rows_read_only():
    rows = tracking_matrix()
    with pytest.raises(TypeError):
        rows[0]["standard_id"] = "X"  # type: ignore[index]


def test_matrix_covers_all_standards():
    ids = {row["standard_id"] for row in tracking_matrix()}
    assert ids == {s.standard_id for s in ISO_STANDARDS}


def test_matrix_ordered_by_category_then_id():
    rows = tracking_matrix()
    keys = [(CATEGORIES.index(row["category"]), row["standard_id"]) for row in rows]
    assert keys == sorted(keys)


def test_matrix_aligned_flag_matches_module():
    for row in tracking_matrix():
        assert row["aligned"] == (row["sdacs_module"] is not None)


# --- 결정성 ---------------------------------------------------------------

def test_report_is_deterministic():
    a, b = tracking_report(), tracking_report()
    assert (a.total, a.published, a.aligned, a.gaps) == (b.total, b.published, b.aligned, b.gaps)


def test_matrix_is_deterministic():
    assert tracking_matrix() == tracking_matrix()
