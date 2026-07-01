"""ODYSSEY Phase 451 — EASA 신뢰 가능 AI 적합성 자가 평가 단위 테스트."""
from __future__ import annotations

import os

import pytest

from simulation.easa_ai_conformance import (
    AI_OBJECTIVES,
    BUILDING_BLOCKS,
    CONFORMANCE_STATUSES,
    AIObjective,
    ConformanceReport,
    conformance_matrix,
    conformance_report,
    find_objective,
    foundational_objectives,
    gaps,
    main,
    objectives_by_block,
    objectives_by_status,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _obj(**kw) -> AIObjective:
    """완전 충족 기본값으로 AIObjective 를 만든다 (테스트 편의)."""
    defaults = dict(
        objective_id="id",
        name="name",
        building_block="learning_assurance",
        anchor="LA:DM-01",
        foundational=True,
        status="conformant",
        sdacs_module="src/rl/ppo_collision.py",
        summary="s",
    )
    defaults.update(kw)
    return AIObjective(**defaults)  # type: ignore[arg-type]


# --- AIObjective 검증 ------------------------------------------------------

def test_objective_rejects_empty_id():
    with pytest.raises(ValueError):
        _obj(objective_id="")


def test_objective_rejects_padded_id():
    with pytest.raises(ValueError):
        _obj(objective_id=" id ")


def test_objective_rejects_internal_space_id():
    with pytest.raises(ValueError):
        _obj(objective_id="foo bar")


def test_objective_rejects_empty_name():
    with pytest.raises(ValueError):
        _obj(name="  ")


def test_objective_rejects_empty_anchor():
    with pytest.raises(ValueError):
        _obj(anchor="  ")


def test_objective_rejects_empty_summary():
    with pytest.raises(ValueError):
        _obj(summary="  ")


def test_objective_rejects_unknown_block():
    with pytest.raises(ValueError):
        _obj(building_block="nope")


def test_objective_rejects_non_bool_foundational():
    with pytest.raises(TypeError):
        _obj(foundational=1)


def test_objective_rejects_unknown_status():
    with pytest.raises(ValueError):
        _obj(status="maybe")


# --- 정직성 결속: gap ⟺ 모듈 없음 -----------------------------------------

def test_gap_must_not_cite_module():
    with pytest.raises(ValueError):
        _obj(status="gap", sdacs_module="src/rl/ppo_collision.py")


def test_gap_with_none_module_is_valid():
    o = _obj(status="gap", sdacs_module=None)
    assert o.is_gap is True


def test_conformant_requires_module():
    with pytest.raises(ValueError):
        _obj(status="conformant", sdacs_module=None)


def test_partial_requires_non_empty_module():
    with pytest.raises(ValueError):
        _obj(status="partial", sdacs_module="   ")


def test_weight_values():
    assert _obj(status="conformant").weight == 1.0
    assert _obj(status="partial", sdacs_module="x").weight == 0.5
    assert _obj(status="gap", sdacs_module=None).weight == 0.0


# --- 카탈로그 무결성 -------------------------------------------------------

def test_catalog_non_empty():
    assert len(AI_OBJECTIVES) >= 15


def test_catalog_ids_unique():
    ids = [o.objective_id for o in AI_OBJECTIVES]
    assert len(ids) == len(set(ids))


def test_all_blocks_present_in_catalog():
    used = {o.building_block for o in AI_OBJECTIVES}
    assert used == set(BUILDING_BLOCKS)


def test_all_statuses_valid():
    assert all(o.status in CONFORMANCE_STATUSES for o in AI_OBJECTIVES)


def test_cited_modules_exist_on_disk():
    """정직성 강제: 인용된 모든 sdacs_module 경로가 디스크에 실재해야 한다."""
    for o in AI_OBJECTIVES:
        if o.sdacs_module is not None:
            path = os.path.join(REPO_ROOT, o.sdacs_module)
            assert os.path.exists(path), f"{o.objective_id}: missing {o.sdacs_module}"


def test_gap_objectives_have_no_module():
    for o in AI_OBJECTIVES:
        if o.status == "gap":
            assert o.sdacs_module is None


def test_non_gap_objectives_cite_module():
    for o in AI_OBJECTIVES:
        if o.status != "gap":
            assert o.sdacs_module


def test_catalog_has_known_gaps():
    """연구 수준 ML — 학습 검증·분류 등 기반 갭이 정직하게 존재해야 한다."""
    gap_ids = {o.objective_id for o in gaps()}
    assert "learning_process_verification" in gap_ids
    assert "ml_application_classification" in gap_ids


def test_safety_net_authority_is_conformant():
    """SDACS 의 강점 — 결정적 안전망이 ML 위에서 권한 보유는 충족이어야 한다."""
    obj = find_objective("classical_safety_net_authority")
    assert obj.status == "conformant"
    assert obj.building_block == "safety_risk_mitigation"


# --- 조회 API --------------------------------------------------------------

def test_find_objective_returns_match():
    obj = find_objective("data_management")
    assert obj.objective_id == "data_management"


def test_find_objective_unknown_raises():
    with pytest.raises(KeyError):
        find_objective("nope")


def test_objectives_by_block_sorted():
    res = objectives_by_block("learning_assurance")
    assert len(res) >= 1
    assert all(o.building_block == "learning_assurance" for o in res)
    assert list(res) == sorted(res, key=lambda o: o.objective_id)


def test_objectives_by_block_unknown_raises():
    with pytest.raises(ValueError):
        objectives_by_block("nope")


def test_foundational_objectives_all_foundational():
    res = foundational_objectives()
    assert len(res) >= 1
    assert all(o.foundational for o in res)


def test_objectives_by_status_filters():
    for status in CONFORMANCE_STATUSES:
        res = objectives_by_status(status)
        assert all(o.status == status for o in res)


def test_objectives_by_status_unknown_raises():
    with pytest.raises(ValueError):
        objectives_by_status("nope")


def test_gaps_all_are_gap():
    assert all(o.is_gap for o in gaps())


# --- ConformanceReport -----------------------------------------------------

def test_report_counts_consistent():
    r = conformance_report()
    assert r.conformant + r.partial + r.gap == r.total
    assert r.total == len(AI_OBJECTIVES)


def test_report_by_block_sums_match():
    r = conformance_report()
    c = sum(v[0] for v in r.by_block.values())
    p = sum(v[1] for v in r.by_block.values())
    g = sum(v[2] for v in r.by_block.values())
    assert (c, p, g) == (r.conformant, r.partial, r.gap)


def test_report_by_block_is_readonly():
    r = conformance_report()
    with pytest.raises(TypeError):
        r.by_block["learning_assurance"] = (0, 0, 0)  # type: ignore[index]


def test_report_weighted_score_in_range():
    r = conformance_report()
    assert 0.0 <= r.weighted_score_pct <= 100.0


def test_report_weighted_score_is_conservative():
    """연구 수준 ML — 가중 점수는 정직하게 낮아야 한다(<60%)."""
    r = conformance_report()
    assert r.weighted_score_pct < 60.0


def test_report_foundational_incomplete_true():
    r = conformance_report()
    assert r.has_foundational_incomplete is True


def test_report_rejects_inconsistent_counts():
    with pytest.raises(ValueError):
        ConformanceReport(
            total=3, conformant=1, partial=1, gap=0,
            foundational_total=1, foundational_conformant=0, by_block={},
        )


def test_report_rejects_negative_counts():
    with pytest.raises(ValueError):
        ConformanceReport(
            total=1, conformant=-1, partial=1, gap=1,
            foundational_total=0, foundational_conformant=0, by_block={},
        )


def test_report_rejects_foundational_over_total():
    with pytest.raises(ValueError):
        ConformanceReport(
            total=2, conformant=2, partial=0, gap=0,
            foundational_total=3, foundational_conformant=0, by_block={},
        )


def test_report_rejects_foundational_conformant_over_foundational_total():
    with pytest.raises(ValueError):
        ConformanceReport(
            total=5, conformant=2, partial=0, gap=3,
            foundational_total=1, foundational_conformant=2, by_block={},
        )


def test_report_rejects_mismatched_by_block():
    with pytest.raises(ValueError):
        ConformanceReport(
            total=2, conformant=2, partial=0, gap=0,
            foundational_total=0, foundational_conformant=0,
            by_block={"learning_assurance": (1, 0, 0)},
        )


def test_report_foundational_pct_zero_when_no_foundational():
    r = ConformanceReport(
        total=1, conformant=1, partial=0, gap=0,
        foundational_total=0, foundational_conformant=0, by_block={},
    )
    assert r.foundational_conformant_pct == 0.0
    assert r.has_foundational_incomplete is False


# --- 매트릭스 / 결정성 -----------------------------------------------------

def test_conformance_matrix_covers_all():
    rows = conformance_matrix()
    assert len(rows) == len(AI_OBJECTIVES)
    assert {r["objective_id"] for r in rows} == {o.objective_id for o in AI_OBJECTIVES}


def test_conformance_matrix_block_grouped():
    rows = conformance_matrix()
    seen_index = [BUILDING_BLOCKS.index(str(r["building_block"])) for r in rows]
    assert seen_index == sorted(seen_index)


def test_conformance_matrix_rows_self_describing():
    """매트릭스 행은 summary 포함 전 필드를 보유해 카탈로그 없이 재구성 가능해야 한다."""
    row = conformance_matrix()[0]
    for key in ("objective_id", "name", "building_block", "anchor",
                "foundational", "status", "sdacs_module", "summary"):
        assert key in row


def test_conformance_matrix_rows_are_readonly():
    row = conformance_matrix()[0]
    with pytest.raises(TypeError):
        row["status"] = "hacked"  # type: ignore[index]


def test_report_rejects_unknown_by_block_key():
    with pytest.raises(ValueError):
        ConformanceReport(
            total=2, conformant=2, partial=0, gap=0,
            foundational_total=0, foundational_conformant=0,
            by_block={"garbage": (2, 0, 0)},
        )


def test_report_is_deterministic():
    a, b = conformance_report(), conformance_report()
    assert (a.total, a.conformant, a.partial, a.gap) == (
        b.total, b.conformant, b.partial, b.gap
    )


def test_matrix_is_deterministic():
    assert conformance_matrix() == conformance_matrix()


# --- CLI -------------------------------------------------------------------

def test_cli_report_runs(capsys):
    assert main(["--report"]) == 0
    out = capsys.readouterr().out
    assert "EASA" in out


def test_cli_matrix_runs(capsys):
    assert main(["--matrix"]) == 0
    assert "매트릭스" in capsys.readouterr().out


def test_cli_gaps_runs(capsys):
    assert main(["--gaps"]) == 0


def test_cli_block_runs(capsys):
    assert main(["--block", "learning_assurance"]) == 0


def test_cli_foundational_runs(capsys):
    assert main(["--foundational"]) == 0


def test_cli_default_is_report(capsys):
    assert main([]) == 0
    assert "가중 점수" in capsys.readouterr().out
