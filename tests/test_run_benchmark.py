"""Tests for scripts/run_benchmark.py (P706 cross-method benchmark runner)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from scripts.run_benchmark import (  # noqa: E402
    _extract_summary,
    _load_adapter_class,
    _load_manifest,
    _run_one,
    _setup_ablations,
    _write_csv,
    ALL_SCENARIOS,
    ALL_METHODS,
    build_parser,
    main,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

def _first_scenario() -> str:
    return sorted(ALL_SCENARIOS)[0]


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

class TestLoadAdapterClass:
    def test_loads_orca(self):
        cls = _load_adapter_class("orca")
        assert cls.name == "orca"

    def test_loads_sdacs_hybrid_via_alias(self):
        cls = _load_adapter_class("sdacs_hybrid")
        assert cls.name == "sdacs_hybrid"

    def test_loads_vo(self):
        cls = _load_adapter_class("vo")
        assert cls.name == "vo"

    def test_loads_cbs(self):
        cls = _load_adapter_class("cbs")
        assert cls.name == "cbs"

    def test_unknown_method_raises(self):
        with pytest.raises(RuntimeError, match="Cannot load adapter"):
            _load_adapter_class("nonexistent_method_xyz")


class TestLoadManifest:
    def test_loads_first_scenario(self):
        manifest = _load_manifest(_first_scenario())
        assert "id" in manifest
        assert "duration_seconds" in manifest

    def test_unknown_scenario_raises(self):
        with pytest.raises(FileNotFoundError):
            _load_manifest("nonexistent_scenario_xyz")


class TestExtractSummary:
    def _minimal_trace(self, n_agents: int = 2) -> dict:
        return {
            "scenario_id": "test_scenario",
            "method": "orca",
            "seed": 0,
            "horizon_seconds": 60.0,
            "dt_s": 1.0,
            "wall_clock_seconds": 0.1,
            "agents": [
                {"agent_id": f"drone_{i:02d}", "positions": [[0.0, 0.0, 100.0]], "goal_reached_at_s": 30.0, "spawn_time_s": 0.0}
                for i in range(n_agents)
            ],
            "tick_latencies_ms": [1.0, 2.0, 1.5],
        }

    def test_goal_rate_all_reached(self):
        summary = _extract_summary(self._minimal_trace(4))
        assert summary["goal_rate"] == 1.0
        assert summary["goals_reached"] == 4

    def test_goal_rate_none_reached(self):
        trace = self._minimal_trace(2)
        for a in trace["agents"]:
            a["goal_reached_at_s"] = None
        summary = _extract_summary(trace)
        assert summary["goal_rate"] == 0.0

    def test_avg_tick_ms(self):
        trace = self._minimal_trace()
        trace["tick_latencies_ms"] = [2.0, 4.0]
        summary = _extract_summary(trace)
        assert summary["avg_tick_ms"] == pytest.approx(3.0)

    def test_rid_cr_computed(self):
        trace = self._minimal_trace(2)
        trace["remote_id_valid_seconds_per_agent"] = {"drone_00": 60.0, "drone_01": 60.0}
        summary = _extract_summary(trace)
        assert summary["rid_cr"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Integration smoke tests
# ---------------------------------------------------------------------------

class TestRunOne:
    def test_orca_single_run(self, tmp_path: Path):
        result = _run_one(_first_scenario(), "orca", 0, tmp_path, wall_limit_s=60.0)
        assert result["status"] in ("ok", "cached")
        assert result["n_agents"] > 0

    def test_sdacs_hybrid_single_run(self, tmp_path: Path):
        result = _run_one(_first_scenario(), "sdacs_hybrid", 0, tmp_path, wall_limit_s=60.0)
        assert result["status"] in ("ok", "cached")

    def test_writes_json(self, tmp_path: Path):
        _run_one(_first_scenario(), "orca", 0, tmp_path, wall_limit_s=60.0)
        json_files = list(tmp_path.glob("*.json"))
        assert len(json_files) == 1
        with open(json_files[0]) as f:
            data = json.load(f)
        assert "agents" in data

    def test_resumes_from_cache(self, tmp_path: Path):
        _run_one(_first_scenario(), "orca", 0, tmp_path, wall_limit_s=60.0)
        result2 = _run_one(_first_scenario(), "orca", 0, tmp_path, wall_limit_s=60.0)
        assert result2["status"] == "cached"


class TestSetupAblations:
    def test_no_reactive_registered(self):
        extra = _setup_ablations(["no_reactive"])
        assert "sdacs_no_reactive" in extra

    def test_no_global_registered(self):
        extra = _setup_ablations(["no_global"])
        assert "sdacs_no_global" in extra

    def test_no_regulatory_registered(self):
        extra = _setup_ablations(["no_regulatory"])
        assert "sdacs_no_regulatory" in extra

    def test_unknown_ablation_skipped(self, capsys):
        extra = _setup_ablations(["invalid_ablation_xyz"])
        assert extra == []


class TestWriteCsv:
    def test_creates_csv(self, tmp_path: Path):
        rows = [{"status": "ok", "scenario": "s1", "method": "orca", "seed": 0, "goal_rate": 1.0}]
        out = tmp_path / "out.csv"
        _write_csv(rows, out)
        assert out.exists()
        content = out.read_text()
        assert "scenario" in content
        assert "orca" in content


class TestCLI:
    def test_dry_run(self):
        ret = main(["--dry-run", "--scenarios", _first_scenario(),
                    "--methods", "orca", "--seeds", "0"])
        assert ret == 0

    def test_full_run_single(self, tmp_path: Path):
        ret = main([
            "--scenarios", _first_scenario(),
            "--methods", "orca",
            "--seeds", "0",
            "--out-dir", str(tmp_path / "runs"),
            "--csv", str(tmp_path / "out.csv"),
            "--jobs", "1",
            "--wall-limit", "30",
        ])
        assert ret == 0
        assert (tmp_path / "out.csv").exists()

    def test_parser_defaults(self):
        p = build_parser()
        args = p.parse_args([])
        assert set(args.methods) == set(ALL_METHODS)
        assert args.seeds == list(range(5))
        assert args.ablation == []
