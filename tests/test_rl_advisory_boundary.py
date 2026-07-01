"""ODYSSEY Phase 453 — RL 자문 경계 정합성 게이트 단위 테스트."""

import pathlib

import pytest

from simulation import rl_advisory_boundary as mod
from simulation.rl_advisory_boundary import (
    ACTIVE_LOOP_MODULES,
    BOUNDARY_INVARIANTS,
    CRITICALITIES,
    INVARIANT_STATUSES,
    ML_IMPORT_TOKENS,
    VERDICT_AT_RISK,
    VERDICT_ENFORCED,
    VERDICT_NOT_ENFORCED,
    BoundaryInvariant,
    BoundaryReport,
    assess_boundary,
    audit_active_loop_imports,
    boundary_matrix,
    find_invariant,
    gaps,
    invariants_by_criticality,
    isolation_holds,
)

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


# --- 카탈로그 무결성 ----------------------------------------------------------

class TestCatalogIntegrity:
    def test_catalog_non_empty(self):
        assert len(BOUNDARY_INVARIANTS) >= 6

    def test_invariant_ids_unique(self):
        ids = [inv.invariant_id for inv in BOUNDARY_INVARIANTS]
        assert len(ids) == len(set(ids))

    def test_all_statuses_valid(self):
        for inv in BOUNDARY_INVARIANTS:
            assert inv.status in INVARIANT_STATUSES

    def test_all_criticalities_valid(self):
        for inv in BOUNDARY_INVARIANTS:
            assert inv.criticality in CRITICALITIES

    def test_has_at_least_one_critical(self):
        assert any(inv.is_critical for inv in BOUNDARY_INVARIANTS)

    def test_ids_are_snake_case(self):
        for inv in BOUNDARY_INVARIANTS:
            assert inv.invariant_id == inv.invariant_id.lower()
            assert " " not in inv.invariant_id


# --- 정직성 결속: unverified ⟺ evidence None ---------------------------------

class TestHonestyBinding:
    def test_unverified_has_no_evidence(self):
        for inv in BOUNDARY_INVARIANTS:
            if inv.status == "unverified":
                assert inv.evidence is None

    def test_non_unverified_cites_evidence(self):
        for inv in BOUNDARY_INVARIANTS:
            if inv.status != "unverified":
                assert inv.evidence and inv.evidence.strip()

    def test_cited_evidence_exists_on_disk(self):
        for inv in BOUNDARY_INVARIANTS:
            if inv.evidence is not None:
                path = _REPO_ROOT / inv.evidence
                assert path.is_file(), f"missing evidence: {inv.evidence}"

    def test_active_loop_modules_exist_on_disk(self):
        for rel in ACTIVE_LOOP_MODULES:
            assert (_REPO_ROOT / rel).is_file(), f"missing active-loop module: {rel}"


# --- BoundaryInvariant 검증 ---------------------------------------------------

class TestInvariantValidation:
    def test_rejects_empty_id(self):
        with pytest.raises(ValueError):
            BoundaryInvariant("", "n", "critical", "upheld", "x.py", "s")

    def test_rejects_padded_id(self):
        with pytest.raises(ValueError):
            BoundaryInvariant(" x ", "n", "critical", "upheld", "x.py", "s")

    def test_rejects_id_with_space(self):
        with pytest.raises(ValueError):
            BoundaryInvariant("a b", "n", "critical", "upheld", "x.py", "s")

    def test_rejects_id_with_tab(self):
        with pytest.raises(ValueError):
            BoundaryInvariant("a\tb", "n", "critical", "upheld", "x.py", "s")

    def test_rejects_non_lowercase_id(self):
        with pytest.raises(ValueError):
            BoundaryInvariant("camelCase", "n", "critical", "upheld", "x.py", "s")

    def test_rejects_empty_name(self):
        with pytest.raises(ValueError):
            BoundaryInvariant("x", "  ", "critical", "upheld", "x.py", "s")

    def test_rejects_empty_summary(self):
        with pytest.raises(ValueError):
            BoundaryInvariant("x", "n", "critical", "upheld", "x.py", "  ")

    def test_rejects_bad_criticality(self):
        with pytest.raises(ValueError):
            BoundaryInvariant("x", "n", "kinda", "upheld", "x.py", "s")

    def test_rejects_bad_status(self):
        with pytest.raises(ValueError):
            BoundaryInvariant("x", "n", "critical", "maybe", "x.py", "s")

    def test_unverified_with_evidence_rejected(self):
        with pytest.raises(ValueError):
            BoundaryInvariant("x", "n", "critical", "unverified", "x.py", "s")

    def test_upheld_without_evidence_rejected(self):
        with pytest.raises(ValueError):
            BoundaryInvariant("x", "n", "critical", "upheld", None, "s")

    def test_partial_without_evidence_rejected(self):
        with pytest.raises(ValueError):
            BoundaryInvariant("x", "n", "recommended", "partial", "   ", "s")

    def test_frozen(self):
        inv = BOUNDARY_INVARIANTS[0]
        with pytest.raises((AttributeError, TypeError)):
            inv.status = "partial"  # type: ignore[misc]

    def test_weight_values(self):
        up = BoundaryInvariant("a", "n", "critical", "upheld", "x.py", "s")
        pa = BoundaryInvariant("b", "n", "critical", "partial", "x.py", "s")
        un = BoundaryInvariant("c", "n", "critical", "unverified", None, "s")
        assert (up.weight, pa.weight, un.weight) == (1.0, 0.5, 0.0)

    def test_is_critical_property(self):
        assert find_invariant("ml_isolated_from_active_loop").is_critical


