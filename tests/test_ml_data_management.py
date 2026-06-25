"""ODYSSEY Phase 455 — ML 데이터 관리 적합성 게이트 단위 테스트."""

import pathlib

import pytest

from simulation import ml_data_management as mod
from simulation.ml_data_management import (
    CRITICALITIES,
    DATA_OBJECTIVES,
    LIFECYCLE_STAGES,
    OBJECTIVE_STATUSES,
    VERDICT_AT_RISK,
    VERDICT_MANAGED,
    VERDICT_NOT_READY,
    DataManagementReport,
    DataObjective,
    artifacts_intact,
    assess_data_management,
    audit_cited_artifacts,
    data_matrix,
    find_objective,
    foundational_objectives,
    gaps,
    objectives_by_stage,
)

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


# --- 카탈로그 무결성 ----------------------------------------------------------

class TestCatalogIntegrity:
    def test_catalog_non_empty(self):
        assert len(DATA_OBJECTIVES) >= 10

    def test_objective_ids_unique(self):
        ids = [obj.objective_id for obj in DATA_OBJECTIVES]
        assert len(ids) == len(set(ids))

    def test_all_statuses_valid(self):
        for obj in DATA_OBJECTIVES:
            assert obj.status in OBJECTIVE_STATUSES

    def test_all_stages_valid(self):
        for obj in DATA_OBJECTIVES:
            assert obj.stage in LIFECYCLE_STAGES

    def test_all_criticalities_valid(self):
        for obj in DATA_OBJECTIVES:
            assert obj.criticality in CRITICALITIES

    def test_has_at_least_one_foundational(self):
        assert any(obj.is_foundational for obj in DATA_OBJECTIVES)

    def test_every_stage_has_an_objective(self):
        present = {obj.stage for obj in DATA_OBJECTIVES}
        assert present == set(LIFECYCLE_STAGES)

    def test_ids_are_snake_case(self):
        for obj in DATA_OBJECTIVES:
            assert obj.objective_id == obj.objective_id.lower()
            assert " " not in obj.objective_id


# --- 정직성 결속: gap ⟺ evidence None ----------------------------------------

class TestHonestyBinding:
    def test_gap_has_no_evidence(self):
        for obj in DATA_OBJECTIVES:
            if obj.status == "gap":
                assert obj.evidence is None

    def test_non_gap_cites_evidence(self):
        for obj in DATA_OBJECTIVES:
            if obj.status != "gap":
                assert obj.evidence and obj.evidence.strip()

    def test_cited_evidence_exists_on_disk(self):
        for obj in DATA_OBJECTIVES:
            if obj.evidence is not None:
                path = _REPO_ROOT / obj.evidence
                assert path.exists(), f"missing evidence: {obj.evidence}"

    def test_at_least_one_real_world_gap(self):
        """정직 공시: 실세계 데이터 출처는 갭이어야 한다(시뮬 생성 한계)."""
        assert find_objective("real_world_data_provenance").is_gap


# --- DataObjective 검증 -------------------------------------------------------

