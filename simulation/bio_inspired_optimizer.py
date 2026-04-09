"""
Phase 475: Bio-Inspired Optimizer
개미군집(ACO v2), 벌집(ABC), 반딧불이(FA) 최적화.
"""

import numpy as np
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Callable, Optional, Tuple


class BioAlgorithm(Enum):
    ACO = "ant_colony"
    ABC = "artificial_bee"
    FIREFLY = "firefly"
    WHALE = "whale"
    BAT = "bat"


@dataclass
class Solution:
    position: np.ndarray
    fitness: float
    algorithm: str


class AntColonyV2:
    def __init__(self, n_ants: int = 30, n_dim: int = 2, evaporation: float = 0.5,
                 alpha: float = 1.0, beta: float = 2.0, rng: np.random.Generator = None):
        self.n_ants = n_ants
        self.n_dim = n_dim
        self.evaporation = evaporation
        self.alpha = alpha
        self.beta = beta
        self.rng = rng or np.random.default_rng(42)
        self.pheromone = np.ones(n_dim) * 0.1

    def optimize(self, func: Callable, bounds: np.ndarray, max_iter: int = 50) -> Solution:
        best_pos = self.rng.uniform(bounds[:, 0], bounds[:, 1])
        best_fit = func(best_pos)
        for _ in range(max_iter):
            for _ in range(self.n_ants):
                pos = self.rng.uniform(bounds[:, 0], bounds[:, 1])
                pos += self.pheromone * self.rng.standard_normal(self.n_dim) * 0.1
                pos = np.clip(pos, bounds[:, 0], bounds[:, 1])
                fit = func(pos)
                if fit < best_fit:
                    best_fit = fit
                    best_pos = pos.copy()
            self.pheromone *= (1 - self.evaporation)
            self.pheromone += 1.0 / (best_fit + 1e-10) * 0.1
        return Solution(best_pos, best_fit, "aco")


class ArtificialBeeColony:
    def __init__(self, n_bees: int = 30, n_dim: int = 2, limit: int = 10,
                 rng: np.random.Generator = None):
        self.n_bees = n_bees
        self.n_dim = n_dim
        self.limit = limit
        self.rng = rng or np.random.default_rng(42)

    def optimize(self, func: Callable, bounds: np.ndarray, max_iter: int = 50) -> Solution:
        pop = self.rng.uniform(bounds[:, 0], bounds[:, 1], (self.n_bees, self.n_dim))
        fitness = np.array([func(p) for p in pop])
        trials = np.zeros(self.n_bees)
        best_idx = np.argmin(fitness)
        best_pos = pop[best_idx].copy()
        best_fit = fitness[best_idx]

        for _ in range(max_iter):
            for i in range(self.n_bees):
                k = self.rng.integers(0, self.n_bees)
                while k == i: k = self.rng.integers(0, self.n_bees)
                j = self.rng.integers(0, self.n_dim)
                new = pop[i].copy()
                new[j] += self.rng.uniform(-1, 1) * (pop[i, j] - pop[k, j])
                new = np.clip(new, bounds[:, 0], bounds[:, 1])
                new_fit = func(new)
                if new_fit < fitness[i]:
                    pop[i] = new
                    fitness[i] = new_fit
                    trials[i] = 0
                else:
                    trials[i] += 1

            for i in range(self.n_bees):
                if trials[i] > self.limit:
                    pop[i] = self.rng.uniform(bounds[:, 0], bounds[:, 1])
                    fitness[i] = func(pop[i])
                    trials[i] = 0

            idx = np.argmin(fitness)
            if fitness[idx] < best_fit:
                best_fit = fitness[idx]
                best_pos = pop[idx].copy()

        return Solution(best_pos, best_fit, "abc")


class FireflyAlgorithm:
    def __init__(self, n_fireflies: int = 30, n_dim: int = 2,
                 alpha: float = 0.5, beta0: float = 1.0, gamma: float = 1.0,
                 rng: np.random.Generator = None):
        self.n = n_fireflies
        self.n_dim = n_dim
        self.alpha = alpha
        self.beta0 = beta0
        self.gamma = gamma
        self.rng = rng or np.random.default_rng(42)

    def optimize(self, func: Callable, bounds: np.ndarray, max_iter: int = 50) -> Solution:
        pop = self.rng.uniform(bounds[:, 0], bounds[:, 1], (self.n, self.n_dim))
        fitness = np.array([func(p) for p in pop])

        for _ in range(max_iter):
            for i in range(self.n):
                for j in range(self.n):
                    if fitness[j] < fitness[i]:
                        r = np.linalg.norm(pop[i] - pop[j])
                        beta = self.beta0 * np.exp(-self.gamma * r**2)
                        pop[i] += beta * (pop[j] - pop[i]) + self.alpha * self.rng.standard_normal(self.n_dim)
                        pop[i] = np.clip(pop[i], bounds[:, 0], bounds[:, 1])
                        fitness[i] = func(pop[i])

        best_idx = np.argmin(fitness)
        return Solution(pop[best_idx], fitness[best_idx], "firefly")


class BioInspiredOptimizer:
    """Unified bio-inspired optimization engine."""

    def __init__(self, algorithm: BioAlgorithm = BioAlgorithm.FIREFLY,
                 n_dim: int = 2, seed: int = 42):
        self.algorithm = algorithm
        self.n_dim = n_dim
        self.rng = np.random.default_rng(seed)
        self.results: List[Solution] = []

    def optimize(self, func: Callable, bounds: np.ndarray,
                 max_iter: int = 50, pop_size: int = 30) -> Solution:
        if self.algorithm == BioAlgorithm.ACO:
            opt = AntColonyV2(pop_size, self.n_dim, rng=self.rng)
        elif self.algorithm == BioAlgorithm.ABC:
            opt = ArtificialBeeColony(pop_size, self.n_dim, rng=self.rng)
        else:
            opt = FireflyAlgorithm(pop_size, self.n_dim, rng=self.rng)

        result = opt.optimize(func, bounds, max_iter)
        self.results.append(result)
        return result

    def compare_all(self, func: Callable, bounds: np.ndarray,
                    max_iter: int = 50) -> Dict[str, Solution]:
        results = {}
        for algo in [BioAlgorithm.ACO, BioAlgorithm.ABC, BioAlgorithm.FIREFLY]:
            self.algorithm = algo
            results[algo.value] = self.optimize(func, bounds, max_iter)
        return results

    def summary(self) -> Dict:
        return {
            "algorithm": self.algorithm.value,
            "dimensions": self.n_dim,
            "runs": len(self.results),
            "best_fitness": min((r.fitness for r in self.results), default=0),
        }
