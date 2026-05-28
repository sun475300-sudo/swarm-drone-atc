"""Unit tests for :mod:`src.analytics.metrics`.

Each metric gets a happy-path test plus an edge case (empty/single-agent/
horizon-zero/etc.). All tests use synthetic ``SimulationTrace`` objects;
none of them touch the actual simulator.
"""
from __future__ import annotations

import math

import pytest

from src.analytics.metrics import (
    Evaluator,
    EvaluatorConfig,
    airspace_utilization,
    flowtime,
    geofence_violation_count,
    laanc_authorization_latency_ms,
    makespan,
    memory_peak_mb,
    minimum_separation_distance,
    near_miss_rate,
    path_efficiency,
    per_tick_latency_percentiles,
    real_time_factor,
    remote_id_compliance_rate,
    time_to_conflict_distribution,
    voronoi_cell_metrics,
)
from src.analytics.types import (
    AgentTrajectory,
    AirspaceCapacity,
    NearMissEvent,
    SimulationTrace,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_two_agent_straight_trace(
    horizon: float = 10.0,
    dt: float = 1.0,
    separation: float = 10.0,
) -> SimulationTrace:
    """Two agents flying parallel straight lines, ``separation`` m apart."""
    n_steps = int(round(horizon / dt))
    a = AgentTrajectory(
        agent_id="a",
        positions=[(float(t), 0.0, 0.0) for t in range(n_steps)],
        goal_reached_at_s=horizon - 1,
    )
    b = AgentTrajectory(
        agent_id="b",
        positions=[(float(t), separation, 0.0) for t in range(n_steps)],
        goal_reached_at_s=horizon - 1,
    )
    return SimulationTrace(
        scenario_id="straight_parallel",
        method="test",
        seed=0,
        horizon_seconds=horizon,
        dt_s=dt,
        wall_clock_seconds=2.0,
        agents=[a, b],
        remote_id_valid_seconds_per_agent={"a": int(horizon), "b": int(horizon)},
        laanc_request_latencies_ms=[100.0, 110.0],
        tick_latencies_ms=[5.0, 6.0, 7.0, 8.0, 9.0, 10.0],
        peak_memory_mb=512.0,
    )


def _make_collision_trace() -> SimulationTrace:
    """Two agents converging into the safety buffer mid-run, then separating."""
    # Step 0..5: distance shrinks from 10 to 0; step 6..10: grows back to 10.
    a = AgentTrajectory(
        agent_id="a",
        positions=[(float(t), 0.0, 0.0) for t in range(11)],
    )
    b = AgentTrajectory(
        agent_id="b",
        positions=[(float(t), max(0.0, 10.0 - 2.0 * t) if t <= 5 else 2.0 * (t - 5), 0.0)
                   for t in range(11)],
    )
    return SimulationTrace(
        scenario_id="head_on_then_recover",
        horizon_seconds=11.0,
        dt_s=1.0,
        wall_clock_seconds=2.0,
        agents=[a, b],
    )


# ---------------------------------------------------------------------------
# Safety
# ---------------------------------------------------------------------------


class TestNearMissRate:
    def test_no_conflict_returns_zero(self) -> None:
        trace = _make_two_agent_straight_trace(separation=20.0)
        assert near_miss_rate(trace) == 0.0

    def test_collision_counts_at_least_one_event(self) -> None:
        trace = _make_collision_trace()
        nmr = near_miss_rate(trace, d_safe=5.0)
        # 1 pair, 11 seconds, ≥ 1 event
        assert nmr >= 1.0 / (1 * 11.0) - 1e-9

    def test_single_agent_returns_zero(self) -> None:
        agent = AgentTrajectory(agent_id="solo", positions=[(0.0, 0.0, 0.0)])
        trace = SimulationTrace(horizon_seconds=10.0, agents=[agent])
        assert near_miss_rate(trace) == 0.0


class TestMSD:
    def test_known_minimum(self) -> None:
        trace = _make_two_agent_straight_trace(separation=7.0)
        assert minimum_separation_distance(trace) == pytest.approx(7.0, rel=1e-6)

    def test_no_agents_returns_inf(self) -> None:
        trace = SimulationTrace(horizon_seconds=10.0)
        assert math.isinf(minimum_separation_distance(trace))


class TestTTC:
    def test_distribution_summary(self) -> None:
        trace = SimulationTrace(
            horizon_seconds=10.0,
            predicted_conflicts=[
                NearMissEvent("a", "b", 1.0, 30.0, 4.0),
                NearMissEvent("a", "c", 2.0, 60.0, 3.5),
                NearMissEvent("b", "c", 3.0, 90.0, 2.0),
            ],
        )
        ttc = time_to_conflict_distribution(trace)
        assert ttc["mean_s"] == pytest.approx(60.0)
        assert ttc["median_s"] == pytest.approx(60.0)

    def test_no_predictions_returns_nan(self) -> None:
        trace = SimulationTrace()
        ttc = time_to_conflict_distribution(trace)
        assert all(math.isnan(v) for v in ttc.values())


# ---------------------------------------------------------------------------
# Efficiency
# ---------------------------------------------------------------------------


class TestPathEfficiency:
    def test_perfect_straight_line(self) -> None:
        agent = AgentTrajectory(
            agent_id="a",
            positions=[(0.0, 0.0, 0.0), (5.0, 0.0, 0.0), (10.0, 0.0, 0.0)],
        )
        trace = SimulationTrace(horizon_seconds=10.0, agents=[agent])
        assert path_efficiency(trace) == pytest.approx(1.0)

    def test_detour_returns_less_than_one(self) -> None:
        agent = AgentTrajectory(
            agent_id="a",
            positions=[(0.0, 0.0, 0.0), (5.0, 5.0, 0.0), (10.0, 0.0, 0.0)],
        )
        trace = SimulationTrace(horizon_seconds=10.0, agents=[agent])
        assert path_efficiency(trace) < 1.0


class TestMakespan:
    def test_uses_max_arrival(self) -> None:
        agents = [
            AgentTrajectory("a", [(0.0, 0.0, 0.0)], goal_reached_at_s=4.0),
            AgentTrajectory("b", [(0.0, 0.0, 0.0)], goal_reached_at_s=7.0),
        ]
        trace = SimulationTrace(horizon_seconds=10.0, agents=agents)
        assert makespan(trace) == pytest.approx(7.0)

    def test_unfinished_uses_horizon(self) -> None:
        agents = [
            AgentTrajectory("a", [(0.0, 0.0, 0.0)], goal_reached_at_s=4.0),
            AgentTrajectory("b", [(0.0, 0.0, 0.0)], goal_reached_at_s=None),
        ]
        trace = SimulationTrace(horizon_seconds=10.0, agents=agents)
        assert makespan(trace) == pytest.approx(10.0)


class TestFlowtime:
    def test_sums_finite(self) -> None:
        agents = [
            AgentTrajectory("a", [(0.0, 0.0, 0.0)], goal_reached_at_s=4.0),
            AgentTrajectory("b", [(0.0, 0.0, 0.0)], goal_reached_at_s=6.0),
        ]
        trace = SimulationTrace(horizon_seconds=10.0, agents=agents)
        assert flowtime(trace) == pytest.approx(10.0)


# ---------------------------------------------------------------------------
# Airspace utilization
# ---------------------------------------------------------------------------


class TestAirspaceUtilization:
    def test_full_utilization_with_explicit_capacity(self) -> None:
        trace = _make_two_agent_straight_trace(horizon=4.0, dt=1.0)
        au = airspace_utilization(trace, capacity=AirspaceCapacity(max_agents=2))
        assert au == pytest.approx(1.0)

    def test_half_utilization(self) -> None:
        trace = _make_two_agent_straight_trace(horizon=4.0, dt=1.0)
        au = airspace_utilization(trace, capacity=AirspaceCapacity(max_agents=4))
        assert au == pytest.approx(0.5)

    def test_no_agents_returns_zero(self) -> None:
        trace = SimulationTrace(horizon_seconds=10.0)
        assert airspace_utilization(trace) == 0.0


class TestVoronoi:
    def test_handoffs_counted(self) -> None:
        trace = SimulationTrace(
            horizon_seconds=4.0,
            voronoi_assignments=[
                {"a": 1, "b": 2},
                {"a": 1, "b": 2},
                {"a": 2, "b": 2},  # a moved to cell 2
                {"a": 2, "b": 1},  # b moved to cell 1
            ],
        )
        m = voronoi_cell_metrics(trace)
        assert m["handoff_rate"] == pytest.approx(2 / 4.0)


# ---------------------------------------------------------------------------
# Regulatory
# ---------------------------------------------------------------------------


class TestRegulatory:
    def test_full_compliance(self) -> None:
        trace = _make_two_agent_straight_trace(horizon=10.0)
        # default fixture sets remote_id_valid_seconds_per_agent = horizon for each
        assert remote_id_compliance_rate(trace) == pytest.approx(1.0)

    def test_partial_compliance(self) -> None:
        trace = _make_two_agent_straight_trace(horizon=10.0)
        # Override
        trace = SimulationTrace(
            horizon_seconds=trace.horizon_seconds,
            agents=trace.agents,
            remote_id_valid_seconds_per_agent={"a": 5, "b": 10},
        )
        assert remote_id_compliance_rate(trace) == pytest.approx(15 / 20)

    def test_geofence_violations(self) -> None:
        trace = SimulationTrace(geofence_violation_timestamps=[1.0, 2.0, 3.0])
        assert geofence_violation_count(trace) == 3

    def test_laanc_latency_mean(self) -> None:
        trace = _make_two_agent_straight_trace()
        assert laanc_authorization_latency_ms(trace) == pytest.approx(105.0)

    def test_laanc_no_data_returns_nan(self) -> None:
        trace = SimulationTrace()
        assert math.isnan(laanc_authorization_latency_ms(trace))


# ---------------------------------------------------------------------------
# Computational
# ---------------------------------------------------------------------------


class TestComputational:
    def test_rtf(self) -> None:
        trace = _make_two_agent_straight_trace(horizon=10.0)
        # horizon 10 s / wall 2 s = 5
        assert real_time_factor(trace) == pytest.approx(5.0)

    def test_rtf_zero_wall_returns_nan(self) -> None:
        trace = SimulationTrace(horizon_seconds=10.0, wall_clock_seconds=0.0)
        assert math.isnan(real_time_factor(trace))

    def test_per_tick_percentiles(self) -> None:
        trace = _make_two_agent_straight_trace()
        p = per_tick_latency_percentiles(trace)
        assert p["p50_ms"] == pytest.approx(7.5)
        assert p["p95_ms"] >= p["p50_ms"]

    def test_memory_peak_passthrough(self) -> None:
        trace = _make_two_agent_straight_trace()
        assert memory_peak_mb(trace) == pytest.approx(512.0)


# ---------------------------------------------------------------------------
# Evaluator façade
# ---------------------------------------------------------------------------


class TestEvaluator:
    def test_returns_flat_dict_with_all_keys(self) -> None:
        ev = Evaluator(EvaluatorConfig(d_safe_m=5.0,
                                       capacity=AirspaceCapacity(max_agents=2)))
        result = ev.evaluate(_make_two_agent_straight_trace())
        expected_keys = {
            "NMR", "MSD", "TTC_mean_s", "TTC_median_s", "TTC_p5_s", "TTC_p95_s",
            "PE", "MS_s", "FT_drone_s", "AU", "VCU_mean_occupancy", "VCU_handoff_rate",
            "RID_CR", "LAANC_latency_ms", "geofence_violations",
            "RTF", "tick_p50_ms", "tick_p95_ms", "tick_p99_ms", "peak_memory_mb",
        }
        assert set(result.keys()) == expected_keys

    def test_json_round_trip(self) -> None:
        original = _make_two_agent_straight_trace()
        roundtrip = SimulationTrace.from_dict(original.to_dict())
        assert Evaluator().evaluate(original) == Evaluator().evaluate(roundtrip)


# ---------------------------------------------------------------------------
# Edge cases — boost coverage for early-return paths and private helpers
# ---------------------------------------------------------------------------

import numpy as np  # noqa: E402

from src.analytics.metrics import _has_separated_since, _main  # noqa: E402


class TestEdgeCases:
    # --- near_miss_rate ---

    def test_nmr_zero_horizon_returns_zero(self) -> None:
        a = AgentTrajectory("a", [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)])
        b = AgentTrajectory("b", [(0.0, 1.0, 0.0), (1.0, 1.0, 0.0)])
        trace = SimulationTrace(horizon_seconds=0.0, dt_s=1.0, agents=[a, b])
        assert near_miss_rate(trace) == 0.0

    # --- minimum_separation_distance ---

    def test_msd_zero_horizon_returns_inf(self) -> None:
        a = AgentTrajectory("a", [(0.0, 0.0, 0.0)])
        b = AgentTrajectory("b", [(1.0, 0.0, 0.0)])
        trace = SimulationTrace(horizon_seconds=0.0, dt_s=1.0, agents=[a, b])
        assert math.isinf(minimum_separation_distance(trace))

    def test_msd_one_agent_no_positions_returns_inf(self) -> None:
        a = AgentTrajectory("a", [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)])
        b = AgentTrajectory("b", positions=[])
        trace = SimulationTrace(horizon_seconds=10.0, dt_s=1.0, agents=[a, b])
        assert math.isinf(minimum_separation_distance(trace))

    # --- path_efficiency ---

    def test_path_efficiency_single_position_agent_skipped(self) -> None:
        agent = AgentTrajectory("a", positions=[(0.0, 0.0, 0.0)])
        trace = SimulationTrace(horizon_seconds=10.0, agents=[agent])
        assert path_efficiency(trace) == 0.0

    def test_path_efficiency_stationary_agent_skipped(self) -> None:
        agent = AgentTrajectory("a", positions=[(0.0, 0.0, 0.0)] * 5)
        trace = SimulationTrace(horizon_seconds=10.0, agents=[agent])
        assert path_efficiency(trace) == 0.0

    # --- makespan ---

    def test_makespan_no_agents_returns_zero(self) -> None:
        trace = SimulationTrace(horizon_seconds=10.0, agents=[])
        assert makespan(trace) == 0.0

    # --- airspace_utilization ---

    def test_airspace_util_zero_horizon_returns_zero(self) -> None:
        a = AgentTrajectory("a", [(0.0, 0.0, 0.0)])
        trace = SimulationTrace(horizon_seconds=0.0, dt_s=1.0, agents=[a])
        assert airspace_utilization(trace) == 0.0

    def test_airspace_util_zero_capacity_returns_zero(self) -> None:
        trace = _make_two_agent_straight_trace(horizon=4.0)
        result = airspace_utilization(trace, capacity=AirspaceCapacity(max_agents=0))
        assert result == 0.0

    # --- voronoi_cell_metrics ---

    def test_voronoi_empty_step_assignment_skipped(self) -> None:
        trace = SimulationTrace(
            horizon_seconds=4.0,
            voronoi_assignments=[{}, {"a": 1}],
        )
        m = voronoi_cell_metrics(trace)
        assert math.isfinite(m["handoff_rate"])

    # --- remote_id_compliance_rate ---

    def test_remote_id_no_agents_returns_zero(self) -> None:
        trace = SimulationTrace(horizon_seconds=10.0, agents=[])
        assert remote_id_compliance_rate(trace) == 0.0

    def test_remote_id_tiny_horizon_rounds_to_zero(self) -> None:
        a = AgentTrajectory("a", positions=[(0.0, 0.0, 0.0)])
        trace = SimulationTrace(
            horizon_seconds=0.4,
            agents=[a],
            remote_id_valid_seconds_per_agent={"a": 1},
        )
        assert remote_id_compliance_rate(trace) == 0.0

    # --- per_tick_latency_percentiles ---

    def test_per_tick_no_data_returns_nan(self) -> None:
        trace = SimulationTrace()
        p = per_tick_latency_percentiles(trace)
        assert all(math.isnan(v) for v in p.values())


