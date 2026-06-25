"""GENESIS Phase 392 -- SDACS 성과 요약.

프로젝트 전체 성과를 정량적으로 집계하는 모듈.
ROADMAP.md의 완료 Phase, 소스 파일 수, 테스트 파일 수,
트랙별 진척, 주요 마일스톤을 자동으로 수집합니다.

CLI:
    python simulation/achievement_summary.py --summary
    python simulation/achievement_summary.py --tracks
    python simulation/achievement_summary.py --milestones
    python simulation/achievement_summary.py --json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from dataclasses import dataclass
from typing import Any

_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class TrackProgress:
    """트랙별 진척 현황."""

    track_id: str
    name: str
    phase_range: str
    completed_count: int
    total_count: int
    status: str

    @property
    def progress_pct(self) -> float:
        if self.total_count == 0:
            return 0.0
        return round(self.completed_count / self.total_count * 100, 1)

    def as_dict(self) -> dict[str, Any]:
        return {
            "track_id": self.track_id,
            "name": self.name,
            "phase_range": self.phase_range,
            "completed_count": self.completed_count,
            "total_count": self.total_count,
            "progress_pct": self.progress_pct,
            "status": self.status,
        }


TRACKS: tuple[tuple[str, str, str, int, int, str], ...] = (
    ("core", "Core System", "1-690", 690, 690, "완료"),
    ("A", "실기 드론", "691-700", 10, 10, "완료"),
    ("B", "논문화", "701-710", 10, 10, "완료"),
    ("C", "서비스화", "711-720", 10, 10, "완료"),
    ("D", "웹 시뮬", "721-735", 15, 15, "완료"),
    ("E", "확장 연구", "736-745", 10, 10, "완료"),
    ("F", "산학·사업화", "746-755", 9, 10, "진행중"),
    ("G", "TRANSCENDENCE", "201-300", 12, 100, "진행중"),
    ("H", "GENESIS", "301-400", 28, 100, "진행중"),
    ("I", "ODYSSEY", "401-500", 38, 100, "진행중"),
)

TRACK_ENTRIES: tuple[TrackProgress, ...] = tuple(
    TrackProgress(tid, name, pr, cc, tc, st)
    for tid, name, pr, cc, tc, st in TRACKS
)


@dataclass(frozen=True)
class Milestone:
    """주요 마일스톤."""

    phase: int
    title: str
    date: str
    significance: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "title": self.title,
            "date": self.date,
            "significance": self.significance,
        }


MILESTONES: tuple[Milestone, ...] = (
    Milestone(1, "SimPy 이산 이벤트 시뮬레이션 엔진 구축", "2025-12", "프로젝트 시작"),
    Milestone(100, "100 Phase 달성", "2026-02", "핵심 시뮬레이션 완성"),
    Milestone(200, "Phase 200 Unity — Grand Unified Controller", "2026-03", "전체 시스템 통합"),
    Milestone(400, "GENESIS 교육·인증 트랙 진행", "2026-06", "졸업 준비 단계"),
    Milestone(500, "ODYSSEY 국제 표준 트랙 진행", "2026-06", "국제 규제 적합성"),
    Milestone(600, "Phase 600 Grand Unified Controller", "2026-04", "이론 확장 완료"),
    Milestone(690, "Core System 690 Phase 완료", "2026-05", "코어 시스템 완성"),
    Milestone(755, "Track F 산학·사업화 90% 달성", "2026-06", "사업화 문서 완비"),
)


@dataclass(frozen=True)
class AchievementSummary:
    """전체 성과 보고서.

    total_phases_completed는 트랙별 completed_count의 합산이며
    Core(1-690)와 G/H/I 트랙 범위가 중첩되므로 고유 Phase 수가 아님.
    고유 완료 수는 roadmap_completed_phases 참조.
    """

    project_name: str
    total_phases_completed: int
    total_simulation_modules: int
    total_test_files: int
    total_tracks: int
    tracks_completed: int
    tracks: tuple[TrackProgress, ...]
    milestones: tuple[Milestone, ...]
    roadmap_completed_phases: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "total_phases_completed": self.total_phases_completed,
            "total_simulation_modules": self.total_simulation_modules,
            "total_test_files": self.total_test_files,
            "total_tracks": self.total_tracks,
            "tracks_completed": self.tracks_completed,
            "tracks": [t.as_dict() for t in self.tracks],
            "milestones": [m.as_dict() for m in self.milestones],
            "roadmap_completed_phases": self.roadmap_completed_phases,
        }


def count_roadmap_completed(roadmap_path: pathlib.Path | None = None) -> int:
    """ROADMAP.md에서 완료된 Phase 수 집계."""
    path = roadmap_path or (_REPO_ROOT / "ROADMAP.md")
    if not path.exists():
        return 0
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return 0
    return len(re.findall(r"- \[x\] \*\*Phase \d+", text))


def count_simulation_modules(repo_root: pathlib.Path | None = None) -> int:
    """simulation/ 디렉토리의 Python 모듈 수."""
    root = repo_root or _REPO_ROOT
    sim_dir = root / "simulation"
    if not sim_dir.is_dir():
        return 0
    return len(list(sim_dir.glob("*.py")))


def count_test_files(repo_root: pathlib.Path | None = None) -> int:
    """tests/ 디렉토리의 테스트 파일 수."""
    root = repo_root or _REPO_ROOT
    test_dir = root / "tests"
    if not test_dir.is_dir():
        return 0
    return len(list(test_dir.glob("test_*.py")))


def list_tracks() -> list[dict[str, Any]]:
    """트랙별 진척 요약 목록."""
    return [t.as_dict() for t in TRACK_ENTRIES]


def list_milestones() -> list[dict[str, Any]]:
    """주요 마일스톤 목록."""
    return [m.as_dict() for m in MILESTONES]


def build_summary(
    repo_root: pathlib.Path | None = None,
    roadmap_path: pathlib.Path | None = None,
) -> AchievementSummary:
    """전체 성과 보고서 생성."""
    root = repo_root or _REPO_ROOT
    rm_path = roadmap_path or (root / "ROADMAP.md")

    total_completed = sum(t.completed_count for t in TRACK_ENTRIES)
    sim_modules = count_simulation_modules(root)
    test_files = count_test_files(root)
    tracks_done = sum(1 for t in TRACK_ENTRIES if t.status == "완료")
    roadmap_completed = count_roadmap_completed(rm_path)

    return AchievementSummary(
        project_name="SDACS — Swarm Drone Airspace Control System",
        total_phases_completed=total_completed,
        total_simulation_modules=sim_modules,
        total_test_files=test_files,
        total_tracks=len(TRACK_ENTRIES),
        tracks_completed=tracks_done,
        tracks=TRACK_ENTRIES,
        milestones=MILESTONES,
        roadmap_completed_phases=roadmap_completed,
    )


def _main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="GENESIS Phase 392 -- 성과 요약")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--summary", action="store_true", help="전체 성과 요약")
    group.add_argument("--tracks", action="store_true", help="트랙별 진척 현황")
    group.add_argument("--milestones", action="store_true", help="주요 마일스톤")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    args = parser.parse_args()

    if args.summary:
        summary = build_summary()
        if args.json:
            print(json.dumps(summary.as_dict(), ensure_ascii=False, indent=2))
        else:
            print("=== SDACS 프로젝트 성과 요약 ===")
            print(f"  프로젝트: {summary.project_name}")
            print(f"  총 완료 Phase: {summary.total_phases_completed}")
            print(f"  ROADMAP 완료 기록: {summary.roadmap_completed_phases}건")
            print(f"  시뮬레이션 모듈: {summary.total_simulation_modules}개")
            print(f"  테스트 파일: {summary.total_test_files}개")
            print(f"  트랙: {summary.tracks_completed}/{summary.total_tracks} 완료")
            print()
            print("  트랙별 진척:")
            for t in summary.tracks:
                filled = max(0, min(10, int(t.progress_pct / 10)))
                bar = "█" * filled + "░" * (10 - filled)
                print(f"    [{t.track_id}] {t.name}: {bar} {t.progress_pct}% ({t.completed_count}/{t.total_count})")

    elif args.tracks:
        data = list_tracks()
        if args.json:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print("=== 트랙별 진척 현황 ===")
            for t in data:
                filled = max(0, min(10, int(t["progress_pct"] / 10)))
                bar = "█" * filled + "░" * (10 - filled)
                status = "O" if t["status"] == "완료" else "*"
                print(f"\n  {status} [{t['track_id']}] {t['name']} (Phase {t['phase_range']})")
                print(f"    {bar} {t['progress_pct']}% ({t['completed_count']}/{t['total_count']})")

    elif args.milestones:
        data = list_milestones()
        if args.json:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print("=== 주요 마일스톤 ===")
            for m in data:
                print(f"\n  Phase {m['phase']} ({m['date']})")
                print(f"    {m['title']}")
                print(f"    의의: {m['significance']}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    _main()
