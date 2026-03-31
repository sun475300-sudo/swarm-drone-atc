# Phase 622: Digital Pheromone — ACO Pheromone Trail
"""
디지털 페로몬 증발/강화 경로 탐색:
개미 군집 최적화 기반 군집 경로 계획.
"""

import numpy as np
from dataclasses import dataclass


class PheromoneGrid:
    def __init__(self, size=50, evaporation=0.05, seed=42):
        self.rng = np.random.default_rng(seed)
        self.size = size
        self.grid = np.ones((size, size)) * 0.01
        self.evaporation = evaporation

    def deposit(self, x: int, y: int, amount=1.0):
        x, y = int(np.clip(x, 0, self.size-1)), int(np.clip(y, 0, self.size-1))
        self.grid[x, y] += amount

    def evaporate(self):
        self.grid *= (1 - self.evaporation)
        self.grid = np.clip(self.grid, 0.001, 100.0)

    def sense(self, x: int, y: int, radius=2) -> np.ndarray:
        x, y = int(np.clip(x, 0, self.size-1)), int(np.clip(y, 0, self.size-1))
        x0 = max(0, x - radius)
        x1 = min(self.size, x + radius + 1)
        y0 = max(0, y - radius)
        y1 = min(self.size, y + radius + 1)
        return self.grid[x0:x1, y0:y1].copy()

    def total_pheromone(self) -> float:
        return float(self.grid.sum())


@dataclass
class AntAgent:
    agent_id: int
    x: int
    y: int
    carrying: bool = False


class DigitalPheromone:
    def __init__(self, n_agents=20, grid_size=50, seed=42):
        self.rng = np.random.default_rng(seed)
        self.grid = PheromoneGrid(grid_size, 0.05, seed)
        self.n = n_agents
        self.agents = [
            AntAgent(i, int(self.rng.integers(0, grid_size)), int(self.rng.integers(0, grid_size)))
            for i in range(n_agents)
        ]
        self.food_source = (grid_size - 5, grid_size - 5)
        self.nest = (5, 5)
        self.steps = 0
        self.food_collected = 0

    def step(self):
        for a in self.agents:
            neighborhood = self.grid.sense(a.x, a.y, 2)
            if neighborhood.size > 0:
                max_idx = np.unravel_index(np.argmax(neighborhood), neighborhood.shape)
                dx = max_idx[0] - 2
                dy = max_idx[1] - 2
                prob_follow = 0.7
                if self.rng.random() < prob_follow and (dx != 0 or dy != 0):
                    a.x = int(np.clip(a.x + np.sign(dx), 0, self.grid.size - 1))
                    a.y = int(np.clip(a.y + np.sign(dy), 0, self.grid.size - 1))
                else:
                    a.x = int(np.clip(a.x + self.rng.integers(-1, 2), 0, self.grid.size - 1))
                    a.y = int(np.clip(a.y + self.rng.integers(-1, 2), 0, self.grid.size - 1))

            if abs(a.x - self.food_source[0]) <= 1 and abs(a.y - self.food_source[1]) <= 1:
                a.carrying = True
            if a.carrying and abs(a.x - self.nest[0]) <= 1 and abs(a.y - self.nest[1]) <= 1:
                a.carrying = False
                self.food_collected += 1

            if a.carrying:
                self.grid.deposit(a.x, a.y, 2.0)
            else:
                self.grid.deposit(a.x, a.y, 0.1)

        self.grid.evaporate()
        self.steps += 1

    def run(self, steps=200):
        for _ in range(steps):
            self.step()

    def summary(self):
        return {
            "agents": self.n,
            "steps": self.steps,
            "food_collected": self.food_collected,
            "total_pheromone": round(self.grid.total_pheromone(), 2),
            "grid_size": self.grid.size,
        }


if __name__ == "__main__":
    dp = DigitalPheromone(20, 50, 42)
    dp.run(200)
    for k, v in dp.summary().items():
        print(f"  {k}: {v}")
