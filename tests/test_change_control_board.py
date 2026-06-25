"""GENESIS Phase 318 — CCB 변경통제 적합성 게이트 테스트."""
from __future__ import annotations

from pathlib import Path

import pytest

from simulation.change_control_board import (
    SEVERITY_CRITICAL,
    SEVERITY_RECOMMENDED,
    STATUS_MET,
    STATUS_PARTIAL,
    STATUS_UNMET,
    VERDICT_CONFORMANT,
    VERDICT_NONCONFORMANT,
    VERDICT_PARTIAL,
    CcbCriterion,
    assess,
    cited_evidence_paths,
    criteria,
    main,
    manifest,
    verify_evidence_on_disk,
)

pytestmark = pytest.mark.unit

_REPO_ROOT = Path(__file__).resolve().parent.parent


# ── dataclass 불변식 + 정직성 결속 ───────────────────────────────────────────
class TestCriterionInvariants:
    def test_valid_met_criterion(self):
        c = CcbCriterion("X-01", "t", SEVERITY_CRITICAL, STATUS_MET, "CHANGELOG.md", "r")
        assert c.status == STATUS_MET

    def test_invalid_status_rejected(self):
        with pytest.raises(ValueError, match="status"):
            CcbCriterion("X-01", "t", SEVERITY_CRITICAL, "maybe", "e", "r")

    def test_invalid_severity_rejected(self):
        with pytest.raises(ValueError, match="severity"):
            CcbCriterion("X-01", "t", "blocker", STATUS_MET, "e", "r")

    def test_met_without_evidence_rejected(self):
        """정직성 결속: MET 인데 증거 경로가 없으면 거부."""
        with pytest.raises(ValueError, match="증거 경로 필수"):
            CcbCriterion("X-01", "t", SEVERITY_CRITICAL, STATUS_MET, None, "r")

    def test_partial_without_evidence_rejected(self):
        with pytest.raises(ValueError, match="증거 경로 필수"):
            CcbCriterion("X-01", "t", SEVERITY_RECOMMENDED, STATUS_PARTIAL, "", "r")

    def test_unmet_with_evidence_rejected(self):
        """정직성 결속: UNMET 인데 증거를 인용하면 거부(허위 충족 차단)."""
        with pytest.raises(ValueError, match="증거를 인용할 수 없음"):
            CcbCriterion("X-01", "t", SEVERITY_RECOMMENDED, STATUS_UNMET, "x.md", "r")

    def test_frozen(self):
        c = criteria()[0]
        with pytest.raises(Exception):
            c.status = STATUS_UNMET  # type: ignore[misc]


# ── 매트릭스 정합성 ──────────────────────────────────────────────────────────
class TestMatrix:
    def test_criteria_present(self):
        assert len(criteria()) == 8

    def test_ids_unique(self):
        ids = [c.criterion_id for c in criteria()]
        assert len(ids) == len(set(ids))

    def test_all_have_rationale(self):
        assert all(c.rationale.strip() for c in criteria())

    def test_every_criterion_binds_honestly(self):
        """전 기준이 정직성 결속을 만족(생성자가 강제하지만 매트릭스 전수 확인)."""
        for c in criteria():
            if c.status in (STATUS_MET, STATUS_PARTIAL):
                assert c.evidence
            else:
                assert c.evidence is None


# ── 판정 로직 ────────────────────────────────────────────────────────────────
class TestAssess:
    def test_live_repo_partial_not_overclaimed(self):
        """현 리포는 CCB-02·03 PARTIAL, CCB-07 UNMET(recommended) → 부분 적합."""
        report = assess()
        assert report.verdict == VERDICT_PARTIAL
        assert "CCB-02" in report.partial
        assert "CCB-03" in report.partial
        assert "CCB-07" in report.unmet
        # CCB-07 은 recommended 이므로 핵심 미충족이 아니다(부적합 아님).
        assert report.unmet_critical == ()

    def test_score_deterministic(self):
        assert assess().score == assess().score

    def test_score_value(self):
        # met 5(=5.0) + partial 2(=1.0) + unmet 1(=0.0) = 6.0 / 8 = 0.75
        assert assess().score == 0.75

    def test_critical_unmet_forces_nonconformant(self):
        rows = (
            CcbCriterion("A", "t", SEVERITY_CRITICAL, STATUS_UNMET, None, "r"),
            CcbCriterion("B", "t", SEVERITY_CRITICAL, STATUS_MET, "CHANGELOG.md", "r"),
        )
        report = assess(rows)
        assert report.verdict == VERDICT_NONCONFORMANT
        assert "A" in report.unmet_critical

    def test_all_met_conformant(self):
        rows = tuple(
            CcbCriterion(f"C-{i}", "t", SEVERITY_CRITICAL, STATUS_MET, "ROADMAP.md", "r")
            for i in range(3)
        )
        report = assess(rows)
        assert report.verdict == VERDICT_CONFORMANT
        assert report.score == 1.0

    def test_empty_rejected(self):
        with pytest.raises(ValueError, match="비어"):
            assess(())

    def test_counts_sum_to_total(self):
        r = assess()
        assert len(r.met) + len(r.partial) + len(r.unmet) == r.total == 8


# ── 정직성 게이트: 인용 증거 디스크 실재 강제 ────────────────────────────────
class TestEvidenceOnDisk:
    def test_cited_evidence_all_exist(self):
        """인용한 모든 증거 산출물이 실제 리포에 존재해야 한다(허위 충족 차단)."""
        assert verify_evidence_on_disk(_REPO_ROOT) == ()

    def test_cited_paths_nonempty_and_sorted(self):
        paths = cited_evidence_paths()
        assert paths == tuple(sorted(paths))
        assert len(paths) >= 1

    def test_missing_evidence_detected(self, tmp_path):
        """빈 디렉터리를 루트로 주면 모든 증거가 누락으로 잡혀야 한다."""
        missing = verify_evidence_on_disk(tmp_path)
        assert set(missing) == set(cited_evidence_paths())


# ── manifest + CLI ───────────────────────────────────────────────────────────
class TestManifestAndCli:
    def test_manifest_shape(self):
        m = manifest()
        assert m["phase"] == 318
        assert m["schema"] == "sdacs-ccb-change-control"
        assert len(m["criteria"]) == 8
        assert m["verdict"] == VERDICT_PARTIAL

    def test_cli_default_matrix(self, capsys):
        assert main([]) == 0
        assert "매트릭스" in capsys.readouterr().out

    def test_cli_report(self, capsys):
        assert main(["--report"]) == 0
        assert "CCB 변경통제" in capsys.readouterr().out

    def test_cli_gaps(self, capsys):
        assert main(["--gaps"]) == 0
        out = capsys.readouterr().out
        assert "CCB-07" in out

    def test_cli_json(self, capsys):
        import json
        assert main(["--json"]) == 0
        parsed = json.loads(capsys.readouterr().out)
        assert parsed["phase"] == 318

    def test_cli_unknown_flag(self, capsys):
        assert main(["--bogus"]) == 2
        assert "알 수 없는" in capsys.readouterr().err
