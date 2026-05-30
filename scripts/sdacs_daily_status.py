"""SDACS 일일 상태 보고서 생성기.

사용법::

    python scripts/sdacs_daily_status.py
    python scripts/sdacs_daily_status.py --output reports/status_custom.md
    python scripts/sdacs_daily_status.py --no-git   # git 명령 스킵 (CI 환경)

출력: reports/status_YYYY-MM-DD.md
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------


def _count_roadmap_items(roadmap_path: Path) -> dict[str, dict[str, int]]:
    """ROADMAP.md에서 트랙별 [x]/[ ] 항목 수를 집계한다."""
    text = roadmap_path.read_text(encoding="utf-8")
    tracks: dict[str, dict[str, int]] = {}
    current_track = "misc"
    for line in text.splitlines():
        m_track = re.match(r"^### Track ([A-Z])", line)
        if m_track:
            current_track = f"Track {m_track.group(1)}"
            tracks.setdefault(current_track, {"done": 0, "todo": 0})
        elif re.match(r"^- \[x\]", line):
            tracks.setdefault(current_track, {"done": 0, "todo": 0})
            tracks[current_track]["done"] += 1
        elif re.match(r"^- \[ \]", line):
            tracks.setdefault(current_track, {"done": 0, "todo": 0})
            tracks[current_track]["todo"] += 1
    return tracks


def _count_test_files(tests_dir: Path) -> int:
    """tests/ 디렉토리에서 test_*.py 파일 수를 센다."""
    return len(list(tests_dir.rglob("test_*.py")))


def _count_completed_phases(roadmap_path: Path) -> int:
    """ROADMAP의 ## Completed 섹션에서 Phase 항목 수를 센다."""
    text = roadmap_path.read_text(encoding="utf-8")
    in_completed = False
    count = 0
    for line in text.splitlines():
        if line.startswith("## Completed"):
            in_completed = True
        elif line.startswith("## ") and in_completed:
            break
        elif in_completed and re.match(r"^### Phase", line):
            count += 1
    return count


def _git_log_recent(
    hours: int = 72,
    no_git: bool = False,
    cwd: Path | None = None,
) -> list[str]:
    """최근 N시간 커밋 요약을 반환한다."""
    if no_git:
        return []
    try:
        result = subprocess.run(
            ["git", "log", f"--since={hours} hours ago", "--oneline", "--no-merges"],
            capture_output=True,
            text=True,
            cwd=cwd or _ROOT,
            timeout=10,
        )
        lines = [l for l in result.stdout.strip().splitlines() if l]
        return lines[:20]
    except Exception as e:
        print(f"[sdacs_daily_status] git log 실패: {e}", file=sys.stderr)
        return []


def _count_remote_branches(
    no_git: bool = False,
    cwd: Path | None = None,
) -> int | None:
    """origin/claude/* 브랜치 수를 센다 (= 오픈 Draft PR 지표)."""
    if no_git:
        return None
    try:
        result = subprocess.run(
            ["git", "branch", "-r", "--list", "origin/claude/*"],
            capture_output=True,
            text=True,
            cwd=cwd or _ROOT,
            timeout=10,
        )
        branches = [l.strip() for l in result.stdout.strip().splitlines() if l.strip()]
        return len(branches)
    except Exception as e:
        print(f"[sdacs_daily_status] git branch 실패: {e}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def generate_report(
    output_path: Path | None = None,
    no_git: bool = False,
    root: Path | None = None,
) -> Path:
    """상태 보고서를 생성하고 파일 경로를 반환한다.

    Args:
        output_path: 출력 파일 경로. None이면 reports/status_YYYY-MM-DD.md.
                     프로젝트 루트 밖 경로는 거부된다.
        no_git: True이면 git 명령을 건너뛴다.
        root: 프로젝트 루트 경로. None이면 _ROOT(이 파일 기준 상위).
    """
    effective_root = (root or _ROOT).resolve()
    today = date.today()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if output_path is None:
        output_path = effective_root / "reports" / f"status_{today}.md"

    resolved_out = output_path.resolve()
    if not str(resolved_out).startswith(str(effective_root)):
        raise ValueError(
            f"출력 경로가 프로젝트 루트 밖입니다: {resolved_out} (root={effective_root})"
        )

    roadmap = effective_root / "ROADMAP.md"
    tests_dir = effective_root / "tests"

    track_items = _count_roadmap_items(roadmap)
    n_test_files = _count_test_files(tests_dir)
    n_phases = _count_completed_phases(roadmap)
    recent_commits = _git_log_recent(no_git=no_git, cwd=effective_root)
    n_draft_prs = _count_remote_branches(no_git=no_git, cwd=effective_root)

    total_done = sum(v["done"] for v in track_items.values())
    total_todo = sum(v["todo"] for v in track_items.values())
    total = total_done + total_todo
    pct = round(100 * total_done / total, 1) if total > 0 else 0.0

    draft_pr_str = str(n_draft_prs) + "건" if n_draft_prs is not None else "측정 불가 (--no-git)"

    lines: list[str] = [
        f"# SDACS 일일 상태 보고서 — {today}",
        "",
        f"> 생성 시각: {ts}",
        "",
        "---",
        "",
        "## 전체 진행률",
        "",
        "| 항목 | 완료 | 미완 | 진행률 |",
        "|------|------|------|--------|",
    ]

    for track, counts in sorted(track_items.items()):
        done = counts["done"]
        todo = counts["todo"]
        t = done + todo
        p = round(100 * done / t, 0) if t > 0 else 0
        lines.append(f"| {track} | {done} | {todo} | {p:.0f}% |")

    lines += [
        f"| **합계** | **{total_done}** | **{total_todo}** | **{pct}%** |",
        "",
        "---",
        "",
        "## 프로젝트 지표",
        "",
        "| 항목 | 값 |",
        "|------|-----|",
        f"| 완료 Phase 그룹 수 | {n_phases} |",
        f"| 테스트 파일 수 | {n_test_files} |",
        f"| 오픈 Draft PR 추정 | {draft_pr_str} |",
        "",
        "---",
        "",
        "## 최근 72h 커밋",
        "",
    ]

    if recent_commits:
        for c in recent_commits:
            lines.append(f"- `{c}`")
    else:
        lines.append("_(git 활동 없음 또는 no-git 모드)_")

    lines += [
        "",
        "---",
        "",
        "## 사람이 필요한 항목",
        "",
        "| Phase | 항목 | 이유 |",
        "|-------|------|------|",
        "| P698-P699 | 실기 비행 시험 | 실물 드론 + 비행 허가 필요 |",
        "| P708-P709 | 논문 내부 리뷰 · 투고 | 지도교수 피드백 + 학회 계정 필요 |",
        "| P720 | 공개 베타 | 파일럿 기관 섭외 + 서버 배포 필요 |",
        "",
        "---",
        "",
        "_자동 생성: `scripts/sdacs_daily_status.py`_",
    ]

    content = "\n".join(lines) + "\n"

    resolved_out.parent.mkdir(parents=True, exist_ok=True)
    resolved_out.write_text(content, encoding="utf-8")
    return resolved_out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python scripts/sdacs_daily_status.py",
        description="SDACS 일일 상태 보고서 생성",
    )
    parser.add_argument("--output", "-o", type=Path, default=None)
    parser.add_argument(
        "--no-git", action="store_true", help="git 명령 스킵 (CI / 오프라인)"
    )
    args = parser.parse_args(argv)

    path = generate_report(output_path=args.output, no_git=args.no_git)
    print(f"✅ 보고서 생성: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
