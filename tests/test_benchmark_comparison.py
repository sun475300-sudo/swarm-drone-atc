"""ODYSSEY Phase 405 — 국제 벤치마크 비교 단위 테스트."""
from __future__ import annotations

import json
import os

import pytest

from simulation import benchmark_comparison as bc

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# --- 카탈로그 형상 ---------------------------------------------------------

def test_three_tools_present():
    keys = {p.key for p in bc.PROFILES}
    assert keys == {"sdacs", "bluesky", "utrafman"}


def test_tool_keys_matches_profiles():
    """allowlist 상수와 실제 카탈로그가 동기화돼야 한다(무음 누락 방지)."""
    assert set(bc.TOOL_KEYS) == {p.key for p in bc.PROFILES}


def test_tool_keys_sorted():
    assert list(bc.TOOL_KEYS) == sorted(bc.TOOL_KEYS)


def test_simulators_sorted_by_key():
    keys = [p.key for p in bc.simulators()]
    assert keys == sorted(keys)
    assert keys == ["bluesky", "sdacs", "utrafman"]


def test_eight_comparison_dimensions():
    assert len(bc.DIMENSIONS) == 8


def test_dimension_ids_unique():
    ids = [d for d, _ in bc.DIMENSIONS]
    assert len(ids) == len(set(ids))


def test_every_tool_covers_each_dimension_exactly_once():
    dim_ids = {d for d, _ in bc.DIMENSIONS}
    for prof in bc.PROFILES:
        got = [a.dimension for a in prof.attributes]
        assert sorted(got) == sorted(dim_ids), prof.key
        assert len(got) == len(set(got)), f"{prof.key} has duplicate dimensions"


# --- 검증 불변식 -----------------------------------------------------------

def test_attribute_rejects_unknown_dimension():
    with pytest.raises(ValueError):
        bc.ComparisonAttribute("nope", "v", "c")


def test_attribute_rejects_blank_value():
    with pytest.raises(ValueError):
        bc.ComparisonAttribute("domain", "  ", "c")


def test_attribute_rejects_blank_citation():
    with pytest.raises(ValueError):
        bc.ComparisonAttribute("domain", "v", "")


def test_attribute_rejects_blank_evidence():
    with pytest.raises(ValueError):
        bc.ComparisonAttribute("domain", "v", "c", evidence="   ")


def test_attribute_allows_none_evidence():
    a = bc.ComparisonAttribute("domain", "v", "c")
    assert a.evidence is None


def test_profile_rejects_unknown_key():
    with pytest.raises(ValueError):
        bc.SimulatorProfile(
            "bogus", "n", "o", "l", "r", "u",
            tuple(bc.ComparisonAttribute(d, "v", "c") for d, _ in bc.DIMENSIONS),
        )


def test_profile_rejects_blank_field():
    with pytest.raises(ValueError):
        bc.SimulatorProfile(
            "sdacs", "", "o", "l", "r", "u",
            tuple(bc.ComparisonAttribute(d, "v", "c") for d, _ in bc.DIMENSIONS),
        )


def test_profile_rejects_missing_dimension():
    partial = tuple(
        bc.ComparisonAttribute(d, "v", "c") for d, _ in bc.DIMENSIONS[:-1]
    )
    with pytest.raises(ValueError):
        bc.SimulatorProfile("sdacs", "n", "o", "l", "r", "u", partial)


def test_profile_rejects_duplicate_dimension():
    dims = [d for d, _ in bc.DIMENSIONS]
    dims[1] = dims[0]  # 중복 생성
    dup = tuple(bc.ComparisonAttribute(d, "v", "c") for d in dims)
    with pytest.raises(ValueError):
        bc.SimulatorProfile("sdacs", "n", "o", "l", "r", "u", dup)


# --- 조회 API --------------------------------------------------------------

def test_find_simulator_roundtrip():
    for key in bc.TOOL_KEYS:
        assert bc.find_simulator(key).key == key


def test_find_simulator_unknown_raises():
    with pytest.raises(KeyError):
        bc.find_simulator("xplane")


def test_is_subject_only_for_sdacs():
    assert bc.find_simulator("sdacs").is_subject
    assert not bc.find_simulator("bluesky").is_subject
    assert not bc.find_simulator("utrafman").is_subject


def test_dimension_label_roundtrip():
    for dim, label in bc.DIMENSIONS:
        assert bc.dimension_label(dim) == label


def test_dimension_label_unknown_raises():
    with pytest.raises(KeyError):
        bc.dimension_label("nope")


def test_attribute_lookup_unknown_raises():
    with pytest.raises(KeyError):
        bc.find_simulator("sdacs").attribute("nope")


def test_compare_dimension_covers_all_tools():
    m = bc.compare_dimension("conflict_method")
    assert set(m.keys()) == set(bc.TOOL_KEYS)


def test_compare_dimension_unknown_raises():
    with pytest.raises(ValueError):
        bc.compare_dimension("nope")


def test_compare_dimension_is_read_only():
    m = bc.compare_dimension("domain")
    with pytest.raises(TypeError):
        m["sdacs"] = None  # type: ignore[index]


# --- 매트릭스 --------------------------------------------------------------

def test_comparison_matrix_has_one_row_per_dimension():
    rows = bc.comparison_matrix()
    assert len(rows) == len(bc.DIMENSIONS)
    assert [r["dimension"] for r in rows] == [d for d, _ in bc.DIMENSIONS]


