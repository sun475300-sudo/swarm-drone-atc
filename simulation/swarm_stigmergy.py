# Phase 545: Swarm Stigmergy — Pheromone-Based Indirect Communication
"""
스티그머지 기반 간접 통신: 페로몬 필드 확산/증발,
개미 군집 최적화(ACO)로 경로 탐색, 집단 의사결정.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class PheromoneCell:
    x: int
    y: int
    concentration: float = 0.0
    ptype: str = "explore"  # explore, danger, food


@dataclass
class StigmergyAgent:
    agent_id: str
    x: int
    y: int
    carrying: bool = False
    path: list = field(default_factory=list)


class PheromoneField:
    """2D 페로몬 필드: 확산 + 증발."""

    def __init__(self, width=50, height=50, evaporation=0.05, diffusion=0.01):
        self.width = width
        self.height = height
        self.evap = evaporation
        self.diff = diffusion
        self.grid = np.zeros((width, height))

    def deposit(self, x: int, y: int, amount: float):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.grid[x, y] += amount

    def evaporate(self):
        self.grid *= (1.0 - self.evap)

    def diffuse(self):
        new_grid = self.grid.copy()
        for x in range(1, self.width - 1):
            for y in range(1, self.height - 1):
                neighbors = (self.grid[x-1, y] + self.grid[x+1, y] +
                             self.grid[x, y-1] + self.grid[x, y+1]) / 4
                new_grid[x, y] = (1 - self.diff) * self.grid[x, y] + self.diff * neighbors
        self.grid = new_grid

    def step(self):
        self.evaporate()
        self.diffuse()

    def sample(self, x: int, y: int) -> float:
        if 0 <= x < self.width and 0 <= y < self.height:
            return float(self.grid[x, y])
        return 0.0

    def total_pheromone(self) -> float:
        return float(self.grid.sum())


class ACOPathfinder:
    """개미 군집 최적화 경로 탐색."""

    def __init__(self, field: PheromoneField, seed=42):
        self.field = field
        self.rng = np.random.default_rng(seed)

    def find_path(self, agent: StigmergyAgent, target_x: int, target_y: int,
                  max_steps=100) -> list:
        path = [(agent.x, agent.y)]
        x, y = agent.x, agent.y
        for _ in range(max_steps):
            if x == target_x and y == target_y:
                break
            neighbors = []
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.field.width and 0 <= ny < self.field.height:
                    ph = self.field.sample(nx, ny) + 0.1
                    dist = abs(nx - target_x) + abs(ny - target_y)
                    score = ph / (dist + 1)
                    neighbors.append((nx, ny, score))
            if not neighbors:
                break
            # 확률적 선택
            scores = np.array([n[2] for n in neighbors])
            probs = scores / scores.sum()
            idx = int(self.rng.choice(len(neighbors), p=probs))
            x, y = neighbors[idx][0], neighbors[idx][1]
            path.append((x, y))
            self.field.deposit(x, y, 1.0)
        agent.x, agent.y = x, y
        agent.path = path
        return path


class SwarmStigmergy:
    """스티그머지 군집 시뮬레이션."""

    def __init__(self, n_agents=15, grid_size=30, seed=42):
        self.rng = np.random.default_rng(seed)
        self.field = PheromoneField(grid_size, grid_size)
        self.aco = ACOPathfinder(self.field, seed)
        self.agents: list[StigmergyAgent] = []
        self.target = (grid_size - 1, grid_size - 1)
        self.paths_found = 0
        self.total_steps = 0

        for i in range(n_agents):
            x = int(self.rng.integers(0, grid_size // 3))
            y = int(self.rng.integers(0, grid_size // 3))
            self.agents.append(StigmergyAgent(f"ant_{i}", x, y))

    def step(self):
        self.total_steps += 1
        for agent in self.agents:
            path = self.aco.find_path(agent, self.target[0], self.target[1], 50)
            if (agent.x, agent.y) == self.target:
                self.paths_found += 1
                # 리셋
                agent.x = int(self.rng.integers(0, self.field.width // 3))
                agent.y = int(self.rng.integers(0, self.field.height // 3))
        self.field.step()

    def run(self, steps=20):
        for _ in range(steps):
            self.step()

    def summary(self):
        return {
            "agents": len(self.agents),
            "grid_size": self.field.width,
            "total_pheromone": round(self.field.total_pheromone(), 2),
            "paths_found": self.paths_found,
            "steps": self.total_steps,
        }


if __name__ == "__main__":
    ss = SwarmStigmergy(15, 30, 42)
    ss.run(20)
    for k, v in ss.summary().items():
        print(f"  {k}: {v}")
