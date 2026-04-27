"""Immutable input types for :mod:`src.analytics.metrics`.

Every field has a default so a minimal ``SimulationTrace()`` can be
constructed for unit tests. Real simulation runs populate every field.

JSON round-trip is supported via :meth:`SimulationTrace.from_dict` and
:meth:`SimulationTrace.to_dict` so traces can be checkpointed and
re-evaluated offline by the CLI.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Sequence, Tuple

Position = Tuple[float, float, float]


@dataclass(frozen=True)
class AgentTrajectory:
    """Per-agent state captured each simulation step.

    Attributes:
        agent_id: Stable identifier (e.g. ``"drone_07"``).
        positions: Sequence of ``(x, y, z)`` tuples in meters, one per
            simulation step. Empty list = agent never spawned.
        goal_reached_at_s: Wall-time the agent reached its goal, in
            simulation seconds since ``trace.start_time_s``. ``None``
            means the agent never reached its goal within the horizon.
        spawn_time_s: First simulation second the agent existed.
    """

    agent_id: str
    positions: List[Position] = field(default_factory=list)
    goal_reached_at_s: Optional[float] = None
    spawn_time_s: float = 0.0


@dataclass(frozen=True)
class NearMissEvent:
    """A predicted (or observed) close-approach event.

    Used by the Time-to-Conflict metric. Predictions come from the CPA
    lookahead module; observed events come from the safety analyzer.
    """

    a_id: str
    b_id: str
    predicted_at_s: float
    lead_time_s: float
    predicted_min_distance_m: float


@dataclass(frozen=True)
class AirspaceCapacity:
    """Operational capacity ceiling — used to normalize utilization."""

    max_agents: int
    volume_m3: Optional[float] = None


@dataclass(frozen=True)
class SimulationTrace:
    """One full simulation run, captured as plain data.

    The metrics module never mutates this structure.
    """

    scenario_id: str = "unknown"
    method: str = "unknown"  # e.g. "sdacs_hybrid", "orca", "vo", "cbs"
    seed: int = 0
    start_time_s: float = 0.0
    horizon_seconds: float = 0.0
    dt_s: float = 1.0
    wall_clock_seconds: float = 0.0

    agents: List[AgentTrajectory] = field(default_factory=list)
    predicted_conflicts: List[NearMissEvent] = field(default_factory=list)

    # Voronoi assignment per step: list of {agent_id -> cell_id}
    voronoi_assignments: List[Dict[str, int]] = field(default_factory=list)

    # Regulatory (per-agent valid Remote ID seconds)
    remote_id_valid_seconds_per_agent: Dict[str, int] = field(default_factory=dict)

    # LAANC mock latencies (ms)
    laanc_request_latencies_ms: List[float] = field(default_factory=list)

    # Sim-time seconds where any drone was outside its authorized volume
    geofence_violation_timestamps: List[float] = field(default_factory=list)

    # Per-tick wall clock (ms)
    tick_latencies_ms: List[float] = field(default_factory=list)

    # Peak resident memory (MB)
    peak_memory_mb: Optional[float] = None

    # ---- Serialization ------------------------------------------------------

    def to_dict(self) -> dict:
        """Plain-dict (JSON-serializable) representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "SimulationTrace":
        """Construct from a dict produced by :meth:`to_dict`."""
        agents = [
            AgentTrajectory(
                agent_id=a["agent_id"],
                positions=[tuple(p) for p in a.get("positions", [])],
                goal_reached_at_s=a.get("goal_reached_at_s"),
                spawn_time_s=float(a.get("spawn_time_s", 0.0)),
            )
            for a in data.get("agents", [])
        ]
        predicted = [
            NearMissEvent(
                a_id=c["a_id"],
                b_id=c["b_id"],
                predicted_at_s=float(c["predicted_at_s"]),
                lead_time_s=float(c["lead_time_s"]),
                predicted_min_distance_m=float(c["predicted_min_distance_m"]),
            )
            for c in data.get("predicted_conflicts", [])
        ]
        return cls(
            scenario_id=data.get("scenario_id", "unknown"),
            method=data.get("method", "unknown"),
            seed=int(data.get("seed", 0)),
            start_time_s=float(data.get("start_time_s", 0.0)),
            horizon_seconds=float(data.get("horizon_seconds", 0.0)),
            dt_s=float(data.get("dt_s", 1.0)),
            wall_clock_seconds=float(data.get("wall_clock_seconds", 0.0)),
            agents=agents,
            predicted_conflicts=predicted,
            voronoi_assignments=[dict(d) for d in data.get("voronoi_assignments", [])],
            remote_id_valid_seconds_per_agent=dict(
                data.get("remote_id_valid_seconds_per_agent", {})
            ),
            laanc_request_latencies_ms=list(data.get("laanc_request_latencies_ms", [])),
            geofence_violation_timestamps=list(data.get("geofence_violation_timestamps", [])),
            tick_latencies_ms=list(data.get("tick_latencies_ms", [])),
            peak_memory_mb=data.get("peak_memory_mb"),
        )
