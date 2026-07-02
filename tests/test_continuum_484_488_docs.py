"""ODYSSEY Phase 484·488 + 브랜치 정리 자료 회귀."""

from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SCRIPTS = ROOT / "scripts"


class TestPhase484ElectronLtsTracking:
    """ODYSSEY Phase 484 — Electron LTS 추적 정책."""

    PATH = DOCS / "CONTINUUM_ELECTRON_LTS_TRACKING.md"

    def test_file_exists(self) -> None:
        assert self.PATH.is_file()

    def test_phase_header(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        assert "Phase 484" in text

    def test_release_cycle_documented(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # Electron 릴리스 주기 + LTS 정책 명시
        assert "8주" in text or "8 weeks" in text.lower()
        assert "LTS" in text

    def test_v32_v39_migration(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # v32 → v39 마이그레이션 교훈
        assert "32.3.3" in text
        assert "v32" in text and ("v39" in text or "39+" in text)

    def test_security_checklist(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # 보안 점검 항목 (Trivy·Bandit·pip-audit·npm audit)
        assert "Trivy" in text
        assert "Bandit" in text
        assert "pip-audit" in text

    def test_references_dependabot_policy(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # Phase 481 dependabot 정책 참조
        assert "CONTINUUM_DEPENDABOT_POLICY" in text or "Phase 481" in text


class TestPhase488SecuritySla:
    """ODYSSEY Phase 488 — 보안 장기 지원 SLA."""

    PATH = DOCS / "CONTINUUM_SECURITY_SLA.md"

    def test_file_exists(self) -> None:
        assert self.PATH.is_file()

    def test_phase_header(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        assert "Phase 488" in text

    def test_cvss_sla_matrix(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # CVSS 4 등급 매트릭스
        for level in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
            assert level in text, f"missing CVSS level {level}"
        # SLA 시간 (6h CRITICAL, 24h HIGH, 1w MEDIUM)
        assert "6h" in text
        assert "24h" in text
        assert "1w" in text

    def test_critical_response_procedure(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # CRITICAL 즉시 대응 T+0/T+1h/T+6h/T+24h 시퀀스
        assert "T+0" in text or "T+1h" in text or "T+24h" in text

    def test_pin_policy_matrix(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # 의존성 핀 정책
        assert "requirements.txt" in text
        assert "package.json" in text
        assert "Electron" in text or "electron" in text

    def test_audit_trail(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # 감사 로그 영구 기록 (CVE-YYYY-XXXX)
        assert "CVE" in text
        assert "docs/security" in text

    def test_key_management(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # 키 관리 + 유출 응답
        assert "JWT" in text
        assert "GPG" in text or "PGP" in text


class TestStaleBranchesCleanup:
    """원격 브랜치 정리 가이드 + 안전 스크립트."""

    GUIDE = DOCS / "maintenance" / "STALE_BRANCHES_CLEANUP.md"
    SCRIPT = SCRIPTS / "cleanup_stale_branches.sh"

    def test_guide_exists(self) -> None:
        assert self.GUIDE.is_file()

    def test_script_exists(self) -> None:
        assert self.SCRIPT.is_file()

    def test_script_executable(self) -> None:
        import os

        assert os.access(self.SCRIPT, os.X_OK), "script must be executable"

    def test_guide_safety_list(self) -> None:
        text = self.GUIDE.read_text(encoding="utf-8")
        # 삭제 금지 브랜치 명시
        assert "main" in text
        assert "ruview-wifi-analysis-2YG4p" in text

    def test_script_safety_list(self) -> None:
        text = self.SCRIPT.read_text(encoding="utf-8")
        # safety list 의 핵심 항목
        assert 'origin/main' in text
        assert 'origin/claude/ruview-wifi-analysis-2YG4p' in text
        assert 'SAFETY_LIST' in text

    def test_script_dry_run_default(self) -> None:
        text = self.SCRIPT.read_text(encoding="utf-8")
        # dry-run 이 기본 모드 (안전 default)
        assert 'MODE="dry-run"' in text

    def test_script_requires_explicit_confirm(self) -> None:
        text = self.SCRIPT.read_text(encoding="utf-8")
        # delete-all 시 "yes" 명시 확인 요구
        assert '!= "yes"' in text or '== "yes"' in text or '"yes"' in text

    def test_script_modes_documented(self) -> None:
        text = self.SCRIPT.read_text(encoding="utf-8")
        # 3 모드 (dry-run, interactive, delete-all)
        assert "dry-run" in text
        assert "interactive" in text
        assert "delete-all" in text

    def test_guide_recovery_documented(self) -> None:
        text = self.GUIDE.read_text(encoding="utf-8")
        # 복구 가능성 (refs/pull/<N>/head 패턴)
        assert "refs/pull" in text or "복구" in text
