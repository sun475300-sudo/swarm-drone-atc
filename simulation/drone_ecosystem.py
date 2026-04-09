# Phase 586: Drone Ecosystem — Lotka-Volterra Dynamics
"""
드론 생태계: Lotka-Volterra 포식자-피식자 모델,
자원 경쟁, 생태적 균형 시뮬레이션.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class Species:
    name: str
    population: float
    growth_rate: float
    carrying_capacity: float


@dataclass
class EcoState:
    time: float
    populations: dict[str, float]
    total_biomass: float


class LotkaVolterra:
    """Lotka-Volterra 확장 모델."""

    def __init__(self, seed=42):
        self.rng = np.random.default_rng(seed)
        self.species: list[Species] = []
        self.interaction: np.ndarray = np.array([])

    def add_species(self, name: str, pop: float, growth: float, capacity: float):
        self.species.append(Species(name, pop, growth, capacity))
        n = len(self.species)
        new_inter = np.zeros((n, n))
        if self.interaction.size > 0:
            old_n = self.interaction.shape[0]
            new_inter[:old_n, :old_n] = self.interaction
        self.interaction = new_inter

    def set_interaction(self, i: int, j: int, value: float):
        self.interaction[i, j] = value

    def step(self, dt=0.1):
        n = len(self.species)
        pops = np.array([s.population for s in self.species])
        dpops = np.zeros(n)
        for i in range(n):
            s = self.species[i]
            logistic = s.growth_rate * pops[i] * (1 - pops[i] / s.carrying_capacity)
            interaction = sum(self.interaction[i, j] * pops[i] * pops[j] for j in range(n) if i != j)
            dpops[i] = logistic + interaction
        pops += dpops * dt
        pops = np.maximum(pops, 0)
        for i, s in enumerate(self.species):
            s.population = float(pops[i])


class DroneEcosystem:
    """드론 생태계 시뮬레이션."""

    def __init__(self, seed=42):
        self.rng = np.random.default_rng(seed)
        self.model = LotkaVolterra(seed)
        self.history: list[EcoState] = []
        self.time = 0.0
        self._setup()

    def _setup(self):
        # 드론 종류: 정찰(prey), 요격(predator), 수송(neutral)
        self.model.add_species("scout", 100.0, 0.5, 200.0)
        self.model.add_species("interceptor", 30.0, 0.3, 80.0)
        self.model.add_species("transport", 50.0, 0.2, 100.0)
        # 상호작용: 요격기가 정찰기 포식
        self.model.set_interaction(0, 1, -0.01)   # scout hurt by interceptor
        self.model.set_interaction(1, 0, 0.005)    # interceptor benefits from scout
        self.model.set_interaction(0, 2, -0.002)   # mild competition
        self.model.set_interaction(2, 0, -0.002)

    def step(self, dt=0.1):
        self.model.step(dt)
        self.time += dt
        pops = {s.name: round(s.population, 2) for s in self.model.species}
        biomass = sum(s.population for s in self.model.species)
        self.history.append(EcoState(self.time, pops, biomass))

    def run(self, steps=200, dt=0.1):
        for _ in range(steps):
            self.step(dt)

    def summary(self):
        final = {s.name: round(s.population, 2) for s in self.model.species}
        biomass_hist = [h.total_biomass for h in self.history]
        return {
            "species": len(self.model.species),
            "steps": len(self.history),
            "final_populations": final,
            "peak_biomass": round(max(biomass_hist), 2) if biomass_hist else 0,
            "final_biomass": round(biomass_hist[-1], 2) if biomass_hist else 0,
        }


if __name__ == "__main__":
    eco = DroneEcosystem(42)
    eco.run(200)
    for k, v in eco.summary().items():
        print(f"  {k}: {v}")
