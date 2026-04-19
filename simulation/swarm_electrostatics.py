# Phase 609: Swarm Electrostatics — Coulomb Interaction Model
"""
정전기 모델 군집: 쿨롱 상호작용,
전하 기반 분리/응집, 전위장 탐색.
"""

import numpy as np
from dataclasses import dataclass


@dataclass
class ChargedAgent:
    agent_id: int
    position: np.ndarray
    charge: float  # positive=repel, negative=attract
    velocity: np.ndarray


class CoulombSwarm:
    def __init__(self, n_agents=20, seed=42):
        self.rng = np.random.default_rng(seed)
        self.n = n_agents
        self.agents = []
        for i in range(n_agents):
            charge = float(self.rng.choice([-1, 1]) * self.rng.uniform(0.5, 2.0))
            self.agents.append(ChargedAgent(
                i,
                self.rng.uniform(-50, 50, 2),
                charge,
                np.zeros(2)
            ))
        self.k_coulomb = 100.0
        self.damping = 0.9

    def compute_forces(self) -> np.ndarray:
        forces = np.zeros((self.n, 2))
        for i in range(self.n):
            for j in range(i + 1, self.n):
                r = self.agents[j].position - self.agents[i].position
                dist = np.linalg.norm(r) + 1e-3
                f_mag = self.k_coulomb * self.agents[i].charge * self.agents[j].charge / (dist ** 2)
                f_dir = r / dist
                forces[i] -= f_mag * f_dir
                forces[j] += f_mag * f_dir
        return forces

    def step(self, dt=0.05):
        forces = self.compute_forces()
        for i, a in enumerate(self.agents):
            a.velocity = (a.velocity + forces[i] * dt) * self.damping
            a.position += a.velocity * dt

    def total_energy(self) -> float:
        energy = 0.0
        for i in range(self.n):
            for j in range(i + 1, self.n):
                dist = np.linalg.norm(self.agents[i].position - self.agents[j].position) + 1e-3
                energy += self.k_coulomb * self.agents[i].charge * self.agents[j].charge / dist
        return float(energy)


class SwarmElectrostatics:
    def __init__(self, n_agents=20, seed=42):
        self.swarm = CoulombSwarm(n_agents, seed)
        self.energy_history: list[float] = []
        self.steps = 0

    def run(self, steps=200):
        for _ in range(steps):
            self.swarm.step()
            self.energy_history.append(self.swarm.total_energy())
            self.steps += 1

    def summary(self):
        return {
            "agents": self.swarm.n,
            "steps": self.steps,
            "initial_energy": round(self.energy_history[0], 2) if self.energy_history else 0,
            "final_energy": round(self.energy_history[-1], 2) if self.energy_history else 0,
            "energy_change": round(self.energy_history[-1] - self.energy_history[0], 2) if self.energy_history else 0,
            "positive_charges": sum(1 for a in self.swarm.agents if a.charge > 0),
        }


if __name__ == "__main__":
    se = SwarmElectrostatics(20, 42)
    se.run(200)
    for k, v in se.summary().items():
        print(f"  {k}: {v}")
