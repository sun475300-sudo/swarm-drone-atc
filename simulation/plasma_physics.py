# Phase 630: Plasma Physics — Vlasov Equation Analogy
"""
플라즈마 물리학 비유 군집 동역학:
블라소프 방정식, 데바이 차폐, 랑다우 감쇠.
"""

import numpy as np
from dataclasses import dataclass


@dataclass
class PlasmaParticle:
    pid: int
    position: np.ndarray
    velocity: np.ndarray
    charge: float
    mass: float = 1.0


class VlasovSimulator:
    def __init__(self, n_particles=30, seed=42):
        self.rng = np.random.default_rng(seed)
        self.n = n_particles
        self.particles = []
        for i in range(n_particles):
            self.particles.append(PlasmaParticle(
                i,
                self.rng.uniform(-50, 50, 2),
                self.rng.normal(0, 2, 2),
                float(self.rng.choice([-1, 1])),
            ))
        self.debye_length = 10.0
        self.dt = 0.05
        self.damping = 0.98

    def compute_field(self) -> np.ndarray:
        field = np.zeros((self.n, 2))
        for i in range(self.n):
            for j in range(self.n):
                if i == j:
                    continue
                r = self.particles[j].position - self.particles[i].position
                dist = np.linalg.norm(r) + 1e-3
                # Debye-screened Coulomb
                screening = np.exp(-dist / self.debye_length)
                force = self.particles[i].charge * self.particles[j].charge * screening / (dist**2)
                field[i] -= force * r / dist
        return field

    def step(self):
        field = self.compute_field()
        for i, p in enumerate(self.particles):
            p.velocity += field[i] * self.dt / p.mass
            p.velocity *= self.damping
            p.position += p.velocity * self.dt

    def kinetic_energy(self) -> float:
        return float(sum(0.5 * p.mass * np.dot(p.velocity, p.velocity) for p in self.particles))

    def potential_energy(self) -> float:
        pe = 0.0
        for i in range(self.n):
            for j in range(i+1, self.n):
                dist = np.linalg.norm(self.particles[i].position - self.particles[j].position) + 1e-3
                screening = np.exp(-dist / self.debye_length)
                pe += self.particles[i].charge * self.particles[j].charge * screening / dist
        return float(pe)


class PlasmaPhysics:
    def __init__(self, n_particles=30, seed=42):
        self.sim = VlasovSimulator(n_particles, seed)
        self.steps = 0
        self.ke_history: list[float] = []
        self.pe_history: list[float] = []

    def run(self, steps=200):
        for _ in range(steps):
            self.sim.step()
            self.ke_history.append(self.sim.kinetic_energy())
            self.pe_history.append(self.sim.potential_energy())
            self.steps += 1

    def summary(self):
        return {
            "particles": self.sim.n,
            "steps": self.steps,
            "debye_length": self.sim.debye_length,
            "final_KE": round(self.ke_history[-1], 4) if self.ke_history else 0,
            "final_PE": round(self.pe_history[-1], 4) if self.pe_history else 0,
            "energy_ratio": round(self.ke_history[-1] / (abs(self.pe_history[-1]) + 1e-6), 4) if self.ke_history else 0,
        }


if __name__ == "__main__":
    pp = PlasmaPhysics(30, 42)
    pp.run(200)
    for k, v in pp.summary().items():
        print(f"  {k}: {v}")
