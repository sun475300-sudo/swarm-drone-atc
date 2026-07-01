"""GENESIS Phase 384 -- 조종자 자격 이론 문제은행 테스트.

검증 항목:
- ExamQuestion / SubjectScore / ExamResult frozen
- ExamQuestion 유효성 검증 (__post_init__)
- QUESTION_BANK 레지스트리 무결성 (40문항, ID 유일, 종별 10문항씩)
- get_question() / filter_by_grade() / filter_by_subject() API
- grade_exam() 채점 로직 (만점, 0점, 부분 정답)
- list_questions() / get_stats() 통계
- CLI 출력 (--list, --grade, --question, --subject, --stats, --json)
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

from simulation.pilot_exam_bank import (
    PASS_THRESHOLD,
    QUESTION_BANK,
    ExamQuestion,
    ExamResult,
    SubjectScore,
    filter_by_grade,
    filter_by_subject,
    get_question,
    get_stats,
    grade_exam,
    list_questions,
)


class TestExamQuestion:
    """ExamQuestion frozen dataclass."""

    def test_frozen(self) -> None:
        q = QUESTION_BANK[0]
        with pytest.raises(AttributeError):
            q.text = "mutated"  # type: ignore[misc]

    def test_fields(self) -> None:
        q = QUESTION_BANK[0]
        assert q.question_id == 1
        assert q.pilot_grade == 4
        assert isinstance(q.choices, tuple)

    def test_invalid_grade(self) -> None:
        with pytest.raises(ValueError, match="pilot_grade must be 1-4"):
            ExamQuestion(99, 5, "test", "q?", ("a", "b"), 0, "m", "c", "d")

    def test_invalid_correct_index(self) -> None:
        with pytest.raises(ValueError, match="correct_index"):
            ExamQuestion(99, 1, "test", "q?", ("a", "b"), 5, "m", "c", "d")

    def test_too_few_choices(self) -> None:
        with pytest.raises(ValueError, match="At least 2 choices"):
            ExamQuestion(99, 1, "test", "q?", ("a",), 0, "m", "c", "d")


class TestSubjectScore:
    """SubjectScore frozen."""

    def test_frozen(self) -> None:
        s = SubjectScore(subject="test", correct=5, total=10, percentage=50.0)
        with pytest.raises(AttributeError):
            s.correct = 99  # type: ignore[misc]


class TestExamResult:
    """ExamResult frozen + as_dict."""

    def test_frozen(self) -> None:
        r = ExamResult(
            pilot_grade=4, total_correct=7, total_questions=10,
            percentage=70.0, passed=True, subject_scores=(),
        )
        with pytest.raises(AttributeError):
            r.passed = False  # type: ignore[misc]

    def test_as_dict(self) -> None:
        r = ExamResult(
            pilot_grade=4, total_correct=7, total_questions=10,
            percentage=70.0, passed=True,
            subject_scores=(
                SubjectScore("항공법규", 3, 3, 100.0),
            ),
        )
        d = r.as_dict()
        assert d["pilot_grade"] == 4
        assert d["passed"] is True
        assert len(d["subjects"]) == 1
        text = json.dumps(d, ensure_ascii=False)
        assert isinstance(text, str)


class TestQuestionBankRegistry:
    """QUESTION_BANK 레지스트리 무결성."""

    def test_exactly_40_questions(self) -> None:
        assert len(QUESTION_BANK) == 40

    def test_is_tuple(self) -> None:
        assert isinstance(QUESTION_BANK, tuple)

    def test_ids_unique(self) -> None:
        ids = [q.question_id for q in QUESTION_BANK]
        assert len(ids) == len(set(ids))

    def test_ids_are_1_to_40(self) -> None:
        ids = sorted(q.question_id for q in QUESTION_BANK)
        assert ids == list(range(1, 41))

    def test_10_per_grade(self) -> None:
        for grade in range(1, 5):
            count = sum(1 for q in QUESTION_BANK if q.pilot_grade == grade)
            assert count == 10, f"Grade {grade} has {count} questions, expected 10"

    def test_all_have_sdacs_module(self) -> None:
        for q in QUESTION_BANK:
            assert len(q.sdacs_module) > 0

    def test_valid_subjects(self) -> None:
        valid = {"항공법규", "비행이론", "기상학", "안전관리"}
        for q in QUESTION_BANK:
            assert q.subject in valid, f"Q{q.question_id} has invalid subject: {q.subject}"

    def test_correct_index_in_range(self) -> None:
        for q in QUESTION_BANK:
            assert 0 <= q.correct_index < len(q.choices)


class TestGetQuestion:
    """get_question() API."""

    def test_valid_id(self) -> None:
        q = get_question(1)
        assert q.question_id == 1

    def test_all_ids_retrievable(self) -> None:
        for i in range(1, 41):
            q = get_question(i)
            assert q.question_id == i

    def test_invalid_id_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown question_id=999"):
            get_question(999)


class TestFilterByGrade:
    """filter_by_grade() 필터링."""

    def test_grade_4(self) -> None:
        questions = filter_by_grade(4)
        assert len(questions) == 10
        assert all(q.pilot_grade == 4 for q in questions)

    def test_grade_1(self) -> None:
        questions = filter_by_grade(1)
        assert len(questions) == 10
        assert all(q.pilot_grade == 1 for q in questions)

    def test_invalid_grade(self) -> None:
        with pytest.raises(ValueError, match="grade must be 1-4"):
            filter_by_grade(5)


class TestFilterBySubject:
    """filter_by_subject() 필터링."""

    def test_existing_subject(self) -> None:
        questions = filter_by_subject("항공법규")
        assert len(questions) > 0
        assert all(q.subject == "항공법규" for q in questions)

    def test_nonexistent_subject(self) -> None:
        questions = filter_by_subject("존재하지않는과목")
        assert len(questions) == 0


class TestListQuestions:
    """list_questions() 목록."""

    def test_returns_40_items(self) -> None:
        result = list_questions()
        assert len(result) == 40

    def test_dict_keys(self) -> None:
        result = list_questions()
        expected = {"id", "grade", "subject", "difficulty", "sdacs_module"}
        for item in result:
            assert set(item.keys()) == expected


class TestGradeExam:
    """grade_exam() 채점 로직."""

    def test_perfect_score(self) -> None:
        answers = {q.question_id: q.correct_index for q in filter_by_grade(4)}
        result = grade_exam(4, answers)
        assert result.total_correct == 10
        assert result.percentage == 100.0
        assert result.passed is True

    def test_zero_score(self) -> None:
        answers = {q.question_id: (q.correct_index + 1) % len(q.choices) for q in filter_by_grade(4)}
        result = grade_exam(4, answers)
        assert result.total_correct == 0
        assert result.percentage == 0.0
        assert result.passed is False

    def test_partial_score(self) -> None:
        questions = filter_by_grade(3)
        answers = {}
        for i, q in enumerate(questions):
            if i < 7:
                answers[q.question_id] = q.correct_index
            else:
                answers[q.question_id] = (q.correct_index + 1) % len(q.choices)
        result = grade_exam(3, answers)
        assert result.total_correct == 7
        assert result.percentage == 70.0
        assert result.passed is True

    def test_missing_answers_counted_wrong(self) -> None:
        result = grade_exam(4, {})
        assert result.total_correct == 0
        assert result.passed is False

    def test_subject_scores_present(self) -> None:
        answers = {q.question_id: q.correct_index for q in filter_by_grade(4)}
        result = grade_exam(4, answers)
        assert len(result.subject_scores) > 0
        for ss in result.subject_scores:
            assert isinstance(ss, SubjectScore)

    def test_result_as_dict(self) -> None:
        answers = {q.question_id: q.correct_index for q in filter_by_grade(2)}
        result = grade_exam(2, answers)
        d = result.as_dict()
        assert d["passed"] is True
        text = json.dumps(d, ensure_ascii=False)
        assert isinstance(text, str)


class TestGetStats:
    """get_stats() 통계."""

    def test_total_questions(self) -> None:
        stats = get_stats()
        assert stats["total_questions"] == 40

    def test_pass_threshold(self) -> None:
        stats = get_stats()
        assert stats["pass_threshold"] == PASS_THRESHOLD

    def test_by_grade_sum(self) -> None:
        stats = get_stats()
        total = sum(stats["by_grade"].values())
        assert total == 40

    def test_json_serializable(self) -> None:
        stats = get_stats()
        text = json.dumps(stats, ensure_ascii=False)
        assert isinstance(text, str)


class TestCLI:
    """CLI 실행."""

    REPO_ROOT = pathlib.Path(__file__).parent.parent
    SCRIPT = str(REPO_ROOT / "simulation" / "pilot_exam_bank.py")
    UTF8_ENV = {**os.environ, "PYTHONUTF8": "1"}

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, self.SCRIPT, *args],
            capture_output=True, encoding="utf-8", env=self.UTF8_ENV,
            timeout=30,
        )

    def test_list_output(self) -> None:
        result = self._run("--list")
        assert result.returncode == 0

    def test_list_json(self) -> None:
        result = self._run("--list", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert len(data) == 40

    def test_grade_output(self) -> None:
        result = self._run("--grade", "4")
        assert result.returncode == 0
        assert "4종" in result.stdout

    def test_grade_json(self) -> None:
        result = self._run("--grade", "4", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert len(data) == 10

    def test_grade_invalid(self) -> None:
        result = self._run("--grade", "5")
        assert result.returncode != 0

    def test_question_output(self) -> None:
        result = self._run("--question", "1")
        assert result.returncode == 0
        assert "Q1" in result.stdout

    def test_question_json(self) -> None:
        result = self._run("--question", "1", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["id"] == 1

    def test_question_invalid(self) -> None:
        result = self._run("--question", "999")
        assert result.returncode != 0

    def test_subject_output(self) -> None:
        result = self._run("--subject", "항공법규")
        assert result.returncode == 0

    def test_subject_json(self) -> None:
        result = self._run("--subject", "항공법규", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert len(data) > 0

    def test_stats_output(self) -> None:
        result = self._run("--stats")
        assert result.returncode == 0
        assert "문제은행" in result.stdout

    def test_stats_json(self) -> None:
        result = self._run("--stats", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["total_questions"] == 40

    def test_no_args_shows_help(self) -> None:
        result = self._run()
        assert result.returncode != 0
