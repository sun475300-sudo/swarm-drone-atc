"""Tests for scripts/compare_baselines.py (P706)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def minimal_trace_dict():
    """Minimal SimulationTrace dict sufficient for _dict_to_trace."""
    return {
        "scenario_id": "01_corridor_crossing",
        "method": "orca",
        "seed": 42,
        "horizon_seconds": 60.0,
        "dt_s": 1.0,
        "wall_clock_seconds": 0.5,
        "agents": [
            {
                "agent_id": "d0",
                "positions": [[0.0, 0.0, 50.0], [1.0, 0.0, 50.0]],
                "goal_reached_at_s": 55.0,
                "spawn_time_s": 0.0,
            },
            {
                "agent_id": "d1",
                "positions": [[10.0, 0.0, 50.0], [9.0, 0.0, 50.0]],
                "goal_reached_at_s": None,
                "spawn_time_s": 0.0,
            },
        ],
        "predicted_conflicts": [],
        "voronoi_assignments": [],
        "remote_id_valid_seconds_per_agent": {"d0": 60, "d1": 60},
        "laanc_request_latencies_ms": [120.0, 130.0],
        "geofence_violation_timestamps": [],
        "tick_latencies_ms": [1.0, 2.0, 1.5],
        "peak_memory_mb": None,
    }


# ---------------------------------------------------------------------------
# Tests for _dict_to_trace
# ---------------------------------------------------------------------------


def test_dict_to_trace_round_trip(minimal_trace_dict):
    """_dict_to_trace must reconstruct a valid SimulationTrace."""
    from compare_baselines import _dict_to_trace

    trace = _dict_to_trace(minimal_trace_dict)
    assert trace.scenario_id == "01_corridor_crossing"
    assert trace.method == "orca"
    assert trace.seed == 42
    assert len(trace.agents) == 2
    assert trace.agents[0].agent_id == "d0"
    assert trace.agents[0].goal_reached_at_s == pytest.approx(55.0)
    assert trace.agents[1].goal_reached_at_s is None


def test_dict_to_trace_positions_are_tuples(minimal_trace_dict):
    """Positions must be tuples (not lists) for metrics functions."""
    from compare_baselines import _dict_to_trace

    trace = _dict_to_trace(minimal_trace_dict)
    for agent in trace.agents:
        for pos in agent.positions:
            assert isinstance(pos, tuple), f"expected tuple, got {type(pos)}"
            assert len(pos) == 3


# ---------------------------------------------------------------------------
# Tests for _aggregate
# ---------------------------------------------------------------------------


def test_aggregate_single_run():
    """_aggregate must handle a single run without crashing."""
    from compare_baselines import METRIC_KEYS, _aggregate

    row = {
        "scenario": "01_corridor_crossing",
        "method": "orca",
        "seed": 42,
        "NMR": 0.001,
        "PE": 0.95,
        "AU": 0.4,
        "RID_CR": 0.0,
        "LAANC_latency_ms": float("nan"),
        "geofence_violations": 0.0,
        "tick_p99_ms": 5.0,
    }
    agg = _aggregate([row])
    assert "01_corridor_crossing" in agg
    assert "orca" in agg["01_corridor_crossing"]
    assert agg["01_corridor_crossing"]["orca"]["NMR"] == pytest.approx(0.001)


def test_aggregate_multiple_seeds():
    """_aggregate must average across seeds."""
    from compare_baselines import _aggregate

    rows = [
        {"scenario": "s1", "method": "orca", "seed": 0, "NMR": 0.0, "PE": 1.0,
         "AU": 0.5, "RID_CR": 0.0, "LAANC_latency_ms": float("nan"),
         "geofence_violations": 0.0, "tick_p99_ms": 1.0},
        {"scenario": "s1", "method": "orca", "seed": 1, "NMR": 0.2, "PE": 0.8,
         "AU": 0.6, "RID_CR": 0.0, "LAANC_latency_ms": float("nan"),
         "geofence_violations": 0.0, "tick_p99_ms": 3.0},
    ]
    agg = _aggregate(rows)
    assert agg["s1"]["orca"]["NMR"] == pytest.approx(0.1)
    assert agg["s1"]["orca"]["PE"] == pytest.approx(0.9)


# ---------------------------------------------------------------------------
# Tests for _write_markdown and _write_csv
# ---------------------------------------------------------------------------


def test_write_markdown_creates_file(tmp_path):
    """_write_markdown must create a non-empty .md file."""
    from compare_baselines import _aggregate, _write_markdown

    rows = [
        {"scenario": "01_corridor_crossing", "method": "orca", "seed": 42,
         "NMR": 0.001, "PE": 0.95, "AU": 0.4, "RID_CR": 0.0,
         "LAANC_latency_ms": float("nan"), "geofence_violations": 0.0, "tick_p99_ms": 2.0},
    ]
    agg = _aggregate(rows)
    out = tmp_path / "table.md"
    _write_markdown(agg, out, ["01_corridor_crossing"], seeds=1)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "P706" in content
    assert "orca" in content
    assert "NMR" in content


def test_write_csv_creates_file(tmp_path):
    """_write_csv must create a CSV with the expected header."""
    from compare_baselines import _write_csv

    rows = [
        {"scenario": "01_corridor_crossing", "method": "orca", "seed": 42,
         "NMR": 0.001, "PE": 0.95, "AU": 0.4, "RID_CR": 0.0,
         "LAANC_latency_ms": float("nan"), "geofence_violations": 0.0, "tick_p99_ms": 2.0},
    ]
    out = tmp_path / "table.csv"
    _write_csv(rows, out)
    assert out.exists()
    header = out.read_text(encoding="utf-8").splitlines()[0]
    assert "scenario" in header
    assert "method" in header
    assert "NMR" in header


# ---------------------------------------------------------------------------
# Integration: quick CLI smoke test
# ---------------------------------------------------------------------------


def test_compare_baselines_quick(tmp_path):
    """Full quick sweep must produce output files in <2 minutes."""
    from compare_baselines import main

    out_dir = tmp_path / "comparison"
    ret = main([
        "--quick",
        "--workers", "2",
        "--out", str(out_dir),
        "--scenarios", "01_corridor_crossing",
        "--methods", "orca",
    ])
    assert ret == 0

    results_dir = REPO_ROOT / "results"
    md = results_dir / "comparison_table.md"
    csv_ = results_dir / "comparison_table.csv"
    assert md.exists(), "comparison_table.md was not created"
    assert csv_.exists(), "comparison_table.csv was not created"
