# Phase 535: Neural Architecture Search — NAS Controller
"""
NAS 컨트롤러: 아키텍처 샘플링, 성능 평가, 진화 알고리즘 기반 탐색.
드론 제어 신경망 최적 구조 자동 탐색.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class Architecture:
    arch_id: str
    layers: list  # [(type, params), ...]
    fitness: float = 0.0
    latency_ms: float = 0.0
    params_count: int = 0


@dataclass
class SearchResult:
    generations: int
    best_fitness: float
    best_arch: Architecture
    population_size: int
    evaluations: int


class ArchitectureSpace:
    """아키텍처 탐색 공간 정의."""

    LAYER_TYPES = ["dense", "conv1d", "lstm", "attention", "skip"]
    ACTIVATIONS = ["relu", "gelu", "tanh", "sigmoid"]
    HIDDEN_SIZES = [16, 32, 64, 128, 256]

    def __init__(self, seed=42):
        self.rng = np.random.default_rng(seed)

    def sample_architecture(self, arch_id: str, min_layers=2, max_layers=6) -> Architecture:
        n_layers = int(self.rng.integers(min_layers, max_layers + 1))
        layers = []
        total_params = 0
        prev_size = 10  # 입력 차원
        for i in range(n_layers):
            ltype = self.LAYER_TYPES[int(self.rng.integers(0, len(self.LAYER_TYPES)))]
            hidden = self.HIDDEN_SIZES[int(self.rng.integers(0, len(self.HIDDEN_SIZES)))]
            act = self.ACTIVATIONS[int(self.rng.integers(0, len(self.ACTIVATIONS)))]
            if ltype == "skip":
                params = 0
            elif ltype == "conv1d":
                params = prev_size * hidden * 3  # kernel=3
            elif ltype == "lstm":
                params = 4 * (prev_size + hidden) * hidden
            elif ltype == "attention":
                params = 3 * prev_size * hidden + hidden * prev_size
            else:
                params = prev_size * hidden + hidden
            layers.append({"type": ltype, "hidden": hidden, "activation": act, "params": params})
            total_params += params
            if ltype != "skip":
                prev_size = hidden

        latency = total_params * 0.001 + self.rng.exponential(0.5)
        return Architecture(arch_id, layers, 0.0, latency, total_params)

    def mutate(self, arch: Architecture, arch_id: str) -> Architecture:
        new_layers = [l.copy() for l in arch.layers]
        if len(new_layers) > 0:
            idx = int(self.rng.integers(0, len(new_layers)))
            mutation = int(self.rng.integers(0, 3))
            if mutation == 0:  # 레이어 타입 변경
                new_layers[idx]["type"] = self.LAYER_TYPES[int(self.rng.integers(0, len(self.LAYER_TYPES)))]
            elif mutation == 1:  # hidden 크기 변경
                new_layers[idx]["hidden"] = self.HIDDEN_SIZES[int(self.rng.integers(0, len(self.HIDDEN_SIZES)))]
            else:  # 활성화 함수 변경
                new_layers[idx]["activation"] = self.ACTIVATIONS[int(self.rng.integers(0, len(self.ACTIVATIONS)))]

        total_params = sum(l.get("params", 0) for l in new_layers)
        latency = total_params * 0.001 + self.rng.exponential(0.5)
        return Architecture(arch_id, new_layers, 0.0, latency, total_params)


class FitnessEvaluator:
    """아키텍처 적합도 평가."""

    def __init__(self, seed=42):
        self.rng = np.random.default_rng(seed)

    def evaluate(self, arch: Architecture) -> float:
        # 시뮬레이션된 정확도: 레이어 수/다양성/크기에 따른 근사
        n_layers = len(arch.layers)
        layer_types = set(l["type"] for l in arch.layers)
        diversity_bonus = len(layer_types) * 0.05
        size_penalty = max(0, arch.params_count - 50000) * 1e-6
        latency_penalty = max(0, arch.latency_ms - 10) * 0.01

        base = 0.5 + min(n_layers, 5) * 0.08
        noise = self.rng.normal(0, 0.02)
        fitness = base + diversity_bonus - size_penalty - latency_penalty + noise
        return float(np.clip(fitness, 0.1, 0.99))


class NeuralArchSearch:
    """진화 알고리즘 기반 NAS."""

    def __init__(self, pop_size=20, generations=10, seed=42):
        self.pop_size = pop_size
        self.generations = generations
        self.space = ArchitectureSpace(seed)
        self.evaluator = FitnessEvaluator(seed + 1)
        self.rng = np.random.default_rng(seed)
        self.population: list[Architecture] = []
        self.best: Architecture | None = None
        self.total_evals = 0

    def initialize(self):
        self.population = [
            self.space.sample_architecture(f"arch_{i}")
            for i in range(self.pop_size)
        ]
        self._evaluate_all()

    def _evaluate_all(self):
        for arch in self.population:
            arch.fitness = self.evaluator.evaluate(arch)
            self.total_evals += 1
        self.population.sort(key=lambda a: a.fitness, reverse=True)
        if not self.best or self.population[0].fitness > self.best.fitness:
            self.best = self.population[0]

    def evolve_one_generation(self):
        # 상위 50% 선택
        survivors = self.population[:self.pop_size // 2]
        # 돌연변이로 자식 생성
        children = []
        for i in range(self.pop_size - len(survivors)):
            parent = survivors[int(self.rng.integers(0, len(survivors)))]
            child = self.space.mutate(parent, f"arch_g{self.total_evals}_{i}")
            children.append(child)
        self.population = survivors + children
        self._evaluate_all()

    def run(self) -> SearchResult:
        self.initialize()
        for g in range(self.generations):
            self.evolve_one_generation()
        return SearchResult(
            self.generations, self.best.fitness, self.best,
            self.pop_size, self.total_evals
        )

    def summary(self):
        return {
            "population": self.pop_size,
            "generations": self.generations,
            "best_fitness": self.best.fitness if self.best else 0,
            "best_params": self.best.params_count if self.best else 0,
            "total_evals": self.total_evals,
        }


if __name__ == "__main__":
    nas = NeuralArchSearch(20, 10, 42)
    result = nas.run()
    print(f"Best fitness: {result.best_fitness:.4f}")
    print(f"Best arch layers: {len(result.best_arch.layers)}")
    print(f"Evaluations: {result.evaluations}")
    print(nas.summary())
