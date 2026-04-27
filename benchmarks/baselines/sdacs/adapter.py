"""SDACS hybrid adapter — full 3-layer system under test.

For the W1 baseline contract this defers to a deterministic placeholder so
the rest of the pipeline (P706 sweep, P705 metrics, P704 Docker repro)
can be smoke-tested end-to-end. The real wiring to
src/airspace_control/controller/ happens in W2 once the runner is verified.
"""
from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Tuple

from src.analytics.types import AgentTrajectory, NearMissEvent, SimulationTrace
from benchmarks.baselines.orca.adapter import Adapter as OrcaAdapter


class Adapter(OrcaAdapter):
    """SDACS hybrid: CBS pre-plan + APF reactive + Remote-ID broadcast."""

    name = "sdacs_hybrid"

    def run(self, hard_wall_time_s: float = 300.0) -> SimulationTrace:
        from src.utils.rng import set_global_seed, get_rng

        set_global_seed(self.seed)
        rng = get_rng()
        wall_start = time.perf_counter()

        # Reuse ORCA's reactive path as the avoidance layer for now.
        base_trace = super().run(hard_wall_time_s=hard_wall_time_s * 0.9)

        # Fill in the SDACS-specific fields:
        # - Remote ID compliance: assume 100% if regulatory layer up
        # - Voronoi assignments: simple grid partition placeholder
        # - Predicted conflicts: empty until CPA wired
        seconds = int(round(self.horizon))
        rid_seconds = {a.agent_id: seconds for a in base_trace.agents}

        # Voronoi placeholder — assign each agent to a fixed cell by index
        voronoi = []
        for step in range(int(round(self.horizon / self.dt))):
            assignment = {a.agent_id: idx % 4 for idx, a in enumerate(base_trace.agents)}
            voronoi.append(assignment)

        return SimulationTrace(
            scenario_id=base_trace.scenario_id,
            method=self.name,
            seed=self.seed,
            horizon_seconds=base_trace.horizon_seconds,
            dt_s=base_trace.dt_s,
            wall_clock_seconds=time.perf_counter() - wall_start,
            agents=base_trace.agents,
            predicted_conflicts=[],  # CPA wiring is W2
            voronoi_assignments=voronoi,
            remote_id_valid_seconds_per_agent=rid_seconds,
            laanc_request_latencies_ms=[100.0] * self.n_agents,  # mock 100 ms
            geofence_violation_timestamps=[],
            tick_latencies_ms=base_trace.tick_latencies_ms,
        )
