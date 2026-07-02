"""ODYSSEY Phase 458 — EASA ML 검증·확인(V&V) 적합성 게이트 단위 테스트."""
from __future__ import annotations

import os
from types import MappingProxyType

import pytest

from simulation.ml_verification_validation import (
    VV_CATEGORIES,
    VV_OBJECTIVES,
    VV_STATUSES,
    VVObjective,
    VVReport,
    _STATUS_WEIGHT,
    find_objective,
    foundational_objectives,
    gaps,
    main,
    objectives_by_category,
    objectives_by_status,
    vv_matrix,
    vv_report,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _obj(**kw) -> VVObjective:
    """완전 충족 기본값으로 VVObjective 를 만든다 (테스트 편의)."""
    defaults = dict(
        objective_id="id",
        name="name",
        category="boundary_testing",
        anchor="VV:BT-01",
        foundational=True,
        status="conformant",
        sdacs_module="src/rl/ppo_collision.py",
        summary="s",
    )
    defaults.update(kw)
    return VVObjective(**defaults)  # type: ignore[arg-type]


# --- VVObjective 검증 --------------------------------------------------------

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


def test_objective_rejects_unknown_category():
    with pytest.raises(ValueError):
        _obj(category="nope")


def test_objective_rejects_non_bool_foundational():
    with pytest.raises(TypeError):
        _obj(foundational=1)


def test_objective_rejects_unknown_status():
    with pytest.raises(ValueError):
        _obj(status="maybe")


# --- 정직성 결속: gap ⟺ 모듈 없음 ---------------------------------------------

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


# --- 가중 값 ------------------------------------------------------------------

def test_weight_values():
    assert _obj(status="conformant").weight == 1.0
    assert _obj(status="partial", sdacs_module="x").weight == 0.5
    assert _obj(status="gap", sdacs_module=None).weight == 0.0


# --- 카탈로그 무결성 ----------------------------------------------------------

def test_catalog_non_empty():
    assert len(VV_OBJECTIVES) >= 15


def test_catalog_ids_unique():
    ids = [o.objective_id for o in VV_OBJECTIVES]
    assert len(ids) == len(set(ids))


def test_all_statuses_valid():
    assert all(o.status in VV_STATUSES for o in VV_OBJECTIVES)


def test_all_categories_valid():
    assert all(o.category in VV_CATEGORIES for o in VV_OBJECTIVES)


def test_all_foundational_are_bool():
    assert all(isinstance(o.foundational, bool) for o in VV_OBJECTIVES)


def test_all_categories_present_in_catalog():
    used = {o.category for o in VV_OBJECTIVES}
    assert used == set(VV_CATEGORIES)


def test_anchors_unique():
    anchors = [o.anchor for o in VV_OBJECTIVES]
    assert len(anchors) == len(set(anchors))


# --- 정직성 결속: 카탈로그 수준 -----------------------------------------------

def test_gap_objectives_have_no_module():
    for o in VV_OBJECTIVES:
        if o.status == "gap":
            assert o.sdacs_module is None, f"{o.objective_id}: gap must have sdacs_module=None"


def test_non_gap_objectives_cite_module():
    for o in VV_OBJECTIVES:
        if o.status != "gap":
            assert o.sdacs_module, f"{o.objective_id}: non-gap must cite sdacs_module"


# --- 디스크 실재 검증 ---------------------------------------------------------

def test_cited_modules_exist_on_disk():
    """정직성 강제: 인용된 모든 sdacs_module 경로가 디스크에 실재해야 한다."""
    for o in VV_OBJECTIVES:
        if o.sdacs_module is not None:
            path = os.path.join(REPO_ROOT, o.sdacs_module)
            assert os.path.exists(path), f"{o.objective_id}: missing {o.sdacs_module}"


# --- find_objective -----------------------------------------------------------

def test_find_objective_returns_match():
    obj = find_objective("deterministic_invariant_property_testing")
    assert obj.objective_id == "deterministic_invariant_property_testing"


def test_find_objective_unknown_raises():
    with pytest.raises(KeyError):
        find_objective("nope")


# --- objectives_by_category ---------------------------------------------------

def test_objectives_by_category_sorted():
    res = objectives_by_category("boundary_testing")
    assert len(res) >= 1
    assert all(o.category == "boundary_testing" for o in res)
    assert list(res) == sorted(res, key=lambda o: o.objective_id)


def test_objectives_by_category_unknown_raises():
    with pytest.raises(ValueError):
        objectives_by_category("nope")


def test_objectives_by_category_all_non_empty():
    for cat in VV_CATEGORIES:
        res = objectives_by_category(cat)
        assert len(res) >= 1, f"category {cat} has no objectives"


# --- foundational_objectives -------------------------------------------------

def test_foundational_objectives_all_foundational():
    res = foundational_objectives()
    assert len(res) >= 1
    assert all(o.foundational for o in res)


def test_foundational_objectives_sorted_by_id():
    res = foundational_objectives()
    assert list(res) == sorted(res, key=lambda o: o.objective_id)


# --- gaps ---------------------------------------------------------------------

def test_gaps_all_are_gap():
    assert all(o.is_gap for o in gaps())


def test_gaps_sorted_by_id():
    res = gaps()
    assert list(res) == sorted(res, key=lambda o: o.objective_id)


# --- objectives_by_status -----------------------------------------------------

def test_objectives_by_status_filters():
    for status in VV_STATUSES:
        res = objectives_by_status(status)
        assert all(o.status == status for o in res)


def test_objectives_by_status_unknown_raises():
    with pytest.raises(ValueError):
        objectives_by_status("nope")


# --- VVReport -----------------------------------------------------------------

def test_report_counts_consistent():
    r = vv_report()
    assert r.conformant + r.partial + r.gap == r.total
    assert r.total == len(VV_OBJECTIVES)


def test_report_weighted_score_in_range():
    r = vv_report()
    assert 0.0 <= r.weighted_score_pct <= 100.0


def test_report_foundational_conformant_pct_in_range():
    r = vv_report()
    assert 0.0 <= r.foundational_conformant_pct <= 100.0


def test_report_has_foundational_incomplete():
    r = vv_report()
    assert r.has_foundational_incomplete is True


def test_report_by_category_sums_match():
    r = vv_report()
    c = sum(v[0] for v in r.by_category.values())
    p = sum(v[1] for v in r.by_category.values())
    g = sum(v[2] for v in r.by_category.values())
    assert (c, p, g) == (r.conformant, r.partial, r.gap)


def test_report_by_category_is_readonly():
    r = vv_report()
    with pytest.raises(TypeError):
        r.by_category["boundary_testing"] = (0, 0, 0)  # type: ignore[index]


def test_report_is_deterministic():
    a, b = vv_report(), vv_report()
    assert (a.total, a.conformant, a.partial, a.gap) == (
        b.total, b.conformant, b.partial, b.gap
    )


# --- VVReport 검증 (수동 생성) ------------------------------------------------

def test_report_rejects_negative_counts():
    with pytest.raises(ValueError):
        VVReport(
            total=1, conformant=-1, partial=1, gap=1,
            foundational_total=0, foundational_conformant=0, by_category={},
        )


def test_report_rejects_sum_mismatch():
    with pytest.raises(ValueError):
        VVReport(
            total=3, conformant=1, partial=1, gap=0,
            foundational_total=1, foundational_conformant=0, by_category={},
        )


def test_report_rejects_foundational_over_total():
    with pytest.raises(ValueError):
        VVReport(
            total=2, conformant=2, partial=0, gap=0,
            foundational_total=3, foundational_conformant=0, by_category={},
        )


def test_report_rejects_foundational_conformant_over_foundational_total():
    with pytest.raises(ValueError):
        VVReport(
            total=5, conformant=2, partial=0, gap=3,
            foundational_total=1, foundational_conformant=2, by_category={},
        )


def test_report_rejects_missing_categories():
    """total>0 이면 by_category 에 모든 카테고리가 있어야 한다."""
    with pytest.raises(ValueError):
        VVReport(
            total=2, conformant=2, partial=0, gap=0,
            foundational_total=0, foundational_conformant=0,
            by_category={"boundary_testing": (2, 0, 0)},
        )


def test_report_rejects_unknown_categories():
    with pytest.raises(ValueError):
        VVReport(
            total=2, conformant=2, partial=0, gap=0,
            foundational_total=0, foundational_conformant=0,
            by_category={"garbage": (2, 0, 0)},
        )


def test_report_rejects_by_category_sum_mismatch():
    """by_category 합이 전체 합과 불일치하면 거부."""
    with pytest.raises(ValueError):
        VVReport(
            total=2, conformant=2, partial=0, gap=0,
            foundational_total=0, foundational_conformant=0,
            by_category={cat: (1, 0, 0) if cat == "boundary_testing" else (0, 0, 0)
                         for cat in VV_CATEGORIES},
        )


def test_report_foundational_pct_zero_when_no_foundational():
    r = VVReport(
        total=0, conformant=0, partial=0, gap=0,
        foundational_total=0, foundational_conformant=0, by_category={},
    )
    assert r.foundational_conformant_pct == 0.0
    assert r.has_foundational_incomplete is False


def test_report_empty_by_category_requires_zero_counts():
    """빈 by_category 우회 불가: 합 불일치 시 거부."""
    with pytest.raises(ValueError):
        VVReport(
            total=1, conformant=1, partial=0, gap=0,
            foundational_total=0, foundational_conformant=0, by_category={},
        )


# --- 매트릭스 / 결정성 -------------------------------------------------------

def test_vv_matrix_returns_tuple_of_mappingproxy():
    rows = vv_matrix()
    assert isinstance(rows, tuple)
    assert all(isinstance(r, MappingProxyType) for r in rows)


def test_vv_matrix_covers_all():
    rows = vv_matrix()
    assert len(rows) == len(VV_OBJECTIVES)
    assert {r["objective_id"] for r in rows} == {o.objective_id for o in VV_OBJECTIVES}


def test_vv_matrix_sorted_by_category_then_id():
    rows = vv_matrix()
    seen_index = [VV_CATEGORIES.index(str(r["category"])) for r in rows]
    assert seen_index == sorted(seen_index)


def test_vv_matrix_intra_category_sorted():
    """카테고리 내부는 objective_id 알파벳 정렬이어야 한다."""
    rows = vv_matrix()
    for cat in VV_CATEGORIES:
        ids = [str(r["objective_id"]) for r in rows if r["category"] == cat]
        assert ids == sorted(ids)


def test_vv_matrix_rows_self_describing():
    """매트릭스 행은 summary 포함 전 필드를 보유해야 한다."""
    row = vv_matrix()[0]
    for key in ("objective_id", "name", "category", "anchor",
                "foundational", "status", "sdacs_module", "summary"):
        assert key in row


def test_vv_matrix_rows_are_readonly():
    row = vv_matrix()[0]
    with pytest.raises(TypeError):
        row["status"] = "hacked"  # type: ignore[index]


def test_matrix_is_deterministic():
    assert vv_matrix() == vv_matrix()


# --- CLI ----------------------------------------------------------------------

def test_cli_matrix_runs(capsys):
    assert main(["--matrix"]) == 0
    out = capsys.readouterr().out
    assert "매트릭스" in out


def test_cli_report_runs(capsys):
    assert main(["--report"]) == 0
    out = capsys.readouterr().out
    assert "EASA" in out


def test_cli_category_runs(capsys):
    assert main(["--category", "boundary_testing"]) == 0
    assert capsys.readouterr().out


def test_cli_gaps_runs(capsys):
    assert main(["--gaps"]) == 0
    assert capsys.readouterr().out


def test_cli_foundational_runs(capsys):
    assert main(["--foundational"]) == 0
    assert capsys.readouterr().out


def test_cli_default_is_report(capsys):
    assert main([]) == 0
    assert "가중 점수" in capsys.readouterr().out
