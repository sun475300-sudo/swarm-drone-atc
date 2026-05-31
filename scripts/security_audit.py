"""P719 — Security audit: pip-audit CVE scan + bandit SAST.

Usage:
    python scripts/security_audit.py            # run all checks
    python scripts/security_audit.py --cve-only # dependency scan only
    python scripts/security_audit.py --sast-only # static analysis only
    python scripts/security_audit.py --json      # machine-readable output
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class AuditFinding:
    tool: str
    severity: str  # "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO"
    description: str
    location: str = ""


@dataclass
class AuditReport:
    cve_findings: list[AuditFinding] = field(default_factory=list)
    sast_findings: list[AuditFinding] = field(default_factory=list)
    cve_scan_ok: bool = False
    sast_scan_ok: bool = False
    errors: list[str] = field(default_factory=list)

    @property
    def critical_count(self) -> int:
        return sum(
            1 for f in self.all_findings if f.severity == "CRITICAL"
        )

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.all_findings if f.severity == "HIGH")

    @property
    def all_findings(self) -> list[AuditFinding]:
        return self.cve_findings + self.sast_findings

    @property
    def passed(self) -> bool:
        return self.critical_count == 0 and self.high_count == 0


def _run(cmd: list[str], capture: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        cwd=ROOT,
    )


def run_cve_scan() -> tuple[list[AuditFinding], bool, str | None]:
    """Run pip-audit to detect known CVEs in installed packages."""
    proc = _run(["python", "-m", "pip_audit", "--format=json", "-r", "pyproject.toml"])
    if proc.returncode not in (0, 1):
        return [], False, f"pip-audit not available or errored: {proc.stderr[:200]}"

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return [], False, "pip-audit output parse error"

    findings: list[AuditFinding] = []
    for dep in data.get("dependencies", []):
        for vuln in dep.get("vulns", []):
            sev = vuln.get("fix_versions") and "HIGH" or "MEDIUM"
            findings.append(
                AuditFinding(
                    tool="pip-audit",
                    severity=sev,
                    description=f"{dep['name']}=={dep['version']}: {vuln['id']} — {vuln.get('description', '')[:120]}",
                    location=f"{dep['name']}=={dep['version']}",
                )
            )
    return findings, True, None


def run_sast_scan() -> tuple[list[AuditFinding], bool, str | None]:
    """Run bandit for Python SAST (static application security testing)."""
    proc = _run(
        [
            "python", "-m", "bandit",
            "-r", "src/", "simulation/", "api/",
            "-f", "json",
            "-ll",  # only medium and above
            "--quiet",
        ]
    )
    # bandit exits 1 when issues found, 0 when clean
    if proc.returncode > 1:
        return [], False, f"bandit not available or error: {proc.stderr[:200]}"

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return [], False, "bandit output parse error"

    sev_map = {"HIGH": "HIGH", "MEDIUM": "MEDIUM", "LOW": "LOW"}
    findings: list[AuditFinding] = []
    for issue in data.get("results", []):
        sev = sev_map.get(issue.get("issue_severity", "LOW"), "LOW")
        findings.append(
            AuditFinding(
                tool="bandit",
                severity=sev,
                description=f"[{issue.get('test_id')}] {issue.get('issue_text', '')}",
                location=f"{issue.get('filename')}:{issue.get('line_number')}",
            )
        )
    return findings, True, None


def audit(run_cve: bool = True, run_sast: bool = True) -> AuditReport:
    report = AuditReport()

    if run_cve:
        findings, ok, err = run_cve_scan()
        report.cve_findings = findings
        report.cve_scan_ok = ok
        if err:
            report.errors.append(err)

    if run_sast:
        findings, ok, err = run_sast_scan()
        report.sast_findings = findings
        report.sast_scan_ok = ok
        if err:
            report.errors.append(err)

    return report


def _print_report(report: AuditReport, as_json: bool) -> None:
    if as_json:
        out = {
            "passed": report.passed,
            "critical": report.critical_count,
            "high": report.high_count,
            "total_findings": len(report.all_findings),
            "findings": [asdict(f) for f in report.all_findings],
            "errors": report.errors,
        }
        print(json.dumps(out, indent=2))
        return

    print("=" * 60)
    print("SDACS Security Audit Report")
    print("=" * 60)

    if report.errors:
        print("\n[WARNINGS]")
        for e in report.errors:
            print(f"  ! {e}")

    _print_section("CVE Scan (pip-audit)", report.cve_findings, report.cve_scan_ok)
    _print_section("SAST (bandit)", report.sast_findings, report.sast_scan_ok)

    print("\n" + "=" * 60)
    status = "PASS" if report.passed else "FAIL"
    print(f"Result: {status}  |  Critical: {report.critical_count}  High: {report.high_count}  Total: {len(report.all_findings)}")
    print("=" * 60)


def _print_section(title: str, findings: list[AuditFinding], ran: bool) -> None:
    print(f"\n[{title}]")
    if not ran:
        print("  (skipped or tool unavailable)")
        return
    if not findings:
        print("  No issues found.")
        return
    for f in findings:
        loc = f" ({f.location})" if f.location else ""
        print(f"  [{f.severity}]{loc} {f.description[:100]}")


def main() -> None:
    parser = argparse.ArgumentParser(description="SDACS security audit")
    parser.add_argument("--cve-only", action="store_true")
    parser.add_argument("--sast-only", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    run_cve = not args.sast_only
    run_sast = not args.cve_only

    report = audit(run_cve=run_cve, run_sast=run_sast)
    _print_report(report, as_json=args.as_json)

    sys.exit(0 if report.passed else 1)


if __name__ == "__main__":
    main()
