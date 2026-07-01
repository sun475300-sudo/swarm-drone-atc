"""GENESIS Phase 391 -- 고교·일반인 체험판 테스트.

검증 항목:
- DifficultyPreset / GlossaryEntry / GuidedScenario / SimplifiedMetric / DemoExperience frozen
- DifficultyPreset __post_init__ 유효성 검증
- GuidedScenario __post_init__ 유효성 검증
- DIFFICULTY_PRESETS / GLOSSARY / GUIDED_SCENARIOS / SIMPLIFIED_METRICS 레지스트리 무결성
- get_preset / get_scenario / get_metric 조회 API
- search_glossary 키워드 검색
- list_presets / list_scenarios / list_metrics 목록
- build_experience / get_stats 전체 패키지
- CLI: --presets, --preset, --glossary, --search, --scenarios, --scenario, --metrics, --explain, --package, --stats, --json
"""
from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

from simulation.demo_experience import (
    DIFFICULTY_PRESETS,
    GLOSSARY,
    GUIDED_SCENARIOS,
    SIMPLIFIED_METRICS,
    VALID_PRESET_IDS,
    DemoExperience,
    DifficultyPreset,
    GlossaryEntry,
    GuidedScenario,
    SimplifiedMetric,
    build_experience,
    get_metric,
    get_preset,
    get_scenario,
    get_stats,
    list_metrics,
    list_presets,
    list_scenarios,
    search_glossary,
)


class TestDifficultyPreset:
    def test_frozen(self) -> None:
        p = DIFFICULTY_PRESETS[0]
        with pytest.raises(AttributeError):
            p.name = "mutated"  # type: ignore[misc]

    def test_fields(self) -> None:
        p = DIFFICULTY_PRESETS[0]
        assert p.preset_id == "easy"
        assert p.drone_count == 5
        assert isinstance(p.description, str)

    def test_as_dict(self) -> None:
        d = DIFFICULTY_PRESETS[0].as_dict()
        assert d["preset_id"] == "easy"
        text = json.dumps(d, ensure_ascii=False)
        assert isinstance(text, str)

    def test_invalid_preset_id_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid preset_id"):
            DifficultyPreset("invalid", "x", "x", 1, 1, 1.0, "x", "x")


class TestGlossaryEntry:
    def test_frozen(self) -> None:
        g = GLOSSARY[0]
        with pytest.raises(AttributeError):
            g.term = "mutated"  # type: ignore[misc]

    def test_fields(self) -> None:
        g = GLOSSARY[0]
        assert "APF" in g.term
        assert len(g.easy_name) > 0
        assert len(g.explanation) > 0
        assert len(g.example) > 0

    def test_as_dict(self) -> None:
        d = GLOSSARY[0].as_dict()
        assert "term" in d
        assert "easy_name" in d


class TestGuidedScenario:
    def test_frozen(self) -> None:
        s = GUIDED_SCENARIOS[0]
        with pytest.raises(AttributeError):
            s.title = "mutated"  # type: ignore[misc]

    def test_fields(self) -> None:
        s = GUIDED_SCENARIOS[0]
        assert s.scenario_id == 1
        assert isinstance(s.steps, tuple)
        assert len(s.steps) >= 1

    def test_as_dict(self) -> None:
        d = GUIDED_SCENARIOS[0].as_dict()
        assert isinstance(d["steps"], list)

    def test_invalid_scenario_id_raises(self) -> None:
        with pytest.raises(ValueError, match="scenario_id must be >= 1"):
            GuidedScenario(0, "x", "x", "x", ("step",), "easy", 5)

    def test_no_steps_raises(self) -> None:
        with pytest.raises(ValueError, match="At least 1 step"):
            GuidedScenario(1, "x", "x", "x", (), "easy", 5)

    def test_invalid_preset_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid preset_id"):
            GuidedScenario(1, "x", "x", "x", ("step",), "invalid", 5)


