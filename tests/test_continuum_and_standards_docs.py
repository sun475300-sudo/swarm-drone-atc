"""ODYSSEY 신규 문서 회귀 — Phase 461·462·481·487 존재·구조 검증."""

from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
STANDARDS = ROOT / "docs" / "standards"
DOCS = ROOT / "docs"


class TestPhase461AstmF38Proposal:
    """ODYSSEY Phase 461 — ASTM F38 기고 초안."""

    PATH = STANDARDS / "SDACS_ASTM_F38_PROPOSAL.md"

    def test_file_exists(self) -> None:
        assert self.PATH.is_file()

    def test_phase_header(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        assert "Phase 461" in text

    def test_references_astm_standards(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # 핵심 F38 표준 4종 명시
        for std in ("F3548-21", "F3411", "F3478", "F3196"):
            assert std in text, f"missing ASTM standard {std}"

    def test_test_methods_defined(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # 3개 시험 방법 (TM-1/2/3)
        assert "SDACS-TM-1" in text
        assert "SDACS-TM-2" in text
        assert "SDACS-TM-3" in text

    def test_acceptance_criteria_present(self) -> None:
        text = self.PATH.read_text(encoding="utf-8").lower()
        # 합격 기준 명시
        assert "합격 기준" in text or "acceptance" in text


class TestPhase462IsoTc20Sc16Tracker:
    """ODYSSEY Phase 462 — ISO/TC 20/SC 16 추적 매트릭스."""

    PATH = STANDARDS / "SDACS_ISO_TC20_SC16_TRACKER.md"

    def test_file_exists(self) -> None:
        assert self.PATH.is_file()

    def test_phase_header(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        assert "Phase 462" in text

    def test_references_iso_standards(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # 핵심 ISO 표준 명시
        for std in ("ISO 21384", "ISO 21895", "ISO 23629"):
            assert std in text, f"missing ISO standard {std}"

    def test_gap_analysis_present(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # 격차 분석 섹션
        assert "격차 분석" in text or "gap" in text.lower()

    def test_contribution_priority(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # 기고 우선순위
        assert "기고 우선순위" in text or "priority" in text.lower()


class TestPhase481DependabotPolicy:
    """ODYSSEY Phase 481 — Dependabot 자동 갱신 정책."""

    PATH = DOCS / "CONTINUUM_DEPENDABOT_POLICY.md"

    def test_file_exists(self) -> None:
        assert self.PATH.is_file()

    def test_phase_header(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        assert "Phase 481" in text

    def test_three_tier_policy(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # Tier 1/2/3 정책
        assert "Tier 1" in text
        assert "Tier 2" in text
        assert "Tier 3" in text

    def test_cvss_severity_mapping(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # 보안 우선순위 — CVSS 매핑
        assert "CRITICAL" in text and "HIGH" in text
        assert "24h" in text or "24시간" in text  # CRITICAL SLO

    def test_dependabot_yml_referenced(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        assert ".github/dependabot.yml" in text


class TestPhase487SuccessionProtocol:
    """ODYSSEY Phase 487 — 유지보수자 승계 규약."""

    PATH = DOCS / "CONTINUUM_SUCCESSION_PROTOCOL.md"

    def test_file_exists(self) -> None:
        assert self.PATH.is_file()

    def test_phase_header(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        assert "Phase 487" in text

    def test_three_stage_transition(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # 3-Stage 전환
        assert "Stage 1" in text
        assert "Stage 2" in text
        assert "Stage 3" in text

    def test_eligibility_criteria(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # 위원 자격 명시
        assert "자격" in text and ("PR" in text or "기여" in text)

    def test_merge_authority_matrix(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # 머지 권한 매트릭스
        assert "LGTM" in text
        assert "만장일치" in text or "unanimous" in text.lower()

    def test_license_reference(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        assert "MIT" in text  # MIT License 보호


class TestDependabotYmlActive:
    """Dependabot 설정 파일 실제 활성 검증."""

    PATH = ROOT / ".github" / "dependabot.yml"

    def test_dependabot_yml_exists(self) -> None:
        assert self.PATH.is_file()

    def test_version_2(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        assert "version: 2" in text

    def test_ecosystems_configured(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # 최소 github-actions + npm 활성
        assert "github-actions" in text
        assert "npm" in text
