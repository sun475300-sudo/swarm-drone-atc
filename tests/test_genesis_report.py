"""GENESIS Phase 396 -- GENESIS 트랙 종합 보고서 테스트.

검증 항목:
- CategoryProgress / SubsystemScore / GenesisReport frozen
- GENESIS_PHASES / TRACK_CATEGORIES 레지스트리 무결성
- generate_report / get_status
- CLI: --report, --status, --json
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

from simulation.genesis_report import (
    CATEGORY_NAMES_KO,
    GENESIS_PHASES,
    TOTAL_GENESIS_PHASES,
    TRACK_CATEGORIES,
    CategoryProgress,
    GenesisReport,
    SubsystemScore,
    generate_report,
    get_status,
)


class TestCategoryProgress:
    def test_frozen(self) -> None:
        c = CategoryProgress("cert", "인증", 5, (301, 302, 303, 304, 305))
        with pytest.raises(AttributeError):
            c.completed_count = 10  # type: ignore[misc]

    def test_as_dict(self) -> None:
        d = CategoryProgress("cert", "인증", 2, (301, 302)).as_dict()
        assert d["category"] == "cert"
        assert d["completed_count"] == 2
        assert d["phase_ids"] == [301, 302]


class TestSubsystemScore:
    def test_frozen(self) -> None:
        s = SubsystemScore("maturity", 75.0, "C", "detail")
        with pytest.raises(AttributeError):
            s.score = 80.0  # type: ignore[misc]

    def test_as_dict(self) -> None:
        d = SubsystemScore("handover", 60.0, "D", "3/5 완료").as_dict()
        assert d["name"] == "handover"
        assert d["score"] == 60.0


class TestGenesisReport:
    def test_frozen(self) -> None:
        r = GenesisReport(10, 100, 10.0, (), (), "F", False)
        with pytest.raises(AttributeError):
            r.overall_grade = "A"  # type: ignore[misc]

    def test_as_dict(self) -> None:
        d = GenesisReport(30, 100, 30.0, (), (), "B", True).as_dict()
        assert d["completed_phases"] == 30
        assert d["legacy_ready"] is True
        text = json.dumps(d, ensure_ascii=False)
        assert isinstance(text, str)


class TestRegistries:
    def test_genesis_phases_is_tuple(self) -> None:
        assert isinstance(GENESIS_PHASES, tuple)

    def test_genesis_phases_nonempty(self) -> None:
        assert len(GENESIS_PHASES) > 0

    def test_track_categories_is_tuple(self) -> None:
        assert isinstance(TRACK_CATEGORIES, tuple)

    def test_all_phase_categories_valid(self) -> None:
        for _, cat, _ in GENESIS_PHASES:
            assert cat in TRACK_CATEGORIES

    def test_all_phases_in_range(self) -> None:
        for phase, _, _ in GENESIS_PHASES:
            assert 301 <= phase <= 400

    def test_unique_phase_ids(self) -> None:
        ids = [p for p, _, _ in GENESIS_PHASES]
        assert len(ids) == len(set(ids))

    def test_category_names_ko_complete(self) -> None:
        for cat in TRACK_CATEGORIES:
            assert cat in CATEGORY_NAMES_KO

    def test_total_genesis_phases(self) -> None:
        assert TOTAL_GENESIS_PHASES == 100


class TestGenerateReport:
    def test_returns_report(self) -> None:
        report = generate_report()
        assert isinstance(report, GenesisReport)

    def test_completion_range(self) -> None:
        report = generate_report()
        assert 0 <= report.completion_pct <= 100

    def test_has_categories(self) -> None:
        report = generate_report()
        assert len(report.categories) == len(TRACK_CATEGORIES)

    def test_has_subsystems(self) -> None:
        report = generate_report()
        assert len(report.subsystems) == 3

    def test_subsystem_names(self) -> None:
        report = generate_report()
        names = {s.name for s in report.subsystems}
        assert names == {"maturity", "handover", "education_assets"}

    def test_overall_grade_valid(self) -> None:
        report = generate_report()
        assert report.overall_grade in ("A", "B", "C", "D", "F")

    def test_as_dict_json_serializable(self) -> None:
        text = json.dumps(generate_report().as_dict(), ensure_ascii=False)
        assert isinstance(text, str)

    def test_invalid_repo_root_raises(self) -> None:
        with pytest.raises(ValueError, match="does not exist"):
            generate_report(pathlib.Path("/nonexistent/path/xxx"))

    def test_empty_repo(self, tmp_path: pathlib.Path) -> None:
        report = generate_report(tmp_path)
        assert report.completed_phases == len(GENESIS_PHASES)
        assert report.completion_pct > 0


class TestGetStatus:
    def test_returns_dict(self) -> None:
        status = get_status()
        assert isinstance(status, dict)

    def test_has_keys(self) -> None:
        status = get_status()
        assert "completion_pct" in status
        assert "overall_grade" in status
        assert "legacy_ready" in status
        assert "subsystem_grades" in status

    def test_json_serializable(self) -> None:
        text = json.dumps(get_status(), ensure_ascii=False)
        assert isinstance(text, str)


class TestCLI:
    REPO_ROOT = pathlib.Path(__file__).parent.parent
    SCRIPT = str(REPO_ROOT / "simulation" / "genesis_report.py")
    UTF8_ENV = {**os.environ, "PYTHONUTF8": "1"}

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, self.SCRIPT, *args],
            capture_output=True, encoding="utf-8", env=self.UTF8_ENV,
            timeout=30,
        )

    def test_report(self) -> None:
        r = self._run("--report")
        assert r.returncode == 0

    def test_report_json(self) -> None:
        r = self._run("--report", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "completed_phases" in data

    def test_status(self) -> None:
        r = self._run("--status")
        assert r.returncode == 0

    def test_status_json(self) -> None:
        r = self._run("--status", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "overall_grade" in data

    def test_no_args(self) -> None:
        r = self._run()
        assert r.returncode != 0
