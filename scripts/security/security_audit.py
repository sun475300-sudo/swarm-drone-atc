#!/usr/bin/env python3
"""P719 — 보안 감사 스크립트: bandit SAST + safety CVE 스캔."""
from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class AuditResult:
    tool: str
    passed: bool
    issues: List[dict] = field(default_factory=list)
    error: str = ""

    def summary(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return f"[{status}] {self.tool}: {len(self.issues)} issue(s)"


def run_bandit() -> AuditResult:
    """bandit — Python SAST (정적 분석)."""
    cmd = [
        sys.executable, "-m", "bandit",
        "-r", str(REPO_ROOT / "src"),
        str(REPO_ROOT / "simulation"),
        str(REPO_ROOT / "api"),
        "-f", "json",
        "-ll",  # medium severity 이상만
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(proc.stdout or "{}")
        issues = data.get("results", [])
        return AuditResult("bandit", proc.returncode == 0, issues)
    except Exception as exc:
        return AuditResult("bandit", False, error=str(exc))


def run_safety() -> AuditResult:
    """safety — 의존성 CVE 스캔."""
    cmd = [sys.executable, "-m", "safety", "check", "--json"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(proc.stdout or "[]")
        vulns = data if isinstance(data, list) else data.get("vulnerabilities", [])
        return AuditResult("safety", proc.returncode == 0, vulns)
    except Exception as exc:
        return AuditResult("safety", False, error=str(exc))


def main() -> int:
    results = [run_bandit(), run_safety()]
    print("=== SDACS Security Audit Report ===")
    for r in results:
        print(r.summary())
        if r.error:
            print(f"  ERROR: {r.error}")
        for issue in r.issues[:5]:
            if isinstance(issue, dict):
                print(f"  - {issue.get('issue_text', issue.get('advisory', issue))}")

    overall = all(r.passed for r in results)
    print(f"\nOverall: {'PASS' if overall else 'FAIL'}")
    return 0 if overall else 1


if __name__ == "__main__":
    sys.exit(main())
