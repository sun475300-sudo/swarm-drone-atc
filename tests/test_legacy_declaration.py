"""GENESIS Phase 400 -- SDACS Legacy 선언 테스트.

검증 항목:
- SubsystemSummary / LegacyDeclaration frozen
- 상수 값 검증
- generate_declaration / render_declaration / generate_certificate
- CLI: --declare, --certificate, --json
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

from simulation.legacy_declaration import (
    DECLARATION_BODY_CONDITIONAL,
    DECLARATION_BODY_PASSED,
    DECLARATION_DATE,
    DECLARATION_TEMPLATE,
    PROJECT_FULL_NAME,
    PROJECT_NAME,
    PROJECT_VERSION,
    LegacyDeclaration,
    SubsystemSummary,
    generate_certificate,
    generate_declaration,
    render_declaration,
)


class TestSubsystemSummary:
    def test_frozen(self) -> None:
        s = SubsystemSummary("maturity", 80.0, "B", "통과")
        with pytest.raises(AttributeError):
            s.score = 90.0  # type: ignore[misc]

    def test_fields(self) -> None:
        s = SubsystemSummary("maturity", 82.9, "B", "통과")
        assert s.name == "maturity"
        assert s.score == 82.9
        assert s.grade == "B"
        assert s.status == "통과"

    def test_as_dict(self) -> None:
        d = SubsystemSummary("x", 90.0, "A", "통과").as_dict()
        assert d["name"] == "x"
        assert d["score"] == 90.0
        assert d["grade"] == "A"
        assert d["status"] == "통과"


class TestLegacyDeclaration:
    def test_frozen(self) -> None:
        decl = LegacyDeclaration(
            "SDACS", "Full Name", "1.0.0", "2026-01-01",
            80.0, "B", True, (), "text",
        )
        with pytest.raises(AttributeError):
            decl.gate_passed = False  # type: ignore[misc]

    def test_as_dict(self) -> None:
        s = SubsystemSummary("a", 90.0, "A", "통과")
        decl = LegacyDeclaration(
            "SDACS", "Full", "1.0.0", "2026-01-01",
            90.0, "A", True, (s,), "body",
        )
        d = decl.as_dict()
        assert d["project_name"] == "SDACS"
        assert d["gate_passed"] is True
        assert len(d["subsystem_summary"]) == 1
        text = json.dumps(d, ensure_ascii=False)
        assert isinstance(text, str)


class TestConstants:
    def test_declaration_date(self) -> None:
        assert DECLARATION_DATE == "2026-06-25"

    def test_project_name(self) -> None:
        assert PROJECT_NAME == "SDACS"

    def test_project_version(self) -> None:
        assert PROJECT_VERSION == "1.0.0"

    def test_project_full_name(self) -> None:
        assert PROJECT_FULL_NAME == "Swarm Drone Airspace Control System"

    def test_declaration_template_has_placeholders(self) -> None:
        assert "{project_name}" in DECLARATION_TEMPLATE
        assert "{overall_grade}" in DECLARATION_TEMPLATE

    def test_body_passed_not_empty(self) -> None:
        assert len(DECLARATION_BODY_PASSED) > 50

    def test_body_conditional_not_empty(self) -> None:
        assert len(DECLARATION_BODY_CONDITIONAL) > 50

    def test_bodies_differ(self) -> None:
        assert DECLARATION_BODY_PASSED != DECLARATION_BODY_CONDITIONAL


class TestGenerateDeclaration:
    def test_returns_declaration(self) -> None:
        decl = generate_declaration()
        assert isinstance(decl, LegacyDeclaration)

    def test_project_name(self) -> None:
        decl = generate_declaration()
        assert decl.project_name == PROJECT_NAME

    def test_project_full_name(self) -> None:
        decl = generate_declaration()
        assert decl.project_full_name == PROJECT_FULL_NAME

    def test_version(self) -> None:
        decl = generate_declaration()
        assert decl.version == PROJECT_VERSION

    def test_declaration_date(self) -> None:
        decl = generate_declaration()
        assert decl.declaration_date == DECLARATION_DATE

    def test_genesis_completion_range(self) -> None:
        decl = generate_declaration()
        assert 0 <= decl.subsystem_health_avg <= 100

    def test_overall_grade_valid(self) -> None:
        decl = generate_declaration()
        assert decl.overall_grade in ("A", "B", "C", "D", "F")

    def test_gate_passed_is_bool(self) -> None:
        decl = generate_declaration()
        assert isinstance(decl.gate_passed, bool)

    def test_subsystem_summary_is_tuple(self) -> None:
        decl = generate_declaration()
        assert isinstance(decl.subsystem_summary, tuple)

    def test_subsystem_count(self) -> None:
        decl = generate_declaration()
        assert len(decl.subsystem_summary) == 6

    def test_subsystem_names(self) -> None:
        decl = generate_declaration()
        names = {s.name for s in decl.subsystem_summary}
        expected = {"maturity", "handover", "education_assets", "genesis_report", "sustainability", "publication"}
        assert names == expected

    def test_declaration_text_not_empty(self) -> None:
        decl = generate_declaration()
        assert len(decl.declaration_text) > 50

    def test_as_dict_json_serializable(self) -> None:
        text = json.dumps(generate_declaration().as_dict(), ensure_ascii=False)
        assert isinstance(text, str)

    def test_invalid_repo_root_raises(self) -> None:
        with pytest.raises(ValueError, match="does not exist"):
            generate_declaration(pathlib.Path("/nonexistent/xxx"))

    def test_empty_repo(self, tmp_path: pathlib.Path) -> None:
        decl = generate_declaration(tmp_path)
        assert isinstance(decl, LegacyDeclaration)
        assert len(decl.subsystem_summary) == 6

    def test_body_passed_when_gate_passes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from unittest.mock import MagicMock
        from simulation.integration_gate import IntegrationGateReport, SubsystemGate
        mock_gate = IntegrationGateReport(
            subsystems=(
                SubsystemGate("maturity", "maturity_assessment", 90.0, "A", True),
                SubsystemGate("handover", "handover_checklist", 85.0, "B", True),
                SubsystemGate("education_assets", "education_asset_registry", 95.0, "A", True),
                SubsystemGate("genesis_report", "genesis_report", 80.0, "B", True),
                SubsystemGate("sustainability", "ecosystem_sustainability", 88.0, "B", True),
                SubsystemGate("publication", "asset_publication_checklist", 82.0, "B", True),
            ),
            total_subsystems=6,
            all_passed=6,
            overall_score=86.7,
            overall_grade="B",
            gate_passed=True,
        )
        monkeypatch.setattr("simulation.legacy_declaration.run_gate", lambda *a, **kw: mock_gate)
        decl = generate_declaration()
        assert decl.gate_passed is True
        assert decl.declaration_text == DECLARATION_BODY_PASSED

    def test_body_conditional_when_gate_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from simulation.integration_gate import IntegrationGateReport, SubsystemGate
        mock_gate = IntegrationGateReport(
            subsystems=(
                SubsystemGate("maturity", "maturity_assessment", 90.0, "A", True),
                SubsystemGate("handover", "handover_checklist", 50.0, "F", False),
                SubsystemGate("education_assets", "education_asset_registry", 95.0, "A", True),
                SubsystemGate("genesis_report", "genesis_report", 30.0, "F", False),
                SubsystemGate("sustainability", "ecosystem_sustainability", 88.0, "B", True),
                SubsystemGate("publication", "asset_publication_checklist", 82.0, "B", True),
            ),
            total_subsystems=6,
            all_passed=4,
            overall_score=72.5,
            overall_grade="C",
            gate_passed=False,
        )
        monkeypatch.setattr("simulation.legacy_declaration.run_gate", lambda *a, **kw: mock_gate)
        decl = generate_declaration()
        assert decl.gate_passed is False
        assert decl.declaration_text == DECLARATION_BODY_CONDITIONAL


class TestRenderDeclaration:
    def test_returns_string(self) -> None:
        decl = generate_declaration()
        text = render_declaration(decl)
        assert isinstance(text, str)

    def test_contains_project_name(self) -> None:
        decl = generate_declaration()
        text = render_declaration(decl)
        assert PROJECT_NAME in text

    def test_contains_date(self) -> None:
        decl = generate_declaration()
        text = render_declaration(decl)
        assert DECLARATION_DATE in text

    def test_contains_grade(self) -> None:
        decl = generate_declaration()
        text = render_declaration(decl)
        assert decl.overall_grade in text

    def test_contains_gate_status(self) -> None:
        decl = generate_declaration()
        text = render_declaration(decl)
        gate = "통과" if decl.gate_passed else "조건부"
        assert gate in text


class TestGenerateCertificate:
    def test_returns_dict(self) -> None:
        cert = generate_certificate()
        assert isinstance(cert, dict)

    def test_has_required_keys(self) -> None:
        cert = generate_certificate()
        for key in ("certificate_type", "project", "version", "date", "grade", "gate_passed", "status", "subsystems"):
            assert key in cert, f"Missing key: {key}"

    def test_project_name(self) -> None:
        cert = generate_certificate()
        assert cert["project"] == PROJECT_NAME

    def test_status_values(self) -> None:
        cert = generate_certificate()
        assert cert["status"] in ("Full Legacy", "Conditional Legacy")

    def test_subsystems_count(self) -> None:
        cert = generate_certificate()
        assert len(cert["subsystems"]) == 6

    def test_json_serializable(self) -> None:
        text = json.dumps(generate_certificate(), ensure_ascii=False)
        assert isinstance(text, str)

    def test_accepts_precomputed_declaration(self) -> None:
        decl = generate_declaration()
        cert = generate_certificate(decl=decl)
        assert cert["project"] == PROJECT_NAME
        assert cert["grade"] == decl.overall_grade


class TestCLI:
    REPO_ROOT = pathlib.Path(__file__).parent.parent
    SCRIPT = str(REPO_ROOT / "simulation" / "legacy_declaration.py")
    UTF8_ENV = {**os.environ, "PYTHONUTF8": "1"}

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, self.SCRIPT, *args],
            capture_output=True, encoding="utf-8", env=self.UTF8_ENV,
            timeout=30,
        )

    def test_declare(self) -> None:
        r = self._run("--declare")
        assert r.returncode == 0
        assert "SDACS" in r.stdout

    def test_declare_json(self) -> None:
        r = self._run("--declare", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["project_name"] == "SDACS"

    def test_certificate(self) -> None:
        r = self._run("--certificate")
        assert r.returncode == 0

    def test_certificate_json(self) -> None:
        r = self._run("--certificate", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "certificate_type" in data

    def test_no_args(self) -> None:
        r = self._run()
        assert r.returncode != 0
