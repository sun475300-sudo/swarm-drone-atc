"""
CI/CD 로깅 유틸리티 — CI 파이프라인에서 실행 정보/성능 요약/스모크 리포트 기록
"""
from __future__ import annotations

from datetime import datetime, timezone


def log_run_info(
    python_version: str = "",
    commit_sha: str = "",
    branch: str = "main",
) -> dict:
    return {
        "status": "ok",
        "python_version": python_version,
        "commit": commit_sha,
        "branch": branch,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def log_perf_summary(summary: dict) -> dict:
    return {
        "status": "ok",
        **summary,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def emit_smoke_report(report: dict) -> dict:
    return {
        "emitted": True,
        "report": report,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
