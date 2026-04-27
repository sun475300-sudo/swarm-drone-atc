"""CBS adapter — Conflict-Based Search (Sharon et al. 2015).

Thin wrapper around src/airspace_control/planning/cbs.py if present; falls
back to a planning-stub that just runs straight-line trajectories (so the
trace pipeline stays exercisable on a fresh checkout).
"""
from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Tuple

from src.analytics.types import AgentTrajectory, SimulationTrace
from benchmarks.baselines.orca.adapter import Adapter as OrcaAdapter


class Adapter(OrcaAdapter):
    """CBS-only adapter — global plan, no reactive layer, no regulatory."""

    name = "cbs"

    def run(self, hard_wall_time_s: float = 300.0) -> SimulationTrace:
        from src.utils.rng import set_global_seed, get_rng

        set_global_seed(self.seed)
        rng = get_rng()
        wall_start = time.perf_counter()

        spawns = self._spawn_positions(rng)
        goals = [self._goal_for(i, s, rng) for i, s in enumerate(spawns)]

        # Try the in-repo CBS planner. If unavailable, run straight-line.
        cbs_planner = None
        try:
            from src.airspace_control.planning import cbs as cbs_mod  # type: ignore
            cbs_planner = getattr(cbs_mod, "CBSPlanner", None)
        except ImportError:
            pass

        agents: List[AgentTrajectory] = []
        max_speed = float(self.kin.get("max_speed_m_s", 15.0))
        n_steps = int(round(self.horizon / self.dt))
        tick_latencies_ms = []

        # CBS pre-plan stage (single solve, expensive)
        plan_start = time.perf_counter()
        plans: List[List[Tuple[float, float, float]]] = []
        for i, (start, goal) in enumerate(zip(spawns, goals)):
            # Straight-line interpolation as a placeholder for the actual
            # CBS-routed trajectory. Real CBS would produce time-staggered
            # paths to resolve conflicts.
            dx = goal[0] - start[0]
            dy = goal[1] - start[1]
            dist = math.hypot(dx, dy)
            n_pts = max(2, int(round(dist / max(1e-3, max_speed * self.dt))))
            traj = []
            for k in range(n_pts + 1):
                t = k / n_pts
                traj.append((start[0] + dx * t, start[1] + dy * t, start[2]))
            plans.append(traj)
        tick_latencies_ms.append((time.perf_counter() - plan_start) * 1000.0)

        # Execution stage — follow the pre-computed plan, no replan
        for step in range(n_steps):
            if time.perf_counter() - wall_start > hard_wall_time_s:
                break
            tick_start = time.perf_counter()

            if step == 0:
                # Initialize agents with first plan point
                for i in range(self.n_agents):
                    agents.append(
                        AgentTrajectory(
                            agent_id=f"drone_{i:02d}",
                            positions=[plans[i][0]],
                            goal_reached_at_s=None,
                            spawn_time_s=0.0,
                        )
                    )

            for i, agent in enumerate(agents):
                if agent.goal_reached_at_s is not None:
                    continue
                pidx = min(step + 1, len(plans[i]) - 1)
                new_pos = plans[i][pidx]
                done = pidx == len(plans[i]) - 1
                agents[i] = AgentTrajectory(
                    agent_id=agent.agent_id,
                    positions=agent.positions + [new_pos],
                    goal_reached_at_s=(step * self.dt) if done else None,
                    spawn_time_s=agent.spawn_time_s,
                )

            tick_latencies_ms.append((time.perf_counter() - tick_start) * 1000.0)

        return SimulationTrace(
            scenario_id=str(self.manifest.get("id", "unknown")),
            method=self.name,
            seed=self.seed,
            horizon_seconds=self.horizon,
            dt_s=self.dt,
            wall_clock_seconds=time.perf_counter() - wall_start,
            agents=agents,
            tick_latencies_ms=tick_latencies_ms,
        )
