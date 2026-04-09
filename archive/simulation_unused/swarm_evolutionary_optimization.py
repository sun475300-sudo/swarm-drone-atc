"""
Phase 481: Swarm Evolutionary Optimization
Evolutionary algorithms for optimizing swarm behavior and parameters.
"""

import numpy as np
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Optional, Tuple, Any, Callable


class SelectionMethod(Enum):
    """Selection methods."""

    TOURNAMENT = auto()
    ROULETTE = auto()
    RANK = auto()
    ELITISM = auto()


class CrossoverType(Enum):
    """Crossover types."""

    SINGLE_POINT = auto()
    TWO_POINT = auto()
    UNIFORM = auto()
    ARITHMETIC = auto()


@dataclass
class Individual:
    """Evolutionary individual."""

    individual_id: str
    genome: np.ndarray
    fitness: float = 0.0
    age: int = 0
    parent_ids: List[str] = field(default_factory=list)


@dataclass
class Population:
    """Population of individuals."""

    generation: int
    individuals: List[Individual]
    best_fitness: float = 0.0
    avg_fitness: float = 0.0
    diversity: float = 0.0


@dataclass
class EvolutionResult:
    """Evolution result."""

    best_individual: Individual
    fitness_history: List[float]
    diversity_history: List[float]
    generations: int
    converged: bool


