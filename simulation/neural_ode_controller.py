# Phase 589: Neural ODE Controller — Continuous-Time Control
"""
Neural ODE 제어기: 연속 시간 신경망,
ODE 솔버(RK4), 궤적 최적화.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class ODEState:
    t: float
    y: np.ndarray


class NeuralODEFunc:
    """신경망 ODE 함수 f(t, y)."""

    def __init__(self, input_dim=4, hidden_dim=16, seed=42):
        rng = np.random.default_rng(seed)
        self.w1 = rng.normal(0, 0.3, (input_dim, hidden_dim))
        self.b1 = np.zeros(hidden_dim)
        self.w2 = rng.normal(0, 0.3, (hidden_dim, input_dim))
        self.b2 = np.zeros(input_dim)

    def __call__(self, t: float, y: np.ndarray) -> np.ndarray:
        h = np.tanh(y @ self.w1 + self.b1)
        return h @ self.w2 + self.b2


class RK4Solver:
    """4차 Runge-Kutta 솔버."""

    def solve(self, func, y0: np.ndarray, t_span: tuple, dt=0.01) -> list[ODEState]:
        t0, t1 = t_span
        t = t0
        y = y0.copy()
        trajectory = [ODEState(t, y.copy())]
        while t < t1:
            h = min(dt, t1 - t)
            k1 = func(t, y)
            k2 = func(t + h / 2, y + h / 2 * k1)
            k3 = func(t + h / 2, y + h / 2 * k2)
            k4 = func(t + h, y + h * k3)
            y = y + h / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
            t += h
            trajectory.append(ODEState(t, y.copy()))
        return trajectory


class NeuralODEController:
    """Neural ODE 기반 드론 제어 시뮬레이션."""

    def __init__(self, state_dim=4, seed=42):
        self.rng = np.random.default_rng(seed)
        self.func = NeuralODEFunc(state_dim, 16, seed)
        self.solver = RK4Solver()
        self.state_dim = state_dim
        self.trajectories: list[list[ODEState]] = []

    def simulate_trajectory(self, y0: np.ndarray = None, t_end=5.0, dt=0.05):
        if y0 is None:
            y0 = self.rng.normal(0, 1, self.state_dim)
        traj = self.solver.solve(self.func, y0, (0, t_end), dt)
        self.trajectories.append(traj)
        return traj

    def run(self, n_trajectories=10, t_end=5.0):
        for _ in range(n_trajectories):
            y0 = self.rng.normal(0, 1, self.state_dim)
            self.simulate_trajectory(y0, t_end)

    def stability_metric(self) -> float:
        """안정성 지표: 궤적 발산 정도."""
        if not self.trajectories:
            return 0.0
        norms = []
        for traj in self.trajectories:
            final_norm = np.linalg.norm(traj[-1].y)
            norms.append(final_norm)
        return float(np.mean(norms))

    def summary(self):
        total_steps = sum(len(t) for t in self.trajectories)
        return {
            "state_dim": self.state_dim,
            "trajectories": len(self.trajectories),
            "total_steps": total_steps,
            "stability": round(self.stability_metric(), 4),
            "solver": "RK4",
        }


if __name__ == "__main__":
    noc = NeuralODEController(4, 42)
    noc.run(10, 5.0)
    for k, v in noc.summary().items():
        print(f"  {k}: {v}")
