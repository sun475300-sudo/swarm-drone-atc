"""GENESIS Phase 383 -- 15주 커리큘럼 슬라이드 패키지 테스트.

검증 항목:
- CurriculumWeek / CurriculumPackage frozen
- CurriculumWeek 유효성 검증 (__post_init__)
- CURRICULUM_WEEKS 레지스트리 무결성 (15주, ID 유일, 카테고리 유효)
- get_week() / filter_by_category() API
- list_weeks() / build_package() / generate_syllabus() / get_stats() 함수
- CLI 출력 (--weeks, --week, --category, --syllabus, --stats, --json)
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

from simulation.curriculum_slide_package import (
    CATEGORIES,
    CURRICULUM_WEEKS,
    CurriculumPackage,
    CurriculumWeek,
    build_package,
    filter_by_category,
    generate_syllabus,
    get_stats,
    get_week,
    list_weeks,
)


class TestCurriculumWeek:
    """CurriculumWeek frozen dataclass."""

    def test_frozen(self) -> None:
        w = CURRICULUM_WEEKS[0]
        with pytest.raises(AttributeError):
            w.topic = "mutated"  # type: ignore[misc]

    def test_fields(self) -> None:
        w = CURRICULUM_WEEKS[0]
        assert w.week_id == 1
        assert w.category == "기초"
        assert isinstance(w.objectives, tuple)
        assert isinstance(w.sdacs_modules, tuple)
        assert isinstance(w.exercises, tuple)
        assert isinstance(w.slide_outline, tuple)
        assert isinstance(w.related_phases, tuple)

    def test_invalid_week_id_low(self) -> None:
        with pytest.raises(ValueError, match="week_id must be 1-15"):
            CurriculumWeek(
                0, "기초", "test",
                ("obj",), ("mod",), ("ex",), ("slide",), (1,),
            )

    def test_invalid_week_id_high(self) -> None:
        with pytest.raises(ValueError, match="week_id must be 1-15"):
            CurriculumWeek(
                16, "기초", "test",
                ("obj",), ("mod",), ("ex",), ("slide",), (1,),
            )

    def test_no_objectives_raises(self) -> None:
        with pytest.raises(ValueError, match="At least 1 objective"):
            CurriculumWeek(
                1, "기초", "test",
                (), ("mod",), ("ex",), ("slide",), (1,),
            )

    def test_invalid_category_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid category"):
            CurriculumWeek(
                1, "잘못된카테고리", "test",
                ("obj",), ("mod",), ("ex",), ("slide",), (1,),
            )

    def test_no_slides_raises(self) -> None:
        with pytest.raises(ValueError, match="At least 1 slide outline"):
            CurriculumWeek(
                1, "기초", "test",
                ("obj",), ("mod",), ("ex",), (), (1,),
            )


class TestCurriculumPackage:
    """CurriculumPackage frozen + as_dict."""

    def test_frozen(self) -> None:
        pkg = build_package()
        with pytest.raises(AttributeError):
            pkg.credits = 99  # type: ignore[misc]

    def test_as_dict(self) -> None:
        pkg = build_package()
        d = pkg.as_dict()
        assert d["course_name"] == "드론 관제 시스템 설계 (Drone ATC System Design)"
        assert d["credits"] == 3
        assert d["total_weeks"] == 15
        assert len(d["weeks"]) == 15
        text = json.dumps(d, ensure_ascii=False)
        assert isinstance(text, str)


class TestCurriculumWeeksRegistry:
    """CURRICULUM_WEEKS 레지스트리 무결성."""

    def test_exactly_15_weeks(self) -> None:
        assert len(CURRICULUM_WEEKS) == 15

    def test_is_tuple(self) -> None:
        assert isinstance(CURRICULUM_WEEKS, tuple)

    def test_ids_unique(self) -> None:
        ids = [w.week_id for w in CURRICULUM_WEEKS]
        assert len(ids) == len(set(ids))

    def test_ids_are_1_to_15(self) -> None:
        ids = sorted(w.week_id for w in CURRICULUM_WEEKS)
        assert ids == list(range(1, 16))

    def test_all_valid_categories(self) -> None:
        for w in CURRICULUM_WEEKS:
            assert w.category in CATEGORIES, f"Week {w.week_id} has invalid category: {w.category}"

    def test_all_have_objectives(self) -> None:
        for w in CURRICULUM_WEEKS:
            assert len(w.objectives) >= 1, f"Week {w.week_id} has no objectives"

    def test_all_have_sdacs_modules(self) -> None:
        for w in CURRICULUM_WEEKS:
            assert len(w.sdacs_modules) >= 1, f"Week {w.week_id} has no sdacs_modules"

    def test_all_have_exercises(self) -> None:
        for w in CURRICULUM_WEEKS:
            assert len(w.exercises) >= 1, f"Week {w.week_id} has no exercises"

    def test_all_have_slide_outline(self) -> None:
        for w in CURRICULUM_WEEKS:
            assert len(w.slide_outline) >= 1, f"Week {w.week_id} has no slide_outline"

    def test_all_have_related_phases(self) -> None:
        for w in CURRICULUM_WEEKS:
            assert len(w.related_phases) >= 1, f"Week {w.week_id} has no related_phases"

    def test_sequential_order(self) -> None:
        for i, w in enumerate(CURRICULUM_WEEKS):
            assert w.week_id == i + 1


class TestGetWeek:
    """get_week() API."""

    def test_valid_week(self) -> None:
        w = get_week(1)
        assert w.week_id == 1

    def test_all_weeks_retrievable(self) -> None:
        for i in range(1, 16):
            w = get_week(i)
            assert w.week_id == i

    def test_invalid_week_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown week_id=99"):
            get_week(99)


class TestFilterByCategory:
    """filter_by_category() 필터링."""

    def test_basics(self) -> None:
        weeks = filter_by_category("기초")
        assert len(weeks) == 3
        assert all(w.category == "기초" for w in weeks)

    def test_core(self) -> None:
        weeks = filter_by_category("핵심")
        assert len(weeks) == 4
        assert all(w.category == "핵심" for w in weeks)

    def test_midterm(self) -> None:
        weeks = filter_by_category("중간")
        assert len(weeks) == 1

    def test_advanced(self) -> None:
        weeks = filter_by_category("심화")
        assert len(weeks) == 4

    def test_project(self) -> None:
        weeks = filter_by_category("프로젝트")
        assert len(weeks) == 3

    def test_nonexistent_category(self) -> None:
        weeks = filter_by_category("존재하지않는")
        assert len(weeks) == 0


class TestListWeeks:
    """list_weeks() 목록."""

    def test_returns_15_items(self) -> None:
        result = list_weeks()
        assert len(result) == 15

    def test_dict_keys(self) -> None:
        result = list_weeks()
        expected = {"week", "category", "topic", "objectives_count", "modules_count", "exercises_count", "slides_count"}
        for item in result:
            assert set(item.keys()) == expected


class TestBuildPackage:
    """build_package() 패키지."""

    def test_package_fields(self) -> None:
        pkg = build_package()
        assert pkg.course_name == "드론 관제 시스템 설계 (Drone ATC System Design)"
        assert pkg.credits == 3
        assert len(pkg.prerequisites) == 3
        assert pkg.total_weeks == 15
        assert len(pkg.weeks) == 15


class TestGenerateSyllabus:
    """generate_syllabus() 강의 계획서."""

    def test_returns_string(self) -> None:
        result = generate_syllabus()
        assert isinstance(result, str)
        assert len(result) > 100

    def test_contains_course_name(self) -> None:
        result = generate_syllabus()
        assert "드론 관제 시스템 설계" in result

    def test_contains_all_weeks(self) -> None:
        result = generate_syllabus()
        for i in range(1, 16):
            assert f"{i}주]" in result


class TestGetStats:
    """get_stats() 통계."""

    def test_total_weeks(self) -> None:
        stats = get_stats()
        assert stats["total_weeks"] == 15

    def test_by_category_sum(self) -> None:
        stats = get_stats()
        total = sum(stats["by_category"].values())
        assert total == 15

    def test_positive_counts(self) -> None:
        stats = get_stats()
        assert stats["total_objectives"] > 0
        assert stats["total_exercises"] > 0
        assert stats["total_slide_sections"] > 0
        assert stats["unique_sdacs_modules"] > 0
        assert stats["related_phases_count"] > 0

    def test_json_serializable(self) -> None:
        stats = get_stats()
        text = json.dumps(stats, ensure_ascii=False)
        assert isinstance(text, str)


class TestCLI:
    """CLI 실행."""

    REPO_ROOT = pathlib.Path(__file__).parent.parent
    SCRIPT = str(REPO_ROOT / "simulation" / "curriculum_slide_package.py")
    UTF8_ENV = {**os.environ, "PYTHONUTF8": "1"}

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, self.SCRIPT, *args],
            capture_output=True, encoding="utf-8", env=self.UTF8_ENV,
            timeout=30,
        )

    def test_weeks_output(self) -> None:
        result = self._run("--weeks")
        assert result.returncode == 0

    def test_weeks_json(self) -> None:
        result = self._run("--weeks", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert len(data) == 15

    def test_week_output(self) -> None:
        result = self._run("--week", "1")
        assert result.returncode == 0
        assert "1주" in result.stdout

    def test_week_json(self) -> None:
        result = self._run("--week", "1", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["week"] == 1

    def test_week_invalid(self) -> None:
        result = self._run("--week", "99")
        assert result.returncode != 0

    def test_category_output(self) -> None:
        result = self._run("--category", "기초")
        assert result.returncode == 0
        assert "기초" in result.stdout

    def test_category_json(self) -> None:
        result = self._run("--category", "기초", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert len(data) == 3

    def test_syllabus_output(self) -> None:
        result = self._run("--syllabus")
        assert result.returncode == 0
        assert "드론 관제 시스템 설계" in result.stdout

    def test_syllabus_json(self) -> None:
        result = self._run("--syllabus", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["total_weeks"] == 15

    def test_stats_output(self) -> None:
        result = self._run("--stats")
        assert result.returncode == 0
        assert "커리큘럼" in result.stdout

    def test_stats_json(self) -> None:
        result = self._run("--stats", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["total_weeks"] == 15

    def test_no_args_shows_help(self) -> None:
        result = self._run()
        assert result.returncode != 0
