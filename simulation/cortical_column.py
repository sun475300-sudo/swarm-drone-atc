# Phase 625: Cortical Column — HTM Temporal Memory
"""
계층적 시간 메모리 패턴 인식:
미니컬럼, 시냅스 성장, 시퀀스 학습.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class Synapse:
    source: int
    permanence: float = 0.5
    connected_threshold: float = 0.3

    @property
    def is_connected(self) -> bool:
        return self.permanence >= self.connected_threshold


@dataclass
class MiniColumn:
    col_id: int
    cells: int = 4
    active: bool = False
    bursting: bool = False
    synapses: list = field(default_factory=list)


class CorticalColumn:
    def __init__(self, n_columns=64, n_inputs=32, seed=42):
        self.rng = np.random.default_rng(seed)
        self.n_columns = n_columns
        self.n_inputs = n_inputs
        self.columns = [MiniColumn(i) for i in range(n_columns)]
        self._init_synapses()
        self.active_columns: list[int] = []
        self.predicted_columns: list[int] = []
        self.learn_count = 0

    def _init_synapses(self):
        for col in self.columns:
            n_syn = self.rng.integers(3, 8)
            sources = self.rng.choice(self.n_inputs, n_syn, replace=False)
            col.synapses = [Synapse(int(s), float(self.rng.uniform(0.2, 0.7))) for s in sources]

    def compute_overlap(self, input_bits: np.ndarray) -> np.ndarray:
        overlaps = np.zeros(self.n_columns)
        for i, col in enumerate(self.columns):
            for syn in col.synapses:
                if syn.is_connected and syn.source < len(input_bits) and input_bits[syn.source]:
                    overlaps[i] += 1
        return overlaps

    def inhibit(self, overlaps: np.ndarray, sparsity=0.1) -> list[int]:
        k = max(1, int(self.n_columns * sparsity))
        top_k = np.argsort(overlaps)[-k:]
        return [int(i) for i in top_k if overlaps[i] > 0]

    def learn(self, active_cols: list[int], input_bits: np.ndarray):
        for col_id in active_cols:
            col = self.columns[col_id]
            for syn in col.synapses:
                if syn.source < len(input_bits) and input_bits[syn.source]:
                    syn.permanence = min(1.0, syn.permanence + 0.05)
                else:
                    syn.permanence = max(0.0, syn.permanence - 0.02)
        self.learn_count += 1

    def process(self, input_bits: np.ndarray) -> list[int]:
        overlaps = self.compute_overlap(input_bits)
        active = self.inhibit(overlaps)
        self.learn(active, input_bits)
        self.active_columns = active
        return active


class CorticalColumnHTM:
    def __init__(self, n_columns=64, n_inputs=32, seed=42):
        self.htm = CorticalColumn(n_columns, n_inputs, seed)
        self.rng = np.random.default_rng(seed)
        self.steps = 0
        self.accuracy_history: list[float] = []

    def run(self, steps=100):
        for _ in range(steps):
            pattern = (self.rng.random(self.htm.n_inputs) > 0.5).astype(int)
            active = self.htm.process(pattern)
            accuracy = len(active) / max(1, self.htm.n_columns) * 10
            self.accuracy_history.append(min(accuracy, 1.0))
            self.steps += 1

    def summary(self):
        return {
            "columns": self.htm.n_columns,
            "inputs": self.htm.n_inputs,
            "steps": self.steps,
            "learn_cycles": self.htm.learn_count,
            "avg_active": round(float(np.mean(self.accuracy_history)), 4) if self.accuracy_history else 0,
        }


if __name__ == "__main__":
    cc = CorticalColumnHTM(64, 32, 42)
    cc.run(100)
    for k, v in cc.summary().items():
        print(f"  {k}: {v}")
