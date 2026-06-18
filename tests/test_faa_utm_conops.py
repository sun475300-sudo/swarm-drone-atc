"""ODYSSEY Phase 402 — FAA UTM ConOps v2.0 정렬 단위 테스트."""
from __future__ import annotations

import os

import pytest

from simulation.faa_utm_conops import (
    FAA_UTM_CAPABILITIES,
    UTM_ROLES,
    ConformanceReport,
    FaaUtmCapability,
    capabilities_by_role,
    capability_matrix,
    conformance_report,
    find_capability,
    gaps,
    implemented_capabilities,
    required_capabilities,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# --- FaaUtmCapability 검증 ------------------------------------------------

def test_capability_rejects_empty_id():
    with pytest.raises(ValueError):
        FaaUtmCapability("", "name", "USS", True, None, "area", "s")


def test_capability_rejects_empty_name():
    with pytest.raises(ValueError):
        FaaUtmCapability("id", "  ", "USS", True, None, "area", "s")


def test_capability_rejects_empty_conops_area():
    with pytest.raises(ValueError):
        FaaUtmCapability("id", "name", "USS", True, None, "  ", "s")


def test_capability_rejects_unknown_role():
    with pytest.raises(ValueError):
        FaaUtmCapability("id", "name", "ATC", True, None, "area", "s")


def test_capability_rejects_non_bool_required():
    with pytest.raises(TypeError):
        FaaUtmCapability("id", "name", "USS", 1, None, "area", "s")  # type: ignore[arg-type]


def test_capability_rejects_blank_module_path():
    with pytest.raises(ValueError):
        FaaUtmCapability("id", "name", "USS", True, "   ", "area", "s")


def test_capability_rejects_padded_id():
    with pytest.raises(ValueError):
        FaaUtmCapability(" id ", "name", "USS", True, None, "area", "s")


def test_capability_rejects_empty_summary():
    with pytest.raises(ValueError):
        FaaUtmCapability("id", "name", "USS", True, None, "area", "  ")


def test_is_implemented_reflects_module_presence():
    mapped = FaaUtmCapability("a", "A", "USS", True, "simulation/remote_id.py", "area", "s")
    gap = FaaUtmCapability("b", "B", "FIMS", True, None, "area", "s")
    assert mapped.is_implemented is True
    assert gap.is_implemented is False


# --- 카탈로그 무결성 -------------------------------------------------------

def test_capability_ids_are_unique():
    ids = [c.capability_id for c in FAA_UTM_CAPABILITIES]
    assert len(ids) == len(set(ids))


def test_all_roles_valid():
    assert all(c.role in UTM_ROLES for c in FAA_UTM_CAPABILITIES)


def test_cited_modules_exist_on_disk():
    """매핑이 인용하는 모든 SDACS 모듈 경로는 리포에 실재해야 한다 (정직성)."""
    for cap in FAA_UTM_CAPABILITIES:
        if cap.sdacs_module is not None:
            full = os.path.join(REPO_ROOT, cap.sdacs_module)
            assert os.path.isfile(full), f"{cap.capability_id} cites missing {cap.sdacs_module}"


def test_remote_id_is_required():
    """14 CFR Part 89 Remote ID 는 핵심 요건이어야 한다."""
    assert find_capability("remote_identification").required is True


def test_fims_data_exchange_is_a_known_gap():
    """FAA 정부 FIMS 게이트웨이 연동은 정직히 표면화된 갭이어야 한다."""
    cap = find_capability("fims_data_exchange")
    assert cap.role == "FIMS"
    assert cap.is_implemented is False
    assert cap.capability_id in {g.capability_id for g in gaps()}


# --- 조회 함수 -------------------------------------------------------------

def test_find_capability_returns_match():
    cap = find_capability("strategic_deconfliction")
    assert cap.name == "Strategic deconfliction"
    assert cap.required is True


def test_find_capability_unknown_raises():
    with pytest.raises(KeyError):
        find_capability("does_not_exist")


def test_capabilities_by_role_rejects_bad_role():
    with pytest.raises(ValueError):
        capabilities_by_role("X9")


def test_capabilities_by_role_returns_only_that_role():
    for role in UTM_ROLES:
        members = capabilities_by_role(role)
        assert all(c.role == role for c in members)


def test_capabilities_by_role_is_sorted_by_id():
    members = capabilities_by_role("USS")
    ids = [c.capability_id for c in members]
    assert ids == sorted(ids)


def test_every_capability_appears_in_exactly_one_role_bucket():
    collected = []
    for role in UTM_ROLES:
        collected.extend(capabilities_by_role(role))
    assert len(collected) == len(FAA_UTM_CAPABILITIES)
    assert {c.capability_id for c in collected} == {c.capability_id for c in FAA_UTM_CAPABILITIES}


def test_gaps_are_unimplemented_only():
    assert all(not c.is_implemented for c in gaps())


def test_implemented_and_gaps_partition_catalog():
    impl = {c.capability_id for c in implemented_capabilities()}
    gap = {c.capability_id for c in gaps()}
    assert impl.isdisjoint(gap)
    assert impl | gap == {c.capability_id for c in FAA_UTM_CAPABILITIES}


def test_required_capabilities_are_required_only():
    assert all(c.required for c in required_capabilities())


# --- ConformanceReport -----------------------------------------------------

def test_conformance_report_totals_consistent():
    r = conformance_report()
    assert r.total == len(FAA_UTM_CAPABILITIES)
    assert r.implemented + r.gaps == r.total


def test_conformance_report_type():
    assert isinstance(conformance_report(), ConformanceReport)


def test_required_not_complete_due_to_fims_gap():
    """FIMS 갭이 존재하므로 핵심 요건은 완전 충족이 아니다 (정직성)."""
    r = conformance_report()
    assert r.is_required_complete is False
    assert 0.0 < r.required_coverage_pct < 100.0


def test_coverage_pct_in_range():
    r = conformance_report()
    assert 0.0 <= r.coverage_pct <= 100.0


def test_by_role_counts_sum_to_total():
    r = conformance_report()
    total_from_roles = sum(tot for _impl, tot in r.by_role.values())
    impl_from_roles = sum(impl for impl, _tot in r.by_role.values())
    assert total_from_roles == r.total
    assert impl_from_roles == r.implemented


def test_by_role_implemented_never_exceeds_total():
    r = conformance_report()
    for impl, tot in r.by_role.values():
        assert 0 <= impl <= tot


def test_conformance_report_is_deterministic():
    assert conformance_report() == conformance_report()


def test_empty_required_coverage_pct_is_zero():
    r = ConformanceReport(0, 0, 0, 0, 0, {})
    assert r.coverage_pct == 0.0
    assert r.required_coverage_pct == 0.0
    assert r.is_required_complete is False


def test_conformance_report_rejects_inconsistent_totals():
    with pytest.raises(ValueError):
        ConformanceReport(5, 10, 0, 0, 0, {})  # implemented+gaps != total


def test_conformance_report_rejects_required_overflow():
    with pytest.raises(ValueError):
        ConformanceReport(5, 3, 2, 2, 9, {})  # required_impl > required_total


def test_conformance_report_by_role_is_read_only():
    r = conformance_report()
    with pytest.raises(TypeError):
        r.by_role["X9"] = (0, 0)  # type: ignore[index]


def test_conformance_report_wraps_plain_dict_by_role_as_read_only():
    """평범한 dict 로 직접 생성해도 by_role 은 읽기 전용으로 강제되어야 한다."""
    r = ConformanceReport(1, 1, 0, 0, 0, {"USS": (1, 1)})
    with pytest.raises(TypeError):
        r.by_role["USS"] = (0, 0)  # type: ignore[index]


# --- capability_matrix -----------------------------------------------------

def test_matrix_covers_all_capabilities():
    rows = capability_matrix()
    assert len(rows) == len(FAA_UTM_CAPABILITIES)
    assert {r["capability_id"] for r in rows} == {c.capability_id for c in FAA_UTM_CAPABILITIES}


def test_matrix_sorted_by_role_then_id():
    rows = capability_matrix()
    keys = [(UTM_ROLES.index(r["role"]), r["capability_id"]) for r in rows]
    assert keys == sorted(keys)


def test_matrix_implemented_flag_matches_module():
    for row in capability_matrix():
        assert row["implemented"] == (row["sdacs_module"] is not None)


def test_matrix_is_deterministic():
    assert capability_matrix() == capability_matrix()
