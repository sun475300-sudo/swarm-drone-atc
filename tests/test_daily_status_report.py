"""일일 상태 리포트 도구 회귀 테스트.

scripts/daily_status_report.py 의 순수 함수(로드맵 파싱·pytest 수집 파싱·
리포트 생성)를 AAA 패턴으로 검증한다. git/pytest 실행은 부수효과라 단위
테스트에서 호출하지 않고, 입력 문자열을 직접 넘겨 결정론적으로 확인한다.
"""

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "daily_status_report.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("daily_status_report", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


dsr = _load_module()


# --- parse_roadmap -------------------------------------------------------

def test_parse_roadmap_counts_checkbox_states_per_track():
    # Arrange
    text = (
        "### Track A — alpha\n"
        "- [ ] A1 pending\n"
        "- [x] A2 done\n"
        "### Track B — beta\n"
        "- [x] B1 done\n"
        "- [~] B2 partial\n"
        "- [ ] B3 pending\n"
    )

    # Act
    stats = dsr.parse_roadmap(text)

    # Assert
    assert stats["tracks"]["Track A — alpha"] == {"done": 1, "partial": 0, "pending": 1}
    assert stats["tracks"]["Track B — beta"] == {"done": 1, "partial": 1, "pending": 1}
    assert stats["totals"] == {"done": 2, "partial": 1, "pending": 2}


def test_parse_roadmap_ignores_non_checkbox_lines():
    # Arrange
    text = "### Track Z\nplain text\n- [x] only one\nmore prose\n"

    # Act
    stats = dsr.parse_roadmap(text)

    # Assert
    assert stats["totals"] == {"done": 1, "partial": 0, "pending": 0}


# --- parse_pytest_collect_output ----------------------------------------

def test_parse_pytest_collect_output_extracts_counts():
    # Arrange
    output = "lots of dots\n3595 tests collected, 5 errors in 5.67s\n"

    # Act
    collected, errors = dsr.parse_pytest_collect_output(output)

    # Assert
    assert collected == 3595
    assert errors == 5


def test_parse_pytest_collect_output_handles_no_errors():
    # Arrange
    output = "100 tests collected in 1.2s\n"

    # Act
    collected, errors = dsr.parse_pytest_collect_output(output)

    # Assert
    assert collected == 100
    assert errors == 0


def test_parse_pytest_collect_output_returns_none_when_unparseable():
    # Arrange
    output = "no module named pytest\n"

    # Act
    collected, errors = dsr.parse_pytest_collect_output(output)

    # Assert
    assert collected is None
    assert errors is None


# --- build_report --------------------------------------------------------

def test_build_report_includes_date_totals_and_tracks():
    # Arrange
    roadmap = {
        "tracks": {"Track A": {"done": 1, "partial": 0, "pending": 1}},
        "totals": {"done": 1, "partial": 0, "pending": 1},
    }
    tests = {"collected": 3595, "errors": 5}
    git = {"branch": "feature", "ahead": 3, "last_commit": "2026-06-03"}

    # Act
    report = dsr.build_report(roadmap, tests, git, date="2026-06-03")

    # Assert
    assert "2026-06-03" in report
    assert "Track A" in report
    assert "3595" in report
    assert "feature" in report


def test_build_report_is_markdown_with_heading():
    # Arrange / Act
    report = dsr.build_report(
        {"tracks": {}, "totals": {"done": 0, "partial": 0, "pending": 0}},
        {"collected": None, "errors": None},
        {"branch": "b", "ahead": 0, "last_commit": "x"},
        date="2026-06-03",
    )

    # Assert
    assert report.lstrip().startswith("#")
    assert "측정 안 함 (--no-pytest)" in report