class TestSimplifiedMetric:
    def test_frozen(self) -> None:
        m = SIMPLIFIED_METRICS[0]
        with pytest.raises(AttributeError):
            m.display_name = "mutated"  # type: ignore[misc]

    def test_as_dict(self) -> None:
        d = SIMPLIFIED_METRICS[0].as_dict()
        assert "metric_id" in d
        assert "display_name" in d
        assert "good_direction" in d


class TestRegistries:
    def test_presets_count(self) -> None:
        assert len(DIFFICULTY_PRESETS) == 3

    def test_presets_is_tuple(self) -> None:
        assert isinstance(DIFFICULTY_PRESETS, tuple)

    def test_presets_unique_ids(self) -> None:
        ids = [p.preset_id for p in DIFFICULTY_PRESETS]
        assert len(ids) == len(set(ids))

    def test_glossary_count(self) -> None:
        assert len(GLOSSARY) == 12

    def test_glossary_is_tuple(self) -> None:
        assert isinstance(GLOSSARY, tuple)

    def test_glossary_unique_terms(self) -> None:
        terms = [g.term for g in GLOSSARY]
        assert len(terms) == len(set(terms))

    def test_scenarios_count(self) -> None:
        assert len(GUIDED_SCENARIOS) == 5

    def test_scenarios_is_tuple(self) -> None:
        assert isinstance(GUIDED_SCENARIOS, tuple)

    def test_scenarios_sequential_ids(self) -> None:
        for i, s in enumerate(GUIDED_SCENARIOS):
            assert s.scenario_id == i + 1

    def test_scenarios_valid_presets(self) -> None:
        for s in GUIDED_SCENARIOS:
            assert s.preset_id in VALID_PRESET_IDS

    def test_metrics_count(self) -> None:
        assert len(SIMPLIFIED_METRICS) == 6

    def test_metrics_unique_ids(self) -> None:
        ids = [m.metric_id for m in SIMPLIFIED_METRICS]
        assert len(ids) == len(set(ids))


class TestGetPreset:
    def test_valid(self) -> None:
        p = get_preset("easy")
        assert p.preset_id == "easy"

    def test_all_retrievable(self) -> None:
        for pid in VALID_PRESET_IDS:
            p = get_preset(pid)
            assert p.preset_id == pid

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown preset_id"):
            get_preset("nonexistent")


class TestGetScenario:
    def test_valid(self) -> None:
        s = get_scenario(1)
        assert s.scenario_id == 1

    def test_all_retrievable(self) -> None:
        for i in range(1, 6):
            s = get_scenario(i)
            assert s.scenario_id == i

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown scenario_id"):
            get_scenario(99)


class TestGetMetric:
    def test_valid(self) -> None:
        m = get_metric("collision_resolution_rate")
        assert m.metric_id == "collision_resolution_rate"

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown metric_id"):
            get_metric("nonexistent")


class TestSearchGlossary:
    def test_find_apf(self) -> None:
        results = search_glossary("APF")
        assert len(results) >= 1
        assert any("APF" in g.term for g in results)

    def test_find_by_easy_name(self) -> None:
        results = search_glossary("충돌")
        assert len(results) >= 1

    def test_find_by_explanation(self) -> None:
        results = search_glossary("자석")
        assert len(results) >= 1

    def test_no_results(self) -> None:
        results = search_glossary("존재하지않는용어xyz")
        assert len(results) == 0

    def test_case_insensitive(self) -> None:
        r1 = search_glossary("apf")
        r2 = search_glossary("APF")
        assert len(r1) == len(r2)


class TestListFunctions:
    def test_list_presets(self) -> None:
        data = list_presets()
        assert len(data) == 3
        assert all("preset_id" in d for d in data)

    def test_list_scenarios(self) -> None:
        data = list_scenarios()
        assert len(data) == 5
        assert all("scenario_id" in d for d in data)

    def test_list_metrics(self) -> None:
        data = list_metrics()
        assert len(data) == 6
        assert all("metric_id" in d for d in data)


