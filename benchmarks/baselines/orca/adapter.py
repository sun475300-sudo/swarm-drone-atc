"""ORCA adapter — Reciprocal Velocity Obstacle (van den Berg 2011).

Wraps the `rvo2` Python bindings if available; falls back to a clean-room
ORCA-lite implementation if not (sufficient for CI smoke tests).

See benchmarks/baselines/orca/README.md for the rationale and known
limitations against the SDACS suite.
"""
from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Tuple

from src.analytics.types import (
    AgentTrajectory,
    SimulationTrace,
)


class Adapter:
    """ORCA / RVO2 adapter."""

    name = "orca"

    def __init__(self, manifest: Dict[str, Any], seed: int) -> None:
        self.manifest = manifest
        self.seed = seed
        self.dt = float(manifest.get("dt_seconds", 1.0))
        self.horizon = float(manifest.get("duration_seconds", 60.0))
        self.bounds = manifest.get("airspace", {}).get("bounds_m", {})
        self.kin = manifest.get("agents", {}).get("kinematics", {})
        self.n_agents = int(manifest.get("agents", {}).get("count", 1))

        self._sim = None  # set in run()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _try_import_rvo2(self):
        try:
            import rvo2  # type: ignore
            return rvo2
        except ImportError:
            return None

    def _spawn_positions(self, rng) -> List[Tuple[float, float, float]]:
        """Generate spawn positions per the manifest's spawn_pattern.

        Falls back to uniform random inside the airspace bounds if the pattern
        is unknown (so smoke tests don't crash on unimplemented patterns).
        """
        pattern = self.manifest.get("agents", {}).get("spawn_pattern", "uniform_random")
        x_lo, x_hi = self.bounds.get("x", [0, 1000])
        y_lo, y_hi = self.bounds.get("y", [0, 1000])
        z_lo, z_hi = self.bounds.get("z", [50, 250])
        positions = []
        for i in range(self.n_agents):
            if pattern == "two_streams":
                # half on x_lo, half on x_hi
                x = x_lo if i < self.n_agents // 2 else x_hi
                y = y_lo + (i % max(1, self.n_agents // 2) + 1) * (y_hi - y_lo) / (self.n_agents // 2 + 1)
                z = (z_lo + z_hi) / 2
            else:
                x = rng.uniform(x_lo, x_hi)
                y = rng.uniform(y_lo, y_hi)
                z = rng.uniform(z_lo, z_hi)
            positions.append((x, y, z))
        return positions

    def _goal_for(self, idx: int, start: Tuple[float, float, float], rng) -> Tuple[float, float, float]:
        """Pick a goal opposite to the spawn (default), or random."""
        x_lo, x_hi = self.bounds.get("x", [0, 1000])
        y_lo, y_hi = self.bounds.get("y", [0, 1000])
        # Mirror across the airspace centre
        cx = (x_lo + x_hi) / 2
        cy = (y_lo + y_hi) / 2
        gx = 2 * cx - start[0]
        gy = 2 * cy - start[1]
        return (gx, gy, start[2])

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def run(self, hard_wall_time_s: float = 300.0) -> SimulationTrace:
        from src.utils.rng import set_global_seed, get_rng

        set_global_seed(self.seed)
        rng = get_rng()
        wall_start = time.perf_counter()

        spawns = self._spawn_positions(rng)
        goals = [self._goal_for(i, s, rng) for i, s in enumerate(spawns)]

        # Try real RVO2; fall back to lite VO step otherwise.
        rvo2 = self._try_import_rvo2()

        agents: List[AgentTrajectory] = [
            AgentTrajectory(
                agent_id=f"drone_{i:02d}",
                positions=[spawns[i]],
                goal_reached_at_s=None,
                spawn_time_s=0.0,
            )
            for i in range(self.n_agents)
        ]

        max_speed = float(self.kin.get("max_speed_m_s", 15.0))
        radius = 1.5  # drone radius assumption
        time_horizon = 5.0
        dt = self.dt

        if rvo2 is not None:
            sim = rvo2.PyRVOSimulator(
                dt, 1.5, 5, time_horizon, time_horizon, radius, max_speed
            )
            for i, p in enumerate(spawns):
                sim.addAgent((p[0], p[1]))
        else:
            sim = None

        n_steps = int(round(self.horizon / dt))
        tick_latencies_ms = []

        for step in range(n_steps):
            if time.perf_counter() - wall_start > hard_wall_time_s:
                break
            tick_start = time.perf_counter()

            if sim is not None:
                # Set preferred velocities toward goals
                for i, agent in enumerate(agents):
                    if agent.goal_reached_at_s is not None:
                        sim.setAgentPrefVelocity(i, (0.0, 0.0))
                        continue
                    cur = (sim.getAgentPosition(i)[0], sim.getAgentPosition(i)[1])
                    gx, gy = goals[i][0], goals[i][1]
                    dx, dy = gx - cur[0], gy - cur[1]
                    dist = math.hypot(dx, dy)
                    if dist < radius * 2:
                        # Mark arrival
                        agents[i] = AgentTrajectory(
                            agent_id=agent.agent_id,
                            positions=agent.positions,
                            goal_reached_at_s=step * dt,
                            spawn_time_s=agent.spawn_time_s,
                        )
                        sim.setAgentPrefVelocity(i, (0.0, 0.0))
                    else:
                        scale = max_speed / dist
                        sim.setAgentPrefVelocity(i, (dx * scale, dy * scale))
                sim.doStep()
                # Record positions
                for i, agent in enumerate(agents):
                    p = sim.getAgentPosition(i)
                    new_pos = (p[0], p[1], spawns[i][2])
                    agents[i] = AgentTrajectory(
                        agent_id=agent.agent_id,
                        positions=agent.positions + [new_pos],
                        goal_reached_at_s=agent.goal_reached_at_s,
                        spawn_time_s=agent.spawn_time_s,
                    )
            else:
                # Lite fallback: each agent steps directly toward its goal
                # ignoring others. Sufficient for smoke testing the trace
                # plumbing; real safety metrics only meaningful with rvo2 installed.
                for i, agent in enumerate(agents):
                    if agent.goal_reached_at_s is not None:
                        continue
                    cur = agent.positions[-1]
                    gx, gy, gz = goals[i]
                    dx, dy = gx - cur[0], gy - cur[1]
                    dist = math.hypot(dx, dy)
                    if dist < radius * 2:
                        agents[i] = AgentTrajectory(
                            agent_id=agent.agent_id,
                            positions=agent.positions,
                            goal_reached_at_s=step * dt,
                            spawn_time_s=agent.spawn_time_s,
                        )
                    else:
                        step_d = min(dist, max_speed * dt)
                        nx = cur[0] + dx / dist * step_d
                        ny = cur[1] + dy / dist * step_d
                        agents[i] = AgentTrajectory(
                            agent_id=agent.agent_id,
                            positions=agent.positions + [(nx, ny, cur[2])],
                            goal_reached_at_s=agent.goal_reached_at_s,
                            spawn_time_s=agent.spawn_time_s,
                        )

            tick_latencies_ms.append((time.perf_counter() - tick_start) * 1000.0)

        wall_total = time.perf_counter() - wall_start
        seconds = int(round(self.horizon))

        return SimulationTrace(
            scenario_id=str(self.manifest.get("id", "unknown")),
            method=self.name,
            seed=self.seed,
            horizon_seconds=self.horizon,
            dt_s=self.dt,
            wall_clock_seconds=wall_total,
            agents=agents,
            # ORCA has no concept of these:
            predicted_conflicts=[],
            voronoi_assignments=[],
            remote_id_valid_seconds_per_agent={},  # ORCA does not broadcast
            laanc_request_latencies_ms=[],
            geofence_violation_timestamps=[],
            tick_latencies_ms=tick_latencies_ms,
        )
