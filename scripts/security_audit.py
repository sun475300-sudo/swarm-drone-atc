"""P719 — Security audit runner.

Runs three layers of security checks and emits a structured report:
  1. bandit  — Python static analysis (SAST)
  2. pip-audit / safety  — dependency CVE scan (SCA)
  3. OWASP checklist  — manual checklist items evaluated from source

Exit code: 0 = clean, 1 = issues found (MEDIUM+), 2 = tool error.

Usage:
    python scripts/security_audit.py
    python scripts/security_audit.py --fail-on low   # fail on any finding
    python scripts/security_audit.py --report reports/security_audit.json
    python scripts/security_audit.py --skip-bandit --skip-cve
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


# --- Severity levels ---

_SEVERITIES = {"low": 1, "medium": 2, "high": 3, "critical": 4}


@dataclass
class Finding:
    tool: str
    severity: str   # low | medium | high | critical
    title: str
    location: str = ""
    detail: str = ""


@dataclass
class AuditReport:
    findings: list[Finding] = field(default_factory=list)
    bandit_ok: bool = False
    cve_ok: bool = False
    owasp_ok: bool = False
    errors: list[str] = field(default_factory=list)

    @property
    def worst_severity(self) -> str:
        if not self.findings:
            return "none"
        return max(self.findings, key=lambda f: _SEVERITIES.get(f.severity, 0)).severity


# --- bandit SAST ---


def run_bandit(report: AuditReport, paths: list[str]) -> None:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "bandit", "-r", *paths, "-f", "json", "-q"],
            capture_output=True,
            text=True,
        )
        if result.returncode not in (0, 1):
            report.errors.append(f"bandit exit {result.returncode}: {result.stderr[:200]}")
            return
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            report.errors.append(f"bandit output not JSON: {result.stdout[:200]}")
            return
        for issue in data.get("results", []):
            report.findings.append(Finding(
                tool="bandit",
                severity=issue.get("issue_severity", "low").lower(),
                title=issue.get("issue_text", ""),
                location=f"{issue.get('filename', '')}:{issue.get('line_number', '')}",
                detail=issue.get("test_id", ""),
            ))
        report.bandit_ok = True
    except FileNotFoundError:
        report.errors.append("bandit not installed — pip install bandit")


# --- pip-audit CVE scan ---


def run_cve_scan(report: AuditReport) -> None:
    # Try pip-audit first, fall back to safety
    for cmd in (
        [sys.executable, "-m", "pip_audit", "--format", "json"],
        [sys.executable, "-m", "safety", "check", "--json"],
    ):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode not in (0, 64, 1):  # 64 = pip-audit vuln found
                continue
            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError:
                continue
            vulns = data if isinstance(data, list) else data.get("vulnerabilities", [])
            for v in vulns:
                pkg = v.get("name") or v.get("package") or "?"
                vuln_id = v.get("id") or v.get("vulnerability_id") or "?"
                report.findings.append(Finding(
                    tool="cve-scan",
                    severity="high",
                    title=f"{pkg}: {vuln_id}",
                    location=f"{pkg}@{v.get('version', '?')}",
                    detail=v.get("description", v.get("advisory", ""))[:200],
                ))
            report.cve_ok = True
            return
        except FileNotFoundError:
            continue
    report.errors.append("no CVE scanner found — pip install pip-audit")


# --- OWASP checklist ---


_OWASP_CHECKS = [
    ("no hardcoded secrets", "grep -r 'password\s*=\s*[\"'][^\"']+[\"']' --include='*.py' -l"),
    ("no debug=True in prod", "grep -r 'debug\s*=\s*True' --include='*.py' -l"),
    ("SQL uses parameterized queries", "grep -r 'execute.*%s\|execute.*format' --include='*.py' -l"),
]


def run_owasp_checklist(report: AuditReport, root: Path) -> None:
    for name, pattern in _OWASP_CHECKS:
        cmd = pattern.split()
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=str(root),
            )
            if result.stdout.strip():
                report.findings.append(Finding(
                    tool="owasp-checklist",
                    severity="high",
                    title=f"Possible issue: {name}",
                    location=result.stdout.strip()[:300],
                ))
        except Exception as exc:
            report.errors.append(f"owasp check '{name}' failed: {exc}")
    report.owasp_ok = True


# --- Report output ---


def _print_report(report: AuditReport, fail_on: str) -> int:
    min_sev = _SEVERITIES.get(fail_on.lower(), 2)

    print("=" * 64)
    print("SDACS P719 Security Audit Report")
    print("=" * 64)
    print(f"bandit SAST       : {'✓' if report.bandit_ok else '✗ skipped/error'}")
    print(f"CVE scan          : {'✓' if report.cve_ok else '✗ skipped/error'}")
    print(f"OWASP checklist   : {'✓' if report.owasp_ok else '✗ skipped/error'}")

    if report.errors:
        print(f"\nTool errors ({len(report.errors)}):")
        for e in report.errors:
            print(f"  ! {e}")

    if not report.findings:
        print("\n✓ No findings.")
    else:
        by_sev: dict[str, list[Finding]] = {}
        for f in report.findings:
            by_sev.setdefault(f.severity, []).append(f)

        print(f"\nFindings ({len(report.findings)} total):")
        for sev in ("critical", "high", "medium", "low"):
            items = by_sev.get(sev, [])
            if not items:
                continue
            print(f"\n  [{sev.upper()}] {len(items)} finding(s):")
            for item in items[:10]:
                loc = f" ({item.location})" if item.location else ""
                print(f"    [{item.tool}]{loc} {item.title}")
            if len(items) > 10:
                print(f"    … {len(items) - 10} more")

    blocking = [f for f in report.findings if _SEVERITIES.get(f.severity, 0) >= min_sev]
    if blocking:
        print(f"\nFAIL — {len(blocking)} finding(s) at {fail_on.upper()}+ severity")
        return 1
    print(f"\nPASS — no findings at {fail_on.upper()}+ severity")
    return 0


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="P719 security audit")
    parser.add_argument("--paths", nargs="+", default=["api", "simulation", "src"],
                        help="source paths for bandit scan")
    parser.add_argument("--fail-on", default="medium",
                        choices=list(_SEVERITIES), help="minimum severity to fail on")
    parser.add_argument("--report", default="",
                        help="write JSON report to this path")
    parser.add_argument("--skip-bandit", action="store_true")
    parser.add_argument("--skip-cve", action="store_true")
    parser.add_argument("--skip-owasp", action="store_true")
    args = parser.parse_args(argv)

    root = Path(__file__).parent.parent
    report = AuditReport()

    if not args.skip_bandit:
        run_bandit(report, args.paths)
    if not args.skip_cve:
        run_cve_scan(report)
    if not args.skip_owasp:
        run_owasp_checklist(report, root)

    if args.report:
        out = Path(args.report)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(
            {
                "worst_severity": report.worst_severity,
                "findings": [asdict(f) for f in report.findings],
                "errors": report.errors,
            },
            indent=2,
        ))
        print(f"Report written to {out}")

    code = _print_report(report, args.fail_on)
    sys.exit(code)


if __name__ == "__main__":
    main()
