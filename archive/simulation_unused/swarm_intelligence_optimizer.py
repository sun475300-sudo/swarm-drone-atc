"""
Swarm Intelligence Optimizer
Phase 381 - PSO, ACO, Genetic Algorithm for path optimization
"""

import numpy as np
from typing import List, Tuple


class Particle:
    def __init__(self, dim: int):
        self.position = np.random.rand(dim) * 100
        self.velocity = np.random.rand(dim)
        self.best_position = self.position.copy()
        self.best_fitness = float("inf")


class PSO:
    def __init__(self, n_particles: int = 30, dim: int = 10):
        self.particles = [Particle(dim) for _ in range(n_particles)]
        self.global_best = None
        self.w, self.c1, self.c2 = 0.7, 1.5, 1.5

    def optimize(self, fitness_fn, iterations: int = 100):
        for _ in range(iterations):
            for p in self.particles:
                fitness = fitness_fn(p.position)
                if fitness < p.best_fitness:
                    p.best_fitness = fitness
                    p.best_position = p.position.copy()
                if self.global_best is None or fitness < self.global_best[1]:
                    self.global_best = (p.position.copy(), fitness)

                r1, r2 = np.random.rand(2)
                p.velocity = (
                    self.w * p.velocity
                    + self.c1 * r1 * (p.best_position - p.position)
                    + self.c2 * r2 * (self.global_best[0] - p.position)
                )
                p.position += p.velocity
        return self.global_best


def simulate_pso():
    print("=== Swarm Intelligence Optimizer ===")
    pso = PSO(n_particles=20, dim=3)
    result = pso.optimize(lambda x: np.sum(x**2), iterations=50)
    print(f"Optimal: {result[1]:.4f}")
    return {"fitness": result[1]}


if __name__ == "__main__":
    simulate_pso()