class TestBuildExperience:
    def test_fields(self) -> None:
        exp = build_experience()
        assert exp.title == "SDACS 드론 관제 시뮬레이터 체험판"
        assert len(exp.presets) == 3
        assert len(exp.glossary) == 12
        assert len(exp.scenarios) == 5
        assert len(exp.metrics) == 6

    def test_frozen(self) -> None:
        exp = build_experience()
        with pytest.raises(AttributeError):
            exp.title = "mutated"  # type: ignore[misc]

    def test_as_dict(self) -> None:
        d = build_experience().as_dict()
        assert "title" in d
        assert "stats" in d
        assert len(d["presets"]) == 3
        text = json.dumps(d, ensure_ascii=False)
        assert isinstance(text, str)


class TestGetStats:
    def test_fields(self) -> None:
        stats = get_stats()
        assert stats["total_presets"] == 3
        assert stats["total_glossary_entries"] == 12
        assert stats["total_scenarios"] == 5
        assert stats["total_metrics"] == 6

    def test_difficulty_levels(self) -> None:
        stats = get_stats()
        assert stats["difficulty_levels"] == ["쉬움", "보통", "어려움"]

    def test_total_steps(self) -> None:
        stats = get_stats()
        assert stats["total_scenario_steps"] == 25

    def test_json_serializable(self) -> None:
        text = json.dumps(get_stats(), ensure_ascii=False)
        assert isinstance(text, str)


class TestCLI:
    REPO_ROOT = pathlib.Path(__file__).parent.parent
    SCRIPT = str(REPO_ROOT / "simulation" / "demo_experience.py")
    UTF8_ENV = {**os.environ, "PYTHONUTF8": "1"}

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, self.SCRIPT, *args],
            capture_output=True, encoding="utf-8", env=self.UTF8_ENV,
            timeout=30,
        )

    def test_presets(self) -> None:
        r = self._run("--presets")
        assert r.returncode == 0

    def test_presets_json(self) -> None:
        r = self._run("--presets", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert len(data) == 3

    def test_preset(self) -> None:
        r = self._run("--preset", "easy")
        assert r.returncode == 0

    def test_preset_json(self) -> None:
        r = self._run("--preset", "easy", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["preset_id"] == "easy"

    def test_preset_invalid(self) -> None:
        r = self._run("--preset", "nonexistent")
        assert r.returncode != 0

    def test_glossary(self) -> None:
        r = self._run("--glossary")
        assert r.returncode == 0

    def test_glossary_json(self) -> None:
        r = self._run("--glossary", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert len(data) == 12

    def test_search(self) -> None:
        r = self._run("--search", "APF")
        assert r.returncode == 0

    def test_search_json(self) -> None:
        r = self._run("--search", "APF", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert len(data) >= 1

    def test_scenarios(self) -> None:
        r = self._run("--scenarios")
        assert r.returncode == 0

    def test_scenarios_json(self) -> None:
        r = self._run("--scenarios", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert len(data) == 5

    def test_scenario(self) -> None:
        r = self._run("--scenario", "1")
        assert r.returncode == 0

    def test_scenario_json(self) -> None:
        r = self._run("--scenario", "1", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["scenario_id"] == 1

    def test_scenario_invalid(self) -> None:
        r = self._run("--scenario", "99")
        assert r.returncode != 0

    def test_metrics(self) -> None:
        r = self._run("--metrics")
        assert r.returncode == 0

    def test_metrics_json(self) -> None:
        r = self._run("--metrics", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert len(data) == 6

    def test_explain(self) -> None:
        r = self._run("--explain", "collision_resolution_rate")
        assert r.returncode == 0

    def test_explain_json(self) -> None:
        r = self._run("--explain", "collision_resolution_rate", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["metric_id"] == "collision_resolution_rate"

    def test_explain_invalid(self) -> None:
        r = self._run("--explain", "nonexistent")
        assert r.returncode != 0

    def test_package(self) -> None:
        r = self._run("--package")
        assert r.returncode == 0

    def test_package_json(self) -> None:
        r = self._run("--package", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "title" in data

    def test_stats(self) -> None:
        r = self._run("--stats")
        assert r.returncode == 0

    def test_stats_json(self) -> None:
        r = self._run("--stats", "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["total_presets"] == 3

    def test_no_args(self) -> None:
        r = self._run()
        assert r.returncode != 0
