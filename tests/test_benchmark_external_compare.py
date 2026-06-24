"""ODYSSEY Phase 405 — BlueSky·U-TRAFMAN 벤치마크 구조 비교 단위 테스트."""
from __future__ import annotations

import dataclasses

import pytest

from simulation import benchmark_external_compare as bec
from simulation.standard_scenarios import BENCHMARK_SET


# --- 카탈로그 형상 ---------------------------------------------------------

def test_two_tools_present():
    assert bec.TOOLS == ("bluesky", "u_trafman")


def test_ten_comparisons_in_order():
    ids = [c.benchmark_id for c in bec.all_comparisons()]
    assert ids == [f"B{n:02d}" for n in range(1, 11)]


def test_benchmark_ids_match_sbs10():
    """SSoT 결속 — 비교 식별자·축이 Phase 465 SBS-10 과 정확히 일치해야 한다."""
    sbs10 = {b.benchmark_id: b.axis for b in BENCHMARK_SET}
    got = {c.benchmark_id for c in bec.all_comparisons()}
    assert got == set(sbs10)
    # 축은 SBS-10 이 유일 출처 — 본 모듈은 복제하지 않고 참조만 한다.
    for row in bec.comparison_matrix():
        assert row["axis"] == sbs10[row["benchmark_id"]]


def test_each_comparison_covers_both_tools_exactly_once():
    for comp in bec.all_comparisons():
        tools = [a.tool for a in comp.analogs]
        assert sorted(tools) == sorted(bec.TOOLS), comp.benchmark_id
        assert len(tools) == len(set(tools)), f"{comp.benchmark_id} 도구 중복"


# --- 정직성 결속 -----------------------------------------------------------

def test_none_status_binds_to_none_analog():
    """status=='none' ⟺ analog is None — 없는 대응을 있다고 주장 불가."""
    for comp in bec.all_comparisons():
        for analog in comp.analogs:
            if analog.status == "none":
                assert analog.analog is None, comp.benchmark_id
            else:
                assert analog.analog and analog.analog.strip(), comp.benchmark_id


def test_none_analog_with_nonempty_string_rejected():
    with pytest.raises(ValueError):
        bec.ToolAnalog("bluesky", "none", "있다고 거짓 주장", "n", "c")


def test_direct_status_requires_analog():
    with pytest.raises(ValueError):
        bec.ToolAnalog("bluesky", "direct", None, "n", "c")
    with pytest.raises(ValueError):
        bec.ToolAnalog("bluesky", "partial", "   ", "n", "c")


def test_unknown_tool_rejected():
    with pytest.raises(ValueError):
        bec.ToolAnalog("foobar", "direct", "x", "n", "c")


def test_unknown_status_rejected():
    with pytest.raises(ValueError):
        bec.ToolAnalog("bluesky", "maybe", "x", "n", "c")


def test_blank_note_and_citation_rejected():
    with pytest.raises(ValueError):
        bec.ToolAnalog("bluesky", "direct", "x", "  ", "c")
    with pytest.raises(ValueError):
        bec.ToolAnalog("bluesky", "direct", "x", "n", "  ")


def test_every_analog_has_citation():
    for comp in bec.all_comparisons():
        for analog in comp.analogs:
            assert analog.citation.strip()


# --- SSoT 위반 거부 --------------------------------------------------------

def test_unknown_benchmark_id_rejected_at_construction():
    a = bec.ToolAnalog("bluesky", "direct", "x", "n", "c")
    b = bec.ToolAnalog("u_trafman", "direct", "y", "n", "c")
    with pytest.raises(KeyError):
        bec.ScenarioComparison("B99", (a, b))


def test_missing_tool_rejected():
    a = bec.ToolAnalog("bluesky", "direct", "x", "n", "c")
    with pytest.raises(ValueError):
        bec.ScenarioComparison("B01", (a,))


def test_duplicate_tool_rejected():
    a = bec.ToolAnalog("bluesky", "direct", "x", "n", "c")
    b = bec.ToolAnalog("bluesky", "partial", "y", "n", "c")
    with pytest.raises(ValueError):
        bec.ScenarioComparison("B01", (a, b))


# --- 조회 API --------------------------------------------------------------

def test_get_comparison_roundtrip():
    comp = bec.get_comparison("B04")
    assert comp.benchmark_id == "B04"
    assert comp.for_tool("bluesky").status == "direct"


def test_get_comparison_unknown_raises():
    with pytest.raises(KeyError):
        bec.get_comparison("Z00")


def test_for_tool_unknown_raises():
    comp = bec.get_comparison("B01")
    with pytest.raises(KeyError):
        comp.for_tool("nope")


