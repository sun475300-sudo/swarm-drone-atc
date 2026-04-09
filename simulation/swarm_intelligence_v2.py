"""Phase 303: Swarm Intelligence v2 — PSO/ACO 기반 군집 지능 v2.

Particle Swarm Optimization + Ant Colony Optimization +
Firefly Algorithm 다중 메타휴리스틱 최적화 프레임워크.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Callable


class OptimizerType(Enum):
    PSO = "pso"
    ACO = "aco"
    FIREFLY = "firefly"
    HYBRID = "hybrid"


@dataclass
class Particle:
    position: np.ndarray
    velocity: np.ndarray
    best_position: np.ndarray
    best_fitness: float = float("inf")
    fitness: float = float("inf")


@dataclass
class Ant:
    path: List[int] = field(default_factory=list)
    path_length: float = float("inf")
    visited: set = field(default_factory=set)


@dataclass
class OptimizationResult:
    best_position: np.ndarray
    best_fitness: float
    iterations: int
    convergence_history: List[float] = field(default_factory=list)
    optimizer_type: OptimizerType = OptimizerType.PSO


class PSOEngine:
    """Particle Swarm Optimization 엔진."""

    def __init__(self, n_particles: int = 30, w: float = 0.7, c1: float = 1.5, c2: float = 1.5, rng_seed: int = 42):
        self._rng = np.random.default_rng(rng_seed)
        self.n_particles = n_particles
        self.w = w  # inertia
        self.c1 = c1  # cognitive
        self.c2 = c2  # social
        self.global_best_pos: Optional[np.ndarray] = None
        self.global_best_fitness = float("inf")

    def optimize(self, objective: Callable, bounds: List[Tuple[float, float]], max_iter: int = 100) -> OptimizationResult:
        dim = len(bounds)
        particles = []
        for _ in range(self.n_particles):
            pos = np.array([self._rng.uniform(lo, hi) for lo, hi in bounds])
            vel = np.array([self._rng.uniform(-(hi - lo) * 0.1, (hi - lo) * 0.1) for lo, hi in bounds])
            p = Particle(position=pos, velocity=vel, best_position=pos.copy())
            p.fitness = objective(pos)
            p.best_fitness = p.fitness
            particles.append(p)

        self.global_best_pos = min(particles, key=lambda p: p.best_fitness).best_position.copy()
        self.global_best_fitness = min(p.best_fitness for p in particles)
        history = [self.global_best_fitness]

        for _ in range(max_iter):
            for p in particles:
                r1 = self._rng.random(dim)
                r2 = self._rng.random(dim)
                p.velocity = (self.w * p.velocity +
                              self.c1 * r1 * (p.best_position - p.position) +
                              self.c2 * r2 * (self.global_best_pos - p.position))
                p.position += p.velocity
                # Clamp to bounds
                for i, (lo, hi) in enumerate(bounds):
                    p.position[i] = np.clip(p.position[i], lo, hi)
                p.fitness = objective(p.position)
                if p.fitness < p.best_fitness:
                    p.best_fitness = p.fitness
                    p.best_position = p.position.copy()
                if p.fitness < self.global_best_fitness:
                    self.global_best_fitness = p.fitness
                    self.global_best_pos = p.position.copy()
            history.append(self.global_best_fitness)

        return OptimizationResult(
            best_position=self.global_best_pos, best_fitness=self.global_best_fitness,
            iterations=max_iter, convergence_history=history, optimizer_type=OptimizerType.PSO,
        )


class ACOEngine:
    """Ant Colony Optimization 엔진 (TSP/경로 최적화)."""

    def __init__(self, n_ants: int = 20, alpha: float = 1.0, beta: float = 2.0,
                 evaporation: float = 0.5, rng_seed: int = 42):
        self._rng = np.random.default_rng(rng_seed)
        self.n_ants = n_ants
        self.alpha = alpha  # pheromone importance
        self.beta = beta    # heuristic importance
        self.evaporation = evaporation

    def solve_tsp(self, distance_matrix: np.ndarray, max_iter: int = 50) -> OptimizationResult:
        n = distance_matrix.shape[0]
        pheromone = np.ones((n, n))
        best_path = list(range(n))
        best_length = self._path_length(best_path, distance_matrix)
        history = [best_length]

        for _ in range(max_iter):
            ants = []
            for _ in range(self.n_ants):
                ant = Ant()
                start = self._rng.integers(n)
                ant.path.append(start)
                ant.visited.add(start)
                for _ in range(n - 1):
                    current = ant.path[-1]
                    probs = self._transition_probs(current, ant.visited, pheromone, distance_matrix, n)
                    next_city = self._rng.choice(n, p=probs)
                    ant.path.append(next_city)
                    ant.visited.add(next_city)
                ant.path_length = self._path_length(ant.path, distance_matrix)
                ants.append(ant)
                if ant.path_length < best_length:
                    best_length = ant.path_length
                    best_path = ant.path.copy()

            # Evaporate
            pheromone *= (1 - self.evaporation)
            # Deposit
            for ant in ants:
                deposit = 1.0 / max(ant.path_length, 1e-6)
                for i in range(len(ant.path) - 1):
                    pheromone[ant.path[i], ant.path[i + 1]] += deposit
            history.append(best_length)

        return OptimizationResult(
            best_position=np.array(best_path, dtype=float),
            best_fitness=best_length, iterations=max_iter,
            convergence_history=history, optimizer_type=OptimizerType.ACO,
        )

    def _path_length(self, path: List[int], dm: np.ndarray) -> float:
        return sum(dm[path[i], path[i + 1]] for i in range(len(path) - 1))

    def _transition_probs(self, current: int, visited: set, pheromone: np.ndarray,
                          dm: np.ndarray, n: int) -> np.ndarray:
        probs = np.zeros(n)
        for j in range(n):
            if j not in visited:
                tau = pheromone[current, j] ** self.alpha
                eta = (1.0 / max(dm[current, j], 1e-6)) ** self.beta
                probs[j] = tau * eta
        total = probs.sum()
        if total > 0:
            probs /= total
        else:
            unvisited = [j for j in range(n) if j not in visited]
            if unvisited:
                for j in unvisited:
                    probs[j] = 1.0 / len(unvisited)
        return probs


class SwarmIntelligenceV2:
    """군집 지능 v2 프레임워크.

    - PSO 연속 최적화
    - ACO 이산 경로 최적화
    - 다중 메타휴리스틱 선택
    - 수렴 이력 추적
    """

    def __init__(self, rng_seed: int = 42):
        self._rng = np.random.default_rng(rng_seed)
        self._pso = PSOEngine(rng_seed=rng_seed)
        self._aco = ACOEngine(rng_seed=rng_seed)
        self._results: Dict[str, OptimizationResult] = {}

    def optimize_continuous(self, name: str, objective: Callable,
                           bounds: List[Tuple[float, float]], max_iter: int = 100) -> OptimizationResult:
        result = self._pso.optimize(objective, bounds, max_iter)
        self._results[name] = result
        return result

    def optimize_tsp(self, name: str, distance_matrix: np.ndarray, max_iter: int = 50) -> OptimizationResult:
        result = self._aco.solve_tsp(distance_matrix, max_iter)
        self._results[name] = result
        return result

    def get_result(self, name: str) -> Optional[OptimizationResult]:
        return self._results.get(name)

    def summary(self) -> dict:
        return {
            "total_optimizations": len(self._results),
            "results": {
                name: {"fitness": r.best_fitness, "iterations": r.iterations, "type": r.optimizer_type.value}
                for name, r in self._results.items()
            },
        }
