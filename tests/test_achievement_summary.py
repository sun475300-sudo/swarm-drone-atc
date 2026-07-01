"""GENESIS Phase 392 -- 성과 요약 테스트.

검증 항목:
- TrackProgress / Milestone / AchievementSummary frozen
- TRACKS / TRACK_ENTRIES / MILESTONES 레지스트리 무결성
- count_roadmap_completed / count_simulation_modules / count_test_files
- list_tracks / list_milestones
- build_summary
- CLI: --summary, --tracks, --milestones, --json
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

from simulation.achievement_summary import (
    MILESTONES,
    TRACK_ENTRIES,
    TRACKS,
    AchievementSummary,
    Milestone,
    TrackProgress,
    build_summary,
    count_roadmap_completed,
    count_simulation_modules,
    count_test_files,
    list_milestones,
    list_tracks,
)


class TestTrackProgress:
    def test_frozen(self) -> None:
        t = TRACK_ENTRIES[0]
        with pytest.raises(AttributeError):
            t.name = "mutated"  # type: ignore[misc]

    def test_fields(self) -> None:
        t = TRACK_ENTRIES[0]
        assert t.track_id == "core"
        assert t.name == "Core System"
        assert t.completed_count == 690
        assert t.total_count == 690

    def test_progress_pct(self) -> None:
        t = TRACK_ENTRIES[0]
        assert t.progress_pct == 100.0

    def test_progress_pct_partial(self) -> None:
        t = TrackProgress("test", "Test", "1-10", 5, 10, "진행중")
        assert t.progress_pct == 50.0

    def test_progress_pct_zero_total(self) -> None:
        t = TrackProgress("test", "Test", "1-0", 0, 0, "없음")
        assert t.progress_pct == 0.0

    def test_as_dict(self) -> None:
        d = TRACK_ENTRIES[0].as_dict()
        assert d["track_id"] == "core"
        assert d["progress_pct"] == 100.0
        text = json.dumps(d, ensure_ascii=False)
        assert isinstance(text, str)


class TestMilestone:
    def test_frozen(self) -> None:
        m = MILESTONES[0]
        with pytest.raises(AttributeError):
            m.title = "mutated"  # type: ignore[misc]

    def test_fields(self) -> None:
        m = MILESTONES[0]
        assert m.phase == 1
        assert isinstance(m.title, str)
        assert isinstance(m.date, str)

    def test_as_dict(self) -> None:
        d = MILESTONES[0].as_dict()
        assert "phase" in d
        assert "title" in d
        text = json.dumps(d, ensure_ascii=False)
        assert isinstance(text, str)


class TestRegistries:
    def test_tracks_is_tuple(self) -> None:
        assert isinstance(TRACKS, tuple)

    def test_track_entries_is_tuple(self) -> None:
        assert isinstance(TRACK_ENTRIES, tuple)

    def test_track_entries_count(self) -> None:
        assert len(TRACK_ENTRIES) == 10

    def test_track_unique_ids(self) -> None:
        ids = [t.track_id for t in TRACK_ENTRIES]
        assert len(ids) == len(set(ids))

    def test_milestones_is_tuple(self) -> None:
        assert isinstance(MILESTONES, tuple)

    def test_milestones_count(self) -> None:
        assert len(MILESTONES) == 8

    def test_milestones_sorted_by_phase(self) -> None:
        phases = [m.phase for m in MILESTONES]
        assert phases == sorted(phases)

    def test_completed_tracks_count(self) -> None:
        done = sum(1 for t in TRACK_ENTRIES if t.status == "완료")
        assert done == 6


class TestCountRoadmapCompleted:
    def test_nonexistent_file(self) -> None:
        assert count_roadmap_completed(pathlib.Path("/nonexistent/ROADMAP.md")) == 0

    def test_real_roadmap(self) -> None:
        repo_root = pathlib.Path(__file__).parent.parent
        result = count_roadmap_completed(repo_root / "ROADMAP.md")
        assert result >= 1

    def test_with_temp_file(self, tmp_path: pathlib.Path) -> None:
        rm = tmp_path / "ROADMAP.md"
        rm.write_text(
            "- [x] **Phase 1** done\n"
            "- [x] **Phase 2** done\n"
            "- [ ] **Phase 3** not done\n",
            encoding="utf-8",
        )
        assert count_roadmap_completed(rm) == 2

    def test_empty_file(self, tmp_path: pathlib.Path) -> None:
        rm = tmp_path / "ROADMAP.md"
        rm.write_text("", encoding="utf-8")
        assert count_roadmap_completed(rm) == 0


class TestCountSimulationModules:
    def test_real_count(self) -> None:
        repo_root = pathlib.Path(__file__).parent.parent
        result = count_simulation_modules(repo_root)
        assert result >= 10

    def test_nonexistent_dir(self, tmp_path: pathlib.Path) -> None:
        assert count_simulation_modules(tmp_path / "nope") == 0

    def test_empty_dir(self, tmp_path: pathlib.Path) -> None:
        (tmp_path / "simulation").mkdir()
        assert count_simulation_modules(tmp_path) == 0


class TestCountTestFiles:
    def test_real_count(self) -> None:
        repo_root = pathlib.Path(__file__).parent.parent
        result = count_test_files(repo_root)
        assert result >= 10

    def test_nonexistent_dir(self, tmp_path: pathlib.Path) -> None:
        assert count_test_files(tmp_path / "nope") == 0


class TestListTracks:
    def test_returns_list(self) -> None:
        data = list_tracks()
        assert isinstance(data, list)
        assert len(data) == 10

    def test_has_keys(self) -> None:
        d = list_tracks()[0]
        assert "track_id" in d
        assert "progress_pct" in d

    def test_json_serializable(self) -> None:
        text = json.dumps(list_tracks(), ensure_ascii=False)
        assert isinstance(text, str)


class TestListMilestones:
    def test_returns_list(self) -> None:
        data = list_milestones()
        assert isinstance(data, list)
        assert len(data) == 8

    def test_has_keys(self) -> None:
        d = list_milestones()[0]
        assert "phase" in d
        assert "title" in d

    def test_json_serializable(self) -> None:
        text = json.dumps(list_milestones(), ensure_ascii=False)
        assert isinstance(text, str)


class TestBuildSummary:
    def test_returns_summary(self) -> None:
        s = build_summary()
        assert isinstance(s, AchievementSummary)

    def test_frozen(self) -> None:
        s = build_summary()
        with pytest.raises(AttributeError):
            s.project_name = "mutated"  # type: ignore[misc]

    def test_project_name(self) -> None:
        s = build_summary()
        assert "SDACS" in s.project_name

    def test_total_phases(self) -> None:
        s = build_summary()
        assert s.total_phases_completed > 0

    def test_tracks_count(self) -> None:
        s = build_summary()
        assert s.total_tracks == 10
        assert s.tracks_completed == 6

    def test_as_dict(self) -> None:
        d = build_summary().as_dict()
        assert "project_name" in d
        assert "tracks" in d
        assert "milestones" in d
        text = json.dumps(d, ensure_ascii=False)
        assert isinstance(text, str)

    def test_with_temp_roadmap(self, tmp_path: pathlib.Path) -> None:
        (tmp_path / "simulation").mkdir()
        (tmp_path / "simulation" / "a.py").touch()
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_a.py").touch()
        rm = tmp_path / "ROADMAP.md"
        rm.write_text("- [x] **Phase 1** done\n", encoding="utf-8")
        s = build_summary(repo_root=tmp_path, roadmap_path=rm)
        assert s.total_simulation_modules == 1
        assert s.total_test_files == 1
        assert s.roadmap_completed_phases == 1


class TestCLI:
    REPO_ROOT = pathlib.Path(__file__).parent.parent
    SCRIPT = str(REPO_ROOT / "simulation" / "achievement_summary.py")
    UTF8_ENV = {**os.environ, "PYTHONUTF8": "1"}

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, self.SCRIPT, *args],
            capture_output=True, encoding="utf-8", env=self.UTF8_ENV,
            timeout=30,
        )

    def test_summary(self) -> None:
        r = self._run("--summary")
        assert r.returncode == 0

    def test_summary_json(self) -> None:
        r = self._run("--summary", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "project_name" in data

    def test_tracks(self) -> None:
        r = self._run("--tracks")
        assert r.returncode == 0

    def test_tracks_json(self) -> None:
        r = self._run("--tracks", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert len(data) == 10

    def test_milestones(self) -> None:
        r = self._run("--milestones")
        assert r.returncode == 0

    def test_milestones_json(self) -> None:
        r = self._run("--milestones", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert len(data) == 8

    def test_no_args(self) -> None:
        r = self._run()
        assert r.returncode != 0
