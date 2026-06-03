#!/usr/bin/env python3
"""일일 상태 리포트 생성기 — 로드맵 진행도·테스트 수집·git 현황 요약.

사용자 요청("매일 확인 + 보고")을 반복 가능하게 자동화한다. ROADMAP.md 의
체크박스를 트랙별로 집계하고, pytest 수집 수와 git 현황을 모아 마크다운
리포트를 `reports/daily_status/<YYYY-MM-DD>.md` 에 기록한 뒤 stdout 으로
요약을 출력한다.

Usage:
    python scripts/daily_status_report.py [--no-pytest] [--out <path>]

순수 함수(parse_roadmap / parse_pytest_collect_output / build_report)는
부수효과가 없어 단위 테스트로 검증한다. git/pytest 호출은 main() 에서만.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import re
import subprocess
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_ROADMAP = _ROOT / "ROADMAP.md"
_REPORT_DIR = _ROOT / "reports" / "daily_status"

# 마크다운 체크박스: "- [ ]" pending, "- [x]" done, "- [~]" partial.
_CHECKBOX = re.compile(r"^\s*-\s*\[([ x~])\]", re.IGNORECASE)
_HEADING = re.compile(r"^#{2,4}\s+(.*\S)\s*$")
_COLLECT = re.compile(r"(\d+)\s+tests?\s+collected(?:,\s*(\d+)\s+errors?)?")

_STATE = {" ": "pending", "x": "done", "X": "done", "~": "partial"}


def parse_roadmap(text: str) -> dict:
    """ROADMAP 마크다운을 트랙별 체크박스 집계로 변환한다.

    헤딩(## ~ ####)을 트랙 경계로 보고, 그 아래 체크박스를 done/partial/
    pending 으로 센다. 헤딩 이전 체크박스는 "(no track)" 으로 묶는다.
    """
    tracks: dict[str, dict] = {}
    totals = {"done": 0, "partial": 0, "pending": 0}
    current = "(no track)"

    for line in text.splitlines():
        heading = _HEADING.match(line)
        if heading:
            current = heading.group(1).strip()
            continue
        box = _CHECKBOX.match(line)
        if not box:
            continue
        state = _STATE.get(box.group(1), "pending")
        bucket = tracks.setdefault(
            current, {"done": 0, "partial": 0, "pending": 0}
        )
        bucket[state] += 1
        totals[state] += 1

    # 체크박스가 하나도 없던 트랙(헤딩만 있는 경우)은 노이즈라 제거한다.
    tracks = {k: v for k, v in tracks.items() if sum(v.values()) > 0}
    return {"tracks": tracks, "totals": totals}


def parse_pytest_collect_output(output: str):
    """pytest 출력에서 (수집 수, 에러 수)를 추출한다. 못 찾으면 (None, None)."""
    match = _COLLECT.search(output)
    if not match:
        return None, None
    collected = int(match.group(1))
    errors = int(match.group(2)) if match.group(2) else 0
    return collected, errors


def build_report(roadmap: dict, tests: dict, git: dict, date: str) -> str:
    """집계 결과를 사람이 읽는 마크다운 리포트로 만든다."""
    t = roadmap["totals"]
    total = t["done"] + t["partial"] + t["pending"]
    pct = (t["done"] / total * 100) if total else 0.0

    lines = [
        f"# SDACS 일일 상태 리포트 — {date}",
        "",
        "## 로드맵 진행도",
        "",
        f"- 완료(done): **{t['done']}** / 부분(partial): **{t['partial']}** "
        f"/ 대기(pending): **{t['pending']}** (총 {total}, 완료율 {pct:.0f}%)",
        "",
        "| 트랙 | done | partial | pending |",
        "|------|------|---------|---------|",
    ]
    for name, c in roadmap["tracks"].items():
        lines.append(
            f"| {name} | {c['done']} | {c['partial']} | {c['pending']} |"
        )

    collected = tests.get("collected")
    errors = tests.get("errors")
    test_line = (
        f"{collected} 수집 / {errors} 에러"
        if collected is not None
        else "측정 안 함 (--no-pytest)"
    )
    lines += [
        "",
        "## 테스트",
        "",
        f"- pytest: {test_line}",
        "",
        "## Git",
        "",
        f"- 브랜치: `{git['branch']}`",
        f"- origin/main 대비 앞선 커밋: {git['ahead']}",
        f"- 마지막 커밋: {git['last_commit']}",
        "",
    ]
    return "\n".join(lines)


def _git(args: list[str]) -> str:
    try:
        return subprocess.run(
            ["git", *args], cwd=_ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def collect_git_stats() -> dict:
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"]) or "unknown"
    ahead = _git(["rev-list", "--count", "origin/main..HEAD"]) or "0"
    last = _git(["log", "-1", "--format=%ci"]) or "unknown"
    return {"branch": branch, "ahead": ahead, "last_commit": last}


def collect_test_stats() -> dict:
    proc = subprocess.run(
        ["python", "-m", "pytest", "tests/", "--collect-only", "-q", "-o", "addopts="],
        cwd=_ROOT,
        capture_output=True,
        text=True,
    )
    collected, errors = parse_pytest_collect_output(proc.stdout + proc.stderr)
    return {"collected": collected, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description="SDACS 일일 상태 리포트 생성")
    parser.add_argument("--no-pytest", action="store_true", help="pytest 수집 생략")
    parser.add_argument("--out", type=Path, default=None, help="리포트 출력 경로")
    args = parser.parse_args()

    date = _dt.date.today().isoformat()
    roadmap = parse_roadmap(_ROADMAP.read_text(encoding="utf-8"))
    tests = {"collected": None, "errors": None}
    if not args.no_pytest:
        tests = collect_test_stats()
    git = collect_git_stats()

    report = build_report(roadmap, tests, git, date)

    out = args.out or (_REPORT_DIR / f"{date}.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")

    print(report)
    print(f"\n[리포트 기록: {out.relative_to(_ROOT)}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
