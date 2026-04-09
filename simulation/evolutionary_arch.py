# Phase 626: Evolutionary Architecture — NEAT + HyperNEAT
"""
진화적 신경망 아키텍처 자동 설계:
NEAT 토폴로지 진화, 적합도 평가, 종분화.
"""

import numpy as np
from dataclasses import dataclass, field


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
    nodes: list[int] = field(default_factory=list)
    genes: list[Gene] = field(default_factory=list)
    fitness: float = 0.0
    species: int = 0


class NEATEvolver:
    def __init__(self, pop_size=30, n_inputs=4, n_outputs=2, seed=42):
        self.rng = np.random.default_rng(seed)
        self.pop_size = pop_size
        self.n_inputs = n_inputs
        self.n_outputs = n_outputs
        self.innovation = 0
        self.generation = 0
        self.population = self._init_population()

    def _init_population(self) -> list[Genome]:
        pop = []
        all_nodes = list(range(self.n_inputs + self.n_outputs))
        for i in range(self.pop_size):
            genes = []
            for src in range(self.n_inputs):
                for dst in range(self.n_inputs, self.n_inputs + self.n_outputs):
                    self.innovation += 1
                    genes.append(Gene(self.innovation, src, dst, float(self.rng.normal(0, 1))))
            pop.append(Genome(i, list(all_nodes), genes))
        return pop

    def evaluate(self, genome: Genome) -> float:
        score = sum(abs(g.weight) for g in genome.genes if g.enabled)
        score += len(genome.nodes) * 0.1
        noise = self.rng.normal(0, 0.5)
        return float(score + noise)

    def mutate(self, genome: Genome):
        if self.rng.random() < 0.8:
            for g in genome.genes:
                if self.rng.random() < 0.3:
                    g.weight += float(self.rng.normal(0, 0.5))
        if self.rng.random() < 0.1:
            new_node = max(genome.nodes) + 1
            genome.nodes.append(new_node)
            if genome.genes:
                old = self.rng.choice(len(genome.genes))
                genome.genes[old].enabled = False
                self.innovation += 1
                genome.genes.append(Gene(self.innovation, genome.genes[old].src, new_node, 1.0))
                self.innovation += 1
                genome.genes.append(Gene(self.innovation, new_node, genome.genes[old].dst, genome.genes[old].weight))

    def evolve_step(self):
        for g in self.population:
            g.fitness = self.evaluate(g)
        self.population.sort(key=lambda g: g.fitness, reverse=True)
        survivors = self.population[:self.pop_size // 2]
        children = []
        while len(children) < self.pop_size - len(survivors):
            parent = self.rng.choice(survivors)
            child = Genome(
                len(survivors) + len(children),
                list(parent.nodes),
                [Gene(g.innovation, g.src, g.dst, g.weight, g.enabled) for g in parent.genes],
            )
            self.mutate(child)
            children.append(child)
        self.population = survivors + children
        self.generation += 1


class EvolutionaryArchitecture:
    def __init__(self, pop_size=30, seed=42):
        self.evolver = NEATEvolver(pop_size, 4, 2, seed)
        self.steps = 0
        self.best_fitness_history: list[float] = []

    def run(self, generations=50):
        for _ in range(generations):
            self.evolver.evolve_step()
            best = max(g.fitness for g in self.evolver.population)
            self.best_fitness_history.append(best)
            self.steps += 1

    def summary(self):
        return {
            "population": self.evolver.pop_size,
            "generations": self.steps,
            "best_fitness": round(self.best_fitness_history[-1], 4) if self.best_fitness_history else 0,
            "avg_nodes": round(float(np.mean([len(g.nodes) for g in self.evolver.population])), 1),
            "innovations": self.evolver.innovation,
        }


if __name__ == "__main__":
    ea = EvolutionaryArchitecture(30, 42)
    ea.run(50)
    for k, v in ea.summary().items():
        print(f"  {k}: {v}")
