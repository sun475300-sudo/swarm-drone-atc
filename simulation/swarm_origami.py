# Phase 581: Swarm Origami — Fold-Based Formation Transform
"""
군집 오리가미: 접힘 변환 기반 대형 전환,
크리즈 패턴, 강체 접힘, 연속 변형.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class CreasePattern:
    vertices: np.ndarray    # (N, 3)
    edges: list             # [(i, j, fold_angle)]
    fold_type: str = "valley"


@dataclass
class FoldState:
    step: int
    positions: np.ndarray
    fold_angle: float
    energy: float


class OrigamiTransformer:
    """접힘 기반 대형 변환기."""

    def __init__(self, n_agents=20, seed=42):
        self.rng = np.random.default_rng(seed)
        self.n = n_agents
        self.positions = self.rng.uniform(-10, 10, (n_agents, 3))
        self.positions[:, 2] = 50.0  # 초기 고도 50m

    def fold(self, axis: np.ndarray, angle: float, pivot: np.ndarray = None):
        """축 기준 접힘 변환."""
        if pivot is None:
            pivot = np.mean(self.positions, axis=0)
        axis = axis / (np.linalg.norm(axis) + 1e-8)
        c, s = np.cos(angle), np.sin(angle)
        K = np.array([[0, -axis[2], axis[1]],
                       [axis[2], 0, -axis[0]],
                       [-axis[1], axis[0], 0]])
        R = np.eye(3) * c + (1 - c) * np.outer(axis, axis) + s * K

        centered = self.positions - pivot
        # 접힘선 한쪽만 변환
        side = centered @ axis
        mask = side > 0
        centered[mask] = (R @ centered[mask].T).T
        self.positions = centered + pivot

    def symmetric_fold(self, n_folds=4):
        """대칭 다중 접힘."""
        for i in range(n_folds):
            angle = np.pi / (i + 2)
            axis = np.array([np.cos(i * np.pi / n_folds), np.sin(i * np.pi / n_folds), 0])
            self.fold(axis, angle)

    def formation_energy(self) -> float:
        """대형 에너지: 에이전트 간 거리 분산."""
        dists = []
        for i in range(self.n):
            for j in range(i + 1, self.n):
                dists.append(np.linalg.norm(self.positions[i] - self.positions[j]))
        return float(np.var(dists)) if dists else 0.0

    def compactness(self) -> float:
        """밀집도: 볼록 껍질 체적 근사."""
        spread = np.std(self.positions, axis=0)
        return float(np.prod(spread + 1e-6))


class SwarmOrigami:
    """군집 오리가미 시뮬레이션."""

    def __init__(self, n_agents=20, seed=42):
        self.rng = np.random.default_rng(seed)
        self.transformer = OrigamiTransformer(n_agents, seed)
        self.history: list[FoldState] = []
        self.steps = 0

    def run(self, n_folds=6):
        for i in range(n_folds):
            angle = float(self.rng.uniform(0.3, 1.5))
            axis = self.rng.normal(0, 1, 3)
            self.transformer.fold(axis, angle)
            energy = self.transformer.formation_energy()
            self.history.append(FoldState(i, self.transformer.positions.copy(), angle, energy))
            self.steps += 1

    def summary(self):
        energies = [h.energy for h in self.history]
        return {
            "agents": self.transformer.n,
            "folds": self.steps,
            "final_energy": round(energies[-1], 2) if energies else 0,
            "min_energy": round(min(energies), 2) if energies else 0,
            "compactness": round(self.transformer.compactness(), 2),
        }


if __name__ == "__main__":
    so = SwarmOrigami(20, 42)
    so.run(6)
    for k, v in so.summary().items():
        print(f"  {k}: {v}")
