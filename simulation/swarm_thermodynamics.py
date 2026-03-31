# Phase 541: Swarm Thermodynamics — Boltzmann Energy Optimization
"""
열역학적 군집 최적화: 볼츠만 분포 기반 에너지 상태,
시뮬레이티드 어닐링으로 최적 배치 탐색, 엔트로피/자유에너지 계산.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class ThermalState:
    position: np.ndarray
    energy: float
    temperature: float
    entropy: float = 0.0


@dataclass
class AnnealingResult:
    initial_energy: float
    final_energy: float
    temperature_final: float
    steps: int
    accepted: int
    rejected: int


class BoltzmannDistribution:
    """볼츠만 분포 기반 에너지 모델."""

    def __init__(self, seed=42):
        self.rng = np.random.default_rng(seed)

    def energy(self, positions: np.ndarray, target_spacing=20.0) -> float:
        """군집 에너지: 드론 간 거리가 target_spacing에서 벗어날수록 에너지 증가."""
        n = len(positions)
        if n < 2:
            return 0.0
        total = 0.0
        for i in range(n):
            for j in range(i + 1, n):
                d = np.linalg.norm(positions[i] - positions[j])
                total += (d - target_spacing) ** 2
        return total / (n * (n - 1) / 2)

    def boltzmann_prob(self, delta_e: float, temperature: float) -> float:
        if delta_e < 0:
            return 1.0
        if temperature < 1e-10:
            return 0.0
        return float(np.exp(-delta_e / temperature))

    def entropy(self, positions: np.ndarray) -> float:
        """Shannon 엔트로피 근사 (위치 분산 기반)."""
        if len(positions) < 2:
            return 0.0
        var = np.var(positions, axis=0).sum()
        return float(0.5 * np.log(2 * np.pi * np.e * max(var, 1e-10)))

    def free_energy(self, energy: float, entropy: float, temperature: float) -> float:
        return energy - temperature * entropy


class SimulatedAnnealing:
    """시뮬레이티드 어닐링 최적화."""

    def __init__(self, seed=42):
        self.rng = np.random.default_rng(seed)
        self.boltz = BoltzmannDistribution(seed)

    def optimize(self, positions: np.ndarray, t_init=100.0, t_min=0.1,
                 cooling=0.95, max_steps=500) -> tuple[np.ndarray, AnnealingResult]:
        current = positions.copy()
        current_e = self.boltz.energy(current)
        initial_e = current_e
        best = current.copy()
        best_e = current_e
        t = t_init
        accepted = 0
        rejected = 0

        for step in range(max_steps):
            # 랜덤 드론 하나 이동
            idx = int(self.rng.integers(0, len(current)))
            delta = self.rng.normal(0, t * 0.1, 3)
            candidate = current.copy()
            candidate[idx] += delta
            cand_e = self.boltz.energy(candidate)
            delta_e = cand_e - current_e

            if self.rng.random() < self.boltz.boltzmann_prob(delta_e, t):
                current = candidate
                current_e = cand_e
                accepted += 1
                if current_e < best_e:
                    best = current.copy()
                    best_e = current_e
            else:
                rejected += 1

            t *= cooling
            if t < t_min:
                break

        return best, AnnealingResult(initial_e, best_e, t, max_steps, accepted, rejected)


class SwarmThermodynamics:
    """군집 열역학 시뮬레이션."""

    def __init__(self, n_drones=20, seed=42):
        self.rng = np.random.default_rng(seed)
        self.n_drones = n_drones
        self.boltz = BoltzmannDistribution(seed)
        self.sa = SimulatedAnnealing(seed)
        self.positions = self.rng.uniform(-100, 100, (n_drones, 3))
        self.positions[:, 2] = 30 + self.rng.uniform(0, 70, n_drones)
        self.result: AnnealingResult | None = None

    def optimize(self, **kwargs):
        self.positions, self.result = self.sa.optimize(self.positions, **kwargs)

    def summary(self):
        e = self.boltz.energy(self.positions)
        s = self.boltz.entropy(self.positions)
        f = self.boltz.free_energy(e, s, 1.0)
        return {
            "drones": self.n_drones,
            "energy": round(e, 2),
            "entropy": round(s, 4),
            "free_energy": round(f, 2),
            "initial_energy": round(self.result.initial_energy, 2) if self.result else 0,
            "final_energy": round(self.result.final_energy, 2) if self.result else 0,
            "accepted": self.result.accepted if self.result else 0,
        }


if __name__ == "__main__":
    st = SwarmThermodynamics(20, 42)
    st.optimize()
    for k, v in st.summary().items():
        print(f"  {k}: {v}")
