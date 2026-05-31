#!/usr/bin/env python3
"""P719 — SDACS 의존성 CVE 스캔 + 보안 감사 리포트 생성.

Usage:
    python scripts/security_audit.py
    python scripts/security_audit.py --out-dir reports/security --format md
    python scripts/security_audit.py --fail-on-critical

Exit codes:
    0 — 감사 완료 (CRITICAL 없음 또는 --fail-on-critical 미사용)
    1 — CRITICAL/HIGH CVE 발견 (--fail-on-critical 사용 시)
    2 — pip-audit 미설치 또는 실행 오류
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# CVSS 기준 심각도 분류 (CVSS 없을 경우 키워드 기반 휴리스틱)
_HIGH_KEYWORDS = {"remote code execution", "rce", "arbitrary code", "privilege escalation"}
_MEDIUM_KEYWORDS = {"denial of service", "dos", "path traversal", "information disclosure"}

# 프로젝트 직접 의존성 (requirements.txt 기준)
_PROJECT_DEPS: set[str] = set()


def _load_project_deps() -> set[str]:
    req_file = REPO_ROOT / "requirements.txt"
    if not req_file.exists():
        return set()
    deps = set()
    for line in req_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            name = line.split(">=")[0].split("<=")[0].split("==")[0].split("[")[0].strip().lower()
            deps.add(name)
    return deps


@dataclass(frozen=True)
class Vulnerability:
    package: str
    version: str
    vuln_id: str
    aliases: list[str]
    fix_versions: list[str]
    description: str
    is_direct_dep: bool = False

    @property
    def severity(self) -> str:
        desc = self.description.lower()
        if any(kw in desc for kw in _HIGH_KEYWORDS):
            return "HIGH"
        if any(kw in desc for kw in _MEDIUM_KEYWORDS):
            return "MEDIUM"
        return "LOW"

    @property
    def cve_ids(self) -> list[str]:
        return [a for a in self.aliases if a.startswith("CVE-")]


@dataclass
class AuditReport:
    scan_time: datetime
    vulns: list[Vulnerability] = field(default_factory=list)
    total_packages: int = 0
    pip_audit_version: str = "unknown"

    @property
    def critical_count(self) -> int:
        return sum(1 for v in self.vulns if v.severity == "HIGH" and v.is_direct_dep)

    @property
    def high_count(self) -> int:
        return sum(1 for v in self.vulns if v.severity == "HIGH")

    @property
    def medium_count(self) -> int:
        return sum(1 for v in self.vulns if v.severity == "MEDIUM")

    @property
    def low_count(self) -> int:
        return sum(1 for v in self.vulns if v.severity == "LOW")


def run_pip_audit() -> dict:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip_audit", "--format", "json"],
            capture_output=True, text=True, timeout=120,
        )
        return json.loads(result.stdout)
    except FileNotFoundError:
        print("ERROR: pip-audit 미설치. pip install pip-audit", file=sys.stderr)
        sys.exit(2)
    except subprocess.TimeoutExpired:
        print("ERROR: pip-audit 시간 초과", file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError as e:
        print(f"ERROR: pip-audit 출력 파싱 실패: {e}", file=sys.stderr)
        sys.exit(2)


def parse_audit_output(data: dict) -> AuditReport:
    project_deps = _load_project_deps()
    report = AuditReport(scan_time=datetime.now(timezone.utc))
    report.total_packages = len(data.get("dependencies", []))

    for dep in data.get("dependencies", []):
        name = dep["name"]
        version = dep.get("version", "unknown")
        is_direct = name.lower().replace("-", "_") in project_deps or name.lower() in project_deps

        for v in dep.get("vulns", []):
            report.vulns.append(Vulnerability(
                package=name,
                version=version,
                vuln_id=v["id"],
                aliases=v.get("aliases", []),
                fix_versions=v.get("fix_versions", []),
                description=v.get("description", ""),
                is_direct_dep=is_direct,
            ))
    return report


def generate_markdown(report: AuditReport, out_path: Path) -> None:
    lines: list[str] = []
    ts = report.scan_time.strftime("%Y-%m-%d %H:%M UTC")
    lines.append(f"# SDACS 의존성 보안 감사 리포트\n")
    lines.append(f"**스캔 시각:** {ts}  \n")
    lines.append(f"**스캔 패키지:** {report.total_packages}개  \n")
    lines.append(f"**취약점 총계:** {len(report.vulns)}개 "
                 f"(HIGH={report.high_count}, MEDIUM={report.medium_count}, LOW={report.low_count})\n")
    lines.append(f"**직접 의존성 HIGH:** {report.critical_count}개\n")

    if not report.vulns:
        lines.append("\n✅ 취약점 없음\n")
    else:
        lines.append("\n## 취약점 목록\n")
        lines.append("| 심각도 | 패키지 | 버전 | ID | CVE | 수정 버전 | 직접 의존? |")
        lines.append("|--------|--------|------|----|-----|----------|-----------|")
        for v in sorted(report.vulns, key=lambda x: (x.severity != "HIGH", x.package)):
            cves = ", ".join(v.cve_ids) if v.cve_ids else "—"
            fix = ", ".join(v.fix_versions) if v.fix_versions else "미정"
            direct = "✅" if v.is_direct_dep else "—"
            lines.append(f"| {v.severity} | {v.package} | {v.version} | {v.vuln_id} | {cves} | {fix} | {direct} |")

        lines.append("\n## 상세 설명\n")
        for v in sorted(report.vulns, key=lambda x: (x.severity != "HIGH", x.package)):
            desc = v.description[:500].replace("\n", " ")
            lines.append(f"### {v.vuln_id} — {v.package} {v.version}")
            lines.append(f"- **심각도:** {v.severity}")
            lines.append(f"- **직접 의존:** {'예' if v.is_direct_dep else '아니오 (전이적 의존)'}")
            lines.append(f"- **수정 버전:** {', '.join(v.fix_versions) if v.fix_versions else '미정'}")
            lines.append(f"- **설명:** {desc}\n")

    lines.append("\n## 권고 사항\n")
    lines.append("1. **직접 의존성 HIGH 취약점** 즉시 패치 (requirements.txt 버전 업데이트)")
    lines.append("2. **전이적 의존성** — 상위 패키지 업데이트로 간접 해결")
    lines.append("3. **수정 버전 미정 항목** — 해당 패키지 동향 모니터링 및 대안 검토")
    lines.append("4. 주기적 재스캔: `python scripts/security_audit.py` (CI 자동화 권장)\n")
    lines.append(f"\n---\n*Generated by SDACS security_audit.py on {ts}*\n")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"리포트 저장: {out_path}")


def _print_summary(report: AuditReport) -> None:
    print(f"\n{'='*60}")
    print(f"SDACS 보안 감사 결과 ({report.scan_time.strftime('%Y-%m-%d %H:%M UTC')})")
    print(f"{'='*60}")
    print(f"스캔 패키지: {report.total_packages}개 | 취약점: {len(report.vulns)}개")
    print(f"HIGH={report.high_count} MEDIUM={report.medium_count} LOW={report.low_count}")
    print(f"직접 의존성 HIGH: {report.critical_count}개")
    if report.vulns:
        print("\n취약점:")
        for v in sorted(report.vulns, key=lambda x: (x.severity != "HIGH", x.package)):
            direct = "[직접]" if v.is_direct_dep else "[전이]"
            print(f"  {v.severity:6} {direct} {v.package}=={v.version} {v.vuln_id}")
    print(f"{'='*60}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SDACS 의존성 CVE 스캔")
    parser.add_argument("--out-dir", default="reports/security",
                        help="리포트 저장 디렉토리 (기본: reports/security)")
    parser.add_argument("--format", choices=["md", "json", "both"], default="md")
    parser.add_argument("--fail-on-critical", action="store_true",
                        help="직접 의존성 HIGH CVE 발견 시 exit code 1")
    args = parser.parse_args(argv)

    data = run_pip_audit()
    report = parse_audit_output(data)
    _print_summary(report)

    out_dir = REPO_ROOT / args.out_dir
    ts_str = report.scan_time.strftime("%Y-%m-%d")

    if args.format in ("md", "both"):
        generate_markdown(report, out_dir / f"cve_scan_{ts_str}.md")

    if args.format in ("json", "both"):
        out_path = out_dir / f"cve_scan_{ts_str}.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        raw = {
            "scan_time": report.scan_time.isoformat(),
            "total_packages": report.total_packages,
            "vulnerabilities": [
                {
                    "package": v.package, "version": v.version,
                    "id": v.vuln_id, "aliases": v.aliases,
                    "fix_versions": v.fix_versions, "severity": v.severity,
                    "is_direct_dep": v.is_direct_dep,
                }
                for v in report.vulns
            ],
        }
        out_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
        print(f"JSON 저장: {out_path}")

    if args.fail_on_critical and report.critical_count > 0:
        print(f"FAIL: 직접 의존성 HIGH CVE {report.critical_count}개 발견", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
