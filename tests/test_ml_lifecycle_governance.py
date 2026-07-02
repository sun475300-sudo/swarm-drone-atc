"""ODYSSEY Phase 460 — EASA ML 수명주기 거버넌스 적합성 게이트 단위 테스트."""
from __future__ import annotations

import os

import pytest

from simulation.ml_lifecycle_governance import (
    LIFECYCLE_CATEGORIES,
    LIFECYCLE_OBJECTIVES,
    LIFECYCLE_STATUSES,
    LifecycleObjective,
    LifecycleReport,
    find_objective,
    foundational_objectives,
    gaps,
    lifecycle_matrix,
    lifecycle_report,
    main,
    objectives_by_category,
    objectives_by_status,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _obj(**kw) -> LifecycleObjective:
    """완전 충족 기본값으로 LifecycleObjective 를 만든다 (테스트 편의)."""
    defaults = dict(
        objective_id="id",
        name="name",
        category="deployment_authorization",
        anchor="LG:DA-01",
        foundational=True,
        status="conformant",
        sdacs_module="src/rl/ppo_collision.py",
        summary="s",
    )
    defaults.update(kw)
    return LifecycleObjective(**defaults)  # type: ignore[arg-type]


# --- LifecycleObjective 불변식 ------------------------------------------------

def test_objective_rejects_empty_id():
    with pytest.raises(ValueError):
        _obj(objective_id="")


def test_objective_rejects_padded_id():
    with pytest.raises(ValueError):
        _obj(objective_id=" id ")


def test_objective_rejects_spaced_id():
    with pytest.raises(ValueError):
        _obj(objective_id="bad id")


def test_objective_rejects_empty_name():
    with pytest.raises(ValueError):
        _obj(name="  ")


def test_objective_rejects_empty_anchor():
    with pytest.raises(ValueError):
        _obj(anchor="")


def test_objective_rejects_empty_summary():
    with pytest.raises(ValueError):
        _obj(summary="")


def test_objective_rejects_unknown_category():
    with pytest.raises(ValueError):
        _obj(category="nonexistent")


def test_objective_rejects_non_bool_foundational():
    with pytest.raises(TypeError):
        _obj(foundational=1)


def test_objective_rejects_unknown_status():
    with pytest.raises(ValueError):
        _obj(status="unknown")


def test_objective_rejects_tab_in_id():
    """snake_case 강제 — 공백 외 탭도 거부해야 한다."""
    with pytest.raises(ValueError):
        _obj(objective_id="id\ttab")


def test_objective_rejects_newline_in_id():
    with pytest.raises(ValueError):
        _obj(objective_id="col\nlumn")


def test_objective_rejects_uppercase_id():
    with pytest.raises(ValueError):
        _obj(objective_id="BadId")


def test_objective_rejects_digit_leading_id():
    with pytest.raises(ValueError):
        _obj(objective_id="1abc")


# --- 정직성 결속: gap ⟺ 근거 없음 --------------------------------------------

def test_gap_must_not_cite_module():
    with pytest.raises(ValueError):
        _obj(status="gap", sdacs_module="src/rl/ppo_collision.py")


def test_conformant_must_cite_module():
    with pytest.raises(ValueError):
        _obj(status="conformant", sdacs_module=None)


def test_partial_must_cite_module():
    with pytest.raises(ValueError):
        _obj(status="partial", sdacs_module="")


def test_gap_with_none_module_is_valid():
    o = _obj(status="gap", sdacs_module=None)
    assert o.is_gap is True
    assert o.weight == 0.0


def test_partial_with_module_is_valid():
    o = _obj(status="partial", sdacs_module="src/training/domain_rand.py")
    assert o.is_gap is False
    assert o.weight == 0.5


def test_weight_values_by_status():
    assert _obj(status="conformant").weight == 1.0
    assert _obj(status="partial").weight == 0.5
    assert _obj(status="gap", sdacs_module=None).weight == 0.0


# --- 카탈로그 무결성 -----------------------------------------------------------

def test_catalog_non_empty():
    assert len(LIFECYCLE_OBJECTIVES) >= 15


def test_catalog_ids_unique():
    ids = [o.objective_id for o in LIFECYCLE_OBJECTIVES]
    assert len(ids) == len(set(ids))


def test_catalog_categories_valid():
    for o in LIFECYCLE_OBJECTIVES:
        assert o.category in LIFECYCLE_CATEGORIES


def test_catalog_statuses_valid():
    for o in LIFECYCLE_OBJECTIVES:
        assert o.status in LIFECYCLE_STATUSES


def test_catalog_anchors_unique():
    """각 목표의 EASA 참조 토큰(anchor)은 고유해야 한다."""
    anchors = [o.anchor for o in LIFECYCLE_OBJECTIVES]
    assert len(anchors) == len(set(anchors))


def test_catalog_all_foundational_are_bool():
    for o in LIFECYCLE_OBJECTIVES:
        assert isinstance(o.foundational, bool)


def test_cited_modules_exist_on_disk():
    """충족/부분 목표가 인용한 경로는 디스크에 실재해야 한다 (허위 충족 차단)."""
    for o in LIFECYCLE_OBJECTIVES:
        if o.sdacs_module is not None:
            path = os.path.join(REPO_ROOT, o.sdacs_module)
            assert os.path.exists(path), f"{o.objective_id}: missing {o.sdacs_module}"


def test_gap_objectives_have_no_module():
    for o in LIFECYCLE_OBJECTIVES:
        if o.is_gap:
            assert o.sdacs_module is None


def test_non_gap_objectives_have_module():
    for o in LIFECYCLE_OBJECTIVES:
        if not o.is_gap:
            assert o.sdacs_module is not None
            assert o.sdacs_module.strip()


def test_all_categories_present_in_catalog():
    """모든 카테고리에 최소 1건의 목표가 존재해야 한다."""
    used = {o.category for o in LIFECYCLE_OBJECTIVES}
    assert used == set(LIFECYCLE_CATEGORIES)


# --- 카테고리별 존재 검증 (모든 카테고리에 최소 1건) ----------------------------

@pytest.mark.parametrize("category", list(LIFECYCLE_CATEGORIES))
def test_every_category_has_at_least_one_objective(category):
    assert len(objectives_by_category(category)) >= 1


# --- 조회 API ----------------------------------------------------------------

def test_find_objective_roundtrip():
    o = LIFECYCLE_OBJECTIVES[0]
    assert find_objective(o.objective_id) is o


def test_find_objective_unknown_raises():
    with pytest.raises(KeyError):
        find_objective("does_not_exist")


def test_objectives_by_category_sorted_and_scoped():
    for category in LIFECYCLE_CATEGORIES:
        members = objectives_by_category(category)
        assert all(o.category == category for o in members)
        assert list(members) == sorted(members, key=lambda o: o.objective_id)


def test_objectives_by_category_rejects_unknown():
    with pytest.raises(ValueError):
        objectives_by_category("nonexistent")


def test_objectives_by_category_partition_covers_catalog():
    seen = sum(len(objectives_by_category(c)) for c in LIFECYCLE_CATEGORIES)
    assert seen == len(LIFECYCLE_OBJECTIVES)


def test_objectives_by_status_scoped():
    for status in LIFECYCLE_STATUSES:
        members = objectives_by_status(status)
        assert all(o.status == status for o in members)
        assert list(members) == sorted(members, key=lambda o: o.objective_id)


def test_objectives_by_status_rejects_unknown():
    with pytest.raises(ValueError):
        objectives_by_status("unknown")


def test_objectives_by_status_partition_covers_catalog():
    seen = sum(len(objectives_by_status(s)) for s in LIFECYCLE_STATUSES)
    assert seen == len(LIFECYCLE_OBJECTIVES)


def test_foundational_objectives_subset():
    f = foundational_objectives()
    assert all(o.foundational for o in f)
    assert len(f) >= 1


def test_foundational_objectives_sorted():
    f = foundational_objectives()
    assert list(f) == sorted(f, key=lambda o: o.objective_id)


def test_gaps_returns_only_gaps():
    g = gaps()
    assert all(o.is_gap for o in g)


def test_gaps_sorted():
    g = gaps()
    assert list(g) == sorted(g, key=lambda o: o.objective_id)


# --- 핵심 정직성 주장 ---------------------------------------------------------

def test_catalog_has_known_gaps():
    """연구 수준 ML — 정식 거버넌스 인프라 갭이 정직하게 존재해야 한다."""
    gap_ids = {o.objective_id for o in gaps()}
    assert "experiment_tracking" in gap_ids
    assert "deployment_gate_process" in gap_ids
    assert "training_data_provenance" in gap_ids
    assert "incident_response_procedure" in gap_ids


def test_advisory_only_deployment_is_conformant():
    """SDACS 의 강점 — ML 자문 전용 배포 제약은 충족이어야 한다."""
    obj = find_objective("advisory_only_deployment_constraint")
    assert obj.status == "conformant"
    assert obj.category == "deployment_authorization"


def test_tool_qualification_is_gap():
    obj = find_objective("tool_qualification")
    assert obj.is_gap is True


def test_data_versioning_is_gap():
    obj = find_objective("data_versioning")
    assert obj.is_gap is True


def test_continuous_airworthiness_governance_is_gap():
    obj = find_objective("continuous_airworthiness_governance")
    assert obj.is_gap is True


def test_model_retirement_policy_is_gap():
    obj = find_objective("model_retirement_policy")
    assert obj.is_gap is True


# --- 리포트 집계 ---------------------------------------------------------------

def test_report_counts_consistent():
    r = lifecycle_report()
    assert r.conformant + r.partial + r.gap == r.total
    assert r.total == len(LIFECYCLE_OBJECTIVES)


def test_report_by_category_sums_match():
    r = lifecycle_report()
    c = sum(v[0] for v in r.by_category.values())
    p = sum(v[1] for v in r.by_category.values())
    g = sum(v[2] for v in r.by_category.values())
    assert (c, p, g) == (r.conformant, r.partial, r.gap)


def test_report_by_category_is_read_only():
    r = lifecycle_report()
    with pytest.raises(TypeError):
        r.by_category["deployment_authorization"] = (0, 0, 0)  # type: ignore[index]


def test_report_score_conservative():
    """SDACS 의 ML 거버넌스는 연구 수준 — 점수는 50% 미만의 보수적 값이어야 한다."""
    r = lifecycle_report()
    assert 0.0 < r.weighted_score_pct < 50.0


def test_report_foundational_incomplete():
    """기반 거버넌스 목표는 다수 미충족(실험 추적·배포 게이트·데이터 출처 갭)이어야 한다."""
    r = lifecycle_report()
    assert r.has_foundational_incomplete is True


def test_report_deterministic():
    r1 = lifecycle_report()
    r2 = lifecycle_report()
    assert r1 == r2


def test_report_foundational_conformant_pct_range():
    r = lifecycle_report()
    assert 0.0 <= r.foundational_conformant_pct <= 100.0


def test_report_weighted_score_in_range():
    r = lifecycle_report()
    assert 0.0 <= r.weighted_score_pct <= 100.0


# --- LifecycleReport 직접 생성 불변식 ------------------------------------------

def test_report_rejects_count_mismatch():
    with pytest.raises(ValueError):
        LifecycleReport(
            total=10, conformant=1, partial=1, gap=1,
            foundational_total=1, foundational_conformant=0, by_category={},
        )


def test_report_rejects_negative_counts():
    with pytest.raises(ValueError):
        LifecycleReport(
            total=-1, conformant=0, partial=0, gap=0,
            foundational_total=0, foundational_conformant=0, by_category={},
        )


def test_report_rejects_unknown_category_key():
    with pytest.raises(ValueError):
        LifecycleReport(
            total=1, conformant=1, partial=0, gap=0,
            foundational_total=0, foundational_conformant=0,
            by_category={
                "development_environment": (1, 0, 0), "data_governance": (0, 0, 0),
                "configuration_management": (0, 0, 0), "deployment_authorization": (0, 0, 0),
                "post_deployment_governance": (0, 0, 0), "strangers": (0, 0, 0),
            },
        )


def test_report_rejects_empty_by_category_when_total_positive():
    """total>0 인데 by_category 가 비면 교차검증 우회 — 거부해야 한다 (정직성 결속)."""
    with pytest.raises(ValueError):
        LifecycleReport(
            total=1, conformant=1, partial=0, gap=0,
            foundational_total=0, foundational_conformant=0, by_category={},
        )


def test_report_rejects_category_sum_mismatch():
    """by_category 합이 상위 총계와 어긋나면 거부해야 한다."""
    with pytest.raises(ValueError):
        LifecycleReport(
            total=1, conformant=1, partial=0, gap=0,
            foundational_total=0, foundational_conformant=0,
            by_category={
                "development_environment": (0, 0, 1), "data_governance": (0, 0, 0),
                "configuration_management": (0, 0, 0), "deployment_authorization": (0, 0, 0),
                "post_deployment_governance": (0, 0, 0),
            },
        )


def test_report_rejects_nonempty_by_category_when_total_zero():
    with pytest.raises(ValueError):
        LifecycleReport(
            total=0, conformant=0, partial=0, gap=0,
            foundational_total=0, foundational_conformant=0,
            by_category={"development_environment": (0, 0, 0)},
        )


def test_report_rejects_foundational_overflow():
    with pytest.raises(ValueError):
        LifecycleReport(
            total=1, conformant=1, partial=0, gap=0,
            foundational_total=1, foundational_conformant=2, by_category={},
        )


def test_report_rejects_foundational_exceeds_total():
    with pytest.raises(ValueError):
        LifecycleReport(
            total=1, conformant=1, partial=0, gap=0,
            foundational_total=2, foundational_conformant=2, by_category={},
        )


def test_report_empty_score_zero():
    r = LifecycleReport(
        total=0, conformant=0, partial=0, gap=0,
        foundational_total=0, foundational_conformant=0, by_category={},
    )
    assert r.weighted_score_pct == 0.0
    assert r.foundational_conformant_pct == 0.0
    assert r.has_foundational_incomplete is False


def test_report_by_category_coerces_plain_dict():
    """by_category 가 일반 dict 로 주어져도 MappingProxyType 으로 동결돼야 한다."""
    r = LifecycleReport(
        total=1, conformant=1, partial=0, gap=0,
        foundational_total=0, foundational_conformant=0,
        by_category={
            "development_environment": (1, 0, 0), "data_governance": (0, 0, 0),
            "configuration_management": (0, 0, 0), "deployment_authorization": (0, 0, 0),
            "post_deployment_governance": (0, 0, 0),
        },
    )
    with pytest.raises(TypeError):
        r.by_category["data_governance"] = (9, 9, 9)  # type: ignore[index]


# --- 매트릭스 -----------------------------------------------------------------

def test_matrix_rows_self_describing():
    rows = lifecycle_matrix()
    assert len(rows) == len(LIFECYCLE_OBJECTIVES)
    keys = {"objective_id", "name", "category", "anchor",
            "foundational", "status", "sdacs_module", "summary"}
    for row in rows:
        assert keys <= set(row.keys())


def test_matrix_rows_read_only():
    row = lifecycle_matrix()[0]
    with pytest.raises(TypeError):
        row["status"] = "conformant"  # type: ignore[index]


def test_matrix_ordered_by_category():
    rows = lifecycle_matrix()
    order = [LIFECYCLE_CATEGORIES.index(str(r["category"])) for r in rows]
    assert order == sorted(order)


def test_matrix_matches_catalog_ids():
    matrix_ids = {str(r["objective_id"]) for r in lifecycle_matrix()}
    catalog_ids = {o.objective_id for o in LIFECYCLE_OBJECTIVES}
    assert matrix_ids == catalog_ids


def test_matrix_intra_category_sorted():
    """카테고리 내부는 objective_id 알파벳 정렬이어야 한다."""
    rows = lifecycle_matrix()
    for cat in LIFECYCLE_CATEGORIES:
        ids = [str(r["objective_id"]) for r in rows if r["category"] == cat]
        assert ids == sorted(ids)


def test_matrix_is_deterministic():
    assert lifecycle_matrix() == lifecycle_matrix()


# --- CLI -----------------------------------------------------------------------

@pytest.mark.parametrize("flag", [
    "--matrix", "--report", "--gaps", "--foundational",
])
def test_cli_flags(flag, capsys):
    assert main([flag]) == 0
    assert capsys.readouterr().out.strip()


def test_cli_category(capsys):
    assert main(["--category", "deployment_authorization"]) == 0
    assert capsys.readouterr().out.strip()


def test_cli_default_is_report(capsys):
    assert main([]) == 0
    assert "거버넌스" in capsys.readouterr().out


def test_cli_invalid_category_rejected():
    with pytest.raises(SystemExit):
        main(["--category", "nonexistent"])
