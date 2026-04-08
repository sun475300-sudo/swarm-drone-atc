"""
Multi-Objective Optimization Engine
Phase 351 - NSGA-II, MOEA/D, Pareto Front Analysis
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Callable, Optional
from collections import defaultdict
import random


@dataclass
class Individual:
    genes: np.ndarray
    objectives: np.ndarray
    rank: int = 0
    crowding_distance: float = 0.0
    dominance_count: int = 0
    dominated_solutions: List[int] = field(default_factory=list)


class NSGAII:
    def __init__(
        self,
        num_objectives: int = 2,
        population_size: int = 100,
        num_generations: int = 100,
        gene_bounds: Tuple[float, float] = (-10, 10),
        num_genes: int = 10,
    ):
        self.num_objectives = num_objectives
        self.population_size = population_size
        self.num_generations = num_generations
        self.gene_bounds = gene_bounds
        self.num_genes = num_genes
        self.population: List[Individual] = []

    def initialize_population(self):
        self.population = []
        for _ in range(self.population_size):
            genes = np.random.uniform(
                self.gene_bounds[0], self.gene_bounds[1], self.num_genes
            )
            individual = Individual(
                genes=genes, objectives=np.zeros(self.num_objectives)
            )
            self.population.append(individual)

    def evaluate(self, individual: Individual, objectives: List[Callable]):
        individual.objectives = np.array([obj(individual.genes) for obj in objectives])

    def dominates(self, ind1: Individual, ind2: Individual) -> bool:
        better_in_any = False
        for i in range(self.num_objectives):
            if ind1.objectives[i] > ind2.objectives[i]:
                return False
            elif ind1.objectives[i] < ind2.objectives[i]:
                better_in_any = True
        return better_in_any

    def fast_non_dominated_sort(self):
        for i, ind in enumerate(self.population):
            ind.dominated_solutions = []
            ind.dominance_count = 0

        for i in range(len(self.population)):
            for j in range(len(self.population)):
                if i != j:
                    if self.dominates(self.population[i], self.population[j]):
                        self.population[i].dominated_solutions.append(j)
                    elif self.dominates(self.population[j], self.population[i]):
                        self.population[i].dominance_count += 1

        fronts = [[]]
        for i, ind in enumerate(self.population):
            if ind.dominance_count == 0:
                ind.rank = 0
                fronts[0].append(i)

        k = 0
        while fronts[k]:
            next_front = []
            for i in fronts[k]:
                for j in self.population[i].dominated_solutions:
                    self.population[j].dominance_count -= 1
                    if self.population[j].dominance_count == 0:
                        self.population[j].rank = k + 1
                        next_front.append(j)
            k += 1
            fronts.append(next_front)

        return fronts[:-1]

    def calculate_crowding_distance(self, front: List[int]):
        if len(front) <= 2:
            for i in front:
                self.population[i].crowding_distance = float("inf")
            return

        for i in front:
            self.population[i].crowding_distance = 0.0

        for obj_idx in range(self.num_objectives):
            sorted_front = sorted(
                front, key=lambda x: self.population[x].objectives[obj_idx]
            )

            self.population[sorted_front[0]].crowding_distance = float("inf")
            self.population[sorted_front[-1]].crowding_distance = float("inf")

            obj_range = (
                self.population[sorted_front[-1]].objectives[obj_idx]
                - self.population[sorted_front[0]].objectives[obj_idx]
            )

            if obj_range == 0:
                continue

            for i in range(1, len(sorted_front) - 1):
                self.population[sorted_front[i]].crowding_distance += (
                    self.population[sorted_front[i + 1]].objectives[obj_idx]
                    - self.population[sorted_front[i - 1]].objectives[obj_idx]
                ) / obj_range

    def select_parents(self) -> List[Individual]:
        fronts = self.fast_non_dominated_sort()

        selected = []
        for front in fronts:
            self.calculate_crowding_distance(front)
            if len(selected) + len(front) <= self.population_size:
                selected.extend([self.population[i] for i in front])
            else:
                remaining = self.population_size - len(selected)
                sorted_front = sorted(
                    front,
                    key=lambda x: self.population[x].crowding_distance,
                    reverse=True,
                )
                selected.extend([self.population[i] for i in sorted_front[:remaining]])
                break

        return selected[: self.population_size]

    def crossover(
        self, parent1: Individual, parent2: Individual
    ) -> Tuple[Individual, Individual]:
        alpha = np.random.random(self.num_genes)
        child1_genes = alpha * parent1.genes + (1 - alpha) * parent2.genes
        child2_genes = (1 - alpha) * parent1.genes + alpha * parent2.genes

        return Individual(
            genes=child1_genes, objectives=np.zeros(self.num_objectives)
        ), Individual(genes=child2_genes, objectives=np.zeros(self.num_objectives))

    def mutate(self, individual: Individual, mutation_rate: float = 0.1):
        for i in range(self.num_genes):
            if np.random.random() < mutation_rate:
                delta = np.random.normal(0, 0.1) * (
                    self.gene_bounds[1] - self.gene_bounds[0]
                )
                individual.genes[i] += delta
                individual.genes[i] = np.clip(
                    individual.genes[i], self.gene_bounds[0], self.gene_bounds[1]
                )

    def create_offspring(self, parents: List[Individual]) -> List[Individual]:
        offspring = []
        for _ in range(self.population_size // 2):
            p1, p2 = random.sample(parents, 2)
            child1, child2 = self.crossover(p1, p2)
            self.mutate(child1)
            self.mutate(child2)
            offspring.extend([child1, child2])
        return offspring

    def merge_and_select(self, parents: List[Individual], offspring: List[Individual]):
        combined = parents + offspring
        fronts = self.fast_non_dominated_sort()

        self.population = []
        for front in fronts:
            self.calculate_crowding_distance(front)
            if len(self.population) + len(front) <= self.population_size:
                self.population.extend([combined[i] for i in front])
            else:
                remaining = self.population_size - len(self.population)
                sorted_front = sorted(
                    front, key=lambda x: combined[x].crowding_distance, reverse=True
                )
                self.population.extend([combined[i] for i in sorted_front[:remaining]])
                break

    def optimize(self, objectives: List[Callable]) -> List[Individual]:
        self.initialize_population()

        for ind in self.population:
            self.evaluate(ind, objectives)

        for gen in range(self.num_generations):
            parents = self.select_parents()
            offspring = self.create_offspring(parents)

            for ind in offspring:
                self.evaluate(ind, objectives)

            self.merge_and_select(parents, offspring)

            if gen % 10 == 0:
                pareto = self.get_pareto_front()
                print(f"Generation {gen}: Pareto front size = {len(pareto)}")

        return self.get_pareto_front()

    def get_pareto_front(self) -> List[Individual]:
        return [ind for ind in self.population if ind.rank == 0]


class MOEAD:
    def __init__(
        self,
        num_objectives: int = 2,
        population_size: int = 100,
        num_neighbors: int = 20,
    ):
        self.num_objectives = num_objectives
        self.population_size = population_size
        self.num_neighbors = num_neighbors
        self.population: List[Individual] = []
        self.neighbors: Dict[int, List[int]] = {}

    def scalarization_function(
        self,
        individual: Individual,
        weight: np.ndarray,
        ideal_point: np.ndarray,
        ref_point: np.ndarray,
    ) -> float:
        d1 = np.sum((individual.objectives - ref_point) * weight)
        d2 = np.linalg.norm(individual.objectives - ref_point - d1 * weight)
        return d1 + 5 * d2

    def update_solution(
        self,
        current: Individual,
        offspring: Individual,
        weight: np.ndarray,
        ideal_point: np.ndarray,
        ref_point: np.ndarray,
    ):
        current_fitness = self.scalarization_function(
            current, weight, ideal_point, ref_point
        )
        offspring_fitness = self.scalarization_function(
            offspring, weight, ideal_point, ref_point
        )

        if offspring_fitness < current_fitness:
            current.genes = offspring.genes.copy()
            current.objectives = offspring.objectives.copy()


class ProblemFactory:
    @staticmethod
    def zdt1(x: np.ndarray) -> float:
        f1 = x[0]
        g = 1 + 9 * np.sum(x[1:]) / (len(x) - 1)
        f2 = g * (1 - np.sqrt(f1 / g))
        return f1

    @staticmethod
    def zdt2(x: np.ndarray) -> float:
        f1 = x[0]
        g = 1 + 9 * np.sum(x[1:]) / (len(x) - 1)
        f2 = g * (1 - (f1 / g) ** 2)
        return f1

    @staticmethod
    def sch(x: np.ndarray) -> float:
        return x[0] ** 2, (x[0] - 2) ** 2


def optimize_drone_path(num_objectives: int = 3) -> List[Individual]:
    def minimize_distance(genes):
        return np.sum(np.abs(genes))

    def minimize_energy(genes):
        return np.sum(genes**2) * 0.1

    def minimize_risk(genes):
        return np.sum(np.abs(np.sin(genes * np.pi))) * 10

    nsga = NSGAII(
        num_objectives=num_objectives,
        population_size=100,
        num_generations=50,
        gene_bounds=(-100, 100),
        num_genes=10,
    )

    objectives = [minimize_distance, minimize_energy, minimize_risk][:num_objectives]
    pareto_front = nsga.optimize(objectives)

    return pareto_front


if __name__ == "__main__":
    print("=== Multi-Objective Optimization (NSGA-II) ===")
    print("Optimizing drone path: Distance, Energy, Risk")

    pareto = optimize_drone_path(num_objectives=3)

    print(f"\nPareto Front Size: {len(pareto)}")
    print("\nBest Solutions:")
    for i, ind in enumerate(pareto[:5]):
        print(
            f"  Solution {i + 1}: objectives = {[f'{o:.2f}' for o in ind.objectives]}"
        )
