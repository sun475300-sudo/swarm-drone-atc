"""GENESIS Phase 312 -- CSAP 통제항목 카탈로그 확장 테스트.

검증 항목:
- ScanResult / CatalogScanReport frozen
- SCAN_RULES 레지스트리 무결성
- scan_catalog / get_domain_scan / list_domains
- CLI: --scan, --domain, --domains, --json
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

from simulation.csap_catalog_extension import (
    SCAN_RULES,
    CatalogScanReport,
    ScanResult,
    get_domain_scan,
    list_domains,
    scan_catalog,
)
from simulation.csap_self_assessment import DEFAULT_CATALOG, Status


class TestScanResult:
    def test_frozen(self) -> None:
        s = ScanResult("1", "정보보호 정책 및 조직", "테스트", Status.IMPLEMENTED, ())
        with pytest.raises(AttributeError):
            s.status = Status.NOT_IMPLEMENTED  # type: ignore[misc]

    def test_fields(self) -> None:
        s = ScanResult("3", "자산 관리", "자산목록", Status.PARTIAL, ("a.py",))
        assert s.domain_code == "3"
        assert s.status is Status.PARTIAL
        assert s.evidence == ("a.py",)

    def test_as_dict(self) -> None:
        d = ScanResult("1", "이름", "항목", Status.IMPLEMENTED, ("f.py",)).as_dict()
        assert d["status"] == "이행"
        assert d["evidence"] == ["f.py"]


class TestCatalogScanReport:
    def test_frozen(self) -> None:
        from simulation.csap_self_assessment import Assessment, DomainScore
        a = Assessment((), 0.5, "보완 후 신청", ())
        r = CatalogScanReport((), a, 0, 0, 0, 0)
        with pytest.raises(AttributeError):
            r.total_controls = 99  # type: ignore[misc]

    def test_as_dict(self) -> None:
        report = scan_catalog()
        d = report.as_dict()
        text = json.dumps(d, ensure_ascii=False)
        assert isinstance(text, str)
        assert "total_controls" in d
        assert "verdict" in d


class TestRegistries:
    def test_scan_rules_is_tuple(self) -> None:
        assert isinstance(SCAN_RULES, tuple)

    def test_scan_rules_count(self) -> None:
        assert len(SCAN_RULES) == 35

    def test_all_domain_codes_valid(self) -> None:
        for domain_code, _, _ in SCAN_RULES:
            assert domain_code in DEFAULT_CATALOG, f"Invalid domain code: {domain_code}"

    def test_all_controls_in_catalog(self) -> None:
        for domain_code, control_name, _ in SCAN_RULES:
            controls = DEFAULT_CATALOG[domain_code][1]
            assert control_name in controls, f"Control '{control_name}' not in domain {domain_code}"

    def test_unique_rules(self) -> None:
        keys = [(dc, cn) for dc, cn, _ in SCAN_RULES]
        assert len(keys) == len(set(keys))

    def test_all_pattern_groups_nonempty(self) -> None:
        for _, _, groups in SCAN_RULES:
            assert len(groups) > 0
            for patterns in groups:
                assert len(patterns) > 0


class TestScanCatalog:
    def test_returns_report(self) -> None:
        report = scan_catalog()
        assert isinstance(report, CatalogScanReport)

    def test_total_controls(self) -> None:
        report = scan_catalog()
        assert report.total_controls == 35

    def test_counts_consistent(self) -> None:
        report = scan_catalog()
        total = report.implemented_count + report.partial_count + report.not_implemented_count
        assert total == report.total_controls

    def test_overall_rate_range(self) -> None:
        report = scan_catalog()
        assert 0 <= report.assessment.overall_rate <= 1.0

    def test_verdict_valid(self) -> None:
        report = scan_catalog()
        assert report.assessment.verdict in ("신청 권장", "보완 후 신청", "준비 부족")

    def test_domains_count(self) -> None:
        report = scan_catalog()
        assert len(report.assessment.domains) == 14

    def test_as_dict_json_serializable(self) -> None:
        text = json.dumps(scan_catalog().as_dict(), ensure_ascii=False)
        assert isinstance(text, str)

    def test_invalid_repo_root_raises(self) -> None:
        with pytest.raises(ValueError, match="does not exist"):
            scan_catalog(pathlib.Path("/nonexistent/xxx"))

    def test_empty_repo(self, tmp_path: pathlib.Path) -> None:
        report = scan_catalog(tmp_path)
        assert report.total_controls == 35
        assert report.not_implemented_count == 35

    def test_scan_results_have_evidence(self) -> None:
        report = scan_catalog()
        for r in report.scan_results:
            if r.status is Status.IMPLEMENTED or r.status is Status.PARTIAL:
                assert len(r.evidence) > 0, f"{r.control} has no evidence"


class TestGetDomainScan:
    def test_valid_domain(self) -> None:
        result = get_domain_scan("1")
        assert result["domain_code"] == "1"
        assert "controls" in result

    def test_all_domains(self) -> None:
        for code in DEFAULT_CATALOG:
            result = get_domain_scan(code)
            assert result["domain_code"] == code

    def test_invalid_domain_raises(self) -> None:
        with pytest.raises(ValueError, match="유효하지 않은"):
            get_domain_scan("999")

    def test_rate_range(self) -> None:
        result = get_domain_scan("1")
        assert 0 <= result["rate"] <= 1.0


class TestListDomains:
    def test_returns_list(self) -> None:
        domains = list_domains()
        assert isinstance(domains, list)

    def test_count(self) -> None:
        assert len(list_domains()) == 14

    def test_has_keys(self) -> None:
        for d in list_domains():
            assert "code" in d
            assert "name" in d
            assert "control_count" in d

    def test_json_serializable(self) -> None:
        text = json.dumps(list_domains(), ensure_ascii=False)
        assert isinstance(text, str)


class TestCLI:
    REPO_ROOT = pathlib.Path(__file__).parent.parent
    SCRIPT = str(REPO_ROOT / "simulation" / "csap_catalog_extension.py")
    UTF8_ENV = {**os.environ, "PYTHONUTF8": "1"}

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, self.SCRIPT, *args],
            capture_output=True, encoding="utf-8", env=self.UTF8_ENV,
            timeout=30,
        )

    def test_scan(self) -> None:
        r = self._run("--scan")
        assert r.returncode == 0
        assert "CSAP" in r.stdout

    def test_scan_json(self) -> None:
        r = self._run("--scan", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "total_controls" in data

    def test_domain(self) -> None:
        r = self._run("--domain", "1")
        assert r.returncode == 0

    def test_domain_json(self) -> None:
        r = self._run("--domain", "1", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["domain_code"] == "1"

    def test_domain_invalid(self) -> None:
        r = self._run("--domain", "999")
        assert r.returncode != 0

    def test_domains(self) -> None:
        r = self._run("--domains")
        assert r.returncode == 0

    def test_domains_json(self) -> None:
        r = self._run("--domains", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert len(data) == 14

    def test_no_args(self) -> None:
        r = self._run()
        assert r.returncode != 0
