"""All baseline adapters must satisfy the BaselineAdapter Protocol contract.

Smoke test, not a correctness test — just confirms each adapter runs end-to-end
on a small scenario without raising and produces a populated SimulationTrace.
"""
from __future__ import annotations

import math

import pytest

from benchmarks.baselines._base import BaselineAdapter, make_adapter
from src.analytics.metrics import Evaluator
from src.analytics.types import SimulationTrace


_TINY_MANIFEST = {
    "id": "tiny_smoke",
    "duration_seconds": 10.0,
    "dt_seconds": 1.0,
    "airspace": {"bounds_m": {"x": [0, 100], "y": [0, 100], "z": [50, 100]}},
    "agents": {
        "count": 4,
        "kinematics": {"max_speed_m_s": 10.0, "max_accel_m_s2": 5.0, "turn_rate_deg_s": 30.0},
        "spawn_pattern": "two_streams",
    },
}


@pytest.mark.parametrize("method", ["orca", "vo", "cbs", "sdacs_hybrid"])
def test_adapter_runs_and_returns_trace(method):
    adapter = make_adapter(method, _TINY_MANIFEST, seed=0)
    assert isinstance(adapter, BaselineAdapter), \
        f"{method} adapter does not satisfy BaselineAdapter Protocol"

    trace = adapter.run(hard_wall_time_s=5.0)
    assert isinstance(trace, SimulationTrace)
    assert trace.method == method or trace.method == method.replace("_hybrid", "_hybrid")
    assert len(trace.agents) == _TINY_MANIFEST["agents"]["count"]
    # Every agent should have at least one position recorded
    assert all(len(a.positions) >= 1 for a in trace.agents)


@pytest.mark.parametrize("method", ["orca", "vo", "cbs", "sdacs_hybrid"])
def test_evaluator_consumes_trace(method):
    adapter = make_adapter(method, _TINY_MANIFEST, seed=0)
    trace = adapter.run(hard_wall_time_s=5.0)
    result = Evaluator().evaluate(trace)
    expected_keys = {"NMR", "MSD", "PE", "MS_s", "RTF"}
    assert expected_keys.issubset(set(result.keys()))
    # MSD should be a real number (or +inf if the adapter never put two
    # agents in proximity)
    assert isinstance(result["MSD"], float)
