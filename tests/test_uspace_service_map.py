"""ODYSSEY Phase 401 — EASA U-space 서비스 매핑 단위 테스트."""
from __future__ import annotations

import os

import pytest

from simulation.uspace_service_map import (
    SERVICE_LEVELS,
    USPACE_SERVICES,
    CoverageReport,
    USpaceService,
    coverage_report,
    find_service,
    gaps,
    implemented_services,
    mandatory_services,
    service_matrix,
    services_by_level,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# --- USpaceService 검증 ---------------------------------------------------

def test_service_rejects_empty_id():
    with pytest.raises(ValueError):
        USpaceService("", "name", "U1", True, None, "s")


def test_service_rejects_empty_name():
    with pytest.raises(ValueError):
        USpaceService("id", "  ", "U1", True, None, "s")


def test_service_rejects_unknown_level():
    with pytest.raises(ValueError):
        USpaceService("id", "name", "U9", True, None, "s")


def test_service_rejects_non_bool_mandatory():
    with pytest.raises(TypeError):
        USpaceService("id", "name", "U1", 1, None, "s")  # type: ignore[arg-type]


def test_service_rejects_blank_module_path():
    with pytest.raises(ValueError):
        USpaceService("id", "name", "U1", True, "   ", "s")


def test_service_rejects_padded_id():
    with pytest.raises(ValueError):
        USpaceService(" id ", "name", "U1", True, None, "s")


def test_service_rejects_empty_summary():
    with pytest.raises(ValueError):
        USpaceService("id", "name", "U1", True, None, "  ")


def test_is_implemented_reflects_module_presence():
    mapped = USpaceService("a", "A", "U1", True, "simulation/remote_id.py", "s")
    gap = USpaceService("b", "B", "U4", False, None, "s")
    assert mapped.is_implemented is True
    assert gap.is_implemented is False


# --- 카탈로그 무결성 -------------------------------------------------------

def test_service_ids_are_unique():
    ids = [s.service_id for s in USPACE_SERVICES]
    assert len(ids) == len(set(ids))


def test_all_levels_valid():
    assert all(s.level in SERVICE_LEVELS for s in USPACE_SERVICES)


def test_cited_modules_exist_on_disk():
    """매핑이 인용하는 모든 SDACS 모듈 경로는 리포에 실재해야 한다 (정직성)."""
    for svc in USPACE_SERVICES:
        if svc.sdacs_module is not None:
            full = os.path.join(REPO_ROOT, svc.sdacs_module)
            assert os.path.isfile(full), f"{svc.service_id} cites missing {svc.sdacs_module}"


def test_mandatory_services_match_eu_2021_664():
    """EU 2021/664 의무 4종이 정확히 mandatory=True 로 표기되어야 한다."""
    expected = {
        "network_identification",
        "geo_awareness",
        "uas_flight_authorisation",
        "traffic_information",
    }
    assert {s.service_id for s in mandatory_services()} == expected


def test_all_mandatory_services_are_implemented():
    assert all(s.is_implemented for s in mandatory_services())


# --- 조회 함수 -------------------------------------------------------------

def test_find_service_returns_match():
    svc = find_service("network_identification")
    assert svc.name == "Network identification service"
    assert svc.mandatory is True


def test_find_service_unknown_raises():
    with pytest.raises(KeyError):
        find_service("does_not_exist")


def test_services_by_level_rejects_bad_level():
    with pytest.raises(ValueError):
        services_by_level("X9")


def test_services_by_level_returns_only_that_level():
    for level in SERVICE_LEVELS:
        members = services_by_level(level)
        assert all(s.level == level for s in members)


def test_services_by_level_is_sorted_by_id():
    members = services_by_level("U2")
    ids = [s.service_id for s in members]
    assert ids == sorted(ids)


def test_every_service_appears_in_exactly_one_level_bucket():
    collected = []
    for level in SERVICE_LEVELS:
        collected.extend(services_by_level(level))
    assert len(collected) == len(USPACE_SERVICES)
    assert {s.service_id for s in collected} == {s.service_id for s in USPACE_SERVICES}


def test_gaps_are_unimplemented_only():
    assert all(not s.is_implemented for s in gaps())


def test_implemented_and_gaps_partition_catalog():
    impl = {s.service_id for s in implemented_services()}
    gap = {s.service_id for s in gaps()}
    assert impl.isdisjoint(gap)
    assert impl | gap == {s.service_id for s in USPACE_SERVICES}


def test_manned_integration_is_a_known_gap():
    assert "manned_aviation_integration" in {s.service_id for s in gaps()}


# --- CoverageReport --------------------------------------------------------

def test_coverage_report_totals_consistent():
    r = coverage_report()
    assert r.total == len(USPACE_SERVICES)
    assert r.implemented + r.gaps == r.total


def test_coverage_report_type():
    assert isinstance(coverage_report(), CoverageReport)


def test_mandatory_coverage_complete():
    r = coverage_report()
    assert r.is_mandatory_complete is True
    assert r.mandatory_coverage_pct == pytest.approx(100.0)


def test_coverage_pct_in_range():
    r = coverage_report()
    assert 0.0 <= r.coverage_pct <= 100.0


def test_by_level_counts_sum_to_total():
    r = coverage_report()
    total_from_levels = sum(tot for _impl, tot in r.by_level.values())
    impl_from_levels = sum(impl for impl, _tot in r.by_level.values())
    assert total_from_levels == r.total
    assert impl_from_levels == r.implemented


def test_by_level_implemented_never_exceeds_total():
    r = coverage_report()
    for impl, tot in r.by_level.values():
        assert 0 <= impl <= tot


def test_coverage_report_is_deterministic():
    assert coverage_report() == coverage_report()


def test_empty_mandatory_coverage_pct_is_zero():
    r = CoverageReport(0, 0, 0, 0, 0, {})
    assert r.coverage_pct == 0.0
    assert r.mandatory_coverage_pct == 0.0
    assert r.is_mandatory_complete is False


def test_coverage_report_rejects_inconsistent_totals():
    with pytest.raises(ValueError):
        CoverageReport(5, 10, 0, 0, 0, {})  # implemented+gaps != total


def test_coverage_report_rejects_mandatory_overflow():
    with pytest.raises(ValueError):
        CoverageReport(5, 3, 2, 2, 9, {})  # mandatory_impl > mandatory_total


def test_coverage_report_by_level_is_read_only():
    r = coverage_report()
    with pytest.raises(TypeError):
        r.by_level["U9"] = (0, 0)  # type: ignore[index]


# --- service_matrix --------------------------------------------------------

def test_matrix_covers_all_services():
    rows = service_matrix()
    assert len(rows) == len(USPACE_SERVICES)
    assert {r["service_id"] for r in rows} == {s.service_id for s in USPACE_SERVICES}


def test_matrix_sorted_by_level_then_id():
    rows = service_matrix()
    keys = [(SERVICE_LEVELS.index(r["level"]), r["service_id"]) for r in rows]
    assert keys == sorted(keys)


def test_matrix_implemented_flag_matches_module():
    for row in service_matrix():
        assert row["implemented"] == (row["sdacs_module"] is not None)


def test_matrix_is_deterministic():
    assert service_matrix() == service_matrix()
