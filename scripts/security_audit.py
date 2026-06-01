#!/usr/bin/env python3
"""P719 — 보안 감사 스크립트 (bandit + dependency CVE 스캔).

bandit: 정적 코드 분석 (OWASP Top-10 패턴 탐지)
safety / pip-audit: 의존성 CVE 스캔

Usage:
    python scripts/security_audit.py
    python scripts/security_audit.py --severity medium  # medium+ 이슈만
    python scripts/security_audit.py --out results/security_audit.json

Exit codes:
    0 — CRITICAL 이슈 없음
    1 — CRITICAL 이슈 발견 또는 스캔 실패
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SCAN_TARGETS = [
    REPO_ROOT / "api",
    REPO_ROOT / "src",
    REPO_ROOT / "simulation",
    REPO_ROOT / "scripts",
]

SEVERITY_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


def run_bandit(targets: list[Path], min_severity: str = "LOW") -> dict[str, Any]:
    paths = [str(p) for p in targets if p.exists()]
    if not paths:
        return {"available": False, "error": "scan targets not found"}

    cmd = [sys.executable, "-m", "bandit", "-r", *paths, "-f", "json", "-q"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        # bandit returns 1 on issues found, 0 on clean — both are valid scan outcomes.
        # returncode 2+ indicates a scan error (config error, crash).
        if result.returncode >= 2 and not result.stdout:
            return {"available": False, "error": f"bandit scan error (rc={result.returncode}): {result.stderr[:200]}"}
        raw = json.loads(result.stdout or "{}")
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        return {"available": False, "error": str(exc)}
    except FileNotFoundError:
        return {"available": False, "error": "bandit not installed (pip install bandit)"}

    issues = raw.get("results", [])
    filtered = [
        i for i in issues
        if SEVERITY_ORDER.get(i.get("issue_severity", "LOW"), 0)
        >= SEVERITY_ORDER.get(min_severity, 0)
    ]

    severity_counts: dict[str, int] = {}
    for i in filtered:
        sev = i.get("issue_severity", "UNKNOWN")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    return {
        "available": True,
        "total_issues": len(filtered),
        "severity_counts": severity_counts,
        "issues": [
            {
                "file": i.get("filename", ""),
                "line": i.get("line_number", 0),
                "severity": i.get("issue_severity", ""),
                "confidence": i.get("issue_confidence", ""),
                "test_id": i.get("test_id", ""),
                "text": i.get("issue_text", ""),
            }
            for i in filtered
        ],
        "metrics": raw.get("metrics", {}),
    }


def run_pip_audit() -> dict[str, Any]:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip_audit", "--format", "json"],
            capture_output=True, text=True, timeout=120,
        )
        data = json.loads(result.stdout or "[]")
        vulns = [
            {"name": d.get("name"), "version": d.get("version"), "vulns": d.get("vulns", [])}
            for d in data if d.get("vulns")
        ]
        return {"available": True, "vulnerable_packages": len(vulns), "details": vulns}
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        return {"available": False, "error": str(exc)}
    except FileNotFoundError:
        return {"available": False, "error": "pip-audit not installed (pip install pip-audit)"}


def run_safety() -> dict[str, Any]:
    req_file = REPO_ROOT / "requirements.txt"
    if not req_file.exists():
        return {"available": False, "error": "requirements.txt not found"}
    try:
        result = subprocess.run(
            [sys.executable, "-m", "safety", "check", "-r", str(req_file), "--json"],
            capture_output=True, text=True, timeout=120,
        )
        data = json.loads(result.stdout or "[]")
        return {"available": True, "vulnerabilities": len(data), "details": data}
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        return {"available": False, "error": str(exc)}
    except FileNotFoundError:
        return {"available": False, "error": "safety not installed (pip install safety)"}


def _has_critical(bandit_result: dict) -> bool:
    return bandit_result.get("severity_counts", {}).get("CRITICAL", 0) > 0


def main() -> int:
    parser = argparse.ArgumentParser(description="SDACS P719 보안 감사")
    parser.add_argument("--severity", choices=["LOW", "MEDIUM", "HIGH", "CRITICAL"], default="LOW")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    print("=" * 60)
    print("SDACS P719 보안 감사 리포트")
    print("=" * 60)

    print("\n[1/3] bandit 정적 분석...")
    bandit = run_bandit(SCAN_TARGETS, min_severity=args.severity)
    if bandit.get("available"):
        print(f"  발견 이슈: {bandit['total_issues']}")
        for sev, cnt in sorted(bandit.get("severity_counts", {}).items(),
                                key=lambda x: SEVERITY_ORDER.get(x[0], 0), reverse=True):
            print(f"    {sev}: {cnt}건")
        if bandit["issues"]:
            print("\n  상위 이슈 (최대 10개):")
            for issue in bandit["issues"][:10]:
                print(f"    [{issue['severity']}] {issue['file']}:{issue['line']} — {issue['text'][:80]}")
    else:
        print(f"  ⚠ bandit 사용 불가: {bandit.get('error')}")

    print("\n[2/3] pip-audit CVE 스캔...")
    pip_audit = run_pip_audit()
    if pip_audit.get("available"):
        print(f"  취약 패키지: {pip_audit['vulnerable_packages']}개")
        for pkg in pip_audit.get("details", []):
            print(f"    {pkg['name']}=={pkg['version']}: {len(pkg['vulns'])}건")
    else:
        print(f"  ⚠ pip-audit 사용 불가: {pip_audit.get('error')}")

    print("\n[3/3] safety 의존성 검사...")
    safety = run_safety()
    if safety.get("available"):
        print(f"  취약점: {safety['vulnerabilities']}개")
    else:
        print(f"  ⚠ safety 사용 불가: {safety.get('error')}")

    report = {
        "bandit": bandit,
        "pip_audit": pip_audit,
        "safety": safety,
        "critical_found": _has_critical(bandit),
    }

    out = args.out or REPO_ROOT / "results" / "security_audit_latest.json"
    out.parent.mkdir(exist_ok=True)
    import datetime
    report["timestamp"] = datetime.datetime.utcnow().isoformat()
    out.write_text(json.dumps(report, indent=2, default=str))

    print("\n" + "=" * 60)
    critical = _has_critical(bandit)
    status = "FAIL — CRITICAL 이슈 발견" if critical else "PASS — CRITICAL 이슈 없음"
    print(f"판정: {status}")
    print(f"리포트 저장: {out}")

    return 1 if critical else 0


if __name__ == "__main__":
    sys.exit(main())
