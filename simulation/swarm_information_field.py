# Phase 603: Swarm Information Field — Fisher Information
"""
정보장 이론: Fisher 정보 행렬,
엔트로피 최소화 군집 배치.
"""

import numpy as np
from dataclasses import dataclass


class FisherInformationField:
    def __init__(self, grid_size=32, seed=42):
        self.rng = np.random.default_rng(seed)
        self.size = grid_size
        x = np.linspace(-2, 2, grid_size)
        y = np.linspace(-2, 2, grid_size)
        X, Y = np.meshgrid(x, y)
        self.info_field = np.exp(-(X**2 + Y**2) / 1.0)
        self.entropy_field = -self.info_field * np.log(self.info_field + 1e-10)

    def fisher_at(self, x: float, y: float) -> float:
        ix = int(np.clip((x + 2) / 4 * self.size, 0, self.size - 1))
        iy = int(np.clip((y + 2) / 4 * self.size, 0, self.size - 1))
        return float(self.info_field[ix, iy])

    def total_entropy(self) -> float:
        return float(np.sum(self.entropy_field))

    def info_gradient(self, x: float, y: float) -> np.ndarray:
        h = 0.01
        gx = (self.fisher_at(x + h, y) - self.fisher_at(x - h, y)) / (2 * h)
        gy = (self.fisher_at(x, y + h) - self.fisher_at(x, y - h)) / (2 * h)
        return np.array([gx, gy])


class SwarmInformationField:
    def __init__(self, n_agents=15, seed=42):
        self.rng = np.random.default_rng(seed)
        self.field = FisherInformationField(32, seed)
        self.positions = self.rng.uniform(-1.5, 1.5, (n_agents, 2))
        self.n = n_agents
        self.steps = 0

    def step(self, lr=0.1):
        for i in range(self.n):
            grad = self.field.info_gradient(self.positions[i, 0], self.positions[i, 1])
            self.positions[i] += lr * grad + self.rng.normal(0, 0.01, 2)
            self.positions[i] = np.clip(self.positions[i], -1.9, 1.9)
        self.steps += 1

    def run(self, steps=50):
        for _ in range(steps):
            self.step()

    def collected_info(self) -> float:
        return float(sum(self.field.fisher_at(p[0], p[1]) for p in self.positions))

    def summary(self):
        return {
            "agents": self.n,
            "steps": self.steps,
            "collected_info": round(self.collected_info(), 4),
            "total_entropy": round(self.field.total_entropy(), 4),
            "avg_info_per_agent": round(self.collected_info() / self.n, 4),
        }


if __name__ == "__main__":
    sif = SwarmInformationField(15, 42)
    sif.run(50)
    for k, v in sif.summary().items():
        print(f"  {k}: {v}")
