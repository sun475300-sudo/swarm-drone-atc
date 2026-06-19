"""ODYSSEY Phase 490 — 디지털 유산 준비도 체크리스트 테스트.

핵심 계약 검증: 기준별 충족 판정(증거 파일 실재 + 아카이브 내구 게이트)·
전체 준비도 판정 우선순위(CRITICAL 미충족 → NOT_READY)·점수 가중 집계·
결정론·매니페스트 JSON 직렬화·체크리스트 무결성·리포 현 상태 정직성.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from simulation.legacy_readiness import (
    CHECKLIST,
    SEVERITY_CRITICAL,
    SEVERITY_IMPORTANT,
    SEVERITY_RECOMMENDED,
    STATE_SATISFIED,
    STATE_UNMET,
    VERDICT_NOT_READY,
    VERDICT_PARTIAL,
    VERDICT_READY,
    LegacyCriterion,
    assess_legacy_readiness,
    check_criterion,
    checklist_manifest,
    main,
)

pytestmark = pytest.mark.unit

_SEVERITIES = (SEVERITY_CRITICAL, SEVERITY_IMPORTANT, SEVERITY_RECOMMENDED)


# --- 헬퍼: 통제된 임시 리포 구성 -------------------------------------------
def _touch(root: Path, rel: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("x", encoding="utf-8")


def _satisfy_evidence(root: Path, criterion: LegacyCriterion) -> None:
    for rel in criterion.evidence:
        _touch(root, rel)


def _fully_stocked_repo(root: Path) -> None:
    """아카이브 게이트를 제외한 모든 증거 파일을 채운다."""
    for c in CHECKLIST:
        _satisfy_evidence(root, c)


# --- 체크리스트 무결성 -----------------------------------------------------
class TestChecklistIntegrity:
    def test_criterion_ids_unique(self):
        ids = [c.criterion_id for c in CHECKLIST]
        assert len(ids) == len(set(ids))

    def test_all_severities_known(self):
        for c in CHECKLIST:
            assert c.severity in _SEVERITIES

    def test_all_have_nonempty_evidence(self):
        for c in CHECKLIST:
            assert c.evidence
            assert all(rel.strip() for rel in c.evidence)

    def test_has_at_least_one_critical(self):
        assert any(c.severity == SEVERITY_CRITICAL for c in CHECKLIST)

    def test_weight_matches_severity(self):
        expected = {SEVERITY_CRITICAL: 3, SEVERITY_IMPORTANT: 2,
                    SEVERITY_RECOMMENDED: 1}
        for c in CHECKLIST:
            assert c.weight() == expected[c.severity]


# --- 개별 기준 판정 --------------------------------------------------------
class TestCheckCriterion:
    def test_all_evidence_present_satisfied(self, tmp_path):
        crit = LegacyCriterion("t", "documentation", SEVERITY_IMPORTANT,
                               "d", ("README.md", "CONTRIBUTING.md"))
        _satisfy_evidence(tmp_path, crit)
        assert check_criterion(crit, tmp_path) == STATE_SATISFIED

    def test_missing_one_evidence_unmet(self, tmp_path):
        crit = LegacyCriterion("t", "documentation", SEVERITY_IMPORTANT,
                               "d", ("README.md", "CONTRIBUTING.md"))
        _touch(tmp_path, "README.md")  # CONTRIBUTING.md 누락
        assert check_criterion(crit, tmp_path) == STATE_UNMET

    def test_directory_does_not_count_as_file(self, tmp_path):
        crit = LegacyCriterion("t", "licensing", SEVERITY_CRITICAL,
                               "d", ("LICENSE",))
        (tmp_path / "LICENSE").mkdir()  # 파일이 아닌 디렉터리
        assert check_criterion(crit, tmp_path) == STATE_UNMET

    def test_durable_archive_gate_blocks_even_with_files(self, tmp_path):
        """파일이 있어도 Phase 489 가 AT_RISK 면 UNMET(리포 현 상태)."""
        crit = LegacyCriterion("t", "archival", SEVERITY_CRITICAL, "d",
                               (".zenodo.json", "CITATION.cff"),
                               requires_durable_archive=True)
        _satisfy_evidence(tmp_path, crit)
        # shipped_registry()는 DOI 미발급 → 내구 아님 → 게이트 차단
        assert check_criterion(crit, tmp_path) == STATE_UNMET

    def test_injected_passing_gate_satisfies_archive(self, tmp_path):
        """게이트 주입(REDUNDANT 가정)으로 아카이브 기준 충족 경로 검증."""
        crit = LegacyCriterion("t", "archival", SEVERITY_CRITICAL, "d",
                               (".zenodo.json", "CITATION.cff"),
                               requires_durable_archive=True)
        _satisfy_evidence(tmp_path, crit)
        assert check_criterion(crit, tmp_path,
                               archive_gate=lambda: True) == STATE_SATISFIED

    def test_injected_passing_gate_still_needs_files(self, tmp_path):
        """게이트가 통과해도 증거 파일이 없으면 여전히 UNMET."""
        crit = LegacyCriterion("t", "archival", SEVERITY_CRITICAL, "d",
                               (".zenodo.json", "CITATION.cff"),
                               requires_durable_archive=True)
        # 파일 미생성
        assert check_criterion(crit, tmp_path,
                               archive_gate=lambda: True) == STATE_UNMET


# --- 전체 준비도 판정 ------------------------------------------------------
class TestAssessReadiness:
    def test_empty_repo_not_ready(self, tmp_path):
        result = assess_legacy_readiness(tmp_path)
        assert result.verdict == VERDICT_NOT_READY
        assert not result.is_ready()
        assert result.unmet_critical  # CRITICAL 다수 미충족

    def test_ready_when_all_satisfied_with_passing_gate(self, tmp_path):
        """모든 증거 파일 + 내구 아카이브 게이트 통과 → READY, 점수 1.0."""
        _fully_stocked_repo(tmp_path)
        result = assess_legacy_readiness(tmp_path, archive_gate=lambda: True)
        assert result.verdict == VERDICT_READY
        assert result.is_ready()
        assert result.score == 1.0
        assert not result.unmet_critical and not result.unmet_other

    def test_partial_when_only_recommended_missing(self, tmp_path):
        """모든 CRITICAL/IMPORTANT 충족 + RECOMMENDED 하나 누락 → PARTIAL."""
        for c in CHECKLIST:
            if c.criterion_id == "governance-succession":
                continue  # 유일한 미충족(RECOMMENDED) 으로 남김
            _satisfy_evidence(tmp_path, c)
        result = assess_legacy_readiness(tmp_path, archive_gate=lambda: True)
        assert result.verdict == VERDICT_PARTIAL
        assert not result.unmet_critical
        assert "governance-succession" in result.unmet_other

    def test_not_ready_when_gate_fails_despite_files(self, tmp_path):
        """모든 파일이 있어도 아카이브 게이트 실패 → CRITICAL 미충족 → NOT_READY."""
        _fully_stocked_repo(tmp_path)
        result = assess_legacy_readiness(tmp_path, archive_gate=lambda: False)
        assert result.verdict == VERDICT_NOT_READY
        assert "archival-durable" in result.unmet_critical

    def test_score_monotonic_with_more_evidence(self, tmp_path):
        before = assess_legacy_readiness(tmp_path).score
        _touch(tmp_path, "README.md")
        _touch(tmp_path, "CONTRIBUTING.md")
        after = assess_legacy_readiness(tmp_path).score
        assert after > before

    def test_score_bounded_unit_interval(self, tmp_path):
        _fully_stocked_repo(tmp_path)
        result = assess_legacy_readiness(tmp_path)
        assert 0.0 <= result.score <= 1.0

    def test_critical_unmet_forces_not_ready(self, tmp_path):
        """IMPORTANT/RECOMMENDED 다 채워도 CRITICAL(LICENSE) 없으면 NOT_READY."""
        for c in CHECKLIST:
            if c.criterion_id == "license-file":
                continue  # LICENSE 의도적 누락
            if c.requires_durable_archive:
                continue
            _satisfy_evidence(tmp_path, c)
        result = assess_legacy_readiness(tmp_path)
        assert result.verdict == VERDICT_NOT_READY
        assert "license-file" in result.unmet_critical

    def test_satisfied_and_unmet_partition_all_criteria(self, tmp_path):
        _fully_stocked_repo(tmp_path)
        result = assess_legacy_readiness(tmp_path)
        total = (len(result.satisfied) + len(result.unmet_critical)
                 + len(result.unmet_other))
        assert total == len(CHECKLIST)

    def test_deterministic(self, tmp_path):
        _fully_stocked_repo(tmp_path)
        a = assess_legacy_readiness(tmp_path)
        b = assess_legacy_readiness(tmp_path)
        assert a == b

    def test_summary_contains_verdict_and_pct(self, tmp_path):
        result = assess_legacy_readiness(tmp_path)
        s = result.summary()
        assert result.verdict in s
        assert "%" in s


# --- 매니페스트 ------------------------------------------------------------
class TestManifest:
    def test_manifest_json_serializable(self):
        m = checklist_manifest()
        text = json.dumps(m, ensure_ascii=False)
        assert json.loads(text) == m

    def test_manifest_lists_all_criteria(self):
        m = checklist_manifest()
        ids = {c["id"] for c in m["criteria"]}
        assert ids == {c.criterion_id for c in CHECKLIST}

    def test_manifest_severity_weights(self):
        m = checklist_manifest()
        assert m["severities"][SEVERITY_CRITICAL] == 3
        assert m["severities"][SEVERITY_RECOMMENDED] == 1


# --- 리포 현 상태 정직성(회귀 핀) ------------------------------------------
# 이 클래스의 두 핀은 *반대 방향*으로 의도적으로 깨진다:
#   - not_ready 핀: 알려진 미비 상태를 고정 → LICENSE 추가·DOI 발급 등
#     상태가 *좋아지면* 깨져 체크리스트 갱신을 강제한다.
#   - satisfied 핀: 알려진 충족 상태를 고정 → 필수 자산이 삭제·이동되어
#     상태가 *나빠지면* 깨져 회귀를 잡는다.
class TestLiveRepoHonesty:
    def _repo_root(self) -> Path:
        return Path(__file__).resolve().parent.parent

    def test_live_repo_not_ready_until_license_and_archive(self):
        """현 리포는 LICENSE 파일·내구 아카이브 미비 → 정직하게 NOT_READY.

        상태 개선(LICENSE 추가·DOI 발급) 시 *의도적으로* 깨지는 정직성 가드.
        """
        result = assess_legacy_readiness(self._repo_root())
        assert result.verdict == VERDICT_NOT_READY
        assert "license-file" in result.unmet_critical
        assert "archival-durable" in result.unmet_critical

    def test_live_repro_and_docs_satisfied(self):
        """재현성·문서·보안 기준은 현재 실제로 충족(자산 실재).

        이 자산 중 하나가 삭제·이름변경되면 깨져 회귀를 잡는다(상태 악화 가드).
        """
        result = assess_legacy_readiness(self._repo_root())
        assert "repro-pinned-deps" in result.satisfied
        assert "handover-docs" in result.satisfied
        assert "security-support" in result.satisfied
        assert "citation-metadata" in result.satisfied


# --- CLI -------------------------------------------------------------------
class TestCli:
    def test_checklist_default(self, capsys):
        assert main([]) == 0
        assert "체크리스트" in capsys.readouterr().out

    def test_status(self, capsys):
        assert main(["--status"]) == 0
        assert "판정" in capsys.readouterr().out

    def test_manifest_emits_json(self, capsys):
        assert main(["--manifest"]) == 0
        parsed = json.loads(capsys.readouterr().out)
        assert parsed["schema"] == "sdacs-digital-legacy-checklist"

    def test_unknown_flag_rejected(self, capsys):
        assert main(["--bogus"]) == 2
        assert "알 수 없는 인자" in capsys.readouterr().err