class TestObjectiveValidation:
    def test_rejects_empty_id(self):
        with pytest.raises(ValueError):
            DataObjective("", "n", "requirements", "foundational", "satisfied", "x.py", "s")

    def test_rejects_padded_id(self):
        with pytest.raises(ValueError):
            DataObjective(" x ", "n", "requirements", "foundational", "satisfied", "x.py", "s")

    def test_rejects_id_with_space(self):
        with pytest.raises(ValueError):
            DataObjective("a b", "n", "requirements", "foundational", "satisfied", "x.py", "s")

    def test_rejects_id_with_tab(self):
        with pytest.raises(ValueError):
            DataObjective("a\tb", "n", "requirements", "foundational", "satisfied", "x.py", "s")

    def test_rejects_non_lowercase_id(self):
        with pytest.raises(ValueError):
            DataObjective("camelCase", "n", "requirements", "foundational", "satisfied", "x.py", "s")

    def test_rejects_empty_name(self):
        with pytest.raises(ValueError):
            DataObjective("x", "  ", "requirements", "foundational", "satisfied", "x.py", "s")

    def test_rejects_empty_summary(self):
        with pytest.raises(ValueError):
            DataObjective("x", "n", "requirements", "foundational", "satisfied", "x.py", "  ")

    def test_rejects_bad_stage(self):
        with pytest.raises(ValueError):
            DataObjective("x", "n", "nope", "foundational", "satisfied", "x.py", "s")

    def test_rejects_bad_criticality(self):
        with pytest.raises(ValueError):
            DataObjective("x", "n", "requirements", "kinda", "satisfied", "x.py", "s")

    def test_rejects_bad_status(self):
        with pytest.raises(ValueError):
            DataObjective("x", "n", "requirements", "foundational", "maybe", "x.py", "s")

    def test_gap_with_evidence_rejected(self):
        with pytest.raises(ValueError):
            DataObjective("x", "n", "requirements", "foundational", "gap", "x.py", "s")

    def test_satisfied_without_evidence_rejected(self):
        with pytest.raises(ValueError):
            DataObjective("x", "n", "requirements", "foundational", "satisfied", None, "s")

    def test_partial_without_evidence_rejected(self):
        with pytest.raises(ValueError):
            DataObjective("x", "n", "requirements", "recommended", "partial", "   ", "s")

    def test_frozen(self):
        obj = DATA_OBJECTIVES[0]
        with pytest.raises((AttributeError, TypeError)):
            obj.status = "partial"  # type: ignore[misc]

    def test_weight_values(self):
        sa = DataObjective("a", "n", "requirements", "foundational", "satisfied", "x.py", "s")
        pa = DataObjective("b", "n", "requirements", "foundational", "partial", "x.py", "s")
        ga = DataObjective("c", "n", "requirements", "foundational", "gap", None, "s")
        assert (sa.weight, pa.weight, ga.weight) == (1.0, 0.5, 0.0)

    def test_is_foundational_property(self):
        assert find_objective("real_world_data_provenance").is_foundational


# --- 인용 산출물 디스크 감사 --------------------------------------------------

class TestArtifactAudit:
    def test_current_repo_artifacts_intact(self):
        """현 리포: 인용 산출물이 전부 디스크에 실재한다."""
        assert audit_cited_artifacts() == ()

    def test_artifacts_intact_true(self):
        assert artifacts_intact() is True

    def test_audit_is_deterministic(self):
        assert audit_cited_artifacts() == audit_cited_artifacts()

    def test_audit_detects_missing_artifact(self, tmp_path, monkeypatch):
        """인용 경로가 사라지면 감사가 부재로 표면화한다."""
        monkeypatch.setattr(mod, "_REPO_ROOT", tmp_path)  # 빈 루트 → 전부 부재
        missing = audit_cited_artifacts()
        # 갭(evidence None)은 감사 대상이 아니므로, 충족/부분 개수만큼 부재로 잡힌다.
        non_gap = [o for o in DATA_OBJECTIVES if o.evidence is not None]
        assert len(missing) == len({o.evidence for o in non_gap})


# --- 판정 (verdict) -----------------------------------------------------------

class TestAssess:
    def test_returns_report(self):
        assert isinstance(assess_data_management(), DataManagementReport)

    def test_current_repo_not_ready(self):
        """현 리포: 실세계 출처 갭(기반)으로 DATA_NOT_READY (정직 공시)."""
        assert assess_data_management().verdict == VERDICT_NOT_READY

    def test_counts_sum_to_total(self):
        r = assess_data_management()
        assert r.satisfied + r.partial + r.gap == r.total

    def test_foundational_satisfied_le_total(self):
        r = assess_data_management()
        assert r.foundational_satisfied <= r.foundational_total <= r.total

    def test_weighted_score_in_range(self):
        assert 0.0 <= assess_data_management().weighted_score_pct <= 100.0

    def test_score_is_conservative(self):
        """정직 공시: 시뮬 데이터 한계로 만점이 아니다."""
        assert assess_data_management().weighted_score_pct < 100.0

    def test_by_stage_sums_match(self):
        r = assess_data_management()
        s = sum(v[0] for v in r.by_stage.values())
        p = sum(v[1] for v in r.by_stage.values())
        g = sum(v[2] for v in r.by_stage.values())
        assert (s, p, g) == (r.satisfied, r.partial, r.gap)

    def test_by_stage_read_only(self):
        r = assess_data_management()
        with pytest.raises(TypeError):
            r.by_stage["collection"] = (0, 0, 0)  # type: ignore[index]

    def test_is_managed_property(self):
        assert assess_data_management().is_managed is False

    def test_deterministic(self):
        a, b = assess_data_management(), assess_data_management()
        assert (a.verdict, a.satisfied, a.partial, a.gap) == (
            b.verdict, b.satisfied, b.partial, b.gap
        )


