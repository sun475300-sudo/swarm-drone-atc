# Phase 585: Holographic Memory — Distributed Associative Storage
"""
홀로그래픽 메모리: 분산 연상 저장,
홀로그래픽 축소 표현(HRR), 바인딩/언바인딩.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class HoloRecord:
    key: str
    value: str
    vector: np.ndarray


class HolographicReducedRep:
    """홀로그래픽 축소 표현(HRR)."""

    def __init__(self, dim=256, seed=42):
        self.dim = dim
        self.rng = np.random.default_rng(seed)
        self.codebook: dict[str, np.ndarray] = {}

    def get_vector(self, symbol: str) -> np.ndarray:
        if symbol not in self.codebook:
            v = self.rng.normal(0, 1.0 / np.sqrt(self.dim), self.dim)
            self.codebook[symbol] = v
        return self.codebook[symbol]

    def bind(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """순환 컨볼루션 바인딩."""
        return np.real(np.fft.ifft(np.fft.fft(a) * np.fft.fft(b)))

    def unbind(self, bound: np.ndarray, key: np.ndarray) -> np.ndarray:
        """역 컨볼루션 언바인딩."""
        inv = np.roll(key[::-1], 1)
        return np.real(np.fft.ifft(np.fft.fft(bound) * np.fft.fft(inv)))

    def superpose(self, vectors: list[np.ndarray]) -> np.ndarray:
        """중첩 (합산)."""
        return np.sum(vectors, axis=0)

    def similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        na = np.linalg.norm(a)
        nb = np.linalg.norm(b)
        if na < 1e-10 or nb < 1e-10:
            return 0.0
        return float(np.dot(a, b) / (na * nb))


class HolographicMemory:
    """홀로그래픽 메모리 시뮬레이션."""

    def __init__(self, dim=256, seed=42):
        self.rng = np.random.default_rng(seed)
        self.hrr = HolographicReducedRep(dim, seed)
        self.memory = np.zeros(dim)
        self.records: list[HoloRecord] = []
        self.recalls = 0
        self.correct = 0

    def store(self, key: str, value: str):
        k_vec = self.hrr.get_vector(key)
        v_vec = self.hrr.get_vector(value)
        bound = self.hrr.bind(k_vec, v_vec)
        self.memory += bound
        self.records.append(HoloRecord(key, value, bound))

    def recall(self, key: str) -> tuple[str, float]:
        k_vec = self.hrr.get_vector(key)
        retrieved = self.hrr.unbind(self.memory, k_vec)
        best_match = ""
        best_sim = -1.0
        for symbol, vec in self.hrr.codebook.items():
            sim = self.hrr.similarity(retrieved, vec)
            if sim > best_sim:
                best_sim = sim
                best_match = symbol
        self.recalls += 1
        # 정답 확인
        for r in self.records:
            if r.key == key and best_match == r.value:
                self.correct += 1
                break
        return best_match, best_sim

    def run(self, n_pairs=15):
        drone_attrs = [
            ("drone_0", "patrol"), ("drone_1", "deliver"), ("drone_2", "survey"),
            ("drone_3", "escort"), ("drone_4", "relay"), ("drone_5", "rescue"),
            ("drone_6", "monitor"), ("drone_7", "intercept"), ("drone_8", "map"),
            ("drone_9", "charge"), ("alpha", "north"), ("bravo", "south"),
            ("charlie", "east"), ("delta", "west"), ("echo", "center"),
        ]
        for key, val in drone_attrs[:n_pairs]:
            self.store(key, val)
        for key, _ in drone_attrs[:n_pairs]:
            self.recall(key)

    def summary(self):
        return {
            "dimension": self.hrr.dim,
            "stored": len(self.records),
            "recalls": self.recalls,
            "correct": self.correct,
            "accuracy": round(self.correct / max(self.recalls, 1), 4),
            "memory_norm": round(float(np.linalg.norm(self.memory)), 4),
        }


if __name__ == "__main__":
    hm = HolographicMemory(256, 42)
    hm.run(15)
    for k, v in hm.summary().items():
        print(f"  {k}: {v}")
