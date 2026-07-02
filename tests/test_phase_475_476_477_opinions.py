"""ODYSSEY Phase 475·476·477 — 국제 WG 의견서 회귀."""

from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
STANDARDS = ROOT / "docs" / "standards"


class _OpinionPaperBase:
    """공통 검증 — Phase 472·474·475·476·477 모든 의견서가 충족해야 할 구조."""

    PATH: pathlib.Path = None
    PHASE: str = None
    TARGET_ORG: str = None

    def test_file_exists(self) -> None:
        assert self.PATH.is_file()

    def test_phase_header(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        assert self.PHASE in text

    def test_target_org(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        assert self.TARGET_ORG in text

    def test_honesty_disclosure(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        assert "정직성" in text

    def test_sister_documents(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # 모든 의견서는 Phase 470 dashboard 참조 + 자매 문서 참조
        assert "Phase 470" in text or "STANDARDS_CONTRIBUTION_DASHBOARD" in text


class TestPhase475FaaUtm(_OpinionPaperBase):
    """Phase 475 — FAA UTM ConOps 의견서."""

    PATH = STANDARDS / "SDACS_FAA_UTM_OPINION.md"
    PHASE = "Phase 475"
    TARGET_ORG = "FAA"

    def test_utm_conops_v2(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        assert "UTM ConOps v2.0" in text or "ConOps" in text

    def test_rtca_sc228(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        assert "RTCA" in text and "SC-228" in text

    def test_five_functions(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # UTM ConOps 5 기능
        for fn in ("SCM", "TCR", "NIS", "CM", "USS"):
            assert fn in text, f"missing function {fn}"


class TestPhase476JarusWg105(_OpinionPaperBase):
    """Phase 476 — JARUS WG-105 SORA 의견서."""

    PATH = STANDARDS / "SDACS_JARUS_WG105_OPINION.md"
    PHASE = "Phase 476"
    TARGET_ORG = "JARUS"

    def test_wg105_target(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        assert "WG-105" in text

    def test_sora_25_target(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        assert "SORA" in text and ("v2.5" in text or "2.5" in text)

    def test_oso_matrix(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # OSO 7·18·24 항목
        for oso in ("OSO #07", "OSO #18", "OSO #24"):
            assert oso in text, f"missing {oso}"

    def test_sora_assess_referenced(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # Phase 302 sora_assessment.py 참조
        assert "sora_assessment" in text or "soraAssess" in text


class TestPhase477IfalpaRpas(_OpinionPaperBase):
    """Phase 477 — IFALPA RPAS Subcommittee 의견서."""

    PATH = STANDARDS / "SDACS_IFALPA_RPAS_OPINION.md"
    PHASE = "Phase 477"
    TARGET_ORG = "IFALPA"

    def test_kapa_submission_path(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        assert "KAPA" in text

    def test_pilot_perspective(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # 유인-무인 통합 관점
        assert "유인" in text or "manned" in text.lower()
        assert "조종사" in text or "pilot" in text.lower()

    def test_ifalpa_position_alignment(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # IFALPA Position 정합 표
        assert "동일 안전 표준" in text or "워크로드" in text or "조사" in text

    def test_phase_309_referenced(self) -> None:
        text = self.PATH.read_text(encoding="utf-8")
        # 조종자 자격 매핑
        assert "Phase 309" in text or "PILOT_LICENSE_MAPPING" in text


class TestStandardsDashboardConsistency:
    """Phase 470 dashboard 가 471·472·474·475·476·477 모두 인벤토리 보유 (분기 갱신 후속)."""

    DASHBOARD = STANDARDS / "SDACS_STANDARDS_CONTRIBUTION_DASHBOARD.md"

    def test_dashboard_exists(self) -> None:
        # 본 검사는 dashboard 자체 존재만 — 인벤토리 갱신은 Phase 470 분기 갱신 절차로 별도
        assert self.DASHBOARD.is_file()