# --- 라이브 임포트 감사 (핵심 불변식) ----------------------------------------

class TestLiveImportAudit:
    def test_active_loop_has_no_ml_imports(self):
        """현 리포: 활성 루프가 RL/ML 모듈을 임포트하지 않는다(경계 구조적 성립)."""
        assert audit_active_loop_imports() == ()

    def test_isolation_holds_true(self):
        assert isolation_holds() is True

    def test_audit_is_deterministic(self):
        assert audit_active_loop_imports() == audit_active_loop_imports()

    def test_audit_detects_ml_import(self, tmp_path, monkeypatch):
        """RL 임포트를 활성 루프에 심으면 감사가 위반으로 표면화한다."""
        fake_root = tmp_path
        mod_dir = fake_root / "simulation"
        mod_dir.mkdir()
        offending = mod_dir / "fake_controller.py"
        offending.write_text("from simulation.rl_path_selector import RLPathSelector\n",
                             encoding="utf-8")
        monkeypatch.setattr(mod, "_REPO_ROOT", fake_root)
        monkeypatch.setattr(mod, "ACTIVE_LOOP_MODULES", ("simulation/fake_controller.py",))
        violations = audit_active_loop_imports()
        assert violations
        assert violations[0][0] == "simulation/fake_controller.py"
        assert "rl_path_selector" in violations[0][1]

    def test_audit_ignores_token_in_comment(self, tmp_path, monkeypatch):
        """주석·문서 문자열의 토큰 언급은 위반이 아니다(import 줄만 검사)."""
        fake_root = tmp_path
        mod_dir = fake_root / "simulation"
        mod_dir.mkdir()
        clean = mod_dir / "fake_clean.py"
        clean.write_text("# this module never uses rl_path_selector\nx = 1\n",
                         encoding="utf-8")
        monkeypatch.setattr(mod, "_REPO_ROOT", fake_root)
        monkeypatch.setattr(mod, "ACTIVE_LOOP_MODULES", ("simulation/fake_clean.py",))
        assert audit_active_loop_imports() == ()

    def test_audit_flags_missing_module(self, tmp_path, monkeypatch):
        """감사 대상 파일이 사라지면 조용히 통과하지 않고 위반으로 표면화한다."""
        monkeypatch.setattr(mod, "_REPO_ROOT", tmp_path)
        monkeypatch.setattr(mod, "ACTIVE_LOOP_MODULES", ("simulation/gone.py",))
        violations = audit_active_loop_imports()
        assert violations == (("simulation/gone.py", "<missing-module>"),)

    def test_ml_tokens_cover_known_rl_modules(self):
        for token in ("rl_path_selector", "deep_rl_controller", "ppo_collision"):
            assert token in ML_IMPORT_TOKENS

    def test_audit_detects_multiline_parenthesized_import(self, tmp_path, monkeypatch):
        """괄호 다중 줄 임포트의 연속 줄 RL 이름도 ast 로 탐지한다(위음성 차단)."""
        fake_root = tmp_path
        mod_dir = fake_root / "simulation"
        mod_dir.mkdir()
        offending = mod_dir / "fake_multi.py"
        offending.write_text(
            "from simulation.rl_path_selector import (\n"
            "    RLPathSelector,\n"
            "    Episode,\n"
            ")\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(mod, "_REPO_ROOT", fake_root)
        monkeypatch.setattr(mod, "ACTIVE_LOOP_MODULES", ("simulation/fake_multi.py",))
        violations = audit_active_loop_imports()
        assert violations and "rl_path_selector" in violations[0][1]

    def test_audit_detects_aliased_import(self, tmp_path, monkeypatch):
        """`import ... as` 별칭 임포트도 탐지한다."""
        fake_root = tmp_path
        mod_dir = fake_root / "simulation"
        mod_dir.mkdir()
        offending = mod_dir / "fake_alias.py"
        offending.write_text("import simulation.deep_rl_controller as ctrl\n", encoding="utf-8")
        monkeypatch.setattr(mod, "_REPO_ROOT", fake_root)
        monkeypatch.setattr(mod, "ACTIVE_LOOP_MODULES", ("simulation/fake_alias.py",))
        assert any("deep_rl_controller" in v[1] for v in audit_active_loop_imports())

    def test_audit_ignores_inline_comment_token(self, tmp_path, monkeypatch):
        """진짜 임포트 줄의 인라인 주석 속 토큰은 위반이 아니다(위양성 차단)."""
        fake_root = tmp_path
        mod_dir = fake_root / "simulation"
        mod_dir.mkdir()
        clean = mod_dir / "fake_inline.py"
        clean.write_text(
            "import numpy as np  # previously replaced rl_path_selector\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(mod, "_REPO_ROOT", fake_root)
        monkeypatch.setattr(mod, "ACTIVE_LOOP_MODULES", ("simulation/fake_inline.py",))
        assert audit_active_loop_imports() == ()

    def test_audit_flags_unparseable_module(self, tmp_path, monkeypatch):
        """파싱 불가 파일은 조용히 통과하지 않고 위반으로 표면화한다."""
        fake_root = tmp_path
        mod_dir = fake_root / "simulation"
        mod_dir.mkdir()
        broken = mod_dir / "fake_broken.py"
        broken.write_text("def (:\n", encoding="utf-8")
        monkeypatch.setattr(mod, "_REPO_ROOT", fake_root)
        monkeypatch.setattr(mod, "ACTIVE_LOOP_MODULES", ("simulation/fake_broken.py",))
        assert audit_active_loop_imports() == (("simulation/fake_broken.py", "<unparseable>"),)


# --- 판정 (verdict) -----------------------------------------------------------

class TestAssessBoundary:
    def test_returns_report(self):
        assert isinstance(assess_boundary(), BoundaryReport)

    def test_current_repo_is_enforced(self):
        """현 리포: 임계 불변식 전부 성립 → BOUNDARY_ENFORCED."""
        assert assess_boundary().verdict == VERDICT_ENFORCED

    def test_counts_sum_to_total(self):
        r = assess_boundary()
        assert r.upheld + r.partial + r.unverified == r.total

    def test_critical_upheld_le_total(self):
        r = assess_boundary()
        assert r.critical_upheld <= r.critical_total <= r.total

    def test_weighted_score_in_range(self):
        assert 0.0 <= assess_boundary().weighted_score_pct <= 100.0

    def test_by_criticality_sums_match(self):
        r = assess_boundary()
        u = sum(v[0] for v in r.by_criticality.values())
        p = sum(v[1] for v in r.by_criticality.values())
        n = sum(v[2] for v in r.by_criticality.values())
        assert (u, p, n) == (r.upheld, r.partial, r.unverified)

    def test_by_criticality_read_only(self):
        r = assess_boundary()
        with pytest.raises(TypeError):
            r.by_criticality["critical"] = (0, 0, 0)  # type: ignore[index]

    def test_is_enforced_property(self):
        assert assess_boundary().is_enforced is True

    def test_deterministic(self):
        a, b = assess_boundary(), assess_boundary()
        assert (a.verdict, a.upheld, a.partial, a.unverified) == (
            b.verdict, b.upheld, b.partial, b.unverified
        )


# --- verdict 우선순위 (_verdict_for) -----------------------------------------

class TestVerdictPriority:
    def _inv(self, crit, status):
        ev = None if status == "unverified" else "simulation/rl_advisory_boundary.py"
        return BoundaryInvariant(f"i_{crit}_{status}", "n", crit, status, ev, "s")

    def test_critical_unverified_not_enforced(self):
        invs = (self._inv("critical", "unverified"), self._inv("recommended", "upheld"))
        assert mod._verdict_for(invs) == VERDICT_NOT_ENFORCED

    def test_critical_partial_at_risk(self):
        invs = (self._inv("critical", "partial"), self._inv("recommended", "upheld"))
        assert mod._verdict_for(invs) == VERDICT_AT_RISK

    def test_all_critical_upheld_enforced(self):
        invs = (self._inv("critical", "upheld"), self._inv("recommended", "partial"))
        assert mod._verdict_for(invs) == VERDICT_ENFORCED

    def test_recommended_unverified_does_not_block(self):
        invs = (self._inv("critical", "upheld"), self._inv("recommended", "unverified"))
        assert mod._verdict_for(invs) == VERDICT_ENFORCED

    def test_unverified_beats_partial(self):
        """임계 미검증과 부분이 공존하면 더 나쁜 NOT_ENFORCED."""
        invs = (self._inv("critical", "unverified"), self._inv("critical", "partial"))
        assert mod._verdict_for(invs) == VERDICT_NOT_ENFORCED

    def test_no_critical_invariants_not_enforced(self):
        """임계 불변식이 없으면 공허한 ENFORCED 가 아니라 NOT_ENFORCED."""
        invs = (self._inv("recommended", "upheld"),)
        assert mod._verdict_for(invs) == VERDICT_NOT_ENFORCED

    def test_empty_invariants_not_enforced(self):
        assert mod._verdict_for(()) == VERDICT_NOT_ENFORCED


# --- 격리 위반 시 강등 (assess_boundary 의 정직성) ----------------------------

class TestIsolationDowngrade:
    def test_isolation_violation_downgrades_to_at_risk(self, tmp_path, monkeypatch):
        """라이브 감사가 위반이면 정적 upheld 선언이 partial 로 강등돼 판정이 AT_RISK."""
        fake_root = tmp_path
        mod_dir = fake_root / "simulation"
        mod_dir.mkdir()
        offending = mod_dir / "fake_ctrl.py"
        offending.write_text("import simulation.deep_rl_controller\n", encoding="utf-8")
        monkeypatch.setattr(mod, "_REPO_ROOT", fake_root)
        monkeypatch.setattr(mod, "ACTIVE_LOOP_MODULES", ("simulation/fake_ctrl.py",))
        r = assess_boundary()
        assert r.verdict == VERDICT_AT_RISK
        assert not r.is_enforced

    def test_unverified_isolation_plus_violation_does_not_crash(self, tmp_path, monkeypatch):
        """격리 불변식이 unverified(근거 None)인데 감사도 위반이면 강등이 정직성
        결속을 깨지 않고(크래시 없이) NOT_ENFORCED 를 반환한다(HIGH#1 회귀)."""
        # 격리 불변식을 unverified 로 교체한 카탈로그를 주입.
        patched = tuple(
            BoundaryInvariant(inv.invariant_id, inv.name, inv.criticality,
                              "unverified", None, inv.summary)
            if inv.invariant_id == "ml_isolated_from_active_loop" else inv
            for inv in BOUNDARY_INVARIANTS
        )
        fake_root = tmp_path
        mod_dir = fake_root / "simulation"
        mod_dir.mkdir()
        (mod_dir / "fake_ctrl.py").write_text(
            "import simulation.rl_path_selector\n", encoding="utf-8")
        monkeypatch.setattr(mod, "BOUNDARY_INVARIANTS", patched)
        monkeypatch.setattr(mod, "_REPO_ROOT", fake_root)
        monkeypatch.setattr(mod, "ACTIVE_LOOP_MODULES", ("simulation/fake_ctrl.py",))
        r = assess_boundary()  # must not raise
        assert r.verdict == VERDICT_NOT_ENFORCED


# --- BoundaryReport 검증 ------------------------------------------------------

class TestReportValidation:
    def _ok_by_crit(self):
        return {"critical": (1, 0, 0), "recommended": (0, 1, 0)}

    def test_counts_mismatch_rejected(self):
        with pytest.raises(ValueError):
            BoundaryReport(VERDICT_ENFORCED, 2, 1, 0, 0, 1, 1, self._ok_by_crit())

    def test_negative_rejected(self):
        with pytest.raises(ValueError):
            BoundaryReport(VERDICT_ENFORCED, 2, -1, 2, 1, 1, 1, self._ok_by_crit())

    def test_critical_upheld_over_total_rejected(self):
        with pytest.raises(ValueError):
            BoundaryReport(VERDICT_ENFORCED, 2, 1, 1, 0, 1, 2, self._ok_by_crit())

    def test_bad_verdict_rejected(self):
        with pytest.raises(ValueError):
            BoundaryReport("NOPE", 2, 1, 1, 0, 1, 1, self._ok_by_crit())

    def test_unknown_criticality_key_rejected(self):
        with pytest.raises(ValueError):
            BoundaryReport(
                VERDICT_ENFORCED, 2, 1, 1, 0, 1, 1,
                {"critical": (1, 0, 0), "bogus": (0, 1, 0)},
            )

    def test_by_criticality_sum_mismatch_rejected(self):
        with pytest.raises(ValueError):
            BoundaryReport(
                VERDICT_ENFORCED, 2, 2, 0, 0, 1, 1,
                {"critical": (1, 0, 0), "recommended": (0, 0, 0)},
            )

    def test_empty_total_score_zero(self):
        r = BoundaryReport(VERDICT_NOT_ENFORCED, 0, 0, 0, 0, 0, 0, {})
        assert r.weighted_score_pct == 0.0

    def test_empty_by_criticality_with_nonzero_counts_rejected(self):
        """빈 by_criticality 가 비-0 카운트와 공존하면 거부(MEDIUM#1 구멍 차단)."""
        with pytest.raises(ValueError):
            BoundaryReport(VERDICT_ENFORCED, 2, 1, 1, 0, 1, 1, {})


# --- 조회 API -----------------------------------------------------------------

class TestQueryApi:
    def test_find_invariant(self):
        inv = find_invariant("deterministic_safety_net_authority")
        assert inv.is_critical

    def test_find_unknown_raises(self):
        with pytest.raises(KeyError):
            find_invariant("nope")

    def test_invariants_by_criticality_sorted(self):
        crit = invariants_by_criticality("critical")
        ids = [i.invariant_id for i in crit]
        assert ids == sorted(ids)
        assert all(i.is_critical for i in crit)

    def test_invariants_by_criticality_bad_value(self):
        with pytest.raises(ValueError):
            invariants_by_criticality("nope")

    def test_gaps_only_unverified(self):
        assert all(i.is_unverified for i in gaps())

    def test_gaps_sorted(self):
        ids = [i.invariant_id for i in gaps()]
        assert ids == sorted(ids)


# --- boundary_matrix ----------------------------------------------------------

class TestBoundaryMatrix:
    def test_row_count(self):
        assert len(boundary_matrix()) == len(BOUNDARY_INVARIANTS)

    def test_rows_read_only(self):
        row = boundary_matrix()[0]
        with pytest.raises(TypeError):
            row["status"] = "x"  # type: ignore[index]

    def test_sorted_by_criticality_then_id(self):
        rows = boundary_matrix()
        keys = [(CRITICALITIES.index(str(r["criticality"])), r["invariant_id"]) for r in rows]
        assert keys == sorted(keys)

    def test_unverified_rows_have_no_evidence(self):
        for row in boundary_matrix():
            if row["status"] == "unverified":
                assert row["evidence"] is None


# --- CLI ----------------------------------------------------------------------

class TestCli:
    def test_invariants(self, capsys):
        assert mod.main(["--invariants"]) == 0
        assert "불변식" in capsys.readouterr().out

    def test_report(self, capsys):
        assert mod.main(["--report"]) == 0
        out = capsys.readouterr().out
        assert "판정" in out and VERDICT_ENFORCED in out

    def test_audit(self, capsys):
        assert mod.main(["--audit"]) == 0
        assert "감사" in capsys.readouterr().out

    def test_gaps(self, capsys):
        assert mod.main(["--gaps"]) == 0

    def test_critical(self, capsys):
        assert mod.main(["--critical"]) == 0
        assert "→" in capsys.readouterr().out

    def test_default_prints_report(self, capsys):
        assert mod.main([]) == 0
        assert "판정" in capsys.readouterr().out
