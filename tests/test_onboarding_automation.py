"""GENESIS Phase 385 -- 후속 기수 온보딩 자동화 테스트.

검증 항목:
- 환경 점검 레지스트리 무결성 (19개, frozen)
- 아키텍처 투어 레지스트리 (18 스톱, ID 유일, frozen)
- 점검 실행 결정성 (CheckResult frozen)
- 투어 조회 API (정상/에러)
- 온보딩 리포트 생성 및 직렬화
- CLI 출력 (--check, --tour, --tour-stop, --report, --setup-hint, --json)
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

from simulation.onboarding_automation import (
    ARCHITECTURE_TOUR,
    ENVIRONMENT_CHECKS,
    CheckResult,
    OnboardingReport,
    generate_report,
    get_tour_stop,
    list_tour_stops,
    run_environment_checks,
    setup_command_hint,
)


class TestEnvironmentCheckRegistry:
    """환경 점검 레지스트리 무결성."""

    def test_exactly_19_checks(self) -> None:
        assert len(ENVIRONMENT_CHECKS) == 19

    def test_is_tuple(self) -> None:
        assert isinstance(ENVIRONMENT_CHECKS, tuple)

    def test_all_frozen(self) -> None:
        for check in ENVIRONMENT_CHECKS:
            with pytest.raises(AttributeError):
                check.name = "mutated"  # type: ignore[misc]

    def test_names_unique(self) -> None:
        names = [c.name for c in ENVIRONMENT_CHECKS]
        assert len(names) == len(set(names))

    def test_categories(self) -> None:
        valid = {"runtime", "core", "dev", "optional", "structure", "config"}
        for check in ENVIRONMENT_CHECKS:
            assert check.category in valid, f"Invalid category: {check.category}"

    def test_check_types(self) -> None:
        valid = {"python_version", "package", "directory", "file"}
        for check in ENVIRONMENT_CHECKS:
            assert check.check_type in valid, f"Invalid check_type: {check.check_type}"

    def test_required_count(self) -> None:
        required = [c for c in ENVIRONMENT_CHECKS if c.required]
        assert len(required) >= 10


class TestCheckResult:
    """CheckResult 불변성."""

    def test_frozen(self) -> None:
        r = CheckResult(name="test", passed=True, detail="ok")
        with pytest.raises(AttributeError):
            r.passed = False  # type: ignore[misc]


class TestRunEnvironmentChecks:
    """run_environment_checks() 실행."""

    def test_returns_tuple(self) -> None:
        results = run_environment_checks()
        assert isinstance(results, tuple)

    def test_returns_19_results(self) -> None:
        results = run_environment_checks()
        assert len(results) == 19

    def test_all_check_result_type(self) -> None:
        results = run_environment_checks()
        for r in results:
            assert isinstance(r, CheckResult)

    def test_python_version_passes(self) -> None:
        results = run_environment_checks()
        py_check = next(r for r in results if r.name == "python_version")
        assert py_check.passed is True

    def test_deterministic(self) -> None:
        r1 = run_environment_checks()
        r2 = run_environment_checks()
        for a, b in zip(r1, r2):
            assert a.name == b.name
            assert a.passed == b.passed


class TestArchitectureTourRegistry:
    """아키텍처 투어 레지스트리."""

    def test_exactly_18_stops(self) -> None:
        assert len(ARCHITECTURE_TOUR) == 18

    def test_is_tuple(self) -> None:
        assert isinstance(ARCHITECTURE_TOUR, tuple)

    def test_ids_are_1_to_18(self) -> None:
        ids = sorted(s.stop_id for s in ARCHITECTURE_TOUR)
        assert ids == list(range(1, 19))

    def test_ids_unique(self) -> None:
        ids = [s.stop_id for s in ARCHITECTURE_TOUR]
        assert len(ids) == len(set(ids))

    def test_all_frozen(self) -> None:
        for stop in ARCHITECTURE_TOUR:
            with pytest.raises(AttributeError):
                stop.title = "mutated"  # type: ignore[misc]

    def test_all_have_key_files(self) -> None:
        for stop in ARCHITECTURE_TOUR:
            assert len(stop.key_files) >= 1

    def test_all_have_exercises(self) -> None:
        for stop in ARCHITECTURE_TOUR:
            assert len(stop.exercises) >= 1

    def test_all_have_concepts(self) -> None:
        for stop in ARCHITECTURE_TOUR:
            assert len(stop.concepts) >= 1

    def test_key_files_are_tuple(self) -> None:
        for stop in ARCHITECTURE_TOUR:
            assert isinstance(stop.key_files, tuple)

    def test_layer_values(self) -> None:
        valid_layers = {
            "개요", "Layer 1 (드론)", "Layer 2 (제어)", "Layer 3 (시뮬)",
            "Layer 4 (UI)", "안전", "시나리오", "테스트", "인증",
            "교육", "국제", "웹", "배포", "마무리",
        }
        for stop in ARCHITECTURE_TOUR:
            assert stop.layer in valid_layers, f"Invalid layer: {stop.layer}"


class TestGetTourStop:
    """get_tour_stop() API."""

    def test_valid_id(self) -> None:
        stop = get_tour_stop(1)
        assert stop.stop_id == 1
        assert stop.title == "SDACS 프로젝트 구조"

    def test_all_ids_retrievable(self) -> None:
        for i in range(1, 19):
            stop = get_tour_stop(i)
            assert stop.stop_id == i

    def test_invalid_id_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown stop_id=99"):
            get_tour_stop(99)

    def test_zero_id_raises(self) -> None:
        with pytest.raises(ValueError):
            get_tour_stop(0)


class TestListTourStops:
    """list_tour_stops() 목록."""

    def test_returns_18_items(self) -> None:
        result = list_tour_stops()
        assert len(result) == 18

    def test_dict_keys(self) -> None:
        result = list_tour_stops()
        expected = {"id", "layer", "title", "files_count", "exercises_count"}
        for item in result:
            assert set(item.keys()) == expected

    def test_sorted_by_id(self) -> None:
        result = list_tour_stops()
        ids = [item["id"] for item in result]
        assert ids == list(range(1, 19))


class TestGenerateReport:
    """generate_report() 통합 리포트."""

    def test_returns_onboarding_report(self) -> None:
        report = generate_report()
        assert isinstance(report, OnboardingReport)

    def test_env_checks_not_empty(self) -> None:
        report = generate_report()
        assert len(report.env_checks) == 19

    def test_pass_rates_in_range(self) -> None:
        report = generate_report()
        assert 0.0 <= report.env_pass_rate <= 100.0
        assert 0.0 <= report.required_pass_rate <= 100.0

    def test_total_tour_stops(self) -> None:
        report = generate_report()
        assert report.total_tour_stops == 18

    def test_as_dict_json_serializable(self) -> None:
        report = generate_report()
        d = report.as_dict()
        text = json.dumps(d, ensure_ascii=False)
        assert isinstance(text, str)

    def test_as_dict_keys(self) -> None:
        report = generate_report()
        d = report.as_dict()
        expected = {"env_pass_rate", "required_pass_rate", "total_tour_stops", "ready", "checks"}
        assert set(d.keys()) == expected

    def test_frozen(self) -> None:
        report = generate_report()
        with pytest.raises(AttributeError):
            report.ready = True  # type: ignore[misc]


class TestSetupCommandHint:
    """setup_command_hint() 힌트 텍스트."""

    def test_returns_string(self) -> None:
        hint = setup_command_hint()
        assert isinstance(hint, str)

    def test_contains_pip_install(self) -> None:
        hint = setup_command_hint()
        assert "pip install" in hint

    def test_contains_pytest(self) -> None:
        hint = setup_command_hint()
        assert "pytest" in hint

    def test_contains_venv(self) -> None:
        hint = setup_command_hint()
        assert "venv" in hint


class TestCLI:
    """CLI 실행."""

    REPO_ROOT = pathlib.Path(__file__).parent.parent
    SCRIPT = str(REPO_ROOT / "simulation" / "onboarding_automation.py")
    UTF8_ENV = {**os.environ, "PYTHONUTF8": "1"}

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, self.SCRIPT, *args],
            capture_output=True, encoding="utf-8", env=self.UTF8_ENV,
        )

    def test_check_output(self) -> None:
        result = self._run("--check")
        assert result.returncode == 0
        assert "python_version" in result.stdout

    def test_check_json(self) -> None:
        result = self._run("--check", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert len(data) == 19

    def test_tour_output(self) -> None:
        result = self._run("--tour")
        assert result.returncode == 0

    def test_tour_json(self) -> None:
        result = self._run("--tour", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert len(data) == 18

    def test_tour_stop_output(self) -> None:
        result = self._run("--tour-stop", "1")
        assert result.returncode == 0
        assert "SDACS" in result.stdout

    def test_tour_stop_json(self) -> None:
        result = self._run("--tour-stop", "1", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["id"] == 1

    def test_tour_stop_invalid(self) -> None:
        result = self._run("--tour-stop", "99")
        assert result.returncode != 0

    def test_report_output(self) -> None:
        result = self._run("--report")
        assert result.returncode == 0
        assert "온보딩 리포트" in result.stdout

    def test_report_json(self) -> None:
        result = self._run("--report", "--json")
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "ready" in data

    def test_setup_hint(self) -> None:
        result = self._run("--setup-hint")
        assert result.returncode == 0
        assert "pip install" in result.stdout

    def test_no_args_shows_help(self) -> None:
        result = self._run()
        assert result.returncode != 0
