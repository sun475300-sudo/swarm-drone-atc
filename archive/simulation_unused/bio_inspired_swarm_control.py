"""
Phase 484: Bio-Inspired Swarm Control
Biologically inspired algorithms for swarm control: ant colony, bee algorithm, firefly.
"""

import numpy as np
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Optional, Tuple, Any, Callable


class BioAlgorithm(Enum):
    """Bio-inspired algorithms."""

    ANT_COLONY = auto()
    BEE_ALGORITHM = auto_FIREFLY = auto()
    PARTICLE_SWARM = auto()
    GENETIC = auto()


@dataclass
class PheromoneTrail:
    """Ant colony pheromone trail."""

    source: str
    target: str
    intensity: float = 1.0
    evaporation_rate: float = 0.1
    timestamp: float = field(default_factory=time.time)


@dataclass
class FoodSource:
    """Bee algorithm food source."""

    source_id: str
    position: np.ndarray
    quality: float
    visits: int = 0
    employed_bees: int = 0


class BioInspiredSwarmControl:
    """Bio-inspired swarm control algorithms."""

    def __init__(
        self,
        n_agents: int,
        algorithm: BioAlgorithm = BioAlgorithm.ANT_COLONY,
        seed: int = 42,
    ):
        self.rng = np.random.default_rng(seed)
        self.n_agents = n_agents
        self.algorithm = algorithm
        self.pheromones: Dict[Tuple[str, str], PheromoneTrail] = {}
        self.food_sources: List[FoodSource] = []
        self.positions: Dict[str, np.ndarray] = {}
        self.velocities: Dict[str, np.ndarray] = {}
        self._init_agents()

    def _init_agents(self) -> None:
        for i in range(self.n_agents):
            did = f"agent_{i}"
            self.positions[did] = self.rng.uniform(-100, 100, size=3)
            self.velocities[did] = self.rng.uniform(-5, 5, size=3)

    def ant_colony_optimize(
        self, distance_matrix: np.ndarray, n_iterations: int = 100
    ) -> Tuple[List[int], float]:
        n = distance_matrix.shape[0]
        pheromone = np.ones((n, n)) * 0.1
        alpha, beta = 1.0, 2.0
        best_path = list(range(n))
        best_cost = np.inf
        for _ in range(n_iterations):
            paths = []
            for _ in range(self.n_agents):
                path = [0]
                unvisited = set(range(1, n))
                while unvisited:
                    current = path[-1]
                    probs = []
                    for j in unvisited:
                        tau = pheromone[current, j] ** alpha
                        eta = (1.0 / (distance_matrix[current, j] + 1e-8)) ** beta
                        probs.append(tau * eta)
                    probs = np.array(probs)
                    probs /= probs.sum()
                    next_node = self.rng.choice(list(unvisited), p=probs)
                    path.append(next_node)
                    unvisited.remove(next_node)
                paths.append(path)
            pheromone *= 0.9
            for path in paths:
                cost = sum(
                    distance_matrix[path[i], path[i + 1]] for i in range(len(path) - 1)
                )
                if cost < best_cost:
                    best_cost = cost
                    best_path = path[:]
                for i in range(len(path) - 1):
                    pheromone[path[i], path[i + 1]] += 1.0 / (cost + 1e-8)
        return best_path, best_cost

    def bee_algorithm_optimize(
        self,
        objective_fn: Callable[[np.ndarray], float],
        bounds: Tuple[np.ndarray, np.ndarray],
        n_iterations: int = 50,
    ) -> Tuple[np.ndarray, float]:
        n_sources = self.n_agents // 2
        dim = len(bounds[0])
        for i in range(n_sources):
            pos = bounds[0] + self.rng.random(dim) * (bounds[1] - bounds[0])
            quality = -objective_fn(pos)
            self.food_sources.append(FoodSource(f"src_{i}", pos, quality))
        best_pos = None
        best_val = np.inf
        for _ in range(n_iterations):
            for src in self.food_sources:
                new_pos = src.position + self.rng.uniform(-1, 1, dim) * 0.1
                new_pos = np.clip(new_pos, bounds[0], bounds[1])
                new_val = objective_fn(new_pos)
                if -new_val > src.quality:
                    src.position = new_pos
                    src.quality = -new_val
                if new_val < best_val:
                    best_val = new_val
                    best_pos = new_pos.copy()
            self.food_sources.sort(key=lambda x: x.quality, reverse=True)
            self.food_sources = self.food_sources[:n_sources]
        return best_pos if best_pos is not None else np.zeros(dim), best_val

    def firefly_optimize(
        self,
        objective_fn: Callable[[np.ndarray], float],
        bounds: Tuple[np.ndarray, np.ndarray],
        n_iterations: int = 50,
    ) -> Tuple[np.ndarray, float]:
        dim = len(bounds[0])
        positions = [
            bounds[0] + self.rng.random(dim) * (bounds[1] - bounds[0])
            for _ in range(self.n_agents)
        ]
        intensities = [objective_fn(p) for p in positions]
        best_idx = np.argmin(intensities)
        best_pos = positions[best_idx].copy()
        best_val = intensities[best_idx]
        beta0, gamma = 1.0, 0.01
        for _ in range(n_iterations):
            for i in range(self.n_agents):
                for j in range(self.n_agents):
                    if intensities[j] < intensities[i]:
                        r = np.linalg.norm(positions[i] - positions[j])
                        beta = beta0 * np.exp(-gamma * r**2)
                        positions[i] += beta * (
                            positions[j] - positions[i]
                        ) + self.rng.uniform(-0.1, 0.1, dim)
                        positions[i] = np.clip(positions[i], bounds[0], bounds[1])
                        intensities[i] = objective_fn(positions[i])
                        if intensities[i] < best_val:
                            best_val = intensities[i]
                            best_pos = positions[i].copy()
        return best_pos, best_val

    def pso_optimize(
        self,
        objective_fn: Callable[[np.ndarray], float],
        bounds: Tuple[np.ndarray, np.ndarray],
        n_iterations: int = 50,
    ) -> Tuple[np.ndarray, float]:
        dim = len(bounds[0])
        positions = [
            bounds[0] + self.rng.random(dim) * (bounds[1] - bounds[0])
            for _ in range(self.n_agents)
        ]
        velocities = [self.rng.uniform(-1, 1, dim) for _ in range(self.n_agents)]
        personal_best = [p.copy() for p in positions]
        personal_best_vals = [objective_fn(p) for p in positions]
        global_best_idx = np.argmin(personal_best_vals)
        global_best = personal_best[global_best_idx].copy()
        global_best_val = personal_best_vals[global_best_idx]
        w, c1, c2 = 0.7, 1.5, 1.5
        for _ in range(n_iterations):
            for i in range(self.n_agents):
                r1, r2 = self.rng.random(dim), self.rng.random(dim)
                velocities[i] = (
                    w * velocities[i]
                    + c1 * r1 * (personal_best[i] - positions[i])
                    + c2 * r2 * (global_best - positions[i])
                )
                positions[i] += velocities[i]
                positions[i] = np.clip(positions[i], bounds[0], bounds[1])
                val = objective_fn(positions[i])
                if val < personal_best_vals[i]:
                    personal_best[i] = positions[i].copy()
                    personal_best_vals[i] = val
                    if val < global_best_val:
                        global_best = positions[i].copy()
                        global_best_val = val
        return global_best, global_best_val

    def optimize(
        self,
        objective_fn: Callable[[np.ndarray], float],
        bounds: Tuple[np.ndarray, np.ndarray],
        n_iterations: int = 50,
    ) -> Tuple[np.ndarray, float]:
        if self.algorithm == BioAlgorithm.ANT_COLONY:
            n = max(5, self.n_agents)
            dist_matrix = np.random.uniform(1, 100, (n, n))
            path, cost = self.ant_colony_optimize(dist_matrix, n_iterations)
            return np.array(path[: len(bounds[0])]), cost
        elif self.algorithm == BioAlgorithm.BEE_ALGORITHM:
            return self.bee_algorithm_optimize(objective_fn, bounds, n_iterations)
        elif self.algorithm == BioAlgorithm.FIREFLY:
            return self.firefly_optimize(objective_fn, bounds, n_iterations)
        else:
            return self.pso_optimize(objective_fn, bounds, n_iterations)


if __name__ == "__main__":
    bio = BioInspiredSwarmControl(
        n_agents=20, algorithm=BioAlgorithm.PARTICLE_SWARM, seed=42
    )
    objective = lambda x: np.sum(x**2)
    bounds = (np.array([-10, -10, -10]), np.array([10, 10, 10]))
    best_pos, best_val = bio.optimize(objective, bounds, n_iterations=30)
    print(f"Best position: {best_pos}")
    print(f"Best value: {best_val:.6f}")
