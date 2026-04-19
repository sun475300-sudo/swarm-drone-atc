"""
Phase 483: Swarm Evolution Engine
유전 알고리즘 기반 군집 행동 진화, NEAT 토폴로지 변이.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple, Callable


class MutationType(Enum):
    WEIGHT = "weight"
    ADD_NODE = "add_node"
    ADD_LINK = "add_link"
    REMOVE_LINK = "remove_link"
    TOGGLE_LINK = "toggle_link"


@dataclass
class Gene:
    innovation: int
    src: int
    dst: int
    weight: float
    enabled: bool = True


@dataclass
class Genome:
    genome_id: int
    genes: List[Gene] = field(default_factory=list)
    n_inputs: int = 4
    n_outputs: int = 2
    n_hidden: int = 0
    fitness: float = 0.0
    species_id: int = 0


@dataclass
class Species:
    species_id: int
    representative: Genome
    members: List[int] = field(default_factory=list)
    best_fitness: float = 0.0
    stagnation: int = 0


class SwarmEvolution:
    """NEAT-style neuroevolution for drone swarm behaviors."""

    def __init__(self, pop_size: int = 50, n_inputs: int = 4, n_outputs: int = 2,
                 seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.pop_size = pop_size
        self.n_inputs = n_inputs
        self.n_outputs = n_outputs
        self.population: List[Genome] = []
        self.species_list: List[Species] = []
        self.generation = 0
        self._innovation_counter = 0
        self._genome_counter = 0
        self._init_population()

    def _next_innovation(self) -> int:
        self._innovation_counter += 1
        return self._innovation_counter

    def _init_population(self):
        for _ in range(self.pop_size):
            self._genome_counter += 1
            genes = []
            for i in range(self.n_inputs):
                for o in range(self.n_outputs):
                    genes.append(Gene(
                        self._next_innovation(), i,
                        self.n_inputs + o,
                        self.rng.standard_normal() * 0.5))
            self.population.append(Genome(
                self._genome_counter, genes, self.n_inputs, self.n_outputs))

    def _activate(self, genome: Genome, inputs: np.ndarray) -> np.ndarray:
        total_nodes = genome.n_inputs + genome.n_outputs + genome.n_hidden
        values = np.zeros(total_nodes)
        values[:genome.n_inputs] = inputs
        for gene in genome.genes:
            if gene.enabled and gene.src < total_nodes and gene.dst < total_nodes:
                values[gene.dst] += values[gene.src] * gene.weight
        outputs = values[genome.n_inputs:genome.n_inputs + genome.n_outputs]
        return np.tanh(outputs)

    def _mutate(self, genome: Genome) -> Genome:
        new_genes = [Gene(g.innovation, g.src, g.dst, g.weight, g.enabled) for g in genome.genes]

        if self.rng.random() < 0.8:
            for g in new_genes:
                if self.rng.random() < 0.1:
                    g.weight += self.rng.standard_normal() * 0.3
                elif self.rng.random() < 0.05:
                    g.weight = self.rng.standard_normal()

        if self.rng.random() < 0.05 and new_genes:
            gene = self.rng.choice(new_genes)
            new_node = genome.n_inputs + genome.n_outputs + genome.n_hidden
            gene.enabled = False
            new_genes.append(Gene(self._next_innovation(), gene.src, new_node, 1.0))
            new_genes.append(Gene(self._next_innovation(), new_node, gene.dst, gene.weight))
            genome.n_hidden += 1

        if self.rng.random() < 0.1:
            total = genome.n_inputs + genome.n_outputs + genome.n_hidden
            src = self.rng.integers(0, total)
            dst = self.rng.integers(genome.n_inputs, total)
            if src != dst:
                new_genes.append(Gene(self._next_innovation(), src, dst,
                                     self.rng.standard_normal() * 0.5))

        self._genome_counter += 1
        return Genome(self._genome_counter, new_genes, genome.n_inputs,
                     genome.n_outputs, genome.n_hidden)

    def _crossover(self, parent1: Genome, parent2: Genome) -> Genome:
        if parent1.fitness < parent2.fitness:
            parent1, parent2 = parent2, parent1
        p2_genes = {g.innovation: g for g in parent2.genes}
        child_genes = []
        for g in parent1.genes:
            if g.innovation in p2_genes and self.rng.random() < 0.5:
                pg = p2_genes[g.innovation]
                child_genes.append(Gene(g.innovation, g.src, g.dst, pg.weight, pg.enabled))
            else:
                child_genes.append(Gene(g.innovation, g.src, g.dst, g.weight, g.enabled))
        self._genome_counter += 1
        return Genome(self._genome_counter, child_genes, parent1.n_inputs,
                     parent1.n_outputs, max(parent1.n_hidden, parent2.n_hidden))

    def _genetic_distance(self, g1: Genome, g2: Genome) -> float:
        innov1 = {g.innovation for g in g1.genes}
        innov2 = {g.innovation for g in g2.genes}
        disjoint = len(innov1.symmetric_difference(innov2))
        common = innov1 & innov2
        w_diff = 0.0
        if common:
            w1 = {g.innovation: g.weight for g in g1.genes}
            w2 = {g.innovation: g.weight for g in g2.genes}
            w_diff = np.mean([abs(w1[i] - w2[i]) for i in common if i in w1 and i in w2])
        n = max(len(g1.genes), len(g2.genes), 1)
        return disjoint / n + 0.4 * w_diff

    def _speciate(self):
        for sp in self.species_list:
            sp.members = []
        for genome in self.population:
            placed = False
            for sp in self.species_list:
                if self._genetic_distance(genome, sp.representative) < 3.0:
                    sp.members.append(genome.genome_id)
                    genome.species_id = sp.species_id
                    placed = True
                    break
            if not placed:
                new_sp = Species(len(self.species_list), genome, [genome.genome_id])
                genome.species_id = new_sp.species_id
                self.species_list.append(new_sp)
        self.species_list = [sp for sp in self.species_list if sp.members]

    def evaluate(self, fitness_fn: Callable[[Genome, Callable], float]):
        for genome in self.population:
            genome.fitness = fitness_fn(genome, lambda inp: self._activate(genome, inp))

    def evolve(self) -> Dict:
        self.generation += 1
        self._speciate()
        sorted_pop = sorted(self.population, key=lambda g: g.fitness, reverse=True)
        n_elite = max(2, self.pop_size // 10)
        new_pop = sorted_pop[:n_elite]

        while len(new_pop) < self.pop_size:
            if self.rng.random() < 0.75 and len(sorted_pop) >= 2:
                idx = self.rng.integers(0, min(len(sorted_pop), self.pop_size // 2), 2)
                child = self._crossover(sorted_pop[idx[0]], sorted_pop[idx[1]])
            else:
                parent = sorted_pop[self.rng.integers(0, min(len(sorted_pop), self.pop_size // 2))]
                child = self._mutate(parent)
            child = self._mutate(child)
            new_pop.append(child)

        self.population = new_pop[:self.pop_size]
        best = max(self.population, key=lambda g: g.fitness)
        return {
            "generation": self.generation,
            "best_fitness": round(best.fitness, 4),
            "avg_fitness": round(float(np.mean([g.fitness for g in self.population])), 4),
            "species": len(self.species_list),
            "best_genes": len(best.genes),
        }

    def summary(self) -> Dict:
        best = max(self.population, key=lambda g: g.fitness) if self.population else None
        return {
            "generation": self.generation,
            "population": len(self.population),
            "species": len(self.species_list),
            "best_fitness": round(best.fitness, 4) if best else 0,
            "avg_genes": round(float(np.mean([len(g.genes) for g in self.population])), 1),
        }
