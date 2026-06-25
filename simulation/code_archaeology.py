"""GENESIS Phase 386 -- 코드 고고학 가이드.

200+ Phase 히스토리를 내비게이션하는 도구.
커밋 메시지에서 Phase 번호를 추출하여 Phase <-> 커밋 매핑을 생성한다.

구성 요소
---------
1. **PhaseCommit**: 커밋 해시, 메시지, 날짜, Phase 번호를 담는 frozen dataclass.
2. **PhaseInfo**: Phase 번호, 트랙, 제목, 커밋 목록을 묶는 frozen dataclass.
3. **parse_phase_commits()**: git log에서 Phase 언급 커밋을 추출.
4. **parse_roadmap_phases()**: ROADMAP.md에서 완료된 Phase 항목을 파싱.
5. **build_phase_index()**: Phase -> 커밋 인덱스 구축.

설계 원칙
---------
- frozen dataclass, 결정적, 부수효과 0 (git log 읽기 전용)
- 기존 모듈 무수정 순수 추가
- subprocess + 정규식만 사용

CLI:
    python simulation/code_archaeology.py --phases           # Phase 목록
    python simulation/code_archaeology.py --phase 382        # Phase 상세
    python simulation/code_archaeology.py --timeline         # 시간순 타임라인
    python simulation/code_archaeology.py --stats            # 통계
    python simulation/code_archaeology.py --search "APF"     # 키워드 검색
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class PhaseCommit:
    """Phase 관련 커밋."""

    commit_hash: str
    date: str
    message: str
    phases: tuple[int, ...]


@dataclass(frozen=True)
class PhaseInfo:
    """Phase 정보."""

    phase_id: int
    track: str
    title: str
    status: str
    commits: tuple[PhaseCommit, ...]


@dataclass(frozen=True)
class ArchaeologyReport:
    """고고학 리포트."""

    total_phases_found: int
    total_commits: int
    earliest_date: str
    latest_date: str
    phases_with_commits: int
    track_distribution: MappingProxyType[str, int]

    def as_dict(self) -> dict[str, Any]:
        return {
            "total_phases_found": self.total_phases_found,
            "total_commits": self.total_commits,
            "earliest_date": self.earliest_date,
            "latest_date": self.latest_date,
            "phases_with_commits": self.phases_with_commits,
            "track_distribution": dict(self.track_distribution),
        }


PHASE_PATTERN = re.compile(r"[Pp]hase\s+(\d+)\b")

TRACK_RANGES: tuple[tuple[str, int, int], ...] = (
    ("Core System", 1, 100),
    ("Safety & Collision", 101, 200),
    ("TRANSCENDENCE", 201, 300),
    ("GENESIS", 301, 400),
    ("ODYSSEY", 401, 500),
    ("Deep Theory", 501, 600),
    ("Advanced Simulation", 601, 690),
    ("AIM & Operations", 691, 755),
)


def _classify_track(phase_id: int) -> str:
    """Phase ID로 트랙 분류."""
    for track_name, start, end in TRACK_RANGES:
        if start <= phase_id <= end:
            return track_name
    return "Unknown"


def parse_phase_commits(repo_path: str = ".") -> tuple[PhaseCommit, ...]:
    """git log에서 Phase 언급 커밋을 추출한다.

    git이 없거나 레포가 아닌 경우 빈 튜플을 반환한다.
    """
    try:
        result = subprocess.run(
            ["git", "log", "--format=%H|%ai|%s", "--all"],
            capture_output=True, encoding="utf-8", errors="replace",
            cwd=repo_path, timeout=30,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, NotADirectoryError, OSError):
        return ()

    if result.returncode != 0:
        return ()

    commits: list[PhaseCommit] = []
    for line in result.stdout.strip().splitlines():
        if not line:
            continue
        parts = line.split("|", 2)
        if len(parts) < 3:
            continue
        commit_hash, date_str, message = parts
        date_short = date_str[:10]

        phase_matches = PHASE_PATTERN.findall(message)
        if not phase_matches:
            continue

        phase_ids = tuple(sorted(set(int(p) for p in phase_matches)))
        commits.append(PhaseCommit(
            commit_hash=commit_hash[:8],
            date=date_short,
            message=message.strip(),
            phases=phase_ids,
        ))

    return tuple(commits)


def parse_roadmap_phases(roadmap_path: str | None = None) -> tuple[PhaseInfo, ...]:
    """ROADMAP.md에서 Phase 항목을 파싱한다."""
    resolved = pathlib.Path(roadmap_path) if roadmap_path else _REPO_ROOT / "ROADMAP.md"
    if not resolved.is_file():
        return ()

    with open(resolved, encoding="utf-8", errors="replace") as f:
        content = f.read()

    phase_line_pattern = re.compile(
        r"-\s+\[([x ])\]\s+\*\*Phase\s+(\d+)[^*]*\*\*\s+.*?—\s+(.*?)(?:\s+\(|$)",
        re.MULTILINE,
    )

    phases: list[PhaseInfo] = []
    for match in phase_line_pattern.finditer(content):
        checked = match.group(1)
        phase_id = int(match.group(2))
        title = match.group(3).strip()

        status = "completed" if checked == "x" else "pending"
        track = _classify_track(phase_id)

        phases.append(PhaseInfo(
            phase_id=phase_id,
            track=track,
            title=title,
            status=status,
            commits=(),
        ))

    phases.sort(key=lambda p: p.phase_id)
    return tuple(phases)


def build_phase_index(
    commits: tuple[PhaseCommit, ...],
    roadmap_phases: tuple[PhaseInfo, ...],
) -> tuple[PhaseInfo, ...]:
    """Phase -> 커밋 인덱스를 구축한다."""
    phase_commits: dict[int, list[PhaseCommit]] = {}
    for commit in commits:
        for pid in commit.phases:
            phase_commits.setdefault(pid, []).append(commit)

    existing_ids = {p.phase_id for p in roadmap_phases}
    result: list[PhaseInfo] = []

    for phase in roadmap_phases:
        matched = tuple(phase_commits.get(phase.phase_id, ()))
        result.append(PhaseInfo(
            phase_id=phase.phase_id,
            track=phase.track,
            title=phase.title,
            status=phase.status,
            commits=matched,
        ))

    for pid in sorted(phase_commits):
        if pid not in existing_ids:
            result.append(PhaseInfo(
                phase_id=pid,
                track=_classify_track(pid),
                title=f"(commit-only Phase {pid})",
                status="unknown",
                commits=tuple(phase_commits[pid]),
            ))

    result.sort(key=lambda p: p.phase_id)
    return tuple(result)


def generate_stats(
    index: tuple[PhaseInfo, ...],
    commits: tuple[PhaseCommit, ...],
) -> ArchaeologyReport:
    """통계 리포트를 생성한다."""
    dates = [c.date for c in commits]
    earliest = min(dates) if dates else "N/A"
    latest = max(dates) if dates else "N/A"

    track_dist: dict[str, int] = {}
    for phase in index:
        track_dist[phase.track] = track_dist.get(phase.track, 0) + 1

    phases_with = sum(1 for p in index if len(p.commits) > 0)

    return ArchaeologyReport(
        total_phases_found=len(index),
        total_commits=len(commits),
        earliest_date=earliest,
        latest_date=latest,
        phases_with_commits=phases_with,
        track_distribution=MappingProxyType(track_dist),
    )


def search_phases(
    index: tuple[PhaseInfo, ...],
    keyword: str,
) -> tuple[PhaseInfo, ...]:
    """키워드로 Phase를 검색한다."""
    keyword_lower = keyword.lower()
    results: list[PhaseInfo] = []
    for phase in index:
        if keyword_lower in phase.title.lower():
            results.append(phase)
            continue
        for commit in phase.commits:
            if keyword_lower in commit.message.lower():
                results.append(phase)
                break
    return tuple(results)


def get_phase(index: tuple[PhaseInfo, ...], phase_id: int) -> PhaseInfo:
    """Phase ID로 조회."""
    for phase in index:
        if phase.phase_id == phase_id:
            return phase
    raise ValueError(f"Phase {phase_id} not found in index")


# -- CLI --

def _main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="GENESIS Phase 386 -- 코드 고고학 가이드",
    )
    parser.add_argument("--phases", action="store_true", help="Phase 목록")
    parser.add_argument("--phase", type=int, metavar="ID", help="Phase 상세")
    parser.add_argument("--timeline", action="store_true", help="시간순 타임라인")
    parser.add_argument("--stats", action="store_true", help="통계")
    parser.add_argument("--search", type=str, metavar="KEYWORD", help="키워드 검색")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    args = parser.parse_args()

    commits = parse_phase_commits()
    roadmap = parse_roadmap_phases()
    index = build_phase_index(commits, roadmap)

    if args.phases:
        if args.json:
            print(json.dumps([
                {"id": p.phase_id, "track": p.track, "title": p.title,
                 "status": p.status, "commits": len(p.commits)}
                for p in index
            ], ensure_ascii=False, indent=2))
        else:
            print(f"{'ID':>5} {'Track':<22} {'St':>2} {'Cm':>3}  Title")
            print("-" * 80)
            for p in index:
                st = "v" if p.status == "completed" else " "
                print(f"{p.phase_id:>5} {p.track:<22} [{st}] {len(p.commits):>3}  {p.title[:48]}")

    elif args.phase is not None:
        try:
            phase = get_phase(index, args.phase)
        except ValueError as exc:
            parser.error(str(exc))
        if args.json:
            print(json.dumps({
                "id": phase.phase_id, "track": phase.track,
                "title": phase.title, "status": phase.status,
                "commits": [
                    {"hash": c.commit_hash, "date": c.date, "message": c.message}
                    for c in phase.commits
                ],
            }, ensure_ascii=False, indent=2))
        else:
            print(f"Phase {phase.phase_id}: {phase.title}")
            print(f"  Track:  {phase.track}")
            print(f"  Status: {phase.status}")
            print(f"  Commits ({len(phase.commits)}):")
            for c in phase.commits:
                print(f"    {c.commit_hash} [{c.date}] {c.message[:72]}")

    elif args.timeline:
        sorted_commits = sorted(commits, key=lambda c: c.date)
        if args.json:
            print(json.dumps([
                {"hash": c.commit_hash, "date": c.date,
                 "message": c.message, "phases": list(c.phases)}
                for c in sorted_commits
            ], ensure_ascii=False, indent=2))
        else:
            for c in sorted_commits:
                phases_str = ",".join(str(p) for p in c.phases)
                print(f"  {c.date} [{c.commit_hash}] Phase {phases_str}: {c.message[:60]}")

    elif args.stats:
        report = generate_stats(index, commits)
        if args.json:
            print(json.dumps(report.as_dict(), ensure_ascii=False, indent=2))
        else:
            print("=== 코드 고고학 통계 ===")
            print(f"  총 Phase 수:        {report.total_phases_found}")
            print(f"  총 커밋 수:         {report.total_commits}")
            print(f"  커밋 있는 Phase:    {report.phases_with_commits}")
            print(f"  최초 커밋:          {report.earliest_date}")
            print(f"  최종 커밋:          {report.latest_date}")
            print("  트랙 분포:")
            for track, count in sorted(report.track_distribution.items()):
                print(f"    {track:<22} {count}")

    elif args.search is not None:
        results = search_phases(index, args.search)
        if args.json:
            print(json.dumps([
                {"id": p.phase_id, "track": p.track, "title": p.title}
                for p in results
            ], ensure_ascii=False, indent=2))
        else:
            print(f"'{args.search}' 검색 결과: {len(results)}건")
            for p in results:
                print(f"  Phase {p.phase_id}: {p.title}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    _main()