def test_comparison_matrix_rows_cover_all_tools():
    for row in bc.comparison_matrix():
        assert set(row["tools"].keys()) == set(bc.TOOL_KEYS)


def test_comparison_matrix_cells_read_only():
    row = bc.comparison_matrix()[0]
    with pytest.raises(TypeError):
        row["tools"]["sdacs"] = None  # type: ignore[index]


def test_comparison_matrix_cell_fields():
    cell = bc.comparison_matrix()[0]["tools"]["sdacs"]
    assert set(cell.keys()) == {"value", "citation", "evidence"}


# --- SDACS 근거(evidence) 정직성 ------------------------------------------

def test_sdacs_evidence_exists_on_disk():
    """SDACS 가 인용한 모든 근거 경로는 디스크에 실재해야 한다."""
    for path in bc.cited_evidence_paths():
        full = os.path.join(REPO_ROOT, path)
        assert os.path.exists(full), f"missing evidence path: {path}"


def test_only_sdacs_has_evidence():
    """외부 도구(BlueSky·U-TRAFMAN)는 검증 불가하므로 evidence 가 없어야 한다."""
    for prof in bc.PROFILES:
        if prof.is_subject:
            continue
        for attr in prof.attributes:
            assert attr.evidence is None, f"{prof.key}/{attr.dimension}"


def test_sdacs_evidence_covers_capability_axes():
    """능력 축(충돌·교통·군집·기상·연합·재현)은 디스크 근거를 보유해야 한다."""
    ev = bc.sdacs_evidence()
    for dim in (
        "conflict_method", "traffic_model", "swarm_support",
        "weather_model", "federation", "reproducibility",
    ):
        assert ev[dim] is not None, dim


def test_sdacs_evidence_read_only():
    ev = bc.sdacs_evidence()
    with pytest.raises(TypeError):
        ev["domain"] = "x"  # type: ignore[index]


def test_cited_evidence_paths_sorted_unique():
    paths = bc.cited_evidence_paths()
    assert list(paths) == sorted(set(paths))


# --- EvidenceReport --------------------------------------------------------

def test_evidence_report_counts_consistent():
    r = bc.evidence_report()
    assert r.with_evidence + r.without_evidence == r.total_dimensions
    assert r.total_dimensions == len(bc.DIMENSIONS)


def test_evidence_report_pct():
    r = bc.evidence_report()
    expected = 100.0 * r.with_evidence / r.total_dimensions
    assert r.evidence_pct == pytest.approx(expected)


def test_evidence_report_rejects_inconsistent_counts():
    with pytest.raises(ValueError):
        bc.EvidenceReport(total_dimensions=8, with_evidence=5, without_evidence=2)


def test_evidence_report_rejects_negative():
    with pytest.raises(ValueError):
        bc.EvidenceReport(total_dimensions=1, with_evidence=-1, without_evidence=2)


# --- 제출 매니페스트 -------------------------------------------------------

def test_submission_manifest_is_json_serializable():
    manifest = bc.submission_manifest()
    dumped = json.dumps(manifest, ensure_ascii=False)
    assert isinstance(dumped, str)


def test_submission_manifest_identity():
    manifest = bc.submission_manifest()
    assert manifest["submission_id"] == bc.SUBMISSION_ID
    assert manifest["version"] == bc.SUBMISSION_VERSION
    assert manifest["subject"] == "sdacs"


def test_submission_manifest_comparators_exclude_subject():
    """제출 매니페스트의 comparators 는 비교 대상만 담고 주체(SDACS)는 제외한다."""
    manifest = bc.submission_manifest()
    keys = {c["key"] for c in manifest["comparators"]}
    assert keys == {"bluesky", "utrafman"}
    assert manifest["subject"] not in keys


def test_submission_manifest_references_sbs10_suite():
    manifest = bc.submission_manifest()
    assert manifest["benchmark_suite"]["suite_id"] == "SDACS-SBS-10"
    assert manifest["benchmark_suite"]["count"] == 10


def test_submission_manifest_matrix_full():
    manifest = bc.submission_manifest()
    assert len(manifest["comparison_matrix"]) == len(bc.DIMENSIONS)


def test_submission_manifest_evidence_coverage():
    manifest = bc.submission_manifest()
    cov = manifest["sdacs_evidence_coverage"]
    assert cov["total_dimensions"] == len(bc.DIMENSIONS)
    assert 0 <= cov["with_evidence"] <= cov["total_dimensions"]


# --- 내용 정직성 -----------------------------------------------------------

def test_external_tools_are_gpl_open_source():
    for key in ("bluesky", "utrafman"):
        prof = bc.find_simulator(key)
        assert "GPL" in prof.license


def test_all_attributes_have_citation():
    for prof in bc.PROFILES:
        for attr in prof.attributes:
            assert attr.citation.strip()


# --- CLI -------------------------------------------------------------------

def test_cli_matrix_runs():
    assert bc.main(["--matrix"]) == 0


def test_cli_tool_runs():
    assert bc.main(["--tool", "sdacs"]) == 0


def test_cli_dimension_runs():
    assert bc.main(["--dimension", "federation"]) == 0


def test_cli_evidence_runs():
    assert bc.main(["--evidence"]) == 0


def test_cli_submission_runs(capsys):
    assert bc.main(["--submission"]) == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["submission_id"] == bc.SUBMISSION_ID


def test_cli_default_runs():
    assert bc.main([]) == 0
