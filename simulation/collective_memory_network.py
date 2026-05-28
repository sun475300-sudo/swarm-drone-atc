# Phase 570: Collective Memory Network — Hopfield Associative Memory
"""
집단 기억 네트워크: Hopfield 네트워크 기반 연상 기억,
패턴 저장/검색, 에너지 함수 최소화.
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class MemoryPattern:
    """``MemoryPattern`` 관련 기능을 제공한다."""
    pattern_id: str
    data: np.ndarray
    label: str


@dataclass
class RecallResult:
    """``RecallResult`` 데이터를 표현한다."""
    query_id: str
    recalled_id: str
    similarity: float
    iterations: int
    converged: bool


class HopfieldNetwork:
    """Hopfield 연상 기억 네트워크."""

    def __init__(self, n_neurons: int):
        """인스턴스를 초기화한다."""
        self.n = n_neurons
        self.weights = np.zeros((n_neurons, n_neurons))
        self.patterns_stored = 0

    def store(self, pattern: np.ndarray):
        """Hebbian 학습으로 패턴 저장."""
        p = np.where(pattern > 0, 1, -1).astype(float)
        self.weights += np.outer(p, p) / self.n
        np.fill_diagonal(self.weights, 0)
        self.patterns_stored += 1

    def recall(self, query: np.ndarray, max_iter=100) -> tuple[np.ndarray, int, bool]:
        """비동기 업데이트로 패턴 검색."""
        state = np.where(query > 0, 1, -1).astype(float)
        for i in range(max_iter):
            old_state = state.copy()
            for j in range(self.n):
                h = self.weights[j] @ state
                state[j] = 1.0 if h >= 0 else -1.0
            if np.array_equal(state, old_state):
                return state, i + 1, True
        return state, max_iter, False

    def energy(self, state: np.ndarray) -> float:
        """``energy`` 동작을 수행한다."""
        s = np.where(state > 0, 1, -1).astype(float)
        return -0.5 * s @ self.weights @ s

    def capacity(self) -> int:
        """이론적 저장 용량: ~0.15N."""
        return int(0.15 * self.n)


class CollectiveMemoryNetwork:
    """집단 기억 네트워크 시뮬레이션."""

    def __init__(self, n_neurons=64, seed=42):
        """인스턴스를 초기화한다."""
        self.rng = np.random.default_rng(seed)
        self.network = HopfieldNetwork(n_neurons)
        self.n_neurons = n_neurons
        self.stored_patterns: list[MemoryPattern] = []
        self.recall_results: list[RecallResult] = []

    def store_patterns(self, n_patterns=10):
        """``store_patterns`` 동작을 수행한다."""
        for i in range(n_patterns):
            data = self.rng.choice([-1, 1], self.n_neurons).astype(float)
            pattern = MemoryPattern(f"PAT_{i:04d}", data, f"formation_{i}")
            self.stored_patterns.append(pattern)
            self.network.store(data)

    def recall_with_noise(self, pattern_idx: int, noise_ratio=0.2) -> RecallResult:
        """``recall_with_noise`` 동작을 수행한다."""
        if pattern_idx >= len(self.stored_patterns):
            return RecallResult("?", "?", 0, 0, False)

        original = self.stored_patterns[pattern_idx]
        query = original.data.copy()

        # 노이즈 주입
        n_flip = int(self.n_neurons * noise_ratio)
        flip_idx = self.rng.choice(self.n_neurons, n_flip, replace=False)
        query[flip_idx] *= -1

        recalled, iters, converged = self.network.recall(query)

        # 가장 유사한 저장 패턴 찾기
        best_sim = -1
        best_id = ""
        for pat in self.stored_patterns:
            sim = float(np.mean(np.where(recalled > 0, 1, -1) == np.where(pat.data > 0, 1, -1)))
            if sim > best_sim:
                best_sim = sim
                best_id = pat.pattern_id

        result = RecallResult(original.pattern_id, best_id, best_sim, iters, converged)
        self.recall_results.append(result)
        return result

    def run(self, n_patterns=10, n_recalls=20, noise=0.2):
        """메인 실행 루프를 수행한다."""
        self.store_patterns(n_patterns)
        for _ in range(n_recalls):
            idx = int(self.rng.integers(0, len(self.stored_patterns)))
            self.recall_with_noise(idx, noise)

    def summary(self):
        """현재 상태 요약을 반환한다."""
        correct = sum(1 for r in self.recall_results if r.similarity > 0.9)
        avg_sim = float(np.mean([r.similarity for r in self.recall_results])) if self.recall_results else 0
        avg_iter = float(np.mean([r.iterations for r in self.recall_results])) if self.recall_results else 0
        return {
            "neurons": self.n_neurons,
            "capacity": self.network.capacity(),
            "stored": len(self.stored_patterns),
            "recalls": len(self.recall_results),
            "correct_recalls": correct,
            "avg_similarity": round(avg_sim, 4),
            "avg_iterations": round(avg_iter, 1),
        }


if __name__ == "__main__":
    cmn = CollectiveMemoryNetwork(64, 42)
    cmn.run(8, 20, 0.15)
    for k, v in cmn.summary().items():
        print(f"  {k}: {v}")
