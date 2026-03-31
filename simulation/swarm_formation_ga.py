# Phase 649: Swarm Formation GA — Genetic Algorithm for Optimal Formation
"""
유전 알고리즘 기반 최적 포메이션 배치.
적합도 함수: 커버리지 + 통신 연결성 + 에너지 효율.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class Individual:
    positions: np.ndarray  # (n_drones, 3)
    fitness: float = 0.0


class FormationGA:
    def __init__(self, n_drones: int = 10, seed: int = 42,
                 pop_size: int = 30, mutation_rate: float = 0.1):
        self.rng = np.random.default_rng(seed)
        self.n_drones = n_drones
        self.pop_size = pop_size
        self.mutation_rate = mutation_rate
        self.population: list[Individual] = []
        self.best: Individual | None = None
        self.history: list[float] = []

    def _random_formation(self) -> np.ndarray:
        return self.rng.uniform(-500, 500, (self.n_drones, 3))

    def _coverage_score(self, positions: np.ndarray) -> float:
        from scipy.spatial import ConvexHull
        try:
            hull = ConvexHull(positions[:, :2])
            return float(hull.volume) / 1e6
        except Exception:
            return 0.0

    def _connectivity_score(self, positions: np.ndarray) -> float:
        n = len(positions)
        connected = 0
        comm_range = 200.0
        for i in range(n):
            for j in range(i + 1, n):
                if np.linalg.norm(positions[i] - positions[j]) < comm_range:
                    connected += 1
        max_edges = n * (n - 1) / 2
        return connected / max(max_edges, 1)

    def _energy_score(self, positions: np.ndarray) -> float:
        centroid = positions.mean(axis=0)
        avg_dist = float(np.mean(np.linalg.norm(positions - centroid, axis=1)))
        return 1.0 / (1.0 + avg_dist / 100.0)

    def fitness(self, positions: np.ndarray) -> float:
        cov = self._coverage_score(positions)
        conn = self._connectivity_score(positions)
        energy = self._energy_score(positions)
        return 0.3 * cov + 0.5 * conn + 0.2 * energy

    def initialize(self) -> None:
        self.population = []
        for _ in range(self.pop_size):
            pos = self._random_formation()
            ind = Individual(positions=pos, fitness=self.fitness(pos))
            self.population.append(ind)
        self.population.sort(key=lambda x: x.fitness, reverse=True)
        self.best = self.population[0]

    def _crossover(self, p1: Individual, p2: Individual) -> Individual:
        mask = self.rng.random(self.n_drones) > 0.5
        child_pos = np.where(mask[:, None], p1.positions, p2.positions)
        return Individual(positions=child_pos)

    def _mutate(self, ind: Individual) -> None:
        for i in range(self.n_drones):
            if self.rng.random() < self.mutation_rate:
                ind.positions[i] += self.rng.normal(0, 50, 3)

    def evolve_step(self) -> float:
        # Tournament selection
        new_pop = [self.best]  # elitism
        while len(new_pop) < self.pop_size:
            t1, t2 = self.rng.choice(len(self.population), 2, replace=False)
            p1 = self.population[t1] if self.population[t1].fitness > self.population[t2].fitness else self.population[t2]
            t3, t4 = self.rng.choice(len(self.population), 2, replace=False)
            p2 = self.population[t3] if self.population[t3].fitness > self.population[t4].fitness else self.population[t4]

            child = self._crossover(p1, p2)
            self._mutate(child)
            child.fitness = self.fitness(child.positions)
            new_pop.append(child)

        self.population = sorted(new_pop, key=lambda x: x.fitness, reverse=True)[:self.pop_size]
        self.best = self.population[0]
        self.history.append(self.best.fitness)
        return self.best.fitness

    def run(self, generations: int = 30) -> dict:
        self.initialize()
        for _ in range(generations):
            self.evolve_step()

        return {
            "generations": generations,
            "best_fitness": round(self.best.fitness, 4) if self.best else 0,
            "initial_fitness": round(self.history[0], 4) if self.history else 0,
            "improvement": round(
                (self.history[-1] - self.history[0]) / max(self.history[0], 1e-9) * 100, 1
            ) if len(self.history) > 1 else 0,
            "n_drones": self.n_drones,
            "pop_size": self.pop_size,
        }


if __name__ == "__main__":
    ga = FormationGA(15, 42)
    result = ga.run(50)
    for k, v in result.items():
        print(f"  {k}: {v}")
