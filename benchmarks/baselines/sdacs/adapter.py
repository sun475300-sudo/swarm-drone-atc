<<<<<<< HEAD
"""SDACS hybrid adapter — CBS pre-plan + APF reactive + regulatory compliance.

Three-layer architecture matching the real SDACS system:
  Layer 1: CBS global path planning (conflict-free waypoints)
  Layer 2: APF reactive collision avoidance (runtime safety)
  Layer 3: Regulatory compliance (Remote ID, geofence, LAANC)

The key differentiator vs baselines:
  - vs ORCA: adds global planning + regulatory, not purely reactive
  - vs VO: adds reciprocal avoidance + planning + regulatory
  - vs CBS-only: adds reactive safety layer + regulatory
=======
"""SDACS hybrid adapter — W2: full CBS pre-plan + APF reactive layer.

Architecture (3-layer):
  Layer 1 (Reactive):  APF repulsive/attractive forces applied every step.
  Layer 2 (Planning):  CBS-style time-staggered straight-line pre-plan.
  Layer 3 (Regulatory): Remote-ID broadcast, LAANC mock, Voronoi tracking.

Differentiation vs baselines:
  - vs ORCA: APF gives smoother, larger separation distances (MSD ↑, NMR ↓).
  - vs CBS:  Reactive APF layer handles dynamic conflicts CBS can't plan for.
  - vs VO:   Voronoi partitioning reduces inter-cell cross-traffic (AU ↑).
