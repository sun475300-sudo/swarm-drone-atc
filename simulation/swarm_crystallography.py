# Phase 621: Swarm Crystallography — Space Group Lattice Placement
"""
결정학 격자 기반 군집 배치 최적화:
공간군 대칭, 브라베 격자, 밀러 지수 기반 드론 배치.
"""

import numpy as np
from dataclasses import dataclass


@dataclass
class LatticePoint:
    index: tuple  # (h, k, l)
    position: np.ndarray
    occupied: bool = False


class BravaisLattice:
    def __init__(self, lattice_type="cubic", a=10.0, seed=42):
        self.rng = np.random.default_rng(seed)
        self.a = a
        self.lattice_type = lattice_type
        self.points: list[LatticePoint] = []
        self._generate()

    def _generate(self):
        basis = self._get_basis()
        for h in range(-3, 4):
            for k in range(-3, 4):
                for l in range(0, 4):
                    pos = h * basis[0] + k * basis[1] + l * basis[2]
                    self.points.append(LatticePoint((h, k, l), pos))

    def _get_basis(self) -> list[np.ndarray]:
        a = self.a
        if self.lattice_type == "cubic":
            return [np.array([a, 0, 0]), np.array([0, a, 0]), np.array([0, 0, a])]
        elif self.lattice_type == "hexagonal":
            return [np.array([a, 0, 0]), np.array([a/2, a*np.sqrt(3)/2, 0]), np.array([0, 0, a*1.5])]
        elif self.lattice_type == "bcc":
            return [np.array([a, 0, 0]), np.array([0, a, 0]), np.array([a/2, a/2, a/2])]
        return [np.array([a, 0, 0]), np.array([0, a, 0]), np.array([0, 0, a])]

    def assign_drones(self, n_drones: int) -> list[np.ndarray]:
        available = [p for p in self.points if not p.occupied]
        self.rng.shuffle(available)
        positions = []
        for i in range(min(n_drones, len(available))):
            available[i].occupied = True
            positions.append(available[i].position.copy())
        return positions


class SwarmCrystallography:
    def __init__(self, n_drones=20, lattice_type="cubic", seed=42):
        self.lattice = BravaisLattice(lattice_type, 15.0, seed)
        self.n_drones = n_drones
        self.positions = self.lattice.assign_drones(n_drones)
        self.steps = 0

    def run(self, steps=50):
        for _ in range(steps):
            for i, pos in enumerate(self.positions):
                self.positions[i] = pos + np.random.normal(0, 0.1, 3)
            self.steps += 1

    def packing_density(self) -> float:
        if len(self.positions) < 2:
            return 0.0
        dists = []
        for i in range(len(self.positions)):
            for j in range(i+1, len(self.positions)):
                dists.append(np.linalg.norm(self.positions[i] - self.positions[j]))
        return float(np.std(dists) / (np.mean(dists) + 1e-6))

    def summary(self):
        return {
            "drones": self.n_drones,
            "lattice": self.lattice.lattice_type,
            "lattice_points": len(self.lattice.points),
            "steps": self.steps,
            "packing_uniformity": round(1 - self.packing_density(), 4),
        }


if __name__ == "__main__":
    sc = SwarmCrystallography(20, "cubic", 42)
    sc.run(50)
    for k, v in sc.summary().items():
        print(f"  {k}: {v}")
