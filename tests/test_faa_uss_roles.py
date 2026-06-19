"""ODYSSEY Phase 402 — FAA UTM USS 역할 매핑 단위 테스트."""
from __future__ import annotations

import os

import pytest

from simulation.faa_uss_roles import (
    CATEGORIES,
    USS_REQUIREMENTS,
    ConformanceReport,
    USSRequirement,
    conformance_report,
    core_requirements,
    find_requirement,
    gaps,
    implemented_requirements,
    requirements_by_category,
    role_matrix,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# --- USSRequirement 검증 --------------------------------------------------

def test_requirement_rejects_empty_id():
    with pytest.raises(ValueError):
        USSRequirement("", "name", "Operation Management", True, None, "s")


def test_requirement_rejects_empty_name():
    with pytest.raises(ValueError):
        USSRequirement("id", "  ", "Operation Management", True, None, "s")


def test_requirement_rejects_unknown_category():
    with pytest.raises(ValueError):
        USSRequirement("id", "name", "No Such Category", True, None, "s")


def test_requirement_rejects_non_bool_core():
    with pytest.raises(TypeError):
        USSRequirement("id", "name", "Operation Management", 1, None, "s")  # type: ignore[arg-type]


def test_requirement_rejects_blank_module_path():
    with pytest.raises(ValueError):
        USSRequirement("id", "name", "Operation Management", True, "   ", "s")


def test_requirement_rejects_padded_id():
    with pytest.raises(ValueError):
        USSRequirement(" id ", "name", "Operation Management", True, None, "s")


def test_requirement_rejects_empty_summary():
    with pytest.raises(ValueError):
        USSRequirement("id", "name", "Operation Management", True, None, "  ")


def test_is_implemented_reflects_module_presence():
    mapped = USSRequirement("a", "A", "Operation Management", True,
                            "simulation/remote_id.py", "s")
    gap = USSRequirement("b", "B", "Information Services", False, None, "s")
    assert mapped.is_implemented is True
    assert gap.is_implemented is False


# --- 카탈로그 무결성 -------------------------------------------------------

def test_requirement_ids_are_unique():
    ids = [r.requirement_id for r in USS_REQUIREMENTS]
    assert len(ids) == len(set(ids))


def test_all_categories_valid():
    assert all(r.category in CATEGORIES for r in USS_REQUIREMENTS)


def test_cited_modules_exist_on_disk():
    """매핑이 인용하는 모든 SDACS 모듈 경로는 리포에 실재해야 한다 (정직성)."""
    for req in USS_REQUIREMENTS:
        if req.sdacs_module is not None:
            full = os.path.join(REPO_ROOT, req.sdacs_module)
            assert os.path.isfile(full), (
                f"{req.requirement_id} cites missing {req.sdacs_module}"
            )


def test_core_requirements_are_all_implemented():
    """핵심 USS Network 역할은 전부 대응 모듈이 있어야 한다."""
    assert all(r.is_implemented for r in core_requirements())


def test_known_core_requirements_present():
    """ConOps v2.0 핵심 역할 집합이 정확히 core=True 로 표기되어야 한다."""
    expected = {
        "operation_planning",
        "strategic_deconfliction",
        "conformance_monitoring",
        "constraint_dissemination",
        "network_remote_id",
        "inter_uss_communication",
        "discovery_synchronization",
    }
    assert {r.requirement_id for r in core_requirements()} == expected


# --- 조회 함수 -------------------------------------------------------------

def test_find_requirement_returns_match():
    req = find_requirement("strategic_deconfliction")
    assert req.name == "Strategic deconfliction"
    assert req.core is True


def test_find_requirement_unknown_raises():
    with pytest.raises(KeyError):
        find_requirement("does_not_exist")


def test_requirements_by_category_rejects_bad_category():
    with pytest.raises(ValueError):
        requirements_by_category("Nope")


def test_requirements_by_category_returns_only_that_category():
    for category in CATEGORIES:
        members = requirements_by_category(category)
        assert all(r.category == category for r in members)


def test_requirements_by_category_is_sorted_by_id():
    members = requirements_by_category("Operation Management")
    ids = [r.requirement_id for r in members]
    assert ids == sorted(ids)


def test_every_requirement_appears_in_exactly_one_category_bucket():
    collected = []
    for category in CATEGORIES:
        collected.extend(requirements_by_category(category))
    assert len(collected) == len(USS_REQUIREMENTS)
    assert {r.requirement_id for r in collected} == {r.requirement_id for r in USS_REQUIREMENTS}


def test_gaps_are_unimplemented_only():
    assert all(not r.is_implemented for r in gaps())


def test_implemented_and_gaps_partition_catalog():
    impl = {r.requirement_id for r in implemented_requirements()}
    gap = {r.requirement_id for r in gaps()}
    assert impl.isdisjoint(gap)
    assert impl | gap == {r.requirement_id for r in USS_REQUIREMENTS}


def test_operator_credentialing_is_a_known_gap():
    assert "operator_credentialing" in {r.requirement_id for r in gaps()}


def test_public_safety_access_is_a_known_gap():
    assert "public_safety_access" in {r.requirement_id for r in gaps()}


# --- ConformanceReport -----------------------------------------------------

def test_conformance_report_totals_consistent():
    r = conformance_report()
    assert r.total == len(USS_REQUIREMENTS)
    assert r.implemented + r.gaps == r.total


def test_conformance_report_type():
    assert isinstance(conformance_report(), ConformanceReport)


def test_core_coverage_complete():
    r = conformance_report()
    assert r.is_core_complete is True
    assert r.core_coverage_pct == pytest.approx(100.0)


def test_coverage_pct_in_range():
    r = conformance_report()
    assert 0.0 <= r.coverage_pct <= 100.0


def test_by_category_counts_sum_to_total():
    r = conformance_report()
    total_from_cats = sum(tot for _impl, tot in r.by_category.values())
    impl_from_cats = sum(impl for impl, _tot in r.by_category.values())
    assert total_from_cats == r.total
    assert impl_from_cats == r.implemented


def test_by_category_implemented_never_exceeds_total():
    r = conformance_report()
    for impl, tot in r.by_category.values():
        assert 0 <= impl <= tot


def test_conformance_report_is_deterministic():
    assert conformance_report() == conformance_report()


def test_empty_core_coverage_pct_is_zero():
    r = ConformanceReport(0, 0, 0, 0, 0, {})
    assert r.coverage_pct == 0.0
    assert r.core_coverage_pct == 0.0
    assert r.is_core_complete is False


def test_conformance_report_rejects_inconsistent_totals():
    with pytest.raises(ValueError):
        ConformanceReport(5, 10, 0, 0, 0, {})  # implemented+gaps != total


def test_conformance_report_rejects_core_overflow():
    with pytest.raises(ValueError):
        ConformanceReport(5, 3, 2, 2, 9, {})  # core_impl > core_total


def test_conformance_report_rejects_core_exceeding_implemented():
    with pytest.raises(ValueError):
        ConformanceReport(10, 3, 7, 5, 4, {})  # core_impl(4) > implemented(3)


def test_conformance_report_by_category_is_read_only():
    r = conformance_report()
    with pytest.raises(TypeError):
        r.by_category["No Such Category"] = (0, 0)  # type: ignore[index]


# --- role_matrix -----------------------------------------------------------

def test_matrix_covers_all_requirements():
    rows = role_matrix()
    assert len(rows) == len(USS_REQUIREMENTS)
    assert {r["requirement_id"] for r in rows} == {r.requirement_id for r in USS_REQUIREMENTS}


def test_matrix_sorted_by_category_then_id():
    rows = role_matrix()
    keys = [(CATEGORIES.index(r["category"]), r["requirement_id"]) for r in rows]
    assert keys == sorted(keys)


def test_matrix_implemented_flag_matches_module():
    for row in role_matrix():
        assert row["implemented"] == (row["sdacs_module"] is not None)


def test_matrix_is_deterministic():
    assert role_matrix() == role_matrix()


def test_matrix_rows_are_read_only():
    for row in role_matrix():
        with pytest.raises(TypeError):
            row["requirement_id"] = "mutated"  # type: ignore[index]


# --- CLI ------------------------------------------------------------------

@pytest.mark.parametrize("flag", ["--matrix", "--conformance", "--gaps", "--core"])
def test_cli_flags_exit_zero(flag):
    from simulation.faa_uss_roles import main
    assert main([flag]) == 0


def test_cli_default_exit_zero():
    from simulation.faa_uss_roles import main
    assert main([]) == 0


def test_cli_category_exit_zero():
    from simulation.faa_uss_roles import main
    assert main(["--category", "Inter-USS / Network"]) == 0
