"""ODYSSEY Phase 462 — ISO/TC 20/SC 16 (UAS) 표준 동향 추적 매트릭스 단위 테스트."""
from __future__ import annotations

import os

import pytest

from simulation.iso_tc20_sc16_tracker import (
    ALIGNMENTS,
    ISO_STANDARDS,
    STAGES,
    IsoStandard,
    TrackerReport,
    find_standard,
    gaps,
    main,
    published_standards,
    standards_by_series,
    standards_by_stage,
    tracker_report,
    tracking_matrix,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _std(**kw) -> IsoStandard:
    """발행·정렬 기본값으로 IsoStandard 를 만든다 (테스트 편의)."""
    defaults = dict(
        standard_id="ISO-23629-5",
        designation="ISO 23629-5:2023",
        title="t",
        series="23629",
        stage="PUBLISHED",
        alignment="aligned",
        sdacs_module="simulation/remote_id.py",
        summary="s",
    )
    defaults.update(kw)
    return IsoStandard(**defaults)  # type: ignore[arg-type]


# --- IsoStandard 검증 ------------------------------------------------------

def test_standard_rejects_empty_id():
    with pytest.raises(ValueError):
        _std(standard_id="")


def test_standard_rejects_padded_id():
    with pytest.raises(ValueError):
        _std(standard_id=" ISO-1 ")


def test_standard_rejects_internal_space_id():
    with pytest.raises(ValueError):
        _std(standard_id="ISO 1")


def test_standard_rejects_empty_title():
    with pytest.raises(ValueError):
        _std(title="  ")


def test_standard_rejects_empty_summary():
    with pytest.raises(ValueError):
        _std(summary="")


def test_standard_rejects_empty_designation():
    with pytest.raises(ValueError):
        _std(designation="  ")


def test_standard_rejects_non_digit_series():
    with pytest.raises(ValueError):
        _std(series="abc")


def test_standard_rejects_designation_missing_series():
    # designation 이 series 번호를 참조하지 않으면 거부.
    with pytest.raises(ValueError):
        _std(series="21384", designation="ISO 99999:2023")


def test_standard_rejects_unknown_stage():
    with pytest.raises(ValueError):
        _std(stage="MAYBE")


def test_standard_rejects_unknown_alignment():
    with pytest.raises(ValueError):
        _std(alignment="kinda")


def test_published_requires_year_in_designation():
    # 발행 표준은 :YYYY 발행 연도를 명시해야 한다.
    with pytest.raises(ValueError):
        _std(stage="PUBLISHED", designation="ISO 23629-5")


def test_under_development_allows_no_year():
    std = _std(
        stage="UNDER_DEVELOPMENT",
        designation="ISO/DIS 23629-5",
        alignment="none",
        sdacs_module=None,
    )
    assert not std.is_published


# --- 정직성 결속 (none ⟺ 모듈 없음) ---------------------------------------

def test_none_alignment_must_not_cite_module():
    with pytest.raises(ValueError):
        _std(alignment="none", sdacs_module="simulation/remote_id.py")


def test_aligned_must_cite_module():
    with pytest.raises(ValueError):
        _std(alignment="aligned", sdacs_module=None)


def test_partial_must_cite_module():
    with pytest.raises(ValueError):
        _std(alignment="partial", sdacs_module=None)


def test_aligned_rejects_blank_module():
    with pytest.raises(ValueError):
        _std(alignment="aligned", sdacs_module="   ")


def test_none_alignment_with_none_module_ok():
    std = _std(alignment="none", sdacs_module=None)
    assert std.is_unaligned


# --- 속성 ------------------------------------------------------------------

def test_is_published_property():
    assert _std(stage="PUBLISHED").is_published
    assert not _std(
        stage="UNDER_DEVELOPMENT", designation="ISO/CD 23629-5",
        alignment="none", sdacs_module=None,
    ).is_published


def test_weight_values():
    assert _std(alignment="aligned").weight == 1.0
    assert _std(alignment="partial").weight == 0.5
    assert _std(alignment="none", sdacs_module=None).weight == 0.0


# --- 레지스트리 정합성 -----------------------------------------------------

def test_registry_non_empty():
    assert len(ISO_STANDARDS) >= 9


def test_registry_ids_unique():
    ids = [s.standard_id for s in ISO_STANDARDS]
    assert len(ids) == len(set(ids))


def test_registry_stages_valid():
    for std in ISO_STANDARDS:
        assert std.stage in STAGES


def test_registry_alignments_valid():
    for std in ISO_STANDARDS:
        assert std.alignment in ALIGNMENTS


def test_cited_sdacs_modules_exist_on_disk():
    """정렬(aligned/partial)이 인용한 SDACS 모듈은 디스크에 실재해야 한다."""
    for std in ISO_STANDARDS:
        if std.sdacs_module is not None:
            path = os.path.join(REPO_ROOT, std.sdacs_module)
            assert os.path.isfile(path), f"{std.standard_id} cites missing {std.sdacs_module}"


def test_none_alignment_has_no_module_in_registry():
    for std in ISO_STANDARDS:
        if std.alignment == "none":
            assert std.sdacs_module is None


def test_published_designations_carry_year():
    for std in ISO_STANDARDS:
        if std.is_published:
            assert ":" in std.designation


# --- 조회 API --------------------------------------------------------------

def test_find_standard_found():
    std = find_standard("ISO-23629-8")
    assert std.designation == "ISO 23629-8:2023"
    assert std.alignment == "aligned"


def test_find_standard_unknown_raises():
    with pytest.raises(KeyError):
        find_standard("ISO-00000")


def test_standards_by_series_23629():
    series = standards_by_series("23629")
    assert len(series) == 5
    assert all(s.series == "23629" for s in series)
    # 식별자 정렬 보장
    assert list(series) == sorted(series, key=lambda s: s.standard_id)


def test_standards_by_series_21384():
    series = standards_by_series("21384")
    assert len(series) == 4


def test_standards_by_series_unknown_empty():
    assert standards_by_series("99999") == ()


def test_standards_by_stage_published():
    pub = standards_by_stage("PUBLISHED")
    assert all(s.stage == "PUBLISHED" for s in pub)
    assert len(pub) == 7


def test_standards_by_stage_invalid_raises():
    with pytest.raises(ValueError):
        standards_by_stage("DRAFT")


def test_published_standards_matches_stage():
    assert published_standards() == standards_by_stage("PUBLISHED")


def test_gaps_are_all_unaligned():
    g = gaps()
    assert all(s.is_unaligned for s in g)
    assert len(g) >= 1


# --- 리포트 ----------------------------------------------------------------

def test_report_counts_partition_by_stage():
    r = tracker_report()
    assert r.published + r.under_development + r.withdrawn == r.total


def test_report_counts_partition_by_alignment():
    r = tracker_report()
    assert r.aligned + r.partial + r.none == r.total


def test_report_total_matches_registry():
    assert tracker_report().total == len(ISO_STANDARDS)


def test_report_by_series_sums_to_total():
    r = tracker_report()
    assert sum(r.by_series.values()) == r.total


def test_report_by_series_is_read_only():
    r = tracker_report()
    with pytest.raises(TypeError):
        r.by_series["23629"] = 99  # type: ignore[index]


def test_alignment_score_in_range():
    r = tracker_report()
    assert 0.0 <= r.alignment_score_pct <= 100.0


def test_published_pct_in_range():
    r = tracker_report()
    assert 0.0 <= r.published_pct <= 100.0


def test_report_rejects_inconsistent_stage_counts():
    with pytest.raises(ValueError):
        TrackerReport(
            total=2, published=2, under_development=0, withdrawn=1,
            aligned=2, partial=0, none=0, by_series={},
        )


def test_report_rejects_inconsistent_alignment_counts():
    with pytest.raises(ValueError):
        TrackerReport(
            total=2, published=2, under_development=0, withdrawn=0,
            aligned=2, partial=1, none=0, by_series={},
        )


def test_report_rejects_negative_counts():
    with pytest.raises(ValueError):
        TrackerReport(
            total=1, published=-1, under_development=2, withdrawn=0,
            aligned=1, partial=0, none=0, by_series={},
        )


def test_report_rejects_by_series_mismatch():
    with pytest.raises(ValueError):
        TrackerReport(
            total=2, published=2, under_development=0, withdrawn=0,
            aligned=2, partial=0, none=0, by_series={"23629": 1},
        )


def test_report_freezes_plain_by_series():
    # 직접 생성 시 평범한 dict 도 읽기 전용으로 동결돼야 한다.
    r = TrackerReport(
        total=1, published=1, under_development=0, withdrawn=0,
        aligned=1, partial=0, none=0, by_series={"23629": 1},
    )
    with pytest.raises(TypeError):
        r.by_series["x"] = 1  # type: ignore[index]


def test_empty_report_scores_zero():
    r = TrackerReport(
        total=0, published=0, under_development=0, withdrawn=0,
        aligned=0, partial=0, none=0, by_series={},
    )
    assert r.alignment_score_pct == 0.0
    assert r.published_pct == 0.0


# --- 매트릭스 --------------------------------------------------------------

def test_tracking_matrix_row_count():
    assert len(tracking_matrix()) == len(ISO_STANDARDS)


def test_tracking_matrix_sorted_by_series_then_id():
    rows = tracking_matrix()
    keys = [(r["series"], r["standard_id"]) for r in rows]
    assert keys == sorted(keys)


def test_tracking_matrix_keys():
    row = tracking_matrix()[0]
    assert set(row) == {
        "standard_id", "designation", "title", "series",
        "stage", "alignment", "sdacs_module",
    }


# --- CLI -------------------------------------------------------------------

def test_cli_report_default(capsys):
    assert main([]) == 0
    out = capsys.readouterr().out
    assert "표준 동향" in out


def test_cli_matrix(capsys):
    assert main(["--matrix"]) == 0
    assert "매트릭스" in capsys.readouterr().out


def test_cli_series(capsys):
    assert main(["--series", "23629"]) == 0
    out = capsys.readouterr().out
    assert "ISO 23629-8:2023" in out


def test_cli_published(capsys):
    assert main(["--published"]) == 0
    out = capsys.readouterr().out
    assert "ISO 21384-3:2023" in out


def test_cli_gaps(capsys):
    assert main(["--gaps"]) == 0
    out = capsys.readouterr().out
    assert "갭" in out or "미정렬" in out
