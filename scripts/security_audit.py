"""P719 — SDACS 보안 감사 스크립트.

실행: python scripts/security_audit.py
결과: results/security_audit_<date>.json

도구:
    - bandit: 정적 분석 (OWASP A03/A05)
    - pip-audit: 의존성 CVE 스캔
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RESULTS = REPO / "results"
RESULTS.mkdir(exist_ok=True)


def _run(cmd: list[str]) -> tuple[int, str, str]:
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def run_bandit() -> dict:
    print(">> bandit 정적 분석 실행 중...")
    rc, out, err = _run([
        sys.executable, "-m", "bandit",
        "-r", str(REPO / "src"), str(REPO / "api"), str(REPO / "simulation"),
        "-f", "json", "-q",
        "--exclude", str(REPO / "archive"),
    ])
    if rc not in (0, 1):
        # bandit returns 1 if issues found — that's normal
        return {"error": err, "raw": out[:2000]}
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return {"error": "bandit JSON parse failed", "raw": out[:2000]}

    metrics = data.get("metrics", {})
    issues = data.get("results", [])
    severity_count: dict[str, int] = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for issue in issues:
        sev = issue.get("issue_severity", "LOW").upper()
        severity_count[sev] = severity_count.get(sev, 0) + 1

    return {
        "tool": "bandit",
        "total_issues": len(issues),
        "severity": severity_count,
        "top_issues": [
            {
                "file": i.get("filename", "").replace(str(REPO) + "/", ""),
                "line": i.get("line_number"),
                "severity": i.get("issue_severity"),
                "confidence": i.get("issue_confidence"),
                "test_id": i.get("test_id"),
                "text": i.get("issue_text", "")[:120],
            }
            for i in issues[:20]
        ],
    }


def run_pip_audit() -> dict:
    print(">> pip-audit CVE 스캔 실행 중...")
    rc, out, err = _run([sys.executable, "-m", "pip_audit", "--format", "json", "-q"])
    if rc not in (0, 1):
        return {"error": err[:500], "raw": out[:500]}
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return {"error": "pip-audit JSON parse failed", "raw": out[:500]}

    vulns = data.get("vulnerabilities", [])
    return {
        "tool": "pip-audit",
        "total_vulnerabilities": len(vulns),
        "vulnerable_packages": [
            {
                "name": v.get("name"),
                "version": v.get("version"),
                "vulns": [
                    {"id": vv.get("id"), "fix": vv.get("fix_versions")}
                    for vv in v.get("vulns", [])[:3]
                ],
            }
            for v in vulns[:20]
        ],
    }


def main():
    report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "repo": str(REPO),
        "results": {},
    }

    # bandit
    try:
        report["results"]["bandit"] = run_bandit()
    except Exception as exc:
        report["results"]["bandit"] = {"error": str(exc)}

    # pip-audit
    try:
        report["results"]["pip_audit"] = run_pip_audit()
    except Exception as exc:
        report["results"]["pip_audit"] = {"error": str(exc)}

    # 요약
    b = report["results"].get("bandit", {})
    p = report["results"].get("pip_audit", {})
    high = b.get("severity", {}).get("HIGH", 0)
    medium = b.get("severity", {}).get("MEDIUM", 0)
    cve_count = p.get("total_vulnerabilities", 0)

    report["summary"] = {
        "bandit_high": high,
        "bandit_medium": medium,
        "cve_count": cve_count,
        "pass": high == 0 and cve_count == 0,
    }

    out_path = RESULTS / f"security_audit_{datetime.utcnow().strftime('%Y%m%d')}.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\n감사 보고서: {out_path}")
    print(f"  bandit HIGH={high} MEDIUM={medium}")
    print(f"  CVE 취약점={cve_count}")
    if report["summary"]["pass"]:
        print("  결과: PASS")
    else:
        print("  결과: FAIL — 위 항목 수정 필요")
        sys.exit(1)


if __name__ == "__main__":
    main()
