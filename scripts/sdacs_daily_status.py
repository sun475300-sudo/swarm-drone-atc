"""일일 상태 보고 자동화 — ROADMAP 완료율 + 테스트 수 + git 활동"""

import argparse
import re
import subprocess
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
ROADMAP_PATH = REPO_ROOT / "ROADMAP.md"
TESTS_DIR = REPO_ROOT / "tests"
REPORTS_DIR = REPO_ROOT / "reports"

# 트랙별 파싱 패턴
TRACK_PATTERNS = {
    "Track A (하드웨어)": re.compile(r"^### Track A"),
    "Track B (논문)": re.compile(r"^### Track B"),
    "Track C (배포)": re.compile(r"^### Track C"),
}
CHECKED_RE = re.compile(r"^\s*-\s*\[x\]", re.IGNORECASE)
UNCHECKED_RE = re.compile(r"^\s*-\s*\[ \]")


def parse_roadmap() -> dict[str, dict[str, int]]:
    """ROADMAP.md에서 트랙별 완료/미완 항목 수를 반환."""
    if not ROADMAP_PATH.exists():
        return {}

    text = ROADMAP_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()

    track_order = ["Track A (하드웨어)", "Track B (논문)", "Track C (배포)"]
    results = {t: {"done": 0, "todo": 0} for t in track_order}

    current_track = None
    track_header_re = {
        "Track A (하드웨어)": re.compile(r"^###\s+Track A"),
        "Track B (논문)": re.compile(r"^###\s+Track B"),
        "Track C (배포)": re.compile(r"^###\s+Track C"),
    }
    # 다음 섹션 구분자 (Track 헤더 또는 '---' 또는 '## ')
    section_end_re = re.compile(r"^(---\s*$|##\s+)")

    for line in lines:
        # 트랙 헤더 감지
        matched_track = None
        for track_name, pattern in track_header_re.items():
            if pattern.match(line):
                matched_track = track_name
                break

        if matched_track:
            current_track = matched_track
            continue

        # 섹션 종료 감지 (다음 ## 또는 ---)
        if current_track and section_end_re.match(line):
            # Track C의 경우 다음 섹션으로 넘어가면 종료
            current_track = None
            continue

        if current_track:
            if CHECKED_RE.match(line):
                results[current_track]["done"] += 1
            elif UNCHECKED_RE.match(line):
                results[current_track]["todo"] += 1

    return results


def count_test_files() -> int:
    """tests/ 디렉터리의 test_*.py 파일 수."""
    if not TESTS_DIR.exists():
        return 0
    return len(list(TESTS_DIR.glob("test_*.py")))


def get_git_activity(no_git: bool) -> tuple[int, int]:
    """최근 72h 커밋 수, claude/* 브랜치 수 반환."""
    if no_git:
        return 0, 0

    try:
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "log", "--oneline", "--since=72 hours ago"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        commit_count = len([l for l in result.stdout.splitlines() if l.strip()])
    except Exception:
        commit_count = 0

    try:
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "ls-remote", "--heads", "origin", "refs/heads/claude/*"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        branch_count = len([l for l in result.stdout.splitlines() if l.strip()])
    except Exception:
        branch_count = 0

    return commit_count, branch_count


def build_report(
    today: str,
    track_data: dict[str, dict[str, int]],
    test_file_count: int,
    commit_count: int,
    branch_count: int,
    no_git: bool,
) -> str:
    """마크다운 보고서 문자열 생성."""
    lines = [
        f"# SDACS 일일 상태 보고 — {today}",
        "",
        "## 로드맵 진행률",
        "| 트랙 | 완료 | 미완 | 진행률 |",
        "|------|------|------|--------|",
    ]

    total_done = 0
    total_todo = 0

    for track_name in ["Track A (하드웨어)", "Track B (논문)", "Track C (배포)"]:
        data = track_data.get(track_name, {"done": 0, "todo": 0})
        done = data["done"]
        todo = data["todo"]
        total = done + todo
        pct = f"{done / total * 100:.0f}%" if total > 0 else "N/A"
        lines.append(f"| {track_name} | {done} | {todo} | {pct} |")
        total_done += done
        total_todo += todo

    grand_total = total_done + total_todo
    grand_pct = f"{total_done / grand_total * 100:.0f}%" if grand_total > 0 else "N/A"
    lines.append(f"| **합계** | {total_done} | {total_todo} | {grand_pct} |")

    lines += [
        "",
        "## 테스트 현황",
        f"- 테스트 파일: {test_file_count}개",
        "",
        "## Git 활동 (최근 72h)",
    ]

    if no_git:
        lines += [
            "- 커밋 수: (--no-git 플래그로 생략)",
            "- 오픈 claude/* 브랜치: (--no-git 플래그로 생략)",
        ]
    else:
        lines += [
            f"- 커밋 수: {commit_count}",
            f"- 오픈 claude/* 브랜치: {branch_count}",
        ]

    lines += [
        "",
        "## 사람이 필요한 항목",
        "- P698-P699: 실기 비행 (하드웨어 필요)",
        "- P708-P709: 논문 리뷰·투고 (지도교수 필요)",
        "- P720: 공개 베타 (파일럿 기관 필요)",
    ]

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="SDACS 일일 상태 보고 생성기")
    parser.add_argument("--no-git", action="store_true", help="Git 활동 조회 생략")
    parser.add_argument("--output", metavar="PATH", default=None, help="출력 파일 경로 (기본: reports/status_YYYY-MM-DD.md)")
    args = parser.parse_args()

    today = date.today().isoformat()

    track_data = parse_roadmap()
    test_file_count = count_test_files()
    commit_count, branch_count = get_git_activity(args.no_git)

    report = build_report(today, track_data, test_file_count, commit_count, branch_count, args.no_git)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path = Path(args.output) if args.output else REPORTS_DIR / f"status_{today}.md"
    output_path.write_text(report, encoding="utf-8")

    # 요약 stdout 출력
    total_done = sum(d["done"] for d in track_data.values())
    total_todo = sum(d["todo"] for d in track_data.values())
    grand_total = total_done + total_todo
    grand_pct = f"{total_done / grand_total * 100:.0f}%" if grand_total > 0 else "N/A"

    print(f"SDACS 일일 상태 보고 — {today}")
    print(f"  로드맵: {total_done}/{grand_total} 완료 ({grand_pct})")
    print(f"  테스트 파일: {test_file_count}개")
    if not args.no_git:
        print(f"  커밋 (72h): {commit_count} / claude/* 브랜치: {branch_count}")
    print(f"  보고서 저장: {output_path}")


if __name__ == "__main__":
    main()
