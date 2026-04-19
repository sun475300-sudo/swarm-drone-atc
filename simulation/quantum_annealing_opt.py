# Phase 583: Quantum Annealing Optimization
"""
양자 어닐링 최적화: 이징 모델 기반 QUBO 풀이,
경로/스케줄링 문제 최적화.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class QUBOResult:
    solution: np.ndarray
    energy: float
    iterations: int
    temperature_final: float


class IsingModel:
    """이징 모델 시뮬레이터."""

    def __init__(self, n_spins: int, seed=42):
        self.rng = np.random.default_rng(seed)
        self.n = n_spins
        self.J = self.rng.normal(0, 1, (n_spins, n_spins))
        self.J = (self.J + self.J.T) / 2
        np.fill_diagonal(self.J, 0)
        self.h = self.rng.normal(0, 0.5, n_spins)
        self.spins = self.rng.choice([-1, 1], n_spins).astype(float)

    def energy(self) -> float:
        return float(-0.5 * self.spins @ self.J @ self.spins - self.h @ self.spins)

    def anneal(self, T_start=5.0, T_end=0.01, steps=1000) -> QUBOResult:
        best_spins = self.spins.copy()
        best_energy = self.energy()

        for step in range(steps):
            T = T_start * (T_end / T_start) ** (step / steps)
            i = int(self.rng.integers(0, self.n))
            dE = 2 * self.spins[i] * (self.J[i] @ self.spins + self.h[i])
            if dE < 0 or self.rng.random() < np.exp(-dE / max(T, 1e-10)):
                self.spins[i] *= -1
            e = self.energy()
            if e < best_energy:
                best_energy = e
                best_spins = self.spins.copy()

        self.spins = best_spins
        return QUBOResult(best_spins, best_energy, steps, T_end)


class QuantumAnnealingOpt:
    """양자 어닐링 최적화 시뮬레이션."""

    def __init__(self, n_spins=32, seed=42):
        self.rng = np.random.default_rng(seed)
        self.n_spins = n_spins
        self.model = IsingModel(n_spins, seed)
        self.results: list[QUBOResult] = []

    def run(self, n_runs=5, steps_per_run=500):
        for r in range(n_runs):
            model = IsingModel(self.n_spins, seed=42 + r)
            result = model.anneal(5.0, 0.01, steps_per_run)
            self.results.append(result)

    def summary(self):
        energies = [r.energy for r in self.results]
        return {
            "spins": self.n_spins,
            "runs": len(self.results),
            "best_energy": round(min(energies), 4) if energies else 0,
            "avg_energy": round(float(np.mean(energies)), 4) if energies else 0,
            "energy_std": round(float(np.std(energies)), 4) if energies else 0,
        }


if __name__ == "__main__":
    qa = QuantumAnnealingOpt(32, 42)
    qa.run(5, 500)
    for k, v in qa.summary().items():
        print(f"  {k}: {v}")
