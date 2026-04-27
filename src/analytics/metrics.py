"""SDACS Evaluation Metrics — Phase 705.

Implements every metric defined in ``docs/paper/EVALUATION_METRICS.md``.

Design rules (mirror the spec):

* One metric, one function. No hidden state.
* Sign-consistent: higher = better unless the function name ends in ``_lower_better``.
* Pure NumPy; no I/O, no logging side-effects.
* All inputs are immutable :class:`SimulationTrace` instances (see :mod:`.types`).
* All functions return ``float``/``int``/``dict`` — never NumPy scalars (cast at the boundary).

Usage::

    from src.analytics.metrics import Evaluator
    result = Evaluator().evaluate(trace)
    # -> {"NMR": 1.2e-4, "MSD": 4.8, "PE": 0.93, ...}

CLI::

    python -m src.analytics.metrics path/to/trace.json --output result.json
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

import math

import numpy as np

from .types import (
    AgentTrajectory,
    AirspaceCapacity,
    NearMissEvent,
    SimulationTrace,
)


# =============================================================================
# 1. Safety metrics (Section 1 of EVALUATION_METRICS.md)
# =============================================================================


def near_miss_rate(
    trace: SimulationTrace,
    d_safe: float = 5.0,
    deduplication_separation_factor: float = 2.0,
    deduplication_min_separation_seconds: float = 2.0,
) -> float:
    """Near-Miss Rate (NMR) — events per (drone-pair · second).

    A near-miss between drones *i* and *j* at time *t* occurs when
    ``‖x_i(t) - x_j(t)‖₂ < d_safe``. A pair stays "in conflict" until they
    have separated by ``≥ d_safe * deduplication_separation_factor`` for at
    least ``deduplication_min_separation_seconds`` seconds, after which a
    new event can be counted.

    Args:
        trace: Immutable simulation trace.
        d_safe: Safety buffer in meters. Default 5 m per spec.
        deduplication_separation_factor: Multiplier on ``d_safe`` defining
            "fully separated" again. Default 2.0.
        deduplication_min_separation_seconds: How long the pair must stay
            separated before a new event can fire. Default 2.0 s.

    Returns:
        events / (pair-second). Lower is better. ``0.0`` is ideal.

    Notes:
        Spec: ``EVALUATION_METRICS.md §1.1``.
    """
    n_agents = len(trace.agents)
    if n_agents < 2:
        return 0.0
    horizon_s = trace.horizon_seconds
    if horizon_s <= 0:
        return 0.0

    n_pairs = n_agents * (n_agents - 1) // 2
    events = _count_near_miss_events(
        trace,
        d_safe=d_safe,
        sep_factor=deduplication_separation_factor,
        sep_seconds=deduplication_min_separation_seconds,
    )
    denom = n_pairs * horizon_s
    return float(events) / float(denom)


def minimum_separation_distance(trace: SimulationTrace) -> float:
    """Minimum Separation Distance (MSD) — meters. Higher is better.

    Returns the min over all pairs and all time of the Euclidean distance.
    If the trace has fewer than 2 agents the function returns ``math.inf``
    (no separation defined).

    Spec: ``EVALUATION_METRICS.md §1.2``.
    """
    if len(trace.agents) < 2:
        return float("inf")
    positions, valid = _stack_positions(trace)  # (T, N, 3)
    if positions.shape[0] == 0:
        return float("inf")

    msd = float("inf")
    n = positions.shape[1]
    for i in range(n):
        for j in range(i + 1, n):
            both_valid = valid[:, i] & valid[:, j]
            if not both_valid.any():
                continue
            diffs = positions[both_valid, i, :] - positions[both_valid, j, :]
            d = np.linalg.norm(diffs, axis=1)
            local_min = float(d.min())
            if local_min < msd:
                msd = local_min
    return msd


def time_to_conflict_distribution(
    trace: SimulationTrace,
) -> Dict[str, float]:
    """Time-to-Conflict (TTC) distribution from CPA-predicted events.

    Walks ``trace.predicted_conflicts`` (CPA lookahead output stored at
    prediction time) and returns mean / median / p5 / p95 of the
    ``lead_time_s`` field. Returns NaNs if no predictions present.

    Spec: ``EVALUATION_METRICS.md §1.3``.
    """
    if not trace.predicted_conflicts:
        return {"mean_s": math.nan, "median_s": math.nan, "p5_s": math.nan, "p95_s": math.nan}
    lead = np.fromiter(
        (c.lead_time_s for c in trace.predicted_conflicts), dtype=float
    )
    return {
        "mean_s": float(lead.mean()),
        "median_s": float(np.median(lead)),
        "p5_s": float(np.percentile(lead, 5)),
        "p95_s": float(np.percentile(lead, 95)),
    }


# =============================================================================
# 2. Efficiency metrics
# =============================================================================


def path_efficiency(trace: SimulationTrace) -> float:
    """Mean Path Efficiency (PE) over all agents — dimensionless in (0, 1].

    For each agent ``i``::

        PE_i = ‖x_i(T_end) - x_i(T_start)‖₂  /  ∫ ‖dx_i/dt‖₂ dt

    Returns mean over all agents that recorded ≥ 2 positions.
    1.0 = perfect straight line. Higher is better.

    Spec: ``EVALUATION_METRICS.md §2.1``.
    """
    pes: List[float] = []
    for agent in trace.agents:
        if len(agent.positions) < 2:
            continue
        pos = np.asarray(agent.positions, dtype=float)
        straight_line = float(np.linalg.norm(pos[-1] - pos[0]))
        deltas = np.linalg.norm(np.diff(pos, axis=0), axis=1)
        path_length = float(deltas.sum())
        if path_length <= 0:
            continue
        # Clamp for numerical safety; spec says PE ∈ (0, 1]
        pes.append(min(1.0, straight_line / path_length))
    if not pes:
        return 0.0
    return float(np.mean(pes))


def makespan(trace: SimulationTrace) -> float:
    """Makespan (MS) — seconds. Lower is better.

    ``MS = max_i (T_goal_i - T_start)``. Agents that never reached their
    goal contribute ``trace.horizon_seconds`` (i.e. as if they used the
    full horizon).

    Spec: ``EVALUATION_METRICS.md §2.2``.
    """
    horizon = trace.horizon_seconds
    times: List[float] = []
    for agent in trace.agents:
        if agent.goal_reached_at_s is None:
            times.append(horizon)
        else:
            times.append(max(0.0, agent.goal_reached_at_s - trace.start_time_s))
    if not times:
        return 0.0
    return float(max(times))


def flowtime(trace: SimulationTrace) -> float:
    """Flowtime (FT) — drone-seconds. Lower is better.

    ``FT = Σ_i (T_goal_i - T_start)``. Same fallback rule as makespan.

    Spec: ``EVALUATION_METRICS.md §2.3``.
    """
    horizon = trace.horizon_seconds
    total = 0.0
    for agent in trace.agents:
        if agent.goal_reached_at_s is None:
            total += horizon
        else:
            total += max(0.0, agent.goal_reached_at_s - trace.start_time_s)
    return float(total)


# =============================================================================
# 3. Airspace utilization
# =============================================================================


def airspace_utilization(
    trace: SimulationTrace, capacity: AirspaceCapacity | None = None
) -> float:
    """Airspace Utilization (AU) — dimensionless in [0, 1].

    ``AU = (1 / T) ∫ (active_drones(t) / capacity) dt``. Default capacity
    is the maximum number of agents observed in the trace (i.e. AU = 1
    means "always at peak"). Pass ``capacity`` to compare against an
    operational ceiling.

    Spec: ``EVALUATION_METRICS.md §3.1``.
    """
    if not trace.agents or trace.horizon_seconds <= 0:
        return 0.0
    _, valid = _stack_positions(trace)  # (T, N)
    if valid.shape[0] == 0:
        return 0.0
    active_per_step = valid.sum(axis=1).astype(float)
    cap = float(capacity.max_agents) if capacity is not None else float(active_per_step.max() or 1.0)
    if cap <= 0:
        return 0.0
    # Time-average of fraction
    return float(np.clip(active_per_step / cap, 0.0, 1.0).mean())


def voronoi_cell_metrics(trace: SimulationTrace) -> Dict[str, float]:
    """Voronoi cell occupancy and handoff statistics.

    Returns ``mean_occupancy`` (drones per cell) and ``handoff_rate``
    (boundary crossings per second). If the trace has no
    ``voronoi_assignments``, returns NaNs.

    Spec: ``EVALUATION_METRICS.md §3.2``.
    """
    if not trace.voronoi_assignments:
        return {"mean_occupancy": math.nan, "handoff_rate": math.nan}
    by_step = trace.voronoi_assignments  # List[Dict[agent_id, cell_id]]
    occupancies: List[float] = []
    handoffs = 0
    for step_assignment in by_step:
        if not step_assignment:
            continue
        cells = list(step_assignment.values())
        unique_cells = set(cells)
        if unique_cells:
            occupancies.append(len(cells) / len(unique_cells))
    for prev, cur in zip(by_step, by_step[1:]):
        for agent_id, cell in cur.items():
            if prev.get(agent_id) is not None and prev[agent_id] != cell:
                handoffs += 1
    horizon = trace.horizon_seconds or 1.0
    return {
        "mean_occupancy": float(np.mean(occupancies)) if occupancies else math.nan,
        "handoff_rate": float(handoffs) / float(horizon),
    }


# =============================================================================
# 4. Regulatory conformance (SDACS-specific)
# =============================================================================


def remote_id_compliance_rate(trace: SimulationTrace) -> float:
    """Remote-ID Compliance Rate (RID-CR) — fraction in [0, 1].

    Fraction of (drone × second) cells with a valid F3411 broadcast.
    1.0 means full compliance. Spec target ≥ 0.999.

    Spec: ``EVALUATION_METRICS.md §4.1``.
    """
    if not trace.agents or trace.horizon_seconds <= 0:
        return 0.0
    n_agents = len(trace.agents)
    seconds = int(round(trace.horizon_seconds))
    if seconds <= 0:
        return 0.0
    denom = n_agents * seconds
    valid = sum(int(t) for t in trace.remote_id_valid_seconds_per_agent.values())
    return float(valid) / float(denom)


def laanc_authorization_latency_ms(trace: SimulationTrace) -> float:
    """Mean LAANC authorization latency — milliseconds. Lower is better.

    Spec: ``EVALUATION_METRICS.md §4.2``. Target ≤ 200 ms.
    """
    if not trace.laanc_request_latencies_ms:
        return math.nan
    return float(np.mean(trace.laanc_request_latencies_ms))


def geofence_violation_count(trace: SimulationTrace) -> int:
    """Number of timestamps where any drone is outside its authorized volume.

    Spec: ``EVALUATION_METRICS.md §4.3``. Hard target = 0.
    """
    return int(trace.geofence_violation_timestamps.__len__())


# =============================================================================
# 5. Computational efficiency
# =============================================================================


def real_time_factor(trace: SimulationTrace) -> float:
    """Real-Time Factor (RTF) — simulated_seconds / wall_clock_seconds.

    Higher is better. RTF > 1 means faster than real time.

    Spec: ``EVALUATION_METRICS.md §5.1``.
    """
    if trace.wall_clock_seconds <= 0:
        return math.nan
    return float(trace.horizon_seconds) / float(trace.wall_clock_seconds)


def per_tick_latency_percentiles(trace: SimulationTrace) -> Dict[str, float]:
    """p50 / p95 / p99 of per-tick wall clock (ms).

    Spec: ``EVALUATION_METRICS.md §5.2``.
    """
    if not trace.tick_latencies_ms:
        return {"p50_ms": math.nan, "p95_ms": math.nan, "p99_ms": math.nan}
    arr = np.asarray(trace.tick_latencies_ms, dtype=float)
    return {
        "p50_ms": float(np.percentile(arr, 50)),
        "p95_ms": float(np.percentile(arr, 95)),
        "p99_ms": float(np.percentile(arr, 99)),
    }


def memory_peak_mb(trace: SimulationTrace) -> float:
    """Peak resident memory in MB. Lower is better.

    Spec: ``EVALUATION_METRICS.md §5.3``.
    """
    return float(trace.peak_memory_mb) if trace.peak_memory_mb is not None else math.nan


# =============================================================================
# Evaluator façade
# =============================================================================


@dataclass(frozen=True)
class EvaluatorConfig:
    """Knobs for :class:`Evaluator`. Defaults match the paper spec."""

    d_safe_m: float = 5.0
    capacity: AirspaceCapacity | None = None


class Evaluator:
    """Run the full metric battery on a :class:`SimulationTrace`.

    Example::

        ev = Evaluator()
        result = ev.evaluate(trace)
        # result["NMR"], result["MSD"], result["PE"], result["MS"], ...

    The returned dict is flat for easy serialization; nested metrics
    (e.g. TTC distribution) are flattened with a ``_`` separator.
    """

    def __init__(self, config: EvaluatorConfig | None = None) -> None:
        self.config = config or EvaluatorConfig()

    def evaluate(self, trace: SimulationTrace) -> Dict[str, float]:
        """Compute all metrics. Returns a flat dict."""
        ttc = time_to_conflict_distribution(trace)
        voronoi = voronoi_cell_metrics(trace)
        latency = per_tick_latency_percentiles(trace)
        result: Dict[str, float] = {
            # 1. Safety
            "NMR": near_miss_rate(trace, d_safe=self.config.d_safe_m),
            "MSD": minimum_separation_distance(trace),
            "TTC_mean_s": ttc["mean_s"],
            "TTC_median_s": ttc["median_s"],
            "TTC_p5_s": ttc["p5_s"],
            "TTC_p95_s": ttc["p95_s"],
            # 2. Efficiency
            "PE": path_efficiency(trace),
            "MS_s": makespan(trace),
            "FT_drone_s": flowtime(trace),
            # 3. Airspace utilization
            "AU": airspace_utilization(trace, capacity=self.config.capacity),
            "VCU_mean_occupancy": voronoi["mean_occupancy"],
            "VCU_handoff_rate": voronoi["handoff_rate"],
            # 4. Regulatory
            "RID_CR": remote_id_compliance_rate(trace),
            "LAANC_latency_ms": laanc_authorization_latency_ms(trace),
            "geofence_violations": float(geofence_violation_count(trace)),
            # 5. Computational
            "RTF": real_time_factor(trace),
            "tick_p50_ms": latency["p50_ms"],
            "tick_p95_ms": latency["p95_ms"],
            "tick_p99_ms": latency["p99_ms"],
            "peak_memory_mb": memory_peak_mb(trace),
        }
        return result


# =============================================================================
# Internal helpers
# =============================================================================


def _stack_positions(
    trace: SimulationTrace,
) -> Tuple[np.ndarray, np.ndarray]:
    """Return (positions, valid_mask) shaped (T, N, 3) and (T, N).

    Aligns all agents to a common time grid based on ``trace.dt_s`` and
    ``trace.horizon_seconds``. Missing samples (agent not yet spawned or
    already reached goal) are masked out via ``valid_mask``.
    """
    dt = trace.dt_s if trace.dt_s > 0 else 1.0
    n_steps = int(round(trace.horizon_seconds / dt))
    n_agents = len(trace.agents)
    if n_steps <= 0 or n_agents == 0:
        return np.zeros((0, 0, 3)), np.zeros((0, 0), dtype=bool)

    positions = np.full((n_steps, n_agents, 3), np.nan, dtype=float)
    valid = np.zeros((n_steps, n_agents), dtype=bool)
    for ai, agent in enumerate(trace.agents):
        for step_idx, pos in enumerate(agent.positions):
            if step_idx >= n_steps:
                break
            positions[step_idx, ai] = pos
            valid[step_idx, ai] = True
    return positions, valid


def _count_near_miss_events(
    trace: SimulationTrace,
    *,
    d_safe: float,
    sep_factor: float,
    sep_seconds: float,
) -> int:
    """Count distinct near-miss events with the de-duplication rule from §1.1."""
    positions, valid = _stack_positions(trace)
    n_steps, n_agents, _ = positions.shape
    if n_steps == 0 or n_agents < 2:
        return 0
    dt = trace.dt_s if trace.dt_s > 0 else 1.0
    sep_threshold = d_safe * sep_factor
    sep_steps_required = max(1, int(round(sep_seconds / dt)))

    events = 0
    for i in range(n_agents):
        for j in range(i + 1, n_agents):
            both_valid = valid[:, i] & valid[:, j]
            if not both_valid.any():
                continue
            diffs = positions[:, i, :] - positions[:, j, :]
            d = np.linalg.norm(diffs, axis=1)
            d = np.where(both_valid, d, np.inf)
            in_conflict = d < d_safe
            far_enough = d >= sep_threshold

            counted_at: int = -10**9  # ensures the first event fires
            consecutive_far = 0
            for step in range(n_steps):
                if far_enough[step]:
                    consecutive_far += 1
                else:
                    consecutive_far = 0
                if (
                    in_conflict[step]
                    and (step - counted_at) > sep_steps_required
                    and (
                        counted_at < 0
                        or consecutive_far < sep_steps_required  # tracker reset
                        or _has_separated_since(
                            far_enough, counted_at, step, sep_steps_required
                        )
                    )
                ):
                    events += 1
                    counted_at = step
    return events


def _has_separated_since(
    far_enough: np.ndarray, last_event_step: int, current_step: int, sep_steps_required: int
) -> bool:
    """True if the pair was separated for ``sep_steps_required`` consecutive
    steps somewhere between ``last_event_step`` and ``current_step``."""
    if last_event_step < 0 or current_step <= last_event_step:
        return True
    window = far_enough[last_event_step + 1 : current_step + 1]
    if window.size == 0:
        return False
    # Look for sep_steps_required consecutive True values
    run = 0
    for v in window:
        if v:
            run += 1
            if run >= sep_steps_required:
                return True
        else:
            run = 0
    return False


# =============================================================================
# CLI entry point
# =============================================================================


def _main(argv: Sequence[str] | None = None) -> int:
    """``python -m src.analytics.metrics <trace.json> [--output result.json]``"""
    import argparse
    import json
    import sys

    parser = argparse.ArgumentParser(
        prog="python -m src.analytics.metrics",
        description="Run all SDACS metrics on a saved SimulationTrace JSON.",
    )
    parser.add_argument("trace", help="Path to SimulationTrace JSON")
    parser.add_argument(
        "--output", "-o", help="Path to write result JSON. Default: stdout"
    )
    parser.add_argument("--d-safe", type=float, default=5.0)
    args = parser.parse_args(argv)

    with open(args.trace, "r", encoding="utf-8") as f:
        trace_dict = json.load(f)
    trace = SimulationTrace.from_dict(trace_dict)
    cfg = EvaluatorConfig(d_safe_m=args.d_safe)
    result = Evaluator(cfg).evaluate(trace)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, sort_keys=True)
    else:
        json.dump(result, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI shim
    raise SystemExit(_main())
