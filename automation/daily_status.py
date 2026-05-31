#!/usr/bin/env python3
"""Daily status report for the SDACS project.

Checks:
  - Git status (current branch, commits ahead of main)
  - ROADMAP progress (completed / total phases)
  - Open GitHub PR count (from git remote refs)
  - Test suite health (collect count)
  - P706 sweep results (if data/p706_summary.json exists)
  - Paper draft progress (filled TBD count)

Usage:
    python automation/daily_status.py           # print report to stdout
    python automation/daily_status.py --md      # Markdown-formatted
    python automation/daily_status.py --out status.md   # save to file
"""
from __future__ import annotations

import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(cmd: list[str], cwd: Path | None = None) -> str:
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=cwd or REPO_ROOT, timeout=30
        )
        return result.stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def _count_in_file(path: Path, pattern: str) -> int:
    try:
        return path.read_text(encoding="utf-8").count(pattern)
    except FileNotFoundError:
        return 0


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_git() -> dict:
    branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    short_sha = _run(["git", "rev-parse", "--short", "HEAD"])
    ahead = _run(["git", "rev-list", "--count", "origin/main..HEAD"])
    last_commit = _run(["git", "log", "-1", "--format=%s"])
    dirty = bool(_run(["git", "status", "--porcelain"]))
    return {
        "branch": branch,
        "sha": short_sha,
        "ahead_of_main": int(ahead) if ahead.isdigit() else "?",
        "last_commit": last_commit,
        "dirty": dirty,
    }


def check_roadmap() -> dict:
    roadmap = REPO_ROOT / "ROADMAP.md"
    if not roadmap.exists():
        return {"done": 0, "total": 0, "pct": 0}
    text = roadmap.read_text(encoding="utf-8")
    done = text.count("- [x]") + text.count("(완료)")
    pending = text.count("- [ ]")
    total = done + pending
    # Count phases from track headers
    tracks = {
        "A (Hardware)": text.count("P69") > 0,
        "B (Paper)": text.count("P70") > 0,
        "C (Deployment)": text.count("P71") > 0,
    }
    p706_done = "P706" in text and ("✅" in text or "완료" in text or "비교" in text)
    return {
        "done_items": done,
        "pending_items": pending,
        "total_items": total,
        "tracks": tracks,
        "p706_data": (REPO_ROOT / "data" / "p706_summary.json").exists(),
    }


def check_tests() -> dict:
    """Try to count test files; avoid running pytest which takes too long."""
    test_dir = REPO_ROOT / "tests"
    test_files = list(test_dir.glob("test_*.py")) if test_dir.exists() else []
    # Estimate from file count (each file averages ~45 tests historically)
    return {
        "test_files": len(test_files),
        "estimated_count": len(test_files) * 45,
    }


def check_p706() -> dict:
    summary_path = REPO_ROOT / "data" / "p706_summary.json"
    if not summary_path.exists():
        return {"available": False}
    with open(summary_path, encoding="utf-8") as f:
        summary = json.load(f)

    sdacs = summary.get("sdacs_hybrid", {})
    orca = summary.get("orca", {})

    def fmt(m: dict, metric: str) -> str:
        entry = m.get(metric, {})
        mean = entry.get("mean")
        return f"{mean:.4f}" if isinstance(mean, float) else "N/A"

    return {
        "available": True,
        "runs": sum(
            summary.get(m, {}).get("NMR", {}).get("n", 0) for m in summary
        ),
        "sdacs_nmr": fmt(sdacs, "NMR"),
        "orca_nmr": fmt(orca, "NMR"),
        "sdacs_msd": fmt(sdacs, "MSD"),
        "sdacs_pe": fmt(sdacs, "PE"),
        "sdacs_rid_cr": fmt(sdacs, "RID_CR"),
    }


def check_paper() -> dict:
    draft = REPO_ROOT / "docs" / "paper" / "PAPER_DRAFT.md"
    if not draft.exists():
        return {"tbd_count": "?", "sections_done": 0}
    text = draft.read_text(encoding="utf-8")
    tbd = text.count("[TBD")
    todo = text.count("[TODO")
    # Count filled sections: abstract, intro, related, arch, benchmark, results, discussion
    section_keywords = [
        "## 1. Abstract",
        "## 2. Related Work",
        "## 3. System Architecture",
        "## 4. Benchmark Suite",
        "## 5. Experiments and Results",
        "## 6. Discussion",
        "## 7. Conclusion",
    ]
    sections_present = sum(1 for s in section_keywords if s in text)
    return {
        "tbd_count": tbd,
        "todo_count": todo,
        "sections_present": sections_present,
        "total_sections": len(section_keywords),
    }