# ---------------------------------------------------------------------------
# _has_separated_since (lines 508-522)
# ---------------------------------------------------------------------------


class TestHasSeparatedSince:
    def test_negative_last_event_returns_true(self) -> None:
        far = np.array([False, False, False])
        assert _has_separated_since(far, -1, 2, 2) is True

    def test_current_le_last_returns_true(self) -> None:
        far = np.array([True, True, True])
        assert _has_separated_since(far, 3, 3, 2) is True

    def test_sufficient_consecutive_returns_true(self) -> None:
        far = np.array([False, True, True, True, False])
        assert _has_separated_since(far, 0, 4, 3) is True

    def test_insufficient_consecutive_returns_false(self) -> None:
        far = np.array([False, True, True, False, True])
        assert _has_separated_since(far, 0, 4, 3) is False

    def test_alternating_never_enough_returns_false(self) -> None:
        far = np.array([False, True, False, True, False])
        assert _has_separated_since(far, 0, 4, 2) is False

    def test_empty_window_returns_false(self) -> None:
        far = np.array([False, False])
        # window = far[2:3] — but last=1, current=2, window=[False] → run=0 → False
        assert _has_separated_since(far, 1, 2, 2) is False


# ---------------------------------------------------------------------------
# _main() CLI entry point (lines 532-559)
# ---------------------------------------------------------------------------


class TestMainCLI:
    def test_main_writes_to_stdout(self, tmp_path, capsys) -> None:
        import json

        trace = _make_two_agent_straight_trace()
        trace_file = tmp_path / "trace.json"
        trace_file.write_text(json.dumps(trace.to_dict()), encoding="utf-8")

        rc = _main([str(trace_file)])
        assert rc == 0
        out = capsys.readouterr().out
        data = json.loads(out)
        assert "NMR" in data
        assert "MSD" in data

    def test_main_writes_to_output_file(self, tmp_path) -> None:
        import json

        trace = _make_two_agent_straight_trace()
        trace_file = tmp_path / "trace.json"
        result_file = tmp_path / "result.json"
        trace_file.write_text(json.dumps(trace.to_dict()), encoding="utf-8")

        rc = _main([str(trace_file), "--output", str(result_file)])
        assert rc == 0
        data = json.loads(result_file.read_text(encoding="utf-8"))
        assert "PE" in data
