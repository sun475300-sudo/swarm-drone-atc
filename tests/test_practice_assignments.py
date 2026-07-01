"""GENESIS Phase 382 — 실습 과제 10종 단위 테스트.

검증 항목:
- 과제 레지스트리 무결성 (10종, ID 유일, frozen)
- 채점 로직 결정성 (grade() 반복 호출 동일 결과)
- 부울/비율 기준 채점 정확도
- 합격/불합격 경계 검증
- CLI 출력 (--list, --detail, --rubric)
- 에러 케이스 (잘못된 ID, 음수 배점)
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

from simulation.practice_assignments import (
    ASSIGNMENTS,
    PASS_PERCENTAGE,
    Assignment,
    Criterion,
    CriterionScore,
    GradeResult,
    Submission,
    get_assignment,
    grade,
    list_assignments,
    rubric_text,
)


class TestAssignmentRegistry:
    """과제 레지스트리 무결성."""

    def test_exactly_10_assignments(self) -> None:
        assert len(ASSIGNMENTS) == 10

    def test_ids_are_1_to_10(self) -> None:
        ids = sorted(a.assignment_id for a in ASSIGNMENTS)
        assert ids == list(range(1, 11))

    def test_ids_are_unique(self) -> None:
        ids = [a.assignment_id for a in ASSIGNMENTS]
        assert len(ids) == len(set(ids))

    def test_all_assignments_frozen(self) -> None:
        for a in ASSIGNMENTS:
            with pytest.raises(AttributeError):
                a.title = "mutated"  # type: ignore[misc]

    def test_all_criteria_frozen(self) -> None:
        for a in ASSIGNMENTS:
            for c in a.criteria:
                with pytest.raises(AttributeError):
                    c.name = "mutated"  # type: ignore[misc]

    def test_total_points_positive(self) -> None:
        for a in ASSIGNMENTS:
            assert a.total_points > 0, f"Assignment {a.assignment_id} has non-positive total"

    def test_each_assignment_has_criteria(self) -> None:
        for a in ASSIGNMENTS:
            assert len(a.criteria) >= 2, f"Assignment {a.assignment_id} needs ≥2 criteria"

    def test_each_assignment_has_learning_outcomes(self) -> None:
        for a in ASSIGNMENTS:
            assert len(a.learning_outcomes) >= 1

    def test_weeks_in_valid_range(self) -> None:
        for a in ASSIGNMENTS:
            assert 1 <= a.week <= 16

    def test_difficulty_values(self) -> None:
        valid = {"입문", "기초", "중급", "고급"}
        for a in ASSIGNMENTS:
            assert a.difficulty in valid, f"Assignment {a.assignment_id}: {a.difficulty}"


class TestGetAssignment:
    """get_assignment() 조회."""

    def test_valid_id(self) -> None:
        a = get_assignment(1)
        assert a.assignment_id == 1
        assert a.title == "기본 시뮬레이션 실행 및 KPI 측정"

    def test_all_ids_retrievable(self) -> None:
        for i in range(1, 11):
            a = get_assignment(i)
            assert a.assignment_id == i

    def test_invalid_id_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown assignment_id=99"):
            get_assignment(99)

    def test_zero_id_raises(self) -> None:
        with pytest.raises(ValueError):
            get_assignment(0)


class TestListAssignments:
    """list_assignments() 목록."""

    def test_returns_10_items(self) -> None:
        result = list_assignments()
        assert len(result) == 10

    def test_dict_keys(self) -> None:
        result = list_assignments()
        expected_keys = {"id", "title", "category", "difficulty", "week", "total_points", "criteria_count"}
        for item in result:
            assert set(item.keys()) == expected_keys

    def test_sorted_by_id(self) -> None:
        result = list_assignments()
        ids = [item["id"] for item in result]
        assert ids == list(range(1, 11))


class TestCriterionValidation:
    """Criterion 생성 시 유효성 검증."""

    def test_negative_max_points_raises(self) -> None:
        with pytest.raises(ValueError, match="max_points must be positive"):
            Criterion("bad", "desc", -5.0, 1.0)

    def test_zero_max_points_raises(self) -> None:
        with pytest.raises(ValueError, match="max_points must be positive"):
            Criterion("bad", "desc", 0.0, 1.0)

    def test_zero_threshold_non_boolean_raises(self) -> None:
        with pytest.raises(ValueError, match="threshold must be positive"):
            Criterion("bad", "desc", 10.0, 0.0)

    def test_zero_threshold_boolean_ok(self) -> None:
        c = Criterion("ok", "desc", 10.0, 0.0, is_boolean=True)
        assert c.is_boolean is True


class TestGrading:
    """grade() 채점 로직."""

    def test_perfect_score_assignment_1(self) -> None:
        sub = Submission(
            assignment_id=1,
            measurements={
                "collision_count": 0.0,
                "resolution_rate": 0.95,
                "report_submitted": 1.0,
            },
        )
        result = grade(sub)
        assert result.passed is True
        assert result.percentage == pytest.approx(100.0)
        assert result.total_earned == pytest.approx(result.total_possible)

    def test_zero_score(self) -> None:
        sub = Submission(assignment_id=1, measurements={})
        result = grade(sub)
        assert result.passed is False

    def test_partial_score_below_pass(self) -> None:
        sub = Submission(
            assignment_id=1,
            measurements={
                "collision_count": 10.0,
                "resolution_rate": 0.5,
            },
        )
        result = grade(sub)
        assert result.passed is False

    def test_boolean_criterion_all_or_nothing(self) -> None:
        sub = Submission(
            assignment_id=1,
            measurements={
                "collision_count": 0.0,
                "resolution_rate": 0.95,
                "report_submitted": 0.5,
            },
        )
        result = grade(sub)
        report_score = next(s for s in result.scores if s.criterion_name == "report_submitted")
        assert report_score.points_earned == pytest.approx(0.0)
        assert report_score.passed is False

    def test_boolean_criterion_passes_at_1(self) -> None:
        sub = Submission(
            assignment_id=1,
            measurements={
                "collision_count": 0.0,
                "resolution_rate": 0.95,
                "report_submitted": 1.0,
            },
        )
        result = grade(sub)
        report_score = next(s for s in result.scores if s.criterion_name == "report_submitted")
        assert report_score.points_earned == pytest.approx(30.0)
        assert report_score.passed is True

    def test_ratio_criterion_capped_at_max(self) -> None:
        sub = Submission(
            assignment_id=1,
            measurements={
                "collision_count": 0.0,
                "resolution_rate": 1.5,
                "report_submitted": 1.0,
            },
        )
        result = grade(sub)
        res_score = next(s for s in result.scores if s.criterion_name == "resolution_rate")
        assert res_score.achieved_ratio == pytest.approx(1.0)
        assert res_score.points_earned == pytest.approx(40.0)

    def test_lower_better_zero_is_perfect(self) -> None:
        sub = Submission(
            assignment_id=1,
            measurements={"collision_count": 0.0},
        )
        result = grade(sub)
        col_score = next(s for s in result.scores if s.criterion_name == "collision_count")
        assert col_score.achieved_ratio == pytest.approx(1.0)
        assert col_score.points_earned == pytest.approx(30.0)
        assert col_score.passed is True

    def test_lower_better_at_threshold(self) -> None:
        sub = Submission(
            assignment_id=1,
            measurements={"collision_count": 20.0},
        )
        result = grade(sub)
        col_score = next(s for s in result.scores if s.criterion_name == "collision_count")
        assert col_score.achieved_ratio == pytest.approx(1.0)
        assert col_score.passed is True

    def test_lower_better_above_threshold(self) -> None:
        sub = Submission(
            assignment_id=1,
            measurements={"collision_count": 40.0},
        )
        result = grade(sub)
        col_score = next(s for s in result.scores if s.criterion_name == "collision_count")
        assert col_score.achieved_ratio == pytest.approx(0.5)
        assert col_score.passed is False

    def test_submission_rejects_nan(self) -> None:
        with pytest.raises(ValueError, match="must be finite"):
            Submission(assignment_id=1, measurements={"x": float("nan")})

    def test_submission_rejects_inf(self) -> None:
        with pytest.raises(ValueError, match="must be finite"):
            Submission(assignment_id=1, measurements={"x": float("inf")})

    def test_submission_rejects_negative(self) -> None:
        with pytest.raises(ValueError, match="must be non-negative"):
            Submission(assignment_id=1, measurements={"x": -1.0})

    def test_submission_measurements_immutable(self) -> None:
        sub = Submission(assignment_id=1, measurements={"x": 1.0})
        with pytest.raises(TypeError):
            sub.measurements["x"] = 2.0  # type: ignore[index]

    def test_deterministic_grading(self) -> None:
        sub = Submission(
            assignment_id=3,
            measurements={
                "param_sets_tested": 7.0,
                "best_resolution_rate": 0.98,
                "sensitivity_analysis": 1.0,
                "conclusion_quality": 0.8,
            },
        )
        r1 = grade(sub)
        r2 = grade(sub)
        assert r1.total_earned == r2.total_earned
        assert r1.percentage == r2.percentage
        assert r1.passed == r2.passed

    def test_grade_all_assignments_perfect(self) -> None:
        for a in ASSIGNMENTS:
            measurements: dict[str, float] = {}
            for c in a.criteria:
                if c.is_boolean:
                    measurements[c.name] = 1.0
                elif c.is_lower_better:
                    measurements[c.name] = 0.0
                else:
                    measurements[c.name] = c.threshold
            sub = Submission(assignment_id=a.assignment_id, measurements=measurements)
            result = grade(sub)
            assert result.passed is True, f"Assignment {a.assignment_id} should pass with threshold values"
            assert result.percentage == pytest.approx(100.0)

    def test_grade_result_frozen(self) -> None:
        sub = Submission(assignment_id=1, measurements={"report_submitted": 1.0})
        result = grade(sub)
        with pytest.raises(AttributeError):
            result.passed = False  # type: ignore[misc]


class TestGradeResultDict:
    """GradeResult.as_dict() 직렬화."""

    def test_as_dict_keys(self) -> None:
        sub = Submission(assignment_id=1, measurements={"report_submitted": 1.0})
        result = grade(sub)
        d = result.as_dict()
        assert "assignment_id" in d
        assert "total_earned" in d
        assert "total_possible" in d
        assert "percentage" in d
        assert "passed" in d
        assert "criteria" in d

    def test_as_dict_json_serializable(self) -> None:
        sub = Submission(assignment_id=1, measurements={"report_submitted": 1.0})
        result = grade(sub)
        text = json.dumps(result.as_dict(), ensure_ascii=False)
        assert isinstance(text, str)

    def test_criterion_score_frozen(self) -> None:
        sub = Submission(assignment_id=1, measurements={"report_submitted": 1.0})
        result = grade(sub)
        for s in result.scores:
            with pytest.raises(AttributeError):
                s.points_earned = 999.0  # type: ignore[misc]


class TestRubricText:
    """rubric_text() 출력."""

    def test_contains_title(self) -> None:
        text = rubric_text(1)
        assert "기본 시뮬레이션 실행 및 KPI 측정" in text

    def test_contains_all_criteria(self) -> None:
        text = rubric_text(1)
        assert "collision_count" in text
        assert "resolution_rate" in text
        assert "report_submitted" in text

    def test_contains_pass_percentage(self) -> None:
        text = rubric_text(1)
        assert str(PASS_PERCENTAGE) in text

    def test_all_assignments_rubric(self) -> None:
        for a in ASSIGNMENTS:
            text = rubric_text(a.assignment_id)
            assert a.title in text

    def test_invalid_id_raises(self) -> None:
        with pytest.raises(ValueError):
            rubric_text(0)


class TestCLI:
    """CLI 실행."""

    REPO_ROOT = pathlib.Path(__file__).parent.parent
    SCRIPT = str(REPO_ROOT / "simulation" / "practice_assignments.py")
    UTF8_ENV = {**__import__("os").environ, "PYTHONUTF8": "1"}

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, self.SCRIPT, *args],
            capture_output=True, encoding="utf-8", env=self.UTF8_ENV,
        )

    def test_list_output(self) -> None:
        result = self._run("--list")
        assert result.returncode == 0

    def test_list_json(self) -> None:
        result = self._run("--list", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert len(data) == 10

    def test_detail_output(self) -> None:
        result = self._run("--detail", "1")
        assert result.returncode == 0

    def test_rubric_output(self) -> None:
        result = self._run("--rubric", "1")
        assert result.returncode == 0

    def test_no_args_shows_help(self) -> None:
        result = self._run()
        assert result.returncode != 0

    def test_invalid_detail_id(self) -> None:
        result = self._run("--detail", "99")
        assert result.returncode != 0