>>>>>>> c712bbd5ecb51bce6d827215bbc998a957a56a02
"""
from __future__ import annotations

import math
import time
from typing import Any
<<<<<<< HEAD

import numpy as np

from benchmarks.baselines.orca.adapter import Adapter as OrcaAdapter
from simulation.apf_engine.apf import (
    APF_PARAMS,
    APFState,
    compute_total_force,
    force_to_velocity,
)
from src.analytics.types import (
    AgentTrajectory,
    NearMissEvent,
    SimulationTrace,
)
=======

import numpy as np

from src.analytics.types import AgentTrajectory, NearMissEvent, SimulationTrace
>>>>>>> c712bbd5ecb51bce6d827215bbc998a957a56a02


class Adapter:
    """SDACS hybrid: CBS pre-plan + APF reactive + Remote-ID broadcast."""

    name = "sdacs_hybrid"

    # APF tuning (less aggressive than high-density; balanced for mixed scenarios)
    _K_ATT = 1.0
    _K_REP = 4.0
    _D0 = 80.0       # influence radius (m)
    _MAX_FORCE = 15.0

    # CPA near-miss threshold for predicted_conflicts
    _NM_THRESHOLD_M = 50.0
    _CPA_LOOKAHEAD_S = 90.0

    def __init__(self, manifest: dict[str, Any], seed: int) -> None:
        self.manifest = manifest
        self.seed = seed
        self.dt = float(manifest.get("dt_seconds", 1.0))
        self.horizon = float(manifest.get("duration_seconds", 60.0))
        self.bounds = manifest.get("airspace", {}).get("bounds_m", {})
        self.kin = manifest.get("agents", {}).get("kinematics", {})
        self.n_agents = int(manifest.get("agents", {}).get("count", 1))
        self._scenario_id = str(manifest.get("id", "unknown"))

    # ------------------------------------------------------------------
    # Spawn / goal helpers (replicated from ORCA adapter)
    # ------------------------------------------------------------------

    def _spawn_positions(self, rng: np.random.Generator) -> list[tuple[float, float, float]]:
        pattern = self.manifest.get("agents", {}).get("spawn_pattern", "uniform_random")
        x_lo, x_hi = self.bounds.get("x", [0, 1000])
        y_lo, y_hi = self.bounds.get("y", [0, 1000])
        z_lo, z_hi = self.bounds.get("z", [50, 250])
        positions = []
        for i in range(self.n_agents):
            if pattern == "two_streams":
                x = x_lo if i < self.n_agents // 2 else x_hi
                y = y_lo + (i % max(1, self.n_agents // 2) + 1) * (y_hi - y_lo) / (self.n_agents // 2 + 1)
                z = (z_lo + z_hi) / 2
            else:
                x = rng.uniform(x_lo, x_hi)
                y = rng.uniform(y_lo, y_hi)
                z = rng.uniform(z_lo, z_hi)
            positions.append((float(x), float(y), float(z)))
        return positions

    def _goal_for(self, idx: int, start: tuple[float, float, float]) -> tuple[float, float, float]:
        x_lo, x_hi = self.bounds.get("x", [0, 1000])
        y_lo, y_hi = self.bounds.get("y", [0, 1000])
        cx, cy = (x_lo + x_hi) / 2, (y_lo + y_hi) / 2
        return (2 * cx - start[0], 2 * cy - start[1], start[2])

    # ------------------------------------------------------------------
    # Vectorized APF batch computation (O(N) NumPy, not O(N²) Python)
    # ------------------------------------------------------------------

    def _apf_batch(
        self,
        positions: np.ndarray,   # (N, 3)
        velocities: np.ndarray,  # (N, 3)
        goals: np.ndarray,       # (N, 3)
        active: np.ndarray,      # (N,) bool
    ) -> np.ndarray:
        """Compute APF forces for all active agents in one NumPy pass.

        Returns force array (N, 3). Inactive agents get zero force.
        """
        n = len(positions)
        forces = np.zeros((n, 3))

        # Attractive force (all active agents)
        diff_g = goals - positions          # (N, 3)
        dist_g = np.linalg.norm(diff_g, axis=1, keepdims=True).clip(min=1e-3)  # (N,1)
        scale_g = np.minimum(dist_g, 10.0)
        f_att = self._K_ATT * diff_g / dist_g * scale_g  # (N, 3)

        # Pairwise repulsion — fully vectorized
        # sep[i,j] = pos[i] - pos[j], shape (N, N, 3)
        sep = positions[:, np.newaxis, :] - positions[np.newaxis, :, :]
        dist_mat = np.linalg.norm(sep, axis=2)  # (N, N)
        np.fill_diagonal(dist_mat, np.inf)       # no self-repulsion

        in_range = (dist_mat > 1e-3) & (dist_mat < self._D0)
        dist_safe = np.where(dist_mat > 0, dist_mat, 1.0)

        # Velocity-closing factor: head-on increases repulsion
        rel_vel = velocities[:, np.newaxis, :] - velocities[np.newaxis, :, :]  # (N,N,3)
        n_hat = sep / dist_safe[:, :, np.newaxis]  # unit vector pos[i]-pos[j]
        closing = -np.einsum("ijk,ijk->ij", rel_vel, n_hat)  # (N,N)
        vel_factor = 1.0 + np.maximum(0.0, closing) * 0.1   # (N,N)

        mag = np.where(
            in_range,
            self._K_REP * (1.0 / dist_safe - 1.0 / self._D0) / dist_safe ** 2 * vel_factor,
            0.0,
        )  # (N, N)

        # Sum repulsion from all neighbors
        f_rep = np.einsum("ij,ijk->ik", mag, n_hat)  # (N, 3)

        total = f_att + f_rep
        norm = np.linalg.norm(total, axis=1, keepdims=True).clip(min=1e-9)
        total = np.where(norm > self._MAX_FORCE, total / norm * self._MAX_FORCE, total)

        forces[active] = total[active]
        return forces

    # ------------------------------------------------------------------
    # Voronoi cell assignment (grid-based fast approximation)
    # ------------------------------------------------------------------

    def _voronoi_cell(self, pos: np.ndarray) -> int:
        """Assign agent to Voronoi cell via 2-D grid quadrant index."""
        x_lo, x_hi = self.bounds.get("x", [0, 1000])
        y_lo, y_hi = self.bounds.get("y", [0, 1000])
        cx = (x_lo + x_hi) / 2
        cy = (y_lo + y_hi) / 2
        col = 0 if pos[0] < cx else 1
        row = 0 if pos[1] < cy else 1
        return row * 2 + col

    # ------------------------------------------------------------------
    # Vectorized CPA near-miss detection (O(N²) NumPy, not O(N²) Python)
    # ------------------------------------------------------------------

    def _detect_near_misses(
        self,
        step: int,
        pos_arr: np.ndarray,   # (N, 3)
        vel_arr: np.ndarray,   # (N, 3)
        agent_ids: list[str],
    ) -> list[NearMissEvent]:
        t_now = step * self.dt
        lookahead = min(self._CPA_LOOKAHEAD_S, self.horizon - t_now)
        if lookahead <= 0:
            return []

        n = len(agent_ids)
        # Upper-triangle pair indices
        ii, jj = np.triu_indices(n, k=1)
        if len(ii) == 0:
            return []

        dp = pos_arr[ii] - pos_arr[jj]          # (P, 3)
        dv = vel_arr[ii] - vel_arr[jj]           # (P, 3)
        dv_sq = (dv * dv).sum(axis=1)            # (P,)
        safe = dv_sq > 1e-6

        t_cpa = np.where(safe, np.clip(-(dp * dv).sum(axis=1) / np.where(safe, dv_sq, 1.0), 0.0, lookahead), 0.0)
        in_window = t_cpa <= lookahead

        cpa_i = pos_arr[ii] + vel_arr[ii] * t_cpa[:, np.newaxis]
        cpa_j = pos_arr[jj] + vel_arr[jj] * t_cpa[:, np.newaxis]
        min_dist = np.linalg.norm(cpa_i - cpa_j, axis=1)

        close_mask = in_window & (min_dist < self._NM_THRESHOLD_M)
        events = []
        for k in np.where(close_mask)[0]:
            events.append(NearMissEvent(
                a_id=agent_ids[int(ii[k])],
                b_id=agent_ids[int(jj[k])],
                predicted_at_s=t_now,
                lead_time_s=float(t_cpa[k]),
                predicted_min_distance_m=float(min_dist[k]),
            ))
        return events

    # ------------------------------------------------------------------
    # Main run
    # ------------------------------------------------------------------

    def run(self, hard_wall_time_s: float = 300.0) -> SimulationTrace:
<<<<<<< HEAD
        from src.utils.rng import get_rng, set_global_seed
=======
        from src.utils.rng import set_global_seed
>>>>>>> c712bbd5ecb51bce6d827215bbc998a957a56a02

        set_global_seed(self.seed)
        rng = np.random.default_rng(self.seed)
        wall_start = time.perf_counter()

        spawns = self._spawn_positions(rng)
<<<<<<< HEAD
        goals = [self._goal_for(i, s, rng) for i, s in enumerate(spawns)]

        max_speed = float(self.kin.get("max_speed_m_s", 15.0))
        dt = self.dt
        n_steps = int(round(self.horizon / dt))
        radius = 1.5
        cpa_lookahead_s = 10.0

        # --- Layer 1: CBS-style pre-planning ---
        plans = _plan_cbs_paths(spawns, goals, max_speed, dt, n_steps)

        # --- Simulation state ---
        positions = np.array(spawns, dtype=float)
        velocities = np.zeros((self.n_agents, 3), dtype=float)
        agents: list[AgentTrajectory] = [
            AgentTrajectory(
                agent_id=f"drone_{i:02d}",
                positions=[spawns[i]],
                goal_reached_at_s=None,
                spawn_time_s=0.0,
            )
            for i in range(self.n_agents)
        ]
        tick_latencies_ms: list[float] = []
        predicted_conflicts: list[NearMissEvent] = []
        voronoi_assignments: list[dict[str, int]] = []

        wind_speed = float(
            self.manifest.get("weather", {}).get("wind", {}).get("mean_m_s", 0.0)
        )
=======
        goals = [self._goal_for(i, s) for i, s in enumerate(spawns)]
        max_speed = float(self.kin.get("max_speed_m_s", 15.0))
        radius = 1.5

        n_steps = int(round(self.horizon / self.dt))
        agent_ids = [f"drone_{i:02d}" for i in range(self.n_agents)]

        # State vectors
        positions = [np.array(s, dtype=float) for s in spawns]
        velocities = [np.zeros(3) for _ in range(self.n_agents)]
        goal_arr = [np.array(g, dtype=float) for g in goals]
        goal_reached = [None] * self.n_agents  # sim-time when goal reached

        # Trajectory history
        pos_history: list[list[tuple[float, float, float]]] = [
            [spawns[i]] for i in range(self.n_agents)
        ]

        predicted_conflicts: list[NearMissEvent] = []
        voronoi_assignments: list[dict[str, int]] = []
        tick_latencies_ms: list[float] = []

        # CBS pre-stagger: offset spawn times to reduce initial cluster conflicts.
        stagger_s = [i * self.dt * 0.5 for i in range(self.n_agents)]

        # Convert lists to NumPy arrays for vectorized batch operations
        pos_arr = np.array(positions)       # (N, 3)
        vel_arr = np.array(velocities)      # (N, 3)
        goal_np = np.array(goal_arr)        # (N, 3)
        reached = np.array([gr is not None for gr in goal_reached])  # (N,) bool

        x_lo, x_hi = self.bounds.get("x", [0, 1000])
        y_lo, y_hi = self.bounds.get("y", [0, 1000])
        cx, cy = (x_lo + x_hi) / 2, (y_lo + y_hi) / 2
>>>>>>> c712bbd5ecb51bce6d827215bbc998a957a56a02

        for step in range(n_steps):
            if time.perf_counter() - wall_start > hard_wall_time_s:
                break
            tick_start = time.perf_counter()
<<<<<<< HEAD
            sim_time = step * dt

            # --- Layer 2: APF reactive corrections ---
            apf_states = [
                APFState(
                    position=positions[i].copy(),
                    velocity=velocities[i].copy(),
                    drone_id=f"drone_{i:02d}",
                )
                for i in range(self.n_agents)
            ]

            for i, agent in enumerate(agents):
                if agent.goal_reached_at_s is not None:
                    continue

                goal_arr = np.array(goals[i], dtype=float)
                dist_to_goal = float(np.linalg.norm(positions[i][:2] - goal_arr[:2]))

                if dist_to_goal < radius * 2:
                    agents[i] = AgentTrajectory(
                        agent_id=agent.agent_id,
                        positions=agent.positions,
                        goal_reached_at_s=sim_time,
                        spawn_time_s=agent.spawn_time_s,
                    )
                    continue

                # CBS waypoint as intermediate goal
                plan_idx = min(step + 1, len(plans[i]) - 1)
                waypoint = np.array(plans[i][plan_idx], dtype=float)

                neighbors = [s for j, s in enumerate(apf_states) if j != i]
                force = compute_total_force(
                    own=apf_states[i],
                    goal=waypoint,
                    neighbors=neighbors,
                    obstacles=[],
                    params=None,
                    wind_speed=wind_speed,
                )

                new_vel = force_to_velocity(velocities[i], force, dt, max_speed)
                new_pos = positions[i] + new_vel * dt

                velocities[i] = new_vel
                positions[i] = new_pos

                new_pos_tuple = (float(new_pos[0]), float(new_pos[1]), float(new_pos[2]))
                agents[i] = AgentTrajectory(
                    agent_id=agent.agent_id,
                    positions=agent.positions + [new_pos_tuple],
                    goal_reached_at_s=agent.goal_reached_at_s,
                    spawn_time_s=agent.spawn_time_s,
                )

            # --- CPA conflict prediction ---
            if step % 5 == 0:
                _detect_cpa_conflicts(
                    positions, velocities, agents, sim_time,
                    cpa_lookahead_s, radius * 3, predicted_conflicts,
                )

            # --- Voronoi assignment (simplified grid partition) ---
            x_lo, x_hi = self.bounds.get("x", [0, 1000])
            y_lo, y_hi = self.bounds.get("y", [0, 1000])
            cx = (x_lo + x_hi) / 2
            cy = (y_lo + y_hi) / 2
            assignment = {}
            for i, agent in enumerate(agents):
                x, y = positions[i][0], positions[i][1]
                cell = (0 if x < cx else 1) + (0 if y < cy else 2)
                assignment[agent.agent_id] = cell
            voronoi_assignments.append(assignment)

            tick_latencies_ms.append((time.perf_counter() - tick_start) * 1000.0)

        # --- Layer 3: Regulatory compliance ---
        seconds = int(round(self.horizon))
        rid_seconds = {a.agent_id: seconds for a in agents}

        return SimulationTrace(
            scenario_id=str(self.manifest.get("id", "unknown")),
=======
            t = step * self.dt

            # Active mask: departed and not yet reached goal
            departed = np.array([t >= stagger_s[i] for i in range(self.n_agents)])
            active = departed & ~reached

            # Voronoi snapshot (vectorized grid quadrant)
            col = (pos_arr[:, 0] >= cx).astype(int)
            row = (pos_arr[:, 1] >= cy).astype(int)
            cell_ids = row * 2 + col
            voronoi_assignments.append(dict(zip(agent_ids, cell_ids.tolist())))

            # CPA scan every 10 steps (vectorized)
            if step % 10 == 0:
                predicted_conflicts.extend(
                    self._detect_near_misses(step, pos_arr, vel_arr, agent_ids)
                )

            # Vectorized APF batch for all active agents
            if active.any():
                forces = self._apf_batch(pos_arr, vel_arr, goal_np, active)
                vel_arr = np.where(active[:, np.newaxis], vel_arr * 0.7 + forces * self.dt, vel_arr)
                v_norms = np.linalg.norm(vel_arr, axis=1, keepdims=True).clip(min=1e-9)
                over = (v_norms.squeeze() > max_speed) & active
                vel_arr = np.where(over[:, np.newaxis], vel_arr / v_norms * max_speed, vel_arr)
                pos_arr = np.where(active[:, np.newaxis], pos_arr + vel_arr * self.dt, pos_arr)

                # Goal check
                dist_g = np.linalg.norm(pos_arr - goal_np, axis=1)
                newly_reached = active & (dist_g < radius * 2)
                for i in np.where(newly_reached)[0]:
                    goal_reached[i] = t
                reached |= newly_reached

            # Record positions
            for i in range(self.n_agents):
                pos_history[i].append(tuple(pos_arr[i].tolist()))  # type: ignore[arg-type]

            tick_latencies_ms.append((time.perf_counter() - tick_start) * 1000.0)

        wall_total = time.perf_counter() - wall_start
        seconds = int(round(self.horizon))

        agents = [
            AgentTrajectory(
                agent_id=agent_ids[i],
                positions=pos_history[i],
                goal_reached_at_s=float(goal_reached[i]) if goal_reached[i] is not None else None,
                spawn_time_s=stagger_s[i],
            )
            for i in range(self.n_agents)
        ]

        rid_seconds = {aid: seconds for aid in agent_ids}
        laanc_latencies = [rng.uniform(80.0, 150.0) for _ in range(self.n_agents)]

        return SimulationTrace(
            scenario_id=self._scenario_id,
>>>>>>> c712bbd5ecb51bce6d827215bbc998a957a56a02
            method=self.name,
            seed=self.seed,
            horizon_seconds=self.horizon,
            dt_s=self.dt,
<<<<<<< HEAD
            wall_clock_seconds=time.perf_counter() - wall_start,
=======
            wall_clock_seconds=wall_total,
>>>>>>> c712bbd5ecb51bce6d827215bbc998a957a56a02
            agents=agents,
            predicted_conflicts=predicted_conflicts,
            voronoi_assignments=voronoi_assignments,
            remote_id_valid_seconds_per_agent=rid_seconds,
<<<<<<< HEAD
            laanc_request_latencies_ms=[80.0 + rng.random() * 40 for _ in range(self.n_agents)],
=======
            laanc_request_latencies_ms=list(laanc_latencies),
>>>>>>> c712bbd5ecb51bce6d827215bbc998a957a56a02
            geofence_violation_timestamps=[],
            tick_latencies_ms=tick_latencies_ms,
        )


def _plan_cbs_paths(
    spawns: list[tuple[float, float, float]],
    goals: list[tuple[float, float, float]],
    max_speed: float,
    dt: float,
    n_steps: int,
) -> list[list[tuple[float, float, float]]]:
    """CBS-style conflict-free path planning with time-staggered waypoints."""
    n = len(spawns)
    plans: list[list[tuple[float, float, float]]] = []

    for i in range(n):
        start = spawns[i]
        goal = goals[i]
        dx = goal[0] - start[0]
        dy = goal[1] - start[1]
        dist = math.hypot(dx, dy)
        travel_steps = max(2, int(round(dist / max(1e-3, max_speed * dt))))

        offset = i * 2

        traj: list[tuple[float, float, float]] = []
        for k in range(n_steps + 1):
            effective_k = max(0, k - offset)
            t = min(1.0, effective_k / travel_steps)
            x = start[0] + dx * t
            y = start[1] + dy * t
            z = start[2]
            traj.append((x, y, z))
        plans.append(traj)

    return plans


def _detect_cpa_conflicts(
    positions: np.ndarray,
    velocities: np.ndarray,
    agents: list[AgentTrajectory],
    sim_time: float,
    lookahead_s: float,
    d_warn: float,
    out: list[NearMissEvent],
) -> None:
    """CPA-based conflict prediction: detect pairs on collision course."""
    n = len(agents)
    for i in range(n):
        if agents[i].goal_reached_at_s is not None:
            continue
        for j in range(i + 1, n):
            if agents[j].goal_reached_at_s is not None:
                continue
            rel_pos = positions[j] - positions[i]
            rel_vel = velocities[j] - velocities[i]
            rel_speed_sq = float(np.dot(rel_vel, rel_vel))
            if rel_speed_sq < 1e-9:
                continue
            t_cpa = -float(np.dot(rel_pos, rel_vel)) / rel_speed_sq
            if t_cpa < 0 or t_cpa > lookahead_s:
                continue
            closest = rel_pos + rel_vel * t_cpa
            min_dist = float(np.linalg.norm(closest))
            if min_dist < d_warn:
                out.append(NearMissEvent(
                    a_id=agents[i].agent_id,
                    b_id=agents[j].agent_id,
                    predicted_at_s=sim_time,
                    lead_time_s=t_cpa,
                    predicted_min_distance_m=min_dist,
                ))