class SwarmEvolutionaryOptimizer:
    """Evolutionary optimizer for swarm parameters."""

    def __init__(self, n_individuals: int = 50, genome_size: int = 10, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_individuals = n_individuals
        self.genome_size = genome_size
        self.population: Optional[Population] = None
        self.fitness_history: List[float] = []
        self.diversity_history: List[float] = []
        self.selection_method = SelectionMethod.TOURNAMENT
        self.crossover_type = CrossoverType.UNIFORM
        self.mutation_rate = 0.1
        self.crossover_rate = 0.8
        self._init_population()

    def _init_population(self) -> None:
        individuals = []
        for i in range(self.n_individuals):
            genome = self.rng.uniform(-1, 1, self.genome_size)
            ind = Individual(f"ind_{i}", genome)
            individuals.append(ind)
        self.population = Population(0, individuals)

    def evaluate_fitness(self, fitness_fn: Callable[[np.ndarray], float]) -> None:
        for ind in self.population.individuals:
            ind.fitness = fitness_fn(ind.genome)
        self.population.best_fitness = max(
            ind.fitness for ind in self.population.individuals
        )
        self.population.avg_fitness = np.mean(
            [ind.fitness for ind in self.population.individuals]
        )
        genomes = np.array([ind.genome for ind in self.population.individuals])
        self.population.diversity = float(np.mean(np.std(genomes, axis=0)))

    def _tournament_select(self, k: int = 3) -> Individual:
        candidates = self.rng.choice(self.population.individuals, k, replace=False)
        return max(candidates, key=lambda x: x.fitness)

    def _roulette_select(self) -> Individual:
        fitnesses = np.array(
            [max(0, ind.fitness) for ind in self.population.individuals]
        )
        total = fitnesses.sum()
        if total == 0:
            return self.rng.choice(self.population.individuals)
        probs = fitnesses / total
        return self.rng.choice(self.population.individuals, p=probs)

    def _select_parent(self) -> Individual:
        if self.selection_method == SelectionMethod.TOURNAMENT:
            return self._tournament_select()
        elif self.selection_method == SelectionMethod.ROULETTE:
            return self._roulette_select()
        else:
            return self._tournament_select()

    def _crossover(
        self, parent1: Individual, parent2: Individual
    ) -> Tuple[np.ndarray, np.ndarray]:
        if self.rng.random() > self.crossover_rate:
            return parent1.genome.copy(), parent2.genome.copy()
        if self.crossover_type == CrossoverType.SINGLE_POINT:
            point = self.rng.integers(1, self.genome_size)
            child1 = np.concatenate([parent1.genome[:point], parent2.genome[point:]])
            child2 = np.concatenate([parent2.genome[:point], parent1.genome[point:]])
        elif self.crossover_type == CrossoverType.TWO_POINT:
            p1, p2 = sorted(self.rng.choice(self.genome_size, 2, replace=False))
            child1 = parent1.genome.copy()
            child2 = parent2.genome.copy()
            child1[p1:p2] = parent2.genome[p1:p2]
            child2[p1:p2] = parent1.genome[p1:p2]
        else:
            mask = self.rng.random(self.genome_size) < 0.5
            child1 = np.where(mask, parent1.genome, parent2.genome)
            child2 = np.where(mask, parent2.genome, parent1.genome)
        return child1, child2

    def _mutate(self, genome: np.ndarray) -> np.ndarray:
        mask = self.rng.random(self.genome_size) < self.mutation_rate
        noise = self.rng.standard_normal(self.genome_size) * 0.1
        genome = genome + mask * noise
        return np.clip(genome, -1, 1)

    def evolve(
        self, fitness_fn: Callable[[np.ndarray], float], n_generations: int = 100
    ) -> EvolutionResult:
        for gen in range(n_generations):
            self.evaluate_fitness(fitness_fn)
            self.fitness_history.append(self.population.best_fitness)
            self.diversity_history.append(self.population.diversity)
            new_individuals = []
            elite = max(self.population.individuals, key=lambda x: x.fitness)
            elite_copy = Individual(f"elite_{gen}", elite.genome.copy(), elite.fitness)
            new_individuals.append(elite_copy)
            while len(new_individuals) < self.n_individuals:
                p1 = self._select_parent()
                p2 = self._select_parent()
                c1_genome, c2_genome = self._crossover(p1, p2)
                c1_genome = self._mutate(c1_genome)
                c2_genome = self._mutate(c2_genome)
                c1 = Individual(
                    f"ind_{gen}_{len(new_individuals)}",
                    c1_genome,
                    parent_ids=[p1.individual_id, p2.individual_id],
                )
                new_individuals.append(c1)
                if len(new_individuals) < self.n_individuals:
                    c2 = Individual(
                        f"ind_{gen}_{len(new_individuals)}",
                        c2_genome,
                        parent_ids=[p1.individual_id, p2.individual_id],
                    )
                    new_individuals.append(c2)
            self.population.individuals = new_individuals
            self.population.generation = gen + 1
        self.evaluate_fitness(fitness_fn)
        best = max(self.population.individuals, key=lambda x: x.fitness)
        converged = len(self.fitness_history) > 10 and (
            np.std(self.fitness_history[-10:]) < 0.01
        )
        return EvolutionResult(
            best,
            self.fitness_history,
            self.diversity_history,
            self.population.generation,
            converged,
        )


class SwarmParameterEvolver:
    """Evolves swarm control parameters."""

    def __init__(self, n_drones: int, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_drones = n_drones
        self.optimizer = SwarmEvolutionaryOptimizer(
            n_individuals=30, genome_size=8, seed=seed
        )

    def _swarm_fitness(self, genome: np.ndarray) -> float:
        separation_weight = genome[0] * 2 + 2
        alignment_weight = genome[1] + 1
        cohesion_weight = genome[2] + 1
        max_speed = genome[3] * 10 + 15
        perception_range = genome[4] * 50 + 100
        positions = self.rng.uniform(-100, 100, (self.n_drones, 3))
        velocities = self.rng.uniform(-max_speed, max_speed, (self.n_drones, 3))
        centroid = positions.mean(axis=0)
        spread = np.mean(np.linalg.norm(positions - centroid, axis=1))
        vel_norms = np.linalg.norm(velocities, axis=1)
        normalized = velocities / (vel_norms[:, None] + 1e-8)
        alignment = np.mean(np.abs(normalized @ normalized.T))
        min_dist = np.inf
        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                dist = np.linalg.norm(positions[i] - positions[j])
                min_dist = min(min_dist, dist)
        fitness = (
            alignment * alignment_weight
            + (1.0 / (1.0 + spread / 100)) * cohesion_weight
        )
        if min_dist < 5:
            fitness -= 10
        return fitness

    def evolve_parameters(self, n_generations: int = 50) -> EvolutionResult:
        return self.optimizer.evolve(self._swarm_fitness, n_generations)

    def get_optimal_params(self) -> Dict[str, float]:
        result = self.evolve_parameters(30)
        genome = result.best_individual.genome
        return {
            "separation_weight": genome[0] * 2 + 2,
            "alignment_weight": genome[1] + 1,
            "cohesion_weight": genome[2] + 1,
            "max_speed": genome[3] * 10 + 15,
            "perception_range": genome[4] * 50 + 100,
            "fitness": result.best_individual.fitness,
            "generations": result.generations,
        }


if __name__ == "__main__":
    evolver = SwarmParameterEvolver(n_drones=10, seed=42)
    params = evolver.get_optimal_params()
    print(f"Optimal params: {params}")