# --- verdict 우선순위 (_verdict_for) -----------------------------------------

class TestVerdictPriority:
    def _obj(self, crit, status):
        ev = None if status == "gap" else "simulation/ml_data_management.py"
        return DataObjective(f"o_{crit}_{status}", "n", "requirements", crit, status, ev, "s")

    def test_foundational_gap_not_ready(self):
        objs = (self._obj("foundational", "gap"), self._obj("recommended", "satisfied"))
        assert mod._verdict_for(objs) == VERDICT_NOT_READY

    def test_foundational_partial_at_risk(self):
        objs = (self._obj("foundational", "partial"), self._obj("recommended", "satisfied"))
        assert mod._verdict_for(objs) == VERDICT_AT_RISK

    def test_all_foundational_satisfied_managed(self):
        objs = (self._obj("foundational", "satisfied"), self._obj("recommended", "partial"))
        assert mod._verdict_for(objs) == VERDICT_MANAGED

    def test_recommended_gap_does_not_block(self):
        objs = (self._obj("foundational", "satisfied"), self._obj("recommended", "gap"))
        assert mod._verdict_for(objs) == VERDICT_MANAGED

    def test_gap_beats_partial(self):
        objs = (self._obj("foundational", "gap"), self._obj("foundational", "partial"))
        assert mod._verdict_for(objs) == VERDICT_NOT_READY

    def test_no_foundational_not_ready(self):
        objs = (self._obj("recommended", "satisfied"),)
        assert mod._verdict_for(objs) == VERDICT_NOT_READY

    def test_empty_objectives_not_ready(self):
        assert mod._verdict_for(()) == VERDICT_NOT_READY


# --- 산출물 부재 시 강등 (assess 의 정직성) ----------------------------------

class TestArtifactDowngrade:
    def test_missing_artifact_downgrades_to_gap(self, tmp_path, monkeypatch):
        """인용 산출물이 사라지면 정적 satisfied/partial 선언이 gap 으로 강등된다."""
        monkeypatch.setattr(mod, "_REPO_ROOT", tmp_path)  # 전부 부재
        r = assess_data_management()
        # 모든 비-gap 목표가 gap 으로 강등 → satisfied/partial 0.
        assert r.satisfied == 0 and r.partial == 0
        assert r.gap == r.total
        assert r.verdict == VERDICT_NOT_READY

    def test_downgrade_preserves_honesty_binding(self, tmp_path, monkeypatch):
        """강등된 목표는 근거 None 으로 정직성 결속(gap ⟺ evidence None)을 유지.

        DataObjective.__post_init__ 가 gap+근거 공존을 거부하므로, assess 가 크래시 없이
        전부 gap 으로 강등된다는 사실 자체가 결속 유지의 증거다. by_stage 합도 전부 갭임을
        명시 검증해 결속을 가독화한다(어드바이저 MEDIUM 반영).
        """
        monkeypatch.setattr(mod, "_REPO_ROOT", tmp_path)
        r = assess_data_management()  # 크래시 없이 검증 통과해야 함
        assert r.is_managed is False
        assert r.satisfied == 0 and r.partial == 0 and r.gap == r.total
        for stage_counts in r.by_stage.values():
            assert stage_counts[0] == 0 and stage_counts[1] == 0  # 충족·부분 없음


# --- DataManagementReport 검증 ------------------------------------------------

