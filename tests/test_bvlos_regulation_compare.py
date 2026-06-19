"""ODYSSEY Phase 409 — 다국 BVLOS 규제 비교 단위 테스트."""
from __future__ import annotations

import os

import pytest

from simulation import bvlos_regulation_compare as brc

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# --- 카탈로그 형상 ---------------------------------------------------------

def test_four_jurisdictions_present():
    codes = {reg.code for reg in brc.REGULATIONS}
    assert codes == {"KR", "US", "EU", "JP"}


def test_jurisdiction_codes_matches_regulations():
    """allowlist 상수와 실제 카탈로그가 동기화돼야 한다(무음 누락 방지)."""
    assert set(brc.JURISDICTION_CODES) == {r.code for r in brc.REGULATIONS}


def test_jurisdictions_sorted_by_code():
    codes = [reg.code for reg in brc.jurisdictions()]
    assert codes == sorted(codes)
    assert codes == ["EU", "JP", "KR", "US"]


def test_every_jurisdiction_covers_each_dimension_exactly_once():
    dim_ids = {d for d, _ in brc.DIMENSIONS}
    for reg in brc.REGULATIONS:
        got = [r.dimension for r in reg.requirements]
        assert sorted(got) == sorted(dim_ids), reg.code
        assert len(got) == len(set(got)), f"{reg.code} has duplicate dimensions"


def test_six_comparison_dimensions():
    assert len(brc.DIMENSIONS) == 6
    ids = [d for d, _ in brc.DIMENSIONS]
    assert len(ids) == len(set(ids))


# --- 조회 API --------------------------------------------------------------

def test_find_jurisdiction_returns_matching():
    reg = brc.find_jurisdiction("KR")
    assert reg.name == "대한민국"
    assert reg.authority == "국토교통부(MOLIT)"


def test_find_jurisdiction_unknown_raises():
    with pytest.raises(KeyError):
        brc.find_jurisdiction("CN")


def test_requirement_lookup_by_dimension():
    reg = brc.find_jurisdiction("US")
    req = reg.requirement("remote_id")
    assert "Remote ID" in req.value
    assert "Part 89" in req.citation


def test_requirement_unknown_dimension_raises():
    reg = brc.find_jurisdiction("EU")
    with pytest.raises(KeyError):
        reg.requirement("nonexistent")


def test_dimension_label_lookup():
    assert brc.dimension_label("remote_id") == "Remote ID(원격 식별) 요건"


def test_dimension_label_unknown_raises():
    with pytest.raises(KeyError):
        brc.dimension_label("nope")


# --- 축별 대조 -------------------------------------------------------------

def test_compare_dimension_covers_all_jurisdictions():
    mapping = brc.compare_dimension("pilot_competency")
    assert set(mapping) == {"EU", "JP", "KR", "US"}
    for req in mapping.values():
        assert req.dimension == "pilot_competency"


def test_compare_dimension_unknown_raises():
    with pytest.raises(ValueError):
        brc.compare_dimension("unknown_axis")


def test_compare_dimension_returns_readonly_mapping():
    mapping = brc.compare_dimension("remote_id")
    with pytest.raises(TypeError):
        mapping["KR"] = mapping["US"]  # type: ignore[index]


# --- 매트릭스 (도구 간 교환) -----------------------------------------------

def test_comparison_matrix_one_row_per_dimension():
    matrix = brc.comparison_matrix()
    assert len(matrix) == len(brc.DIMENSIONS)
    dims = [row["dimension"] for row in matrix]
    assert dims == [d for d, _ in brc.DIMENSIONS]  # 축 순서 보존


def test_comparison_matrix_each_cell_has_value_and_citation():
    for row in brc.comparison_matrix():
        cells = row["jurisdictions"]
        assert set(cells) == {"EU", "JP", "KR", "US"}
        for code, cell in cells.items():
            assert cell["value"].strip()
            assert cell["citation"].strip()


def test_comparison_matrix_is_deterministic():
    assert brc.comparison_matrix() == brc.comparison_matrix()


def test_comparison_matrix_cells_are_readonly():
    """하류 소비자가 셀을 변조할 수 없어야 한다(공유 상태 보호)."""
    row = brc.comparison_matrix()[0]
    with pytest.raises(TypeError):
        row["jurisdictions"]["KR"] = {"value": "x", "citation": "y"}  # type: ignore[index]


# --- SDACS 지원 커버리지 + 정직성 -----------------------------------------

def test_support_report_counts_consistent():
    r = brc.support_report()
    assert r.total == 4
    assert r.supported + r.gaps == r.total
    # KR·US·EU 지원, JP 갭 → 3/4.
    assert r.supported == 3
    assert r.gaps == 1


