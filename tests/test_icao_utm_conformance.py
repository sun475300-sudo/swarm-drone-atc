"""ODYSSEY Phase 407 — ICAO UTM Framework Ed.4 적합성 자가 평가 단위 테스트."""
from __future__ import annotations

import os

import pytest

from simulation.icao_utm_conformance import (
    CONFORMANCE_STATUSES,
    JOURNEY_PHASES,
    UTM_CAPABILITIES,
    ConformanceReport,
    UTMCapability,
    capabilities_by_phase,
    capabilities_by_status,
    conformance_matrix,
    conformance_report,
    core_principles,
    find_capability,
    gaps,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _cap(**kw) -> UTMCapability:
    """완전 충족 기본값으로 UTMCapability 를 만든다 (테스트 편의)."""
    defaults = dict(
        capability_id="id",
        name="name",
        journey_phase="plan",
        core_principle=True,
        status="conformant",
        sdacs_module="simulation/remote_id.py",
        summary="s",
    )
    defaults.update(kw)
    return UTMCapability(**defaults)  # type: ignore[arg-type]


# --- UTMCapability 검증 ----------------------------------------------------

def test_capability_rejects_empty_id():
    with pytest.raises(ValueError):
        _cap(capability_id="")


def test_capability_rejects_padded_id():
    with pytest.raises(ValueError):
        _cap(capability_id=" id ")


def test_capability_rejects_internal_space_id():
    with pytest.raises(ValueError):
        _cap(capability_id="foo bar")


def test_capability_rejects_empty_name():
    with pytest.raises(ValueError):
        _cap(name="  ")


def test_capability_rejects_empty_summary():
    with pytest.raises(ValueError):
        _cap(summary="  ")


def test_capability_rejects_unknown_phase():
    with pytest.raises(ValueError):
        _cap(journey_phase="fly")


def test_capability_rejects_unknown_status():
    with pytest.raises(ValueError):
        _cap(status="maybe")


def test_capability_rejects_non_bool_core():
    with pytest.raises(TypeError):
        _cap(core_principle=1)


def test_gap_must_not_cite_module():
    with pytest.raises(ValueError):
        _cap(status="gap", sdacs_module="simulation/remote_id.py")


def test_conformant_must_cite_module():
    with pytest.raises(ValueError):
        _cap(status="conformant", sdacs_module=None)


def test_partial_must_cite_module():
    with pytest.raises(ValueError):
        _cap(status="partial", sdacs_module=None)


def test_conformant_rejects_blank_module():
    with pytest.raises(ValueError):
        _cap(status="conformant", sdacs_module="   ")


def test_gap_capability_allows_none_module():
    cap = _cap(status="gap", sdacs_module=None)
    assert cap.is_gap is True
    assert cap.weight == 0.0


def test_weight_reflects_status():
    assert _cap(status="conformant").weight == 1.0
    assert _cap(status="partial").weight == 0.5
    assert _cap(status="gap", sdacs_module=None).weight == 0.0


# --- 카탈로그 무결성 -------------------------------------------------------

def test_capability_ids_are_unique():
    ids = [c.capability_id for c in UTM_CAPABILITIES]
    assert len(ids) == len(set(ids))


def test_all_phases_valid():
    assert all(c.journey_phase in JOURNEY_PHASES for c in UTM_CAPABILITIES)


def test_all_statuses_valid():
    assert all(c.status in CONFORMANCE_STATUSES for c in UTM_CAPABILITIES)


def test_cited_modules_exist_on_disk():
    """매핑이 인용하는 모든 SDACS 모듈 경로는 리포에 실재해야 한다 (정직성)."""
    for cap in UTM_CAPABILITIES:
        if cap.sdacs_module is not None:
            full = os.path.join(REPO_ROOT, cap.sdacs_module)
            assert os.path.isfile(full), f"{cap.capability_id} cites missing {cap.sdacs_module}"


def test_gap_capabilities_have_no_module():
    """gap 역량은 모듈을 인용하지 않아야 한다 (정직성 결속)."""
    for cap in UTM_CAPABILITIES:
        if cap.is_gap:
            assert cap.sdacs_module is None


def test_non_gap_capabilities_cite_module():
    for cap in UTM_CAPABILITIES:
        if not cap.is_gap:
            assert cap.sdacs_module is not None


def test_known_gaps_present():
    gap_ids = {c.capability_id for c in gaps()}
    assert "e_registration" in gap_ids
    assert "incident_investigation" in gap_ids


def test_every_journey_phase_has_at_least_one_capability():
    for phase in JOURNEY_PHASES:
        assert capabilities_by_phase(phase), f"phase {phase} has no capability"


# --- 조회 함수 -------------------------------------------------------------

def test_find_capability_returns_match():
    cap = find_capability("remote_identification")
    assert cap.name == "Remote identification"
    assert cap.status == "conformant"


def test_find_capability_unknown_raises():
    with pytest.raises(KeyError):
        find_capability("does_not_exist")


def test_capabilities_by_phase_rejects_bad_phase():
    with pytest.raises(ValueError):
        capabilities_by_phase("teleport")


def test_capabilities_by_phase_returns_only_that_phase():
    for phase in JOURNEY_PHASES:
        members = capabilities_by_phase(phase)
        assert all(c.journey_phase == phase for c in members)


def test_capabilities_by_phase_is_sorted_by_id():
    members = capabilities_by_phase("monitor")
    ids = [c.capability_id for c in members]
    assert ids == sorted(ids)


def test_every_capability_appears_in_exactly_one_phase_bucket():
    collected = []
    for phase in JOURNEY_PHASES:
        collected.extend(capabilities_by_phase(phase))
    assert len(collected) == len(UTM_CAPABILITIES)
    assert {c.capability_id for c in collected} == {c.capability_id for c in UTM_CAPABILITIES}


def test_capabilities_by_status_rejects_bad_status():
    with pytest.raises(ValueError):
        capabilities_by_status("unknown")


def test_capabilities_by_status_partitions_catalog():
    collected = []
    for status in CONFORMANCE_STATUSES:
        members = capabilities_by_status(status)
        assert all(c.status == status for c in members)
        collected.extend(members)
    assert {c.capability_id for c in collected} == {c.capability_id for c in UTM_CAPABILITIES}
    assert len(collected) == len(UTM_CAPABILITIES)


def test_core_principles_are_core_only():
    assert all(c.core_principle for c in core_principles())


def test_gaps_are_gap_status_only():
    assert all(c.is_gap for c in gaps())


# --- ConformanceReport -----------------------------------------------------

def test_report_totals_consistent():
    r = conformance_report()
    assert r.total == len(UTM_CAPABILITIES)
    assert r.conformant + r.partial + r.gap == r.total


def test_report_type():
    assert isinstance(conformance_report(), ConformanceReport)


def test_weighted_score_in_range():
    r = conformance_report()
    assert 0.0 <= r.weighted_score_pct <= 100.0


def test_weighted_score_matches_formula():
    r = conformance_report()
    expected = 100.0 * (r.conformant * 1.0 + r.partial * 0.5) / r.total
    assert r.weighted_score_pct == pytest.approx(expected)


def test_core_conformant_pct_in_range():
    r = conformance_report()
    assert 0.0 <= r.core_conformant_pct <= 100.0


def test_has_core_incomplete_consistent_with_counts():
    r = conformance_report()
    assert r.has_core_incomplete == (r.core_conformant < r.core_total)


def test_has_core_incomplete_triggered_by_partial_core_item():
    """핵심 갭이 없어도 핵심 partial 항목 1건이면 has_core_incomplete True."""
    # core_total=2, 둘 다 갭 아님(1 conformant + 1 partial) → core_conformant=1 < 2.
    r = ConformanceReport(2, 1, 1, 0, 2, 1, {"plan": (1, 1, 0)})
    assert r.gap == 0
    assert r.has_core_incomplete is True


def test_by_phase_counts_sum_to_total():
    r = conformance_report()
    total = sum(c + p + g for c, p, g in r.by_phase.values())
    conformant = sum(c for c, _p, _g in r.by_phase.values())
    partial = sum(p for _c, p, _g in r.by_phase.values())
    gap = sum(g for _c, _p, g in r.by_phase.values())
    assert total == r.total
    assert conformant == r.conformant
    assert partial == r.partial
    assert gap == r.gap


def test_report_is_deterministic():
    assert conformance_report() == conformance_report()


def test_report_by_phase_is_read_only():
    r = conformance_report()
    with pytest.raises(TypeError):
        r.by_phase["manage"] = (0, 0, 0)  # type: ignore[index]


def test_report_rejects_inconsistent_totals():
    with pytest.raises(ValueError):
        ConformanceReport(10, 5, 3, 0, 0, 0, {})  # 5+3+0 != 10


def test_report_rejects_core_overflow():
    with pytest.raises(ValueError):
        ConformanceReport(5, 5, 0, 0, 2, 9, {})  # core_conformant > core_total


def test_report_rejects_core_total_overflow():
    with pytest.raises(ValueError):
        ConformanceReport(5, 5, 0, 0, 9, 1, {})  # core_total > total


def test_empty_report_scores_zero():
    r = ConformanceReport(0, 0, 0, 0, 0, 0, {})
    assert r.weighted_score_pct == 0.0
    assert r.core_conformant_pct == 0.0
    assert r.has_core_incomplete is False


def test_report_rejects_by_phase_sum_mismatch():
    with pytest.raises(ValueError):
        ConformanceReport(3, 2, 1, 0, 1, 1, {"manage": (99, 99, 99)})


def test_report_by_phase_frozen_when_built_from_plain_dict():
    """평범한 dict 로 직접 생성해도 by_phase 는 읽기 전용으로 동결되어야 한다."""
    r = ConformanceReport(2, 1, 1, 0, 0, 0, {"plan": (1, 1, 0)})
    with pytest.raises(TypeError):
        r.by_phase["plan"] = (0, 0, 0)  # type: ignore[index]


# --- conformance_matrix ----------------------------------------------------

def test_matrix_covers_all_capabilities():
    rows = conformance_matrix()
    assert len(rows) == len(UTM_CAPABILITIES)
    assert {r["capability_id"] for r in rows} == {c.capability_id for c in UTM_CAPABILITIES}


def test_matrix_sorted_by_phase_then_id():
    rows = conformance_matrix()
    keys = [(JOURNEY_PHASES.index(r["journey_phase"]), r["capability_id"]) for r in rows]
    assert keys == sorted(keys)


def test_matrix_module_matches_status():
    for row in conformance_matrix():
        if row["status"] == "gap":
            assert row["sdacs_module"] is None
        else:
            assert row["sdacs_module"] is not None


def test_matrix_is_deterministic():
    assert conformance_matrix() == conformance_matrix()


# --- CLI smoke -------------------------------------------------------------

def test_cli_default_no_args_runs():
    from simulation.icao_utm_conformance import main
    assert main([]) == 0


def test_cli_report_runs():
    from simulation.icao_utm_conformance import main
    assert main(["--report"]) == 0


def test_cli_matrix_runs():
    from simulation.icao_utm_conformance import main
    assert main(["--matrix"]) == 0


def test_cli_gaps_and_core_run():
    from simulation.icao_utm_conformance import main
    assert main(["--gaps"]) == 0
    assert main(["--core"]) == 0
    assert main(["--phase", "plan"]) == 0
