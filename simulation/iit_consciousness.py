# Phase 567: IIT Consciousness Metric — Integrated Information Theory
"""
통합 정보 이론(IIT) 기반 군집 의식 지표:
Phi(Φ) 계산, 인과 구조 분석, 창발 측정.
"""

import numpy as np
from dataclasses import dataclass, field
from itertools import combinations


@dataclass
class SystemState:
    nodes: int
    state: np.ndarray
    phi: float = 0.0
    partition: tuple = ()


class IITCalculator:
    """IIT Phi 계산기 (간이)."""

    def __init__(self, n_nodes: int, seed=42):
        self.n = n_nodes
        self.rng = np.random.default_rng(seed)
        # 전이 확률 행렬 (TPM)
        self.tpm = self.rng.dirichlet(np.ones(2**n_nodes), 2**n_nodes)

    def mutual_info(self, p_joint: np.ndarray) -> float:
        """상호 정보량."""
        p_x = p_joint.sum(axis=1, keepdims=True)
        p_y = p_joint.sum(axis=0, keepdims=True)
        outer = p_x @ p_y
        mask = (p_joint > 0) & (outer > 0)
        mi = np.sum(p_joint[mask] * np.log2(p_joint[mask] / outer[mask]))
        return float(mi)

    def compute_phi(self, state: np.ndarray) -> float:
        """MIP(최소 정보 분할) 기반 Phi 근사."""
        n = self.n
        if n <= 1:
            return 0.0

        # 전체 시스템 정보
        total_info = self._system_info(state)

        # 모든 이분할에 대해 최소 정보 손실
        min_loss = float('inf')
        for k in range(1, n):
            for partition_a in combinations(range(n), k):
                partition_b = tuple(i for i in range(n) if i not in partition_a)
                partitioned_info = self._partitioned_info(state, partition_a, partition_b)
                loss = total_info - partitioned_info
                if loss < min_loss:
                    min_loss = loss

        return max(0.0, min_loss)

    def _system_info(self, state: np.ndarray) -> float:
        """전체 시스템 인과 정보."""
        n_states = 2 ** self.n
        idx = min(int(np.sum(state * 2**np.arange(self.n))), n_states - 1)
        probs = self.tpm[idx]
        entropy = -np.sum(probs * np.log2(probs + 1e-12))
        return float(self.n * np.log2(2) - entropy)

    def _partitioned_info(self, state: np.ndarray, part_a: tuple, part_b: tuple) -> float:
        """분할된 시스템 정보."""
        info_a = len(part_a) * np.log2(2) * 0.5
        info_b = len(part_b) * np.log2(2) * 0.5
        # 분할 시 상호 정보 손실 근사
        return float(info_a + info_b) * 0.8


class SwarmConsciousnessMetric:
    """군집 의식 지표 시뮬레이션."""

    def __init__(self, n_drones=8, seed=42):
        self.rng = np.random.default_rng(seed)
        self.n_drones = n_drones
        self.iit = IITCalculator(min(n_drones, 8), seed)
        self.phi_history: list[float] = []
        self.states: list[SystemState] = []
        self.steps = 0

    def measure(self, state: np.ndarray = None):
        if state is None:
            state = self.rng.choice([0, 1], self.n_drones).astype(float)
        phi = self.iit.compute_phi(state[:self.iit.n])
        self.phi_history.append(phi)
        self.states.append(SystemState(self.n_drones, state.copy(), phi))
        self.steps += 1
        return phi

    def run(self, n_steps=50):
        for _ in range(n_steps):
            self.measure()

    def emergence_index(self) -> float:
        """창발 지수: Phi 변동성."""
        if len(self.phi_history) < 2:
            return 0.0
        return float(np.std(self.phi_history) / (np.mean(self.phi_history) + 1e-8))

    def summary(self):
        return {
            "drones": self.n_drones,
            "measurements": self.steps,
            "avg_phi": round(float(np.mean(self.phi_history)) if self.phi_history else 0, 4),
            "max_phi": round(float(np.max(self.phi_history)) if self.phi_history else 0, 4),
            "emergence_index": round(self.emergence_index(), 4),
        }


if __name__ == "__main__":
    scm = SwarmConsciousnessMetric(8, 42)
    scm.run(50)
    for k, v in scm.summary().items():
        print(f"  {k}: {v}")
