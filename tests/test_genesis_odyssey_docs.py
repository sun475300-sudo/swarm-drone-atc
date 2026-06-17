"""GENESIS 303·305·307 + ODYSSEY 421 인증 문서 존재·구조 검증."""

import pathlib

CERT_DIR = pathlib.Path(__file__).resolve().parents[1] / "docs" / "certification"


class TestGenesis303FlightPlanForm:
    """GENESIS Phase 303 — 비행계획 신고 양식 자동 생성."""

    def test_file_exists(self):
        assert (CERT_DIR / "FLIGHT_PLAN_FORM.md").is_file()

    def test_contains_phase_header(self):
        text = (CERT_DIR / "FLIGHT_PLAN_FORM.md").read_text(encoding="utf-8")
        assert "GENESIS" in text and "303" in text

    def test_contains_field_mapping(self):
        text = (CERT_DIR / "FLIGHT_PLAN_FORM.md").read_text(encoding="utf-8")
        assert "드론원스톱" in text or "Drone One-Stop" in text

    def test_contains_export_format(self):
        text = (CERT_DIR / "FLIGHT_PLAN_FORM.md").read_text(encoding="utf-8")
        assert "JSON" in text or "export" in text.lower()

    def test_contains_sora_reference(self):
        text = (CERT_DIR / "FLIGHT_PLAN_FORM.md").read_text(encoding="utf-8")
        assert "soraAssess" in text or "SORA" in text


class TestGenesis305DO178C:
    """GENESIS Phase 305 — DO-178C 갭 분석."""

    def test_file_exists(self):
        assert (CERT_DIR / "DO178C_GAP_ANALYSIS.md").is_file()

    def test_contains_phase_header(self):
        text = (CERT_DIR / "DO178C_GAP_ANALYSIS.md").read_text(encoding="utf-8")
        assert "DO-178C" in text or "DO178C" in text

    def test_contains_dal_d(self):
        text = (CERT_DIR / "DO178C_GAP_ANALYSIS.md").read_text(encoding="utf-8")
        assert "DAL-D" in text or "DAL" in text

    def test_contains_gap_analysis(self):
        text = (CERT_DIR / "DO178C_GAP_ANALYSIS.md").read_text(encoding="utf-8")
        lower = text.lower()
        assert "gap" in lower or "격차" in text


class TestGenesis307AccidentReport:
    """GENESIS Phase 307 — 사고 보고 양식 자동 작성."""

    def test_file_exists(self):
        assert (CERT_DIR / "ACCIDENT_REPORT_FORM.md").is_file()

    def test_contains_phase_header(self):
        text = (CERT_DIR / "ACCIDENT_REPORT_FORM.md").read_text(encoding="utf-8")
        assert "GENESIS" in text and "307" in text

    def test_contains_araib_reference(self):
        text = (CERT_DIR / "ACCIDENT_REPORT_FORM.md").read_text(encoding="utf-8")
        assert "항철위" in text or "ARAIB" in text

    def test_contains_incident_classification(self):
        text = (CERT_DIR / "ACCIDENT_REPORT_FORM.md").read_text(encoding="utf-8")
        assert "사고" in text and "준사고" in text

    def test_contains_reporting_deadline(self):
        text = (CERT_DIR / "ACCIDENT_REPORT_FORM.md").read_text(encoding="utf-8")
        assert "72" in text or "시한" in text


class TestOdyssey421DiscoveryProtocol:
    """ODYSSEY Phase 421 — 인스턴스 디스커버리 프로토콜."""

    def test_file_exists(self):
        assert (CERT_DIR / "INSTANCE_DISCOVERY_PROTOCOL.md").is_file()

    def test_contains_phase_header(self):
        text = (CERT_DIR / "INSTANCE_DISCOVERY_PROTOCOL.md").read_text(encoding="utf-8")
        assert "ODYSSEY" in text and "421" in text

    def test_contains_astm_reference(self):
        text = (CERT_DIR / "INSTANCE_DISCOVERY_PROTOCOL.md").read_text(encoding="utf-8")
        assert "ASTM" in text or "F3548" in text

    def test_contains_message_types(self):
        text = (CERT_DIR / "INSTANCE_DISCOVERY_PROTOCOL.md").read_text(encoding="utf-8")
        assert "ANNOUNCE" in text or "HEARTBEAT" in text

    def test_contains_handover(self):
        text = (CERT_DIR / "INSTANCE_DISCOVERY_PROTOCOL.md").read_text(encoding="utf-8")
        lower = text.lower()
        assert "handover" in lower or "핸드오버" in text