class TestReportValidation:
    def _ok_by_stage(self):
        return {
            "requirements": (1, 0, 0), "collection": (0, 1, 0),
            "preprocessing": (0, 0, 0), "verification": (0, 0, 1),
        }

    def test_counts_mismatch_rejected(self):
        with pytest.raises(ValueError):
            DataManagementReport(VERDICT_MANAGED, 3, 1, 0, 0, 1, 1, self._ok_by_stage())

    def test_negative_rejected(self):
        with pytest.raises(ValueError):
            DataManagementReport(VERDICT_MANAGED, 3, -1, 1, 1, 1, 1, self._ok_by_stage())

    def test_foundational_satisfied_over_total_rejected(self):
        with pytest.raises(ValueError):
            DataManagementReport(VERDICT_MANAGED, 3, 1, 1, 1, 1, 2, self._ok_by_stage())

    def test_bad_verdict_rejected(self):
        with pytest.raises(ValueError):
            DataManagementReport("NOPE", 3, 1, 1, 1, 1, 1, self._ok_by_stage())

    def test_unknown_stage_key_rejected(self):
        with pytest.raises(ValueError):
            DataManagementReport(
                VERDICT_MANAGED, 2, 1, 1, 0, 1, 1,
                {"requirements": (1, 0, 0), "bogus": (0, 1, 0)},
            )

    def test_by_stage_sum_mismatch_rejected(self):
        with pytest.raises(ValueError):
            DataManagementReport(
                VERDICT_MANAGED, 2, 2, 0, 0, 1, 1,
                {"requirements": (1, 0, 0), "collection": (0, 0, 0)},
            )

    def test_empty_total_score_zero(self):
        r = DataManagementReport(VERDICT_NOT_READY, 0, 0, 0, 0, 0, 0, {})
        assert r.weighted_score_pct == 0.0

    def test_empty_by_stage_with_nonzero_counts_rejected(self):
        with pytest.raises(ValueError):
            DataManagementReport(VERDICT_MANAGED, 2, 1, 1, 0, 1, 1, {})

    def test_missing_stage_key_rejected(self):
        """비-빈 리포트에 단계 키가 빠지면 거부(어드바이저 MEDIUM — 표시 시점 KeyError 차단)."""
        with pytest.raises(ValueError):
            DataManagementReport(
                VERDICT_MANAGED, 1, 1, 0, 0, 1, 1,
                {"requirements": (1, 0, 0)},  # collection·preprocessing·verification 누락
            )


# --- 조회 API -----------------------------------------------------------------

class TestQueryApi:
    def test_find_objective(self):
        assert find_objective("train_test_holdout").is_foundational

    def test_find_unknown_raises(self):
        with pytest.raises(KeyError):
            find_objective("nope")

    def test_objectives_by_stage_sorted(self):
        objs = objectives_by_stage("verification")
        ids = [o.objective_id for o in objs]
        assert ids == sorted(ids)
        assert all(o.stage == "verification" for o in objs)

    def test_objectives_by_stage_bad_value(self):
        with pytest.raises(ValueError):
            objectives_by_stage("nope")

    def test_foundational_objectives_sorted(self):
        objs = foundational_objectives()
        ids = [o.objective_id for o in objs]
        assert ids == sorted(ids)
        assert all(o.is_foundational for o in objs)

    def test_gaps_only_gap(self):
        assert all(o.is_gap for o in gaps())

    def test_gaps_sorted(self):
        ids = [o.objective_id for o in gaps()]
        assert ids == sorted(ids)


# --- data_matrix --------------------------------------------------------------

class TestDataMatrix:
    def test_row_count(self):
        assert len(data_matrix()) == len(DATA_OBJECTIVES)

    def test_rows_read_only(self):
        row = data_matrix()[0]
        with pytest.raises(TypeError):
            row["status"] = "x"  # type: ignore[index]

    def test_sorted_by_stage_then_id(self):
        rows = data_matrix()
        keys = [(LIFECYCLE_STAGES.index(str(r["stage"])), r["objective_id"]) for r in rows]
        assert keys == sorted(keys)

    def test_gap_rows_have_no_evidence(self):
        for row in data_matrix():
            if row["status"] == "gap":
                assert row["evidence"] is None


# --- CLI ----------------------------------------------------------------------

class TestCli:
    def test_objectives(self, capsys):
        assert mod.main(["--objectives"]) == 0
        assert "데이터 관리" in capsys.readouterr().out

    def test_report(self, capsys):
        assert mod.main(["--report"]) == 0
        out = capsys.readouterr().out
        assert "판정" in out and VERDICT_NOT_READY in out

    def test_audit(self, capsys):
        assert mod.main(["--audit"]) == 0
        assert "감사" in capsys.readouterr().out

    def test_gaps(self, capsys):
        assert mod.main(["--gaps"]) == 0

    def test_foundational(self, capsys):
        assert mod.main(["--foundational"]) == 0
        assert "→" in capsys.readouterr().out

    def test_stage(self, capsys):
        assert mod.main(["--stage", "collection"]) == 0

    def test_default_prints_report(self, capsys):
        assert mod.main([]) == 0
        assert "판정" in capsys.readouterr().out
