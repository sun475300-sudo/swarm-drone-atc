"""
Phase 415: Neural Architecture Search for Optimal Drone AI Models
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import time


class OperationType(Enum):
    CONV2D = "conv2d"
    DENSE = "dense"
    ATTENTION = "attention"
    POOLING = "pooling"
    BATCH_NORM = "batch_norm"
    DROPOUT = "dropout"


class SearchStrategy(Enum):
    RANDOM = "random"
    EVOLUTION = "evolution"
    REINFORCEMENT = "reinforcement"
    GRADIENT = "gradient"


@dataclass
class NeuralBlock:
    block_id: str
    operation: OperationType
    parameters: Dict[str, Any]
    input_shape: Tuple[int, ...]
    output_shape: Tuple[int, ...]


@dataclass
class Architecture:
    arch_id: str
    blocks: List[NeuralBlock]
    accuracy: float = 0.0
    latency_ms: float = 0.0
    params_count: int = 0


class NeuralArchitectureSearch:
    def __init__(
        self,
        search_space: Dict[str, List[Any]],
        strategy: SearchStrategy = SearchStrategy.EVOLUTION,
        population_size: int = 50,
        generations: int = 100,
        fitness_fn: Optional[Callable] = None,
    ):
        self.search_space = search_space
        self.strategy = strategy
        self.population_size = population_size
        self.generations = generations
        self.fitness_fn = fitness_fn or self._default_fitness

        self.population: List[Architecture] = []
        self.best_architecture: Optional[Architecture] = None

        self.history: List[float] = []

        self._initialize_population()

    def _initialize_population(self):
        for i in range(self.population_size):
            arch = self._generate_random_architecture(f"arch_{i}")
            self.population.append(arch)

    def _generate_random_architecture(self, arch_id: str) -> Architecture:
        num_blocks = np.random.randint(3, 10)
        blocks = []

        input_shape = (224, 224, 3)

        for i in range(num_blocks):
            op_type = np.random.choice(list(OperationType))
            params = self._sample_parameters(op_type)

            block = NeuralBlock(
                block_id=f"block_{i}",
                operation=op_type,
                parameters=params,
                input_shape=input_shape,
                output_shape=self._compute_output_shape(input_shape, op_type, params),
            )
            blocks.append(block)
            input_shape = block.output_shape

        return Architecture(
            arch_id=arch_id,
            blocks=blocks,
        )

    def _sample_parameters(self, op_type: OperationType) -> Dict[str, Any]:
        if op_type == OperationType.CONV2D:
            return {
                "filters": np.random.choice([16, 32, 64, 128, 256]),
                "kernel_size": np.random.choice([3, 5, 7]),
                "strides": np.random.choice([1, 2]),
                "activation": np.random.choice(["relu", "swish", "gelu"]),
            }
        elif op_type == OperationType.DENSE:
            return {
                "units": np.random.choice([64, 128, 256, 512]),
                "activation": np.random.choice(["relu", "tanh", "gelu"]),
            }
        elif op_type == OperationType.ATTENTION:
            return {
                "heads": np.random.choice([4, 8, 16]),
                "key_dim": np.random.choice([32, 64, 128]),
            }
        else:
            return {"pool_size": 2}

    def _compute_output_shape(
        self,
        input_shape: Tuple[int, ...],
        op_type: OperationType,
        params: Dict[str, Any],
    ) -> Tuple[int, ...]:
        if op_type == OperationType.CONV2D:
            if len(input_shape) < 3:
                filters = params.get("filters", 32)
                return (filters,)
            strides = params.get("strides", 1)
            filters = params.get("filters", 32)

            h = input_shape[0] // strides if strides > 1 else input_shape[0]
            w = input_shape[1] // strides if strides > 1 else input_shape[1]
            return (h, w, filters)

        elif op_type == OperationType.DENSE:
            return (params.get("units", 128),)

        elif op_type == OperationType.POOLING:
            pool = params.get("pool_size", 2)
            if len(input_shape) >= 3:
                return (input_shape[0] // pool, input_shape[1] // pool, input_shape[2])
            return input_shape

        return input_shape

    def _default_fitness(self, arch: Architecture) -> float:
        accuracy = np.random.uniform(0.7, 0.95)

        params = sum(self._estimate_params(b) for b in arch.blocks)
        latency = params * 0.001

        fitness = accuracy * 0.7 + (1.0 / (1.0 + latency)) * 0.3

        return fitness

    def _estimate_params(self, block: NeuralBlock) -> int:
        if block.operation == OperationType.CONV2D:
            p = block.parameters
            return (
                p.get("filters", 32)
                * p.get("kernel_size", 3) ** 2
                * block.input_shape[-1]
            )
        elif block.operation == OperationType.DENSE:
            return block.parameters.get("units", 128) * block.input_shape[-1]
        return 0

    def search(self) -> Architecture:
        for gen in range(self.generations):
            fitnesses = [self.fitness_fn(arch) for arch in self.population]

            for i, arch in enumerate(self.population):
                arch.accuracy = fitnesses[i]

            self.history.append(max(fitnesses))

            if (
                self.best_architecture is None
                or max(fitnesses) > self.best_architecture.accuracy
            ):
                self.best_architecture = max(self.population, key=lambda a: a.accuracy)

            if self.strategy == SearchStrategy.EVOLUTION:
                self._evolve_population(fitnesses)
            elif self.strategy == SearchStrategy.RANDOM:
                self._random_search()

            if (gen + 1) % 10 == 0:
                print(
                    f"Generation {gen + 1}/{self.generations}, Best: {self.best_architecture.accuracy:.4f}"
                )

        return self.best_architecture

    def _evolve_population(self, fitnesses: List[float]):
        sorted_pop = sorted(
            zip(fitnesses, self.population), key=lambda x: x[0], reverse=True
        )

        top_50 = [arch for _, arch in sorted_pop[: self.population_size // 2]]

        new_pop = []

        for i in range(self.population_size // 2):
            parent = top_50[i % len(top_50)]
            child = self._crossover(parent)
            child = self._mutate(child)
            new_pop.append(child)

        self.population = top_50 + new_pop

    def _random_search(self):
        for i in range(self.population_size // 2):
            self.population[i] = self._generate_random_architecture(f"arch_random_{i}")

    def _crossover(self, parent: Architecture) -> Architecture:
        return self._generate_random_architecture(f"{parent.arch_id}_child")

    def _mutate(self, arch: Architecture) -> Architecture:
        mutated = Architecture(
            arch_id=f"{arch.arch_id}_mutated",
            blocks=arch.blocks.copy(),
        )

        if np.random.random() < 0.3 and mutated.blocks:
            idx = np.random.randint(0, len(mutated.blocks))
            new_params = self._sample_parameters(mutated.blocks[idx].operation)
            mutated.blocks[idx].parameters.update(new_params)

        return mutated

    def get_best_architecture(self) -> Optional[Architecture]:
        return self.best_architecture

    def get_search_history(self) -> List[float]:
        return self.history