# --- 비교 가능성 집계 ------------------------------------------------------

def test_comparability_report_counts_sum_to_total():
    for tool in bec.TOOLS:
        rep = bec.comparability_report(tool)
        assert rep["direct"] + rep["partial"] + rep["none"] == rep["total"] == 10


def test_comparability_score_matches_weights():
    """점수 = (direct*1.0 + partial*0.5) / total, 결정적."""
    for tool in bec.TOOLS:
        rep = bec.comparability_report(tool)
        expected = round((rep["direct"] * 1.0 + rep["partial"] * 0.5) / rep["total"], 4)
        assert rep["score"] == expected


def test_comparability_report_exact_values():
    """정직한 구조적 비교 가능성 점수 회귀 고정(외부 도구가 SDACS 축을 초과 표현 못 함)."""
    bs = bec.comparability_report("bluesky")
    assert (bs["direct"], bs["partial"], bs["none"], bs["score"]) == (4, 2, 4, 0.5)
    ut = bec.comparability_report("u_trafman")
    assert (ut["direct"], ut["partial"], ut["none"], ut["score"]) == (3, 5, 2, 0.55)


def test_comparability_unknown_tool_raises():
    with pytest.raises(ValueError):
        bec.comparability_report("nope")


def test_security_and_swarm_axes_are_gaps_in_both_tools():
    """B07(보안)·B09(군집 자율)은 양 도구 모두 표현 불가 — 정직 표면화."""
    for tool in bec.TOOLS:
        assert "B07" in bec.gaps(tool)
        assert "B09" in bec.gaps(tool)


def test_gaps_match_none_status():
    for tool in bec.TOOLS:
        expected = tuple(
            c.benchmark_id for c in bec.all_comparisons()
            if c.for_tool(tool).status == "none"
        )
        assert bec.gaps(tool) == expected


def test_gaps_unknown_tool_raises():
    with pytest.raises(ValueError):
        bec.gaps("nope")


# --- 매트릭스/매니페스트 ---------------------------------------------------

def test_comparison_matrix_shape():
    rows = bec.comparison_matrix()
    assert len(rows) == 10
    for row in rows:
        assert set(row) == {
            "benchmark_id", "axis", "bluesky_status", "bluesky_analog",
            "u_trafman_status", "u_trafman_analog",
        }


def test_comparison_matrix_rows_are_read_only():
    """행은 MappingProxyType 로 동결 — 하류 소비자가 공유 상태 변조 불가."""
    row = bec.comparison_matrix()[0]
    with pytest.raises(TypeError):
        row["axis"] = "hacked"  # type: ignore[index]


def test_submission_manifest_has_no_performance_numbers():
    """제출 매니페스트는 구조적 비교만 — 성능 수치 키 부재."""
    manifest = bec.submission_manifest()
    assert manifest["suite_id"] == "SDACS-SBS-10"
    assert manifest["tools"] == list(bec.TOOLS)
    assert "disclaimer" in manifest
    # 도구별 집계는 카운트·점수(비교 가능성)일 뿐 성능 결과가 아니다.
    for tool in bec.TOOLS:
        assert set(manifest["comparability"][tool]) == {
            "tool", "direct", "partial", "none", "total", "score",
        }


def test_manifest_json_serializable():
    import json
    json.dumps(bec.submission_manifest(), ensure_ascii=False)


# --- 불변성 ----------------------------------------------------------------

def test_dataclasses_are_frozen():
    a = bec.get_comparison("B01").for_tool("bluesky")
    with pytest.raises(dataclasses.FrozenInstanceError):
        a.status = "none"  # type: ignore[misc]


def test_weight_property():
    direct = bec.ToolAnalog("bluesky", "direct", "x", "n", "c")
    partial = bec.ToolAnalog("bluesky", "partial", "x", "n", "c")
    none = bec.ToolAnalog("bluesky", "none", None, "n", "c")
    assert (direct.weight, partial.weight, none.weight) == (1.0, 0.5, 0.0)


# --- CLI -------------------------------------------------------------------

def test_cli_matrix_runs():
    assert bec.main(["--matrix"]) == 0


def test_cli_report_runs():
    assert bec.main(["--report"]) == 0


def test_cli_tool_runs():
    assert bec.main(["--tool", "bluesky"]) == 0


def test_cli_tool_unknown_returns_2():
    assert bec.main(["--tool", "nope"]) == 2


def test_cli_gaps_runs():
    assert bec.main(["--gaps"]) == 0


def test_cli_manifest_runs():
    assert bec.main(["--manifest"]) == 0


def test_cli_default_is_matrix():
    assert bec.main([]) == 0
