"""VO adapter — non-cooperative Velocity Obstacle (Fiorini & Shiller 1998).

Same interface as the ORCA adapter but assumes others won't yield.
Reuses the position-stepping helpers from the ORCA fallback path.
"""
from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Tuple

import numpy as np

from src.analytics.types import AgentTrajectory, SimulationTrace
from benchmarks.baselines.orca.adapter import Adapter as OrcaAdapter


class Adapter(OrcaAdapter):
    """Velocity Obstacle (non-reciprocal). Inherits scenario setup from ORCA."""

    name = "vo"

    def run(self, hard_wall_time_s: float = 300.0) -> SimulationTrace:
        from src.utils.rng import set_global_seed, get_rng

        set_global_seed(self.seed)
        rng = get_rng()
        wall_start = time.perf_counter()

        spawns = self._spawn_positions(rng)
        goals = [self._goal_for(i, s, rng) for i, s in enumerate(spawns)]

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
        max_accel = float(self.kin.get("max_accel_m_s2", 5.0))
        radius = 1.5
        dt = self.dt
        n_steps = int(round(self.horizon / dt))
        tick_latencies_ms = []
        velocities = np.zeros((self.n_agents, 2), dtype=float)

        for step in range(n_steps):
            if time.perf_counter() - wall_start > hard_wall_time_s:
                break
            tick_start = time.perf_counter()

            positions = np.array([a.positions[-1][:2] for a in agents], dtype=float)
            for i, agent in enumerate(agents):
                if agent.goal_reached_at_s is not None:
                    continue
                cur = positions[i]
                goal = np.array(goals[i][:2], dtype=float)
                to_goal = goal - cur
                dist = float(np.linalg.norm(to_goal))
                if dist < radius * 2:
                    agents[i] = AgentTrajectory(
                        agent_id=agent.agent_id,
                        positions=agent.positions,
                        goal_reached_at_s=step * dt,
                        spawn_time_s=agent.spawn_time_s,
                    )
                    continue
                desired_v = to_goal / dist * max_speed

                # Cheap VO check: detour around any obstacle in the
                # next-3-second cone.
                for j in range(self.n_agents):
                    if j == i:
                        continue
                    rel = positions[j] - cur
                    rel_dist = float(np.linalg.norm(rel))
                    if rel_dist < 1e-6:
                        continue
                    # Time to closest approach assuming constant velocities
                    rel_v = velocities[j] - desired_v
                    rel_v_norm2 = float(np.dot(rel_v, rel_v))
                    if rel_v_norm2 < 1e-9:
                        continue
                    tcpa = -float(np.dot(rel, rel_v)) / rel_v_norm2
                    if 0 < tcpa < 3.0:
                        # Steer right (perpendicular)
                        perp = np.array([-rel[1], rel[0]]) / max(rel_dist, 1e-6)
                        desired_v = (desired_v + perp * max_speed * 0.3)
                        n = float(np.linalg.norm(desired_v))
                        if n > max_speed:
                            desired_v = desired_v / n * max_speed

                # Acceleration limit
                dv = desired_v - velocities[i]
                dv_norm = float(np.linalg.norm(dv))
                if dv_norm > max_accel * dt:
                    dv = dv / dv_norm * (max_accel * dt)
                velocities[i] = velocities[i] + dv

                new_xy = cur + velocities[i] * dt
                new_pos = (float(new_xy[0]), float(new_xy[1]), agent.positions[-1][2])
                agents[i] = AgentTrajectory(
                    agent_id=agent.agent_id,
                    positions=agent.positions + [new_pos],
                    goal_reached_at_s=agent.goal_reached_at_s,
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