def test_support_pct():
    assert brc.support_report().support_pct == pytest.approx(75.0)


def test_jp_is_documented_gap():
    assert brc.find_jurisdiction("JP").sdacs_support is None
    assert brc.find_jurisdiction("JP").is_supported is False


def test_cited_sdacs_modules_exist_on_disk():
    """정직성 강제: 인용된 SDACS 지원 모듈이 실제로 존재해야 한다."""
    for path in brc.cited_sdacs_modules():
        full = os.path.join(REPO_ROOT, path)
        assert os.path.isfile(full), f"cited SDACS module missing: {path}"


def test_every_requirement_has_nonempty_citation():
    for reg in brc.REGULATIONS:
        for req in reg.requirements:
            assert req.citation.strip(), f"{reg.code}/{req.dimension} citation empty"


def test_every_jurisdiction_has_as_of_snapshot():
    for reg in brc.REGULATIONS:
        year, month = reg.as_of.split("-")
        assert year.isdigit() and month.isdigit()
        assert 1 <= int(month) <= 12


# --- 불변식 검증 (생성자) --------------------------------------------------

def test_requirement_rejects_unknown_dimension():
    with pytest.raises(ValueError):
        brc.BvlosRequirement("bogus", "v", "c")


def test_requirement_rejects_empty_value():
    with pytest.raises(ValueError):
        brc.BvlosRequirement("remote_id", "   ", "c")


def test_requirement_rejects_empty_citation():
    with pytest.raises(ValueError):
        brc.BvlosRequirement("remote_id", "v", "")


def test_jurisdiction_rejects_unknown_code():
    with pytest.raises(ValueError):
        brc.JurisdictionRegulation(
            "ZZ", "n", "f", "a", "2026-06",
            tuple(brc.BvlosRequirement(d, "v", "c") for d, _ in brc.DIMENSIONS),
            None,
        )


def test_jurisdiction_rejects_bad_as_of():
    with pytest.raises(ValueError):
        brc.JurisdictionRegulation(
            "KR", "n", "f", "a", "June 2026",
            tuple(brc.BvlosRequirement(d, "v", "c") for d, _ in brc.DIMENSIONS),
            None,
        )


@pytest.mark.parametrize("bad", ["2026-13", "2026-00", "2026-99"])
def test_jurisdiction_rejects_out_of_range_month(bad):
    full = tuple(brc.BvlosRequirement(d, "v", "c") for d, _ in brc.DIMENSIONS)
    with pytest.raises(ValueError):
        brc.JurisdictionRegulation("KR", "n", "f", "a", bad, full, None)


def test_jurisdiction_rejects_missing_dimension():
    partial = tuple(
        brc.BvlosRequirement(d, "v", "c")
        for d, _ in brc.DIMENSIONS[:-1]  # 한 축 누락
    )
    with pytest.raises(ValueError):
        brc.JurisdictionRegulation("KR", "n", "f", "a", "2026-06", partial, None)


def test_jurisdiction_rejects_duplicate_dimension():
    dims = [d for d, _ in brc.DIMENSIONS]
    dup = tuple(
        brc.BvlosRequirement(d, "v", "c")
        for d in dims[:-1] + [dims[0]]  # 마지막을 첫 축으로 중복
    )
    with pytest.raises(ValueError):
        brc.JurisdictionRegulation("KR", "n", "f", "a", "2026-06", dup, None)


def test_jurisdiction_rejects_empty_sdacs_support():
    full = tuple(brc.BvlosRequirement(d, "v", "c") for d, _ in brc.DIMENSIONS)
    with pytest.raises(ValueError):
        brc.JurisdictionRegulation("KR", "n", "f", "a", "2026-06", full, "   ")


def test_support_report_rejects_inconsistent_counts():
    with pytest.raises(ValueError):
        brc.SupportReport(total=4, supported=3, gaps=2)


# --- CLI -------------------------------------------------------------------

def test_cli_matrix_runs(capsys):
    assert brc.main(["--matrix"]) == 0
    out = capsys.readouterr().out
    assert "BVLOS" in out
    assert "EU" in out and "JP" in out


def test_cli_jurisdiction_runs(capsys):
    assert brc.main(["--jurisdiction", "JP"]) == 0
    out = capsys.readouterr().out
    assert "일본" in out


def test_cli_dimension_runs(capsys):
    assert brc.main(["--dimension", "remote_id"]) == 0
    out = capsys.readouterr().out
    assert "Remote ID" in out


def test_cli_support_default(capsys):
    assert brc.main([]) == 0
    out = capsys.readouterr().out
    assert "3/4" in out
