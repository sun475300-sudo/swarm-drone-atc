"""GENESIS Phase 386 -- 코드 고고학 가이드 테스트.

검증 항목:
- PhaseCommit / PhaseInfo / ArchaeologyReport frozen
- _classify_track() 트랙 분류
- parse_phase_commits() git log 파싱 (실제 레포에서)
- parse_roadmap_phases() ROADMAP.md 파싱 (실제 파일에서)
- build_phase_index() 인덱스 구축
- generate_stats() 통계
- search_phases() / get_phase() 검색/조회
- CLI 출력 (--phases, --phase, --timeline, --stats, --search, --json)
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
from types import MappingProxyType

import pytest

from simulation.code_archaeology import (
    PHASE_PATTERN,
    ArchaeologyReport,
    PhaseCommit,
    PhaseInfo,
    _classify_track,
    build_phase_index,
    generate_stats,
    get_phase,
    parse_phase_commits,
    parse_roadmap_phases,
    search_phases,
)


class TestPhaseCommit:
    """PhaseCommit frozen dataclass."""

    def test_frozen(self) -> None:
        c = PhaseCommit(commit_hash="abc12345", date="2026-06-25",
                        message="feat: Phase 382", phases=(382,))
        with pytest.raises(AttributeError):
            c.message = "mutated"  # type: ignore[misc]

    def test_fields(self) -> None:
        c = PhaseCommit(commit_hash="abc12345", date="2026-06-25",
                        message="feat: Phase 382", phases=(382,))
        assert c.commit_hash == "abc12345"
        assert c.date == "2026-06-25"
        assert c.phases == (382,)


class TestPhaseInfo:
    """PhaseInfo frozen dataclass."""

    def test_frozen(self) -> None:
        p = PhaseInfo(phase_id=1, track="Core", title="test",
                      status="completed", commits=())
        with pytest.raises(AttributeError):
            p.title = "mutated"  # type: ignore[misc]

    def test_fields(self) -> None:
        p = PhaseInfo(phase_id=382, track="GENESIS", title="실습 과제",
                      status="completed", commits=())
        assert p.phase_id == 382
        assert p.track == "GENESIS"


class TestArchaeologyReport:
    """ArchaeologyReport frozen dataclass."""

    def test_frozen(self) -> None:
        r = ArchaeologyReport(
            total_phases_found=10, total_commits=50,
            earliest_date="2026-01-01", latest_date="2026-06-25",
            phases_with_commits=8, track_distribution=MappingProxyType({"GENESIS": 5}),
        )
        with pytest.raises(AttributeError):
            r.total_commits = 999  # type: ignore[misc]

    def test_as_dict(self) -> None:
        r = ArchaeologyReport(
            total_phases_found=10, total_commits=50,
            earliest_date="2026-01-01", latest_date="2026-06-25",
            phases_with_commits=8, track_distribution=MappingProxyType({"GENESIS": 5}),
        )
        d = r.as_dict()
        assert d["total_phases_found"] == 10
        text = json.dumps(d, ensure_ascii=False)
        assert isinstance(text, str)


class TestClassifyTrack:
    """_classify_track() 트랙 분류."""

    def test_core_system(self) -> None:
        assert _classify_track(50) == "Core System"

    def test_genesis(self) -> None:
        assert _classify_track(382) == "GENESIS"

    def test_odyssey(self) -> None:
        assert _classify_track(450) == "ODYSSEY"

    def test_transcendence(self) -> None:
        assert _classify_track(250) == "TRANSCENDENCE"

    def test_unknown(self) -> None:
        assert _classify_track(9999) == "Unknown"


class TestPhasePattern:
    """PHASE_PATTERN 정규식."""

    def test_matches_phase_382(self) -> None:
        m = PHASE_PATTERN.findall("feat(genesis): Phase 382 실습 과제")
        assert "382" in m

    def test_matches_lowercase(self) -> None:
        m = PHASE_PATTERN.findall("phase 100 test")
        assert "100" in m

    def test_no_match(self) -> None:
        m = PHASE_PATTERN.findall("just a regular commit")
        assert len(m) == 0

    def test_multiple_phases(self) -> None:
        m = PHASE_PATTERN.findall("Phase 301 + Phase 302 together")
        assert "301" in m
        assert "302" in m


class TestParsePhaseCommits:
    """parse_phase_commits() 실제 git log 파싱."""

    def test_returns_tuple(self) -> None:
        result = parse_phase_commits()
        assert isinstance(result, tuple)

    def test_all_items_are_phase_commit(self) -> None:
        result = parse_phase_commits()
        for item in result:
            assert isinstance(item, PhaseCommit)

    def test_non_empty_in_this_repo(self) -> None:
        result = parse_phase_commits()
        assert len(result) > 0

    def test_all_have_phases(self) -> None:
        result = parse_phase_commits()
        for item in result:
            assert len(item.phases) >= 1

    def test_invalid_repo_returns_empty(self) -> None:
        result = parse_phase_commits(repo_path="/nonexistent/path")
        assert result == ()


class TestParseRoadmapPhases:
    """parse_roadmap_phases() ROADMAP.md 파싱."""

    def test_returns_tuple(self) -> None:
        result = parse_roadmap_phases()
        assert isinstance(result, tuple)

    def test_non_empty(self) -> None:
        result = parse_roadmap_phases()
        assert len(result) > 0

    def test_all_items_are_phase_info(self) -> None:
        result = parse_roadmap_phases()
        for item in result:
            assert isinstance(item, PhaseInfo)

    def test_sorted_by_id(self) -> None:
        result = parse_roadmap_phases()
        ids = [p.phase_id for p in result]
        assert ids == sorted(ids)

    def test_has_completed_phases(self) -> None:
        result = parse_roadmap_phases()
        completed = [p for p in result if p.status == "completed"]
        assert len(completed) > 0

    def test_missing_file_returns_empty(self) -> None:
        result = parse_roadmap_phases("/nonexistent/ROADMAP.md")
        assert result == ()


class TestBuildPhaseIndex:
    """build_phase_index() 인덱스 구축."""

    def test_with_synthetic_data(self) -> None:
        commits = (
            PhaseCommit("abc", "2026-06-25", "Phase 1 init", (1,)),
            PhaseCommit("def", "2026-06-26", "Phase 2 update", (2,)),
        )
        roadmap = (
            PhaseInfo(1, "Core", "Init", "completed", ()),
            PhaseInfo(2, "Core", "Update", "pending", ()),
        )
        index = build_phase_index(commits, roadmap)
        assert len(index) == 2
        assert len(index[0].commits) == 1
        assert index[0].commits[0].commit_hash == "abc"

    def test_commit_only_phases_appended(self) -> None:
        commits = (
            PhaseCommit("abc", "2026-06-25", "Phase 999 unknown", (999,)),
        )
        roadmap = (
            PhaseInfo(1, "Core", "Init", "completed", ()),
        )
        index = build_phase_index(commits, roadmap)
        assert any(p.phase_id == 999 for p in index)

    def test_empty_inputs(self) -> None:
        index = build_phase_index((), ())
        assert index == ()

    def test_sorted_output(self) -> None:
        commits = (
            PhaseCommit("abc", "2026-06-25", "Phase 300", (300,)),
            PhaseCommit("def", "2026-06-26", "Phase 100", (100,)),
        )
        roadmap = ()
        index = build_phase_index(commits, roadmap)
        ids = [p.phase_id for p in index]
        assert ids == sorted(ids)


class TestGenerateStats:
    """generate_stats() 통계."""

    def test_with_synthetic_data(self) -> None:
        commits = (
            PhaseCommit("abc", "2026-01-01", "Phase 1", (1,)),
            PhaseCommit("def", "2026-06-25", "Phase 2", (2,)),
        )
        index = (
            PhaseInfo(1, "Core", "Init", "completed", (commits[0],)),
            PhaseInfo(2, "Core", "Update", "pending", (commits[1],)),
            PhaseInfo(3, "Core", "Empty", "pending", ()),
        )
        report = generate_stats(index, commits)
        assert report.total_phases_found == 3
        assert report.total_commits == 2
        assert report.earliest_date == "2026-01-01"
        assert report.latest_date == "2026-06-25"
        assert report.phases_with_commits == 2

    def test_empty_data(self) -> None:
        report = generate_stats((), ())
        assert report.total_phases_found == 0
        assert report.earliest_date == "N/A"


class TestSearchPhases:
    """search_phases() 키워드 검색."""

    def test_matches_title(self) -> None:
        index = (
            PhaseInfo(1, "Core", "APF collision", "completed", ()),
            PhaseInfo(2, "Core", "Monte Carlo", "completed", ()),
        )
        results = search_phases(index, "APF")
        assert len(results) == 1
        assert results[0].phase_id == 1

    def test_case_insensitive(self) -> None:
        index = (
            PhaseInfo(1, "Core", "APF collision", "completed", ()),
        )
        results = search_phases(index, "apf")
        assert len(results) == 1

    def test_matches_commit_message(self) -> None:
        commit = PhaseCommit("abc", "2026-01-01", "feat: add APF engine", (1,))
        index = (
            PhaseInfo(1, "Core", "Some title", "completed", (commit,)),
        )
        results = search_phases(index, "APF")
        assert len(results) == 1

    def test_no_match(self) -> None:
        index = (
            PhaseInfo(1, "Core", "Something", "completed", ()),
        )
        results = search_phases(index, "ZZZZZZ")
        assert len(results) == 0


class TestGetPhase:
    """get_phase() 조회."""

    def test_valid_id(self) -> None:
        index = (
            PhaseInfo(1, "Core", "Init", "completed", ()),
            PhaseInfo(2, "Core", "Update", "pending", ()),
        )
        p = get_phase(index, 1)
        assert p.phase_id == 1

    def test_invalid_id(self) -> None:
        index = (
            PhaseInfo(1, "Core", "Init", "completed", ()),
        )
        with pytest.raises(ValueError, match="Phase 99 not found"):
            get_phase(index, 99)


class TestCLI:
    """CLI 실행."""

    REPO_ROOT = pathlib.Path(__file__).parent.parent
    SCRIPT = str(REPO_ROOT / "simulation" / "code_archaeology.py")
    UTF8_ENV = {**os.environ, "PYTHONUTF8": "1"}

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, self.SCRIPT, *args],
            capture_output=True, encoding="utf-8", env=self.UTF8_ENV,
            cwd=str(self.REPO_ROOT), timeout=30,
        )

    def test_phases_output(self) -> None:
        result = self._run("--phases")
        assert result.returncode == 0

    def test_phases_json(self) -> None:
        result = self._run("--phases", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)
        assert len(data) > 0

    def test_phase_output(self) -> None:
        result = self._run("--phase", "382")
        assert result.returncode == 0
        assert "382" in result.stdout

    def test_phase_json(self) -> None:
        result = self._run("--phase", "382", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["id"] == 382

    def test_phase_invalid(self) -> None:
        result = self._run("--phase", "9999")
        assert result.returncode != 0

    def test_timeline_output(self) -> None:
        result = self._run("--timeline")
        assert result.returncode == 0

    def test_timeline_json(self) -> None:
        result = self._run("--timeline", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)

    def test_stats_output(self) -> None:
        result = self._run("--stats")
        assert result.returncode == 0
        assert "고고학" in result.stdout

    def test_stats_json(self) -> None:
        result = self._run("--stats", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "total_phases_found" in data

    def test_search_output(self) -> None:
        result = self._run("--search", "APF")
        assert result.returncode == 0

    def test_search_json(self) -> None:
        result = self._run("--search", "APF", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert isinstance(data, list)

    def test_no_args_shows_help(self) -> None:
        result = self._run()
        assert result.returncode != 0
