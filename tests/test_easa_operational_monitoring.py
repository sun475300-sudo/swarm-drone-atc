"""ODYSSEY Phase 457 — EASA AI 운영 모니터링·드리프트 대응 적합성 게이트 단위 테스트."""
from __future__ import annotations

import os

import pytest

from simulation.easa_operational_monitoring import (
    CONFORMANCE_STATUSES,
    MONITORING_CATEGORIES,
    MONITORING_OBJECTIVES,
    MonitoringObjective,
    MonitoringReport,
    find_objective,
    foundational_objectives,
    gaps,
    main,
    monitoring_matrix,
    monitoring_report,
    objectives_by_category,
    objectives_by_status,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _obj(**kw) -> MonitoringObjective:
    """완전 충족 기본값으로 MonitoringObjective 를 만든다 (테스트 편의)."""
    defaults = dict(
        objective_id="id",
        name="name",
        category="fallback",
        anchor="OM:FB-01",
        foundational=True,
        status="conformant",
        sdacs_module="src/rl/ppo_collision.py",
        summary="s",
    )
    defaults.update(kw)
    return MonitoringObjective(**defaults)  # type: ignore[arg-type]


# --- MonitoringObjective 검증 ----------------------------------------------

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
    assert len(MONITORING_OBJECTIVES) >= 15


def test_catalog_ids_unique():
    ids = [o.objective_id for o in MONITORING_OBJECTIVES]
    assert len(ids) == len(set(ids))


def test_all_categories_present_in_catalog():
    used = {o.category for o in MONITORING_OBJECTIVES}
    assert used == set(MONITORING_CATEGORIES)


def test_all_statuses_valid():
    assert all(o.status in CONFORMANCE_STATUSES for o in MONITORING_OBJECTIVES)


def test_cited_modules_exist_on_disk():
    """정직성 강제: 인용된 모든 sdacs_module 경로가 디스크에 실재해야 한다."""
    for o in MONITORING_OBJECTIVES:
        if o.sdacs_module is not None:
            path = os.path.join(REPO_ROOT, o.sdacs_module)
            assert os.path.exists(path), f"{o.objective_id}: missing {o.sdacs_module}"


def test_gap_objectives_have_no_module():
    for o in MONITORING_OBJECTIVES:
        if o.status == "gap":
            assert o.sdacs_module is None


def test_non_gap_objectives_cite_module():
    for o in MONITORING_OBJECTIVES:
        if o.status != "gap":
            assert o.sdacs_module


def test_anchors_unique():
    anchors = [o.anchor for o in MONITORING_OBJECTIVES]
    assert len(anchors) == len(set(anchors))


def test_catalog_has_known_gaps():
    """연구 수준 ML — 온라인 드리프트/노벨티 탐지 등 기반 갭이 정직하게 존재해야 한다."""
    gap_ids = {o.objective_id for o in gaps()}
    assert "input_distribution_drift" in gap_ids
    assert "online_model_update_management" in gap_ids


def test_fallback_authority_is_conformant():
    """SDACS 의 강점 — out-of-ODD 시 결정적 폴백은 충족이어야 한다."""
    obj = find_objective("out_of_odd_fallback")
    assert obj.status == "conformant"
    assert obj.category == "fallback"


def test_deterministic_authority_is_conformant():
    obj = find_objective("deterministic_authority_runtime")
    assert obj.status == "conformant"
    assert obj.category == "fallback"


def test_drift_detection_is_weakest_category():
    """정직성: 드리프트 탐지 카테고리가 충족 0건이어야 한다(SDACS 의 솔직한 약점)."""
    r = monitoring_report()
    conformant_in_drift, _partial, _gap = r.by_category["drift_detection"]
    assert conformant_in_drift == 0


# --- 조회 API --------------------------------------------------------------

def test_find_objective_returns_match():
    obj = find_objective("uncertainty_quantification")
    assert obj.objective_id == "uncertainty_quantification"


def test_find_objective_unknown_raises():
    with pytest.raises(KeyError):
        find_objective("nope")


def test_objectives_by_category_sorted():
    res = objectives_by_category("fallback")
    assert len(res) >= 1
    assert all(o.category == "fallback" for o in res)
    assert list(res) == sorted(res, key=lambda o: o.objective_id)


def test_objectives_by_category_unknown_raises():
    with pytest.raises(ValueError):
        objectives_by_category("nope")


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


# --- MonitoringReport ------------------------------------------------------

def test_report_counts_consistent():
    r = monitoring_report()
    assert r.conformant + r.partial + r.gap == r.total
    assert r.total == len(MONITORING_OBJECTIVES)


def test_report_by_category_sums_match():
    r = monitoring_report()
    c = sum(v[0] for v in r.by_category.values())
    p = sum(v[1] for v in r.by_category.values())
    g = sum(v[2] for v in r.by_category.values())
    assert (c, p, g) == (r.conformant, r.partial, r.gap)


def test_report_by_category_is_readonly():
    r = monitoring_report()
    with pytest.raises(TypeError):
        r.by_category["fallback"] = (0, 0, 0)  # type: ignore[index]


def test_report_weighted_score_in_range():
    r = monitoring_report()
    assert 0.0 <= r.weighted_score_pct <= 100.0


def test_report_weighted_score_is_conservative():
    """연구 수준 ML — 가중 점수는 정직하게 낮아야 한다(<60%).

    근거(어드바이저 LOW): SDACS 의 ML 은 연구 수준이므로 충족(conformant)은 폴백
    카테고리 중심의 소수에 한정된다. 60% 초과는 근거 없는 충족 주장 위험을 뜻하므로
    임계로 둔다(현 점수 ≈56%).
    """
    r = monitoring_report()
    assert r.weighted_score_pct < 60.0


def test_report_foundational_incomplete_true():
    r = monitoring_report()
    assert r.has_foundational_incomplete is True


def test_report_rejects_inconsistent_counts():
    with pytest.raises(ValueError):
        MonitoringReport(
            total=3, conformant=1, partial=1, gap=0,
            foundational_total=1, foundational_conformant=0, by_category={},
        )


def test_report_rejects_negative_counts():
    with pytest.raises(ValueError):
        MonitoringReport(
            total=1, conformant=-1, partial=1, gap=1,
            foundational_total=0, foundational_conformant=0, by_category={},
        )


def test_report_rejects_foundational_over_total():
    with pytest.raises(ValueError):
        MonitoringReport(
            total=2, conformant=2, partial=0, gap=0,
            foundational_total=3, foundational_conformant=0, by_category={},
        )


def test_report_rejects_foundational_conformant_over_foundational_total():
    with pytest.raises(ValueError):
        MonitoringReport(
            total=5, conformant=2, partial=0, gap=3,
            foundational_total=1, foundational_conformant=2, by_category={},
        )


def test_report_rejects_mismatched_by_category():
    with pytest.raises(ValueError):
        MonitoringReport(
            total=2, conformant=2, partial=0, gap=0,
            foundational_total=0, foundational_conformant=0,
            by_category={"fallback": (1, 0, 0)},
        )


def test_report_rejects_unknown_by_category_key():
    with pytest.raises(ValueError):
        MonitoringReport(
            total=2, conformant=2, partial=0, gap=0,
            foundational_total=0, foundational_conformant=0,
            by_category={"garbage": (2, 0, 0)},
        )


def test_report_foundational_pct_zero_when_no_foundational():
    # 빈 by_category 는 합 (0,0,0) 이므로 conformant/partial/gap·total 모두 0 이어야 한다.
    r = MonitoringReport(
        total=0, conformant=0, partial=0, gap=0,
        foundational_total=0, foundational_conformant=0, by_category={},
    )
    assert r.foundational_conformant_pct == 0.0
    assert r.has_foundational_incomplete is False


def test_report_empty_by_category_requires_zero_counts():
    """빈 by_category 우회 불가(어드바이저 MEDIUM): 합 불일치 시 거부."""
    with pytest.raises(ValueError):
        MonitoringReport(
            total=1, conformant=1, partial=0, gap=0,
            foundational_total=0, foundational_conformant=0, by_category={},
        )


# --- 매트릭스 / 결정성 -----------------------------------------------------

def test_monitoring_matrix_covers_all():
    rows = monitoring_matrix()
    assert len(rows) == len(MONITORING_OBJECTIVES)
    assert {r["objective_id"] for r in rows} == {o.objective_id for o in MONITORING_OBJECTIVES}


def test_monitoring_matrix_category_grouped():
    rows = monitoring_matrix()
    seen_index = [MONITORING_CATEGORIES.index(str(r["category"])) for r in rows]
    assert seen_index == sorted(seen_index)


def test_monitoring_matrix_intra_category_sorted():
    """카테고리 내부는 objective_id 알파벳 정렬이어야 한다(어드바이저 LOW)."""
    rows = monitoring_matrix()
    for cat in MONITORING_CATEGORIES:
        ids = [str(r["objective_id"]) for r in rows if r["category"] == cat]
        assert ids == sorted(ids)


def test_monitoring_matrix_rows_self_describing():
    """매트릭스 행은 summary 포함 전 필드를 보유해 카탈로그 없이 재구성 가능해야 한다."""
    row = monitoring_matrix()[0]
    for key in ("objective_id", "name", "category", "anchor",
                "foundational", "status", "sdacs_module", "summary"):
        assert key in row


def test_monitoring_matrix_rows_are_readonly():
    row = monitoring_matrix()[0]
    with pytest.raises(TypeError):
        row["status"] = "hacked"  # type: ignore[index]


def test_report_is_deterministic():
    a, b = monitoring_report(), monitoring_report()
    assert (a.total, a.conformant, a.partial, a.gap) == (
        b.total, b.conformant, b.partial, b.gap
    )


def test_matrix_is_deterministic():
    assert monitoring_matrix() == monitoring_matrix()


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
    assert capsys.readouterr().out  # 갭 목록 비어있지 않음(어드바이저 LOW)


def test_cli_category_runs(capsys):
    assert main(["--category", "fallback"]) == 0
    assert capsys.readouterr().out


def test_cli_foundational_runs(capsys):
    assert main(["--foundational"]) == 0
    assert capsys.readouterr().out


def test_cli_default_is_report(capsys):
    assert main([]) == 0
    assert "가중 점수" in capsys.readouterr().out
