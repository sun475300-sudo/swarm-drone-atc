"""GENESIS 308·310 + TRANSCENDENCE 209·210 + ODYSSEY 422 문서 존재·구조 검증."""

import pathlib

CERT_DIR = pathlib.Path(__file__).resolve().parents[1] / "docs" / "certification"
DOCS_DIR = pathlib.Path(__file__).resolve().parents[1] / "docs"


class TestGenesis308InsuranceAPI:
    """GENESIS Phase 308 — 보험 요율 산정 인터페이스 사양."""

    def test_file_exists(self):
        assert (CERT_DIR / "INSURANCE_API_SPEC.md").is_file()

    def test_contains_phase_header(self):
        text = (CERT_DIR / "INSURANCE_API_SPEC.md").read_text(encoding="utf-8")
        assert "308" in text

    def test_contains_api_endpoints(self):
        text = (CERT_DIR / "INSURANCE_API_SPEC.md").read_text(encoding="utf-8")
        assert "quote" in text.lower() or "/api/" in text

    def test_contains_risk_factors(self):
        text = (CERT_DIR / "INSURANCE_API_SPEC.md").read_text(encoding="utf-8")
        lower = text.lower()
        assert "risk" in lower or "리스크" in text

    def test_contains_regulatory_reference(self):
        text = (CERT_DIR / "INSURANCE_API_SPEC.md").read_text(encoding="utf-8")
        assert "항공사업법" in text or "보험" in text

    def test_contains_tier_info(self):
        text = (CERT_DIR / "INSURANCE_API_SPEC.md").read_text(encoding="utf-8")
        lower = text.lower()
        assert "basic" in lower or "standard" in lower or "premium" in lower


class TestGenesis310NightBVLOS:
    """GENESIS Phase 310 — 야간·비가시권 특별비행승인 요건."""

    def test_file_exists(self):
        assert (CERT_DIR / "NIGHT_BVLOS_APPROVAL.md").is_file()

    def test_contains_phase_header(self):
        text = (CERT_DIR / "NIGHT_BVLOS_APPROVAL.md").read_text(encoding="utf-8")
        assert "310" in text

    def test_contains_night_scenarios(self):
        text = (CERT_DIR / "NIGHT_BVLOS_APPROVAL.md").read_text(encoding="utf-8")
        assert "야간" in text or "night" in text.lower()

    def test_contains_bvlos_scenarios(self):
        text = (CERT_DIR / "NIGHT_BVLOS_APPROVAL.md").read_text(encoding="utf-8")
        assert "BVLOS" in text or "비가시" in text

    def test_contains_regulatory_reference(self):
        text = (CERT_DIR / "NIGHT_BVLOS_APPROVAL.md").read_text(encoding="utf-8")
        assert "항공안전법" in text or "특별비행" in text

    def test_contains_scenario_ids(self):
        text = (CERT_DIR / "NIGHT_BVLOS_APPROVAL.md").read_text(encoding="utf-8")
        assert "N-1" in text or "B-1" in text


class TestTranscendence209DeprecationPolicy:
    """TRANSCENDENCE Phase 209 — API Deprecation Policy."""

    def test_file_exists(self):
        assert (DOCS_DIR / "API_DEPRECATION_POLICY.md").is_file()

    def test_contains_deprecation_keyword(self):
        text = (DOCS_DIR / "API_DEPRECATION_POLICY.md").read_text(encoding="utf-8")
        lower = text.lower()
        assert "deprecat" in lower or "폐기" in text

    def test_contains_maturity_lifecycle(self):
        text = (DOCS_DIR / "API_DEPRECATION_POLICY.md").read_text(encoding="utf-8")
        assert "production" in text and "beta" in text

    def test_contains_timeline(self):
        text = (DOCS_DIR / "API_DEPRECATION_POLICY.md").read_text(encoding="utf-8")
        assert "12" in text or "6" in text

    def test_contains_sdacs_reference(self):
        text = (DOCS_DIR / "API_DEPRECATION_POLICY.md").read_text(encoding="utf-8")
        assert "_sdacs" in text or "SDACS" in text


class TestTranscendence210SemVer:
    """TRANSCENDENCE Phase 210 — Semantic Versioning Policy."""

    def test_file_exists(self):
        assert (DOCS_DIR / "API_SEMVER_POLICY.md").is_file()

    def test_contains_semver_keyword(self):
        text = (DOCS_DIR / "API_SEMVER_POLICY.md").read_text(encoding="utf-8")
        lower = text.lower()
        assert "semver" in lower or "semantic" in lower or "시맨틱" in text

    def test_contains_major_minor_patch(self):
        text = (DOCS_DIR / "API_SEMVER_POLICY.md").read_text(encoding="utf-8")
        assert "MAJOR" in text and "MINOR" in text and "PATCH" in text

    def test_contains_version_rules(self):
        text = (DOCS_DIR / "API_SEMVER_POLICY.md").read_text(encoding="utf-8")
        lower = text.lower()
        assert "breaking" in lower or "호환" in text


class TestOdyssey422OperationalIntent:
    """ODYSSEY Phase 422 — 운영 의도 교환 포맷."""

    def test_file_exists(self):
        assert (CERT_DIR / "OPERATIONAL_INTENT_FORMAT.md").is_file()

    def test_contains_phase_header(self):
        text = (CERT_DIR / "OPERATIONAL_INTENT_FORMAT.md").read_text(encoding="utf-8")
        assert "422" in text

    def test_contains_4d_volume(self):
        text = (CERT_DIR / "OPERATIONAL_INTENT_FORMAT.md").read_text(encoding="utf-8")
        assert "4D" in text or "volume" in text.lower() or "볼륨" in text

    def test_contains_state_machine(self):
        text = (CERT_DIR / "OPERATIONAL_INTENT_FORMAT.md").read_text(encoding="utf-8")
        assert "Accepted" in text or "Activated" in text

    def test_contains_astm_reference(self):
        text = (CERT_DIR / "OPERATIONAL_INTENT_FORMAT.md").read_text(encoding="utf-8")
        assert "ASTM" in text or "F3548" in text

    def test_contains_json_schema(self):
        text = (CERT_DIR / "OPERATIONAL_INTENT_FORMAT.md").read_text(encoding="utf-8")
        lower = text.lower()
        assert "json" in lower or "schema" in lower
