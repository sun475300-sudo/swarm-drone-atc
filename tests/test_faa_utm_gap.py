"""ODYSSEY Phase 402 -- FAA UTM ConOps v2 USS 갭 분석 단위 테스트."""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from simulation.faa_utm_gap import (
    CATEGORIES,
    COMPLIANCE_LEVELS,
    FAARequirement,
    FAAUTMGapAnalyzer,
    GapAnalysis,
    main,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# --- FAARequirement 검증 ---------------------------------------------------

def test_requirement_rejects_empty_id():
    with pytest.raises(ValueError):
        FAARequirement("", "Registration", "desc", "§1", None, "gap", "note")


def test_requirement_rejects_padded_id():
    with pytest.raises(ValueError):
        FAARequirement(" USS-01 ", "Registration", "desc", "§1", None, "gap", "note")


def test_requirement_rejects_empty_category():
    with pytest.raises(ValueError):
        FAARequirement("USS-99", "  ", "desc", "§1", None, "gap", "note")


def test_requirement_rejects_empty_description():
    with pytest.raises(ValueError):
        FAARequirement("USS-99", "Registration", "  ", "§1", None, "gap", "note")


def test_requirement_rejects_empty_conops_ref():
    with pytest.raises(ValueError):
        FAARequirement("USS-99", "Registration", "desc", "  ", None, "gap", "note")


def test_requirement_rejects_invalid_compliance_level():
    with pytest.raises(ValueError):
        FAARequirement("USS-99", "Registration", "desc", "§1", None, "unknown", "note")


def test_requirement_rejects_blank_module_path():
    with pytest.raises(ValueError):
        FAARequirement("USS-99", "Registration", "desc", "§1", "   ", "full", "note")


def test_requirement_rejects_empty_notes():
    with pytest.raises(ValueError):
        FAARequirement("USS-99", "Registration", "desc", "§1", None, "gap", "  ")


# --- 카탈로그 무결성 -------------------------------------------------------

def test_requirements_catalog_is_non_empty():
    analyzer = FAAUTMGapAnalyzer()
    assert len(analyzer.REQUIREMENTS) >= 20


def test_requirement_ids_are_unique():
    analyzer = FAAUTMGapAnalyzer()
    ids = [r.req_id for r in analyzer.REQUIREMENTS]
    assert len(ids) == len(set(ids))


def test_all_compliance_levels_valid():
    analyzer = FAAUTMGapAnalyzer()
    for req in analyzer.REQUIREMENTS:
        assert req.compliance_level in COMPLIANCE_LEVELS, (
            f"{req.req_id} has invalid compliance_level: {req.compliance_level}"
        )


def test_all_categories_are_recognized():
    analyzer = FAAUTMGapAnalyzer()
    for req in analyzer.REQUIREMENTS:
        assert req.category in CATEGORIES, (
            f"{req.req_id} has unrecognized category: {req.category}"
        )


def test_cited_sdacs_modules_exist_on_disk():
    """매핑이 인용하는 모든 SDACS 모듈 경로는 리포에 실재해야 한다 (정직성)."""
    analyzer = FAAUTMGapAnalyzer()
    for req in analyzer.REQUIREMENTS:
        if req.sdacs_module is not None:
            full_path = os.path.join(REPO_ROOT, req.sdacs_module)
            assert os.path.isfile(full_path), (
                f"{req.req_id} cites missing module: {req.sdacs_module}"
            )


def test_gap_items_have_no_module():
    """compliance_level == 'gap'인 항목은 sdacs_module이 None이어야 한다."""
    analyzer = FAAUTMGapAnalyzer()
    for req in analyzer.REQUIREMENTS:
        if req.compliance_level == "gap":
            assert req.sdacs_module is None, (
                f"{req.req_id} is a gap but has sdacs_module={req.sdacs_module}"
            )


# --- GapAnalysis -----------------------------------------------------------

def test_gap_analysis_counts_sum_to_total():
    analyzer = FAAUTMGapAnalyzer()
    analysis = analyzer.analyze()
    assert analysis.full + analysis.partial + analysis.gap + analysis.not_applicable == analysis.total


def test_gap_analysis_total_matches_catalog():
    analyzer = FAAUTMGapAnalyzer()
    analysis = analyzer.analyze()
    assert analysis.total == len(analyzer.REQUIREMENTS)


def test_compliance_pct_calculation():
    """compliance_pct = (full + 0.5*partial) / (total - not_applicable) * 100"""
    analyzer = FAAUTMGapAnalyzer()
    analysis = analyzer.analyze()
    denominator = analysis.total - analysis.not_applicable
    expected = (analysis.full + 0.5 * analysis.partial) / denominator * 100.0
    assert analysis.compliance_pct == pytest.approx(round(expected, 2))


def test_compliance_pct_in_range():
    analyzer = FAAUTMGapAnalyzer()
    analysis = analyzer.analyze()
    assert 0.0 <= analysis.compliance_pct <= 100.0


def test_by_category_covers_all_used_categories():
    analyzer = FAAUTMGapAnalyzer()
    analysis = analyzer.analyze()
    used_categories = {r.category for r in analyzer.REQUIREMENTS}
    assert set(analysis.by_category.keys()) == used_categories


def test_by_category_counts_sum_per_category():
    analyzer = FAAUTMGapAnalyzer()
    analysis = analyzer.analyze()
    for cat, counts in analysis.by_category.items():
        cat_reqs = [r for r in analyzer.REQUIREMENTS if r.category == cat]
        expected_full = sum(1 for r in cat_reqs if r.compliance_level == "full")
        expected_partial = sum(1 for r in cat_reqs if r.compliance_level == "partial")
        expected_gap = sum(1 for r in cat_reqs if r.compliance_level == "gap")
        assert counts["full"] == expected_full, f"{cat} full mismatch"
        assert counts["partial"] == expected_partial, f"{cat} partial mismatch"
        assert counts["gap"] == expected_gap, f"{cat} gap mismatch"


def test_by_category_is_read_only():
    analyzer = FAAUTMGapAnalyzer()
    analysis = analyzer.analyze()
    with pytest.raises(TypeError):
        analysis.by_category["NewCategory"] = {"full": 0, "partial": 0, "gap": 0}  # type: ignore[index]


def test_gap_analysis_rejects_inconsistent_totals():
    with pytest.raises(ValueError):
        GapAnalysis(total=5, full=10, partial=0, gap=0, not_applicable=0,
                    compliance_pct=100.0, by_category={})


def test_gap_analysis_is_deterministic():
    analyzer = FAAUTMGapAnalyzer()
    assert analyzer.analyze() == analyzer.analyze()


# --- gaps() / requirements_by_category() -----------------------------------

def test_gaps_returns_only_gap_items():
    analyzer = FAAUTMGapAnalyzer()
    for req in analyzer.gaps():
        assert req.compliance_level == "gap"


def test_gaps_count_matches_analysis():
    analyzer = FAAUTMGapAnalyzer()
    assert len(analyzer.gaps()) == analyzer.analyze().gap


def test_requirements_by_category_filters_correctly():
    analyzer = FAAUTMGapAnalyzer()
    for cat in CATEGORIES:
        reqs = analyzer.requirements_by_category(cat)
        for req in reqs:
            assert req.category == cat


def test_requirements_by_category_empty_for_unknown():
    analyzer = FAAUTMGapAnalyzer()
    assert analyzer.requirements_by_category("Nonexistent") == ()


def test_requirements_by_category_sorted_by_req_id():
    analyzer = FAAUTMGapAnalyzer()
    reqs = analyzer.requirements_by_category("Telemetry")
    ids = [r.req_id for r in reqs]
    assert ids == sorted(ids)


# --- to_json() -------------------------------------------------------------

def test_to_json_returns_list_of_dicts():
    analyzer = FAAUTMGapAnalyzer()
    result = analyzer.to_json()
    assert isinstance(result, list)
    assert all(isinstance(item, dict) for item in result)


def test_to_json_length_matches_catalog():
    analyzer = FAAUTMGapAnalyzer()
    assert len(analyzer.to_json()) == len(analyzer.REQUIREMENTS)


def test_to_json_round_trip():
    """JSON 직렬화 및 역직렬화가 데이터를 보존한다."""
    analyzer = FAAUTMGapAnalyzer()
    data = analyzer.to_json()
    serialized = json.dumps(data, ensure_ascii=False)
    deserialized = json.loads(serialized)
    assert deserialized == data


def test_to_json_contains_expected_keys():
    analyzer = FAAUTMGapAnalyzer()
    expected_keys = {"req_id", "category", "description", "conops_ref",
                     "sdacs_module", "compliance_level", "notes"}
    for item in analyzer.to_json():
        assert set(item.keys()) == expected_keys


# --- gap_report() ----------------------------------------------------------

def test_gap_report_contains_summary_sections():
    analyzer = FAAUTMGapAnalyzer()
    report = analyzer.gap_report()
    assert "FAA UTM ConOps v2" in report
    assert "충족률" in report
    assert "카테고리별 현황" in report
    assert "요구사항 상세" in report


def test_gap_report_mentions_all_categories():
    analyzer = FAAUTMGapAnalyzer()
    report = analyzer.gap_report()
    used_categories = {r.category for r in analyzer.REQUIREMENTS}
    for cat in used_categories:
        assert cat in report


def test_gap_report_is_deterministic():
    analyzer = FAAUTMGapAnalyzer()
    assert analyzer.gap_report() == analyzer.gap_report()


# --- CLI -------------------------------------------------------------------

def test_cli_default_runs_without_error():
    assert main([]) == 0


def test_cli_report_runs_without_error():
    assert main(["--report"]) == 0


def test_cli_gaps_runs_without_error():
    assert main(["--gaps"]) == 0


def test_cli_json_runs_without_error():
    assert main(["--json"]) == 0


def test_cli_category_runs_without_error():
    assert main(["--category", "Telemetry"]) == 0


def test_cli_category_unknown_runs_without_error():
    assert main(["--category", "Nonexistent"]) == 0


def test_cli_module_invocation():
    """python -m simulation.faa_utm_gap 가 정상 실행된다."""
    result = subprocess.run(
        [sys.executable, "-m", "simulation.faa_utm_gap"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=30,
    )
    assert result.returncode == 0
    assert "FAA UTM" in result.stdout
