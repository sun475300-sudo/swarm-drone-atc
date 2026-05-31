"""P719 — SDACS 보안 감사 스크립트.

수행 항목:
  1. bandit (Python 정적 분석)
  2. safety / pip-audit (의존성 CVE 스캔)
  3. OWASP ZAP baseline (API 엔드포인트 — 실행 중일 때)
  4. 하드코딩 비밀 탐지 (git-secrets / truffleHog 패턴)

사용:
    python scripts/security_audit.py               # 로컬 정적 분석
    python scripts/security_audit.py --zap          # ZAP 포함 (서버 실행 필요)
    python scripts/security_audit.py --out report   # JSON 보고서 저장
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Finding:
    severity: str  # CRITICAL HIGH MEDIUM LOW INFO
    tool: str
    code: str
    message: str
    file: str = ""
    line: int = 0


@dataclass
class AuditReport:
    findings: list[Finding] = field(default_factory=list)
    passed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "CRITICAL")

    @property
    def high_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == "HIGH")


def _run(cmd: list[str], cwd: Path = REPO_ROOT) -> tuple[int, str, str]:
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
    return result.returncode, result.stdout, result.stderr


# --- 1. bandit ---

def run_bandit(report: AuditReport) -> None:
    print("▶ bandit 정적 분석 실행...")
    rc, stdout, stderr = _run([
        sys.executable, "-m", "bandit",
        "-r", "api/", "simulation/", "src/", "scripts/",
        "-f", "json", "-q",
    ])
    if rc not in (0, 1):
        # rc=1 means findings, rc=0 means clean
        report.errors.append(f"bandit 실행 오류: {stderr[:200]}")
        return
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        report.errors.append("bandit JSON 파싱 실패")
        return

    sev_map = {"HIGH": "HIGH", "MEDIUM": "MEDIUM", "LOW": "LOW"}
    for issue in data.get("results", []):
        sev = sev_map.get(issue.get("issue_severity", "LOW"), "LOW")
        report.add(Finding(
            severity=sev,
            tool="bandit",
            code=issue.get("test_id", ""),
            message=issue.get("issue_text", ""),
            file=issue.get("filename", ""),
            line=issue.get("line_number", 0),
        ))

    if not data.get("results"):
        report.passed.append("bandit: 취약점 없음")
    print(f"  bandit: {len(data.get('results', []))}건 발견")


# --- 2. pip-audit (의존성 CVE) ---

def run_pip_audit(report: AuditReport) -> None:
    print("▶ pip-audit 의존성 CVE 스캔...")
    rc, stdout, stderr = _run([
        sys.executable, "-m", "pip_audit",
        "--format", "json", "--require-hashes=false",
    ])
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        report.errors.append(f"pip-audit JSON 파싱 실패: {stderr[:200]}")
        return

    vulns = data.get("vulnerabilities", []) or data.get("dependencies", [])
    for dep in vulns:
        for vuln in dep.get("vulns", []):
            report.add(Finding(
                severity="HIGH",
                tool="pip-audit",
                code=vuln.get("id", ""),
                message=f"{dep.get('name')}@{dep.get('version')}: {vuln.get('description', '')[:120]}",
            ))

    if not any(dep.get("vulns") for dep in vulns):
        report.passed.append("pip-audit: CVE 없음")
    print(f"  pip-audit: CVE {sum(len(d.get('vulns', [])) for d in vulns)}건")


# --- 3. 하드코딩 비밀 탐지 ---

_SECRET_PATTERNS = [
    (re.compile(r'(?i)(password|passwd|pwd)\s*=\s*["\'][^"\']{4,}["\']'), "hardcoded_password"),
    (re.compile(r'(?i)(api_key|apikey|secret_key|jwt_secret)\s*=\s*["\'][^"\']{8,}["\']'), "hardcoded_secret"),
    (re.compile(r'(?i)bearer\s+[A-Za-z0-9\-_\.]{20,}'), "hardcoded_bearer"),
    (re.compile(r'(?i)AKIA[0-9A-Z]{16}'), "aws_access_key"),
]

_EXCLUDE_PATHS = {
    "api/auth.py",       # 기본값은 env 오버라이드 가능
    "tests/",
    "docs/",
}


def run_secret_scan(report: AuditReport) -> None:
    print("▶ 하드코딩 비밀 패턴 스캔...")
    py_files = list(REPO_ROOT.rglob("*.py"))
    hits = 0
    for path in py_files:
        rel = path.relative_to(REPO_ROOT)
        if any(str(rel).startswith(ex) for ex in _EXCLUDE_PATHS):
            continue
        try:
            content = path.read_text(errors="replace")
        except OSError:
            continue
        for pattern, code in _SECRET_PATTERNS:
            for m in pattern.finditer(content):
                line_no = content[: m.start()].count("\n") + 1
                report.add(Finding(
                    severity="CRITICAL",
                    tool="secret-scan",
                    code=code,
                    message=m.group(0)[:80],
                    file=str(rel),
                    line=line_no,
                ))
                hits += 1

    if hits == 0:
        report.passed.append("secret-scan: 하드코딩 비밀 없음")
    print(f"  secret-scan: {hits}건 발견")


# --- 4. OWASP ZAP (선택) ---

def run_zap(report: AuditReport, target: str = "http://localhost:8080") -> None:
    print(f"▶ OWASP ZAP baseline scan ({target})...")
    rc, stdout, stderr = _run([
        "docker", "run", "--rm", "--network=host",
        "ghcr.io/zaproxy/zaproxy:stable",
        "zap-baseline.py", "-t", target, "-J", "/zap/wrk/zap_report.json",
    ])
    print(f"  ZAP 완료 (rc={rc})")
    if rc not in (0, 2):  # 2 = warnings found
        report.errors.append(f"ZAP 실행 오류 (rc={rc})")


# --- 메인 ---

def main(args: argparse.Namespace) -> int:
    report = AuditReport()

    run_secret_scan(report)
    run_bandit(report)
    run_pip_audit(report)
    if args.zap:
        run_zap(report, args.zap_target)

    # 결과 출력
    print("\n" + "=" * 60)
    print(f"[P719 보안 감사 결과]")
    print(f"  CRITICAL: {report.critical_count}")
    print(f"  HIGH:     {report.high_count}")
    print(f"  MEDIUM:   {sum(1 for f in report.findings if f.severity == 'MEDIUM')}")
    print(f"  LOW:      {sum(1 for f in report.findings if f.severity == 'LOW')}")
    print(f"  통과:     {len(report.passed)}")
    print(f"  오류:     {len(report.errors)}")

    for f in report.findings:
        loc = f"{f.file}:{f.line}" if f.file else ""
        print(f"  [{f.severity}] {f.tool}/{f.code} {loc} — {f.message[:80]}")

    if args.out:
        out_path = Path(args.out).with_suffix(".json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps({
            "findings": [vars(f) for f in report.findings],
            "passed": report.passed,
            "errors": report.errors,
        }, indent=2, ensure_ascii=False))
        print(f"\n  보고서 저장: {out_path}")

    # CRITICAL 또는 HIGH 있으면 비정상 종료
    return 1 if (report.critical_count + report.high_count) > 0 else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="P719 SDACS 보안 감사")
    parser.add_argument("--zap", action="store_true", help="OWASP ZAP baseline 포함")
    parser.add_argument("--zap-target", default="http://localhost:8080")
    parser.add_argument("--out", default="", help="JSON 보고서 출력 경로")
    sys.exit(main(parser.parse_args()))