def check_open_prs() -> dict:
    """Count open PRs via git remote refs."""
    refs = _run(["git", "ls-remote", "--heads", "origin"])
    branches = [
        line.split("\t")[1].replace("refs/heads/", "")
        for line in refs.splitlines()
        if "\t" in line
    ]
    claude_branches = [b for b in branches if b.startswith("claude/")]
    return {
        "claude_branches": len(claude_branches),
        "note": "Approximate; use GitHub UI for precise open-PR count.",
    }


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------


def render(git: dict, roadmap: dict, tests: dict, p706: dict, paper: dict, prs: dict, markdown: bool) -> str:
    today = datetime.date.today().isoformat()
    lines = []

    if markdown:
        lines.append(f"# SDACS 일일 상태 보고서 — {today}")
        lines.append("")
        lines.append("## Git")
        lines.append(f"- 브랜치: `{git['branch']}`  SHA: `{git['sha']}`")
        lines.append(f"- main 대비 +{git['ahead_of_main']} 커밋  {'(미커밋 변경 있음)' if git['dirty'] else '(클린)'}")
        lines.append(f"- 최근 커밋: {git['last_commit']}")
        lines.append("")
        lines.append("## 로드맵 진행상황")
        p706_mark = "✅" if roadmap["p706_data"] else "⏳"
        lines.append(f"- P706 스윕 데이터: {p706_mark}")
        lines.append(f"- 대기 항목: {roadmap['pending_items']}개  완료: {roadmap['done_items']}개")
        lines.append("")
        lines.append("## 테스트 현황")
        lines.append(f"- 테스트 파일: {tests['test_files']}개  (추정 ~{tests['estimated_count']:,}건)")
        lines.append("")
        lines.append("## P706 비교 실험 결과")
        if p706["available"]:
            lines.append(f"- 총 실행 횟수: {p706['runs']} runs")
            lines.append(f"- SDACS NMR: {p706['sdacs_nmr']}  (ORCA: {p706['orca_nmr']})")
            lines.append(f"- SDACS MSD: {p706['sdacs_msd']} m")
            lines.append(f"- SDACS PE: {p706['sdacs_pe']}")
            lines.append(f"- SDACS RID-CR: {p706['sdacs_rid_cr']} (1.0 = 100% 규정 준수)")
        else:
            lines.append("- ❌ data/p706_summary.json 없음 — `python scripts/p706_sweep.py` 실행 필요")
        lines.append("")
        lines.append("## 논문 초안")
        lines.append(f"- 섹션: {paper['sections_present']}/{paper['total_sections']} 작성됨")
        lines.append(f"- TBD 잔여: {paper['tbd_count']}개  TODO 잔여: {paper['todo_count']}개")
        lines.append("")
        lines.append("## 오픈 PR 브랜치")
        lines.append(f"- `claude/` 브랜치: {prs['claude_branches']}개")
        lines.append(f"> {prs['note']}")
        lines.append("")
        lines.append("---")
        lines.append(f"*자동 생성: `automation/daily_status.py` @ {today}*")
    else:
        lines.append(f"=== SDACS 일일 상태 보고서 === {today}")
        lines.append(f"Git: {git['branch']} ({git['sha']}) +{git['ahead_of_main']} {'dirty' if git['dirty'] else 'clean'}")
        lines.append(f"Roadmap: pending={roadmap['pending_items']}  p706_data={'YES' if roadmap['p706_data'] else 'NO'}")
        lines.append(f"Tests: {tests['test_files']} files  (~{tests['estimated_count']:,} est.)")
        if p706["available"]:
            lines.append(f"P706: SDACS NMR={p706['sdacs_nmr']} MSD={p706['sdacs_msd']}m PE={p706['sdacs_pe']} RID-CR={p706['sdacs_rid_cr']}")
        else:
            lines.append("P706: NOT AVAILABLE — run scripts/p706_sweep.py")
        lines.append(f"Paper: {paper['sections_present']}/{paper['total_sections']} sections  TBD={paper['tbd_count']} TODO={paper['todo_count']}")
        lines.append(f"PRs: claude/ branches={prs['claude_branches']}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="daily_status")
    p.add_argument("--md", action="store_true", help="Markdown output.")
    p.add_argument("--out", default=None, help="Save to file instead of stdout.")
    args = p.parse_args(argv)

    git = check_git()
    roadmap = check_roadmap()
    tests = check_tests()
    p706 = check_p706()
    paper = check_paper()
    prs = check_open_prs()

    report = render(git, roadmap, tests, p706, paper, prs, markdown=args.md or args.out is not None)

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report + "\n", encoding="utf-8")
        print(f"Report saved → {out}")
    else:
        print(report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
