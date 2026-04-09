"""
유전 알고리즘 경로 플래너
========================
GA 기반 다중 드론 경로 최적화 (교차/돌연변이/선택).

사용법:
    gp = GeneticPathPlanner(seed=42)
    gp.set_environment(obstacles=[(100,100,0)], nfz=[(500,500,100)])
    best = gp.optimize(start=(0,0,50), goal=(800,800,50), generations=100)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import numpy as np


@dataclass
class Individual:
    waypoints: list[tuple[float, float, float]]
    fitness: float = 0.0


class GeneticPathPlanner:
    def __init__(self, pop_size: int = 50, n_waypoints: int = 5,
                 mutation_rate: float = 0.1, crossover_rate: float = 0.7,
                 seed: int = 42) -> None:
        self._rng = np.random.default_rng(seed)
        self.pop_size = pop_size
        self.n_waypoints = n_waypoints
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self._obstacles: list[tuple[float, float, float]] = []
        self._nfz: list[tuple[float, float, float, float]] = []  # (x,y,z,radius)
        self._plans: int = 0

    def set_environment(self, obstacles: list | None = None,
                        nfz: list | None = None) -> None:
        self._obstacles = obstacles or []
        self._nfz = nfz or []

    def _random_path(self, start: tuple, goal: tuple) -> list[tuple[float, float, float]]:
        path = [start]
        for i in range(self.n_waypoints):
            t = (i + 1) / (self.n_waypoints + 1)
            base = tuple(s + (g - s) * t for s, g in zip(start, goal))
            noise = tuple(self._rng.normal(0, 50) for _ in range(3))
            wp = tuple(round(b + n, 1) for b, n in zip(base, noise))
            path.append(wp)
        path.append(goal)
        return path

    def _path_length(self, path: list) -> float:
        total = 0.0
        for i in range(1, len(path)):
            total += np.sqrt(sum((a - b) ** 2 for a, b in zip(path[i-1], path[i])))
        return total

    def _obstacle_penalty(self, path: list) -> float:
        penalty = 0.0
        for wp in path:
            for obs in self._obstacles:
                dist = np.sqrt(sum((a - b) ** 2 for a, b in zip(wp, obs[:3])))
                if dist < 30:
                    penalty += (30 - dist) * 10
            for nfz in self._nfz:
                dist = np.sqrt((wp[0] - nfz[0]) ** 2 + (wp[1] - nfz[1]) ** 2)
                radius = nfz[3] if len(nfz) > 3 else 100
                if dist < radius:
                    penalty += (radius - dist) * 20
        return penalty

    def _smoothness(self, path: list) -> float:
        if len(path) < 3:
            return 0
        total = 0.0
        for i in range(1, len(path) - 1):
            v1 = tuple(path[i][j] - path[i-1][j] for j in range(3))
            v2 = tuple(path[i+1][j] - path[i][j] for j in range(3))
            dot = sum(a * b for a, b in zip(v1, v2))
            m1 = max(np.sqrt(sum(a**2 for a in v1)), 1e-6)
            m2 = max(np.sqrt(sum(a**2 for a in v2)), 1e-6)
            cos_angle = np.clip(dot / (m1 * m2), -1, 1)
            total += 1 - cos_angle
        return total

    def _fitness(self, individual: Individual) -> float:
        length = self._path_length(individual.waypoints)
        penalty = self._obstacle_penalty(individual.waypoints)
        smooth = self._smoothness(individual.waypoints)
        return 1.0 / (1.0 + length * 0.01 + penalty + smooth * 5)

    def _crossover(self, p1: Individual, p2: Individual) -> Individual:
        if self._rng.random() > self.crossover_rate:
            return Individual(waypoints=list(p1.waypoints))
        # 단일점 교차
        point = self._rng.integers(1, len(p1.waypoints) - 1)
        child_wps = list(p1.waypoints[:point]) + list(p2.waypoints[point:])
        return Individual(waypoints=child_wps)

    def _mutate(self, ind: Individual) -> None:
        for i in range(1, len(ind.waypoints) - 1):
            if self._rng.random() < self.mutation_rate:
                noise = tuple(self._rng.normal(0, 20) for _ in range(3))
                ind.waypoints[i] = tuple(
                    round(ind.waypoints[i][j] + noise[j], 1) for j in range(3)
                )

    def _tournament_select(self, pop: list[Individual], k: int = 3) -> Individual:
        candidates = self._rng.choice(len(pop), size=min(k, len(pop)), replace=False)
        return max((pop[i] for i in candidates), key=lambda x: x.fitness)

    def optimize(self, start: tuple[float, float, float],
                 goal: tuple[float, float, float],
                 generations: int = 100) -> dict[str, Any]:
        # 초기 집단 생성
        population = [Individual(waypoints=self._random_path(start, goal))
                      for _ in range(self.pop_size)]

        for ind in population:
            ind.fitness = self._fitness(ind)

        best_ever = max(population, key=lambda x: x.fitness)

        for gen in range(generations):
            new_pop = []
            for _ in range(self.pop_size):
                p1 = self._tournament_select(population)
                p2 = self._tournament_select(population)
                child = self._crossover(p1, p2)
                self._mutate(child)
                child.fitness = self._fitness(child)
                new_pop.append(child)

            # 엘리트 보존
            new_pop[0] = Individual(waypoints=list(best_ever.waypoints),
                                    fitness=best_ever.fitness)
            population = new_pop
            gen_best = max(population, key=lambda x: x.fitness)
            if gen_best.fitness > best_ever.fitness:
                best_ever = gen_best

        self._plans += 1
        return {
            "path": best_ever.waypoints,
            "fitness": round(best_ever.fitness, 6),
            "length": round(self._path_length(best_ever.waypoints), 1),
            "generations": generations,
        }

    def summary(self) -> dict[str, Any]:
        return {
            "plans_generated": self._plans,
            "pop_size": self.pop_size,
            "obstacles": len(self._obstacles),
            "nfz_zones": len(self._nfz),
        }
