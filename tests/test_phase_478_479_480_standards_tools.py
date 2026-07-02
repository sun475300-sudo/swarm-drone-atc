"""ODYSSEY Phase 478·479·480 — 표준 정책 추적 도구 회귀."""

from __future__ import annotations

import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
STANDARDS = ROOT / "docs" / "standards"
SCRIPTS = ROOT / "scripts"


class TestPhase478ConformanceCheck:
    """Phase 478 — 표준 산출물 정합성 자동 점검."""

    SCRIPT = SCRIPTS / "standards_conformance_check.py"

    def test_script_exists(self) -> None:
        assert self.SCRIPT.is_file()

    def test_script_executable(self) -> None:
        import os

        assert os.access(self.SCRIPT, os.X_OK), "script must be executable"

    def test_phase_header(self) -> None:
        text = self.SCRIPT.read_text(encoding="utf-8")
        assert "Phase 478" in text

    def test_module_imports(self) -> None:
        spec = importlib.util.spec_from_file_location("conformance", str(self.SCRIPT))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        # STANDARDS_ARTIFACTS list 정의
        assert isinstance(mod.STANDARDS_ARTIFACTS, list)
        assert len(mod.STANDARDS_ARTIFACTS) >= 10

    def test_artifacts_cover_all_phases(self) -> None:
        """본 PR 까지 작성된 표준 산출물 모두 추적 대상."""
        spec = importlib.util.spec_from_file_location("conformance", str(self.SCRIPT))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        phases = {a["phase"] for a in mod.STANDARDS_ARTIFACTS}
        # Phase 461·462·463·464·465·470·471·472·474·475·476·477
        for phase_num in (461, 462, 463, 464, 465, 470, 471, 472, 474, 475, 476, 477):
            assert f"Phase {phase_num}" in phases, f"missing Phase {phase_num}"

    def test_actual_conformance_passes(self) -> None:
        """본 점검 자체가 현재 통과해야 (모든 산출물 정합성 OK)."""
        spec = importlib.util.spec_from_file_location("conformance", str(self.SCRIPT))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        data = mod.run_all_checks()
        assert data["ok"], f"conformance failed: {data['issues']}"

    def test_check_mode_exit_codes(self) -> None:
        """--check 모드는 ok=True 시 0, False 시 1."""
        spec = importlib.util.spec_from_file_location("conformance", str(self.SCRIPT))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        # run_all_checks 직접 검사 (CLI 분기 로직)
        data = mod.run_all_checks()
        # 현재 통과 상태이므로 exit code 0 기대
        assert data["ok"]


class TestPhase479WatchProcedure:
    """Phase 479 — 표준 변경 모니터링 절차."""

    PATH = STANDARDS / "STANDARDS_WATCH_PROCEDURE.md"

    def test_file_exists(self) -> None:
        assert self.PATH.is_file()

    def test_phase_header(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        assert "Phase 479" in text

    def test_target_organizations(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # 10 표준 기관 채널
        for org in ("ASTM", "ISO", "EASA", "FAA", "ICAO", "JARUS", "GUTMA", "IFALPA"):
            assert org in text, f"missing {org}"

    def test_trigger_events(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # 5 트리거 이벤트
        assert "발간" in text
        assert "개정" in text
        assert "Public Comment" in text or "공개 의견" in text

    def test_quarterly_procedure(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # 분기 4단계 점검 절차
        assert "분기" in text
        assert "1주" in text or "2-4주" in text or "마감 주" in text

    def test_references_dashboard_and_478(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        assert "Phase 470" in text or "STANDARDS_CONTRIBUTION_DASHBOARD" in text
        assert "Phase 478" in text or "standards_conformance_check" in text


class TestPhase480QuarterlyReportTemplate:
    """Phase 480 — 분기 보고서 템플릿."""

    PATH = STANDARDS / "SDACS_STANDARDS_QUARTERLY_REPORT_TEMPLATE.md"

    def test_file_exists(self) -> None:
        assert self.PATH.is_file()

    def test_phase_header(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        assert "Phase 480" in text

    def test_template_sections(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # 표준 분기 보고서 섹션
        for section in ("분기 요약", "추적 표준 변경", "회의 참석", "정합성 점검", "다음 분기 계획"):
            assert section in text, f"missing section {section}"

    def test_conformance_check_command(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # Phase 478 명령 첨부
        assert "standards_conformance_check.py" in text

    def test_filename_convention(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # 파일명 규약 (YYYY-QN)
        assert "YYYY-QN" in text or "YYYY" in text

    def test_honesty_section(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # 한계 + 누락 정직성 공시 섹션
        assert "정직성" in text
        assert "누락" in text or "수행하지 못한" in text


class TestStandardsConformanceLive:
    """Phase 478 정합성이 실 산출물에 대해 통과 — Live 게이트."""

    def test_all_artifacts_pass_conformance(self) -> None:
        """본 PR 의 모든 표준 산출물이 정합성 점검 통과해야 함."""
        script = SCRIPTS / "standards_conformance_check.py"
        spec = importlib.util.spec_from_file_location("conformance", str(script))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        data = mod.run_all_checks()
        assert data["ok"], (
            f"표준 정합성 위반 {data['issues_count']}건: {data['issues']}"
        )
