# Phase 607: Multi-Fidelity Simulation — Adaptive LOD
"""
다중 충실도 시뮬레이션: 저/중/고 충실도 전환,
비용-정확도 트레이드오프, 적응형 LOD.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class FidelityLevel:
    name: str
    cost: float  # relative compute cost
    accuracy: float  # 0-1
    dt: float  # time step


class AdaptiveSimulator:
    def __init__(self, seed=42):
        self.rng = np.random.default_rng(seed)
        self.levels = {
            "low": FidelityLevel("low", 1.0, 0.6, 1.0),
            "medium": FidelityLevel("medium", 5.0, 0.85, 0.1),
            "high": FidelityLevel("high", 20.0, 0.98, 0.01),
        }
        self.current_level = "low"
        self.state = self.rng.uniform(-10, 10, 4)
        self.total_cost = 0.0

    def set_fidelity(self, level: str):
        if level in self.levels:
            self.current_level = level

    def step(self) -> np.ndarray:
        fl = self.levels[self.current_level]
        noise = self.rng.normal(0, 1 - fl.accuracy, len(self.state))
        dynamics = -0.1 * self.state + noise
        self.state = self.state + dynamics * fl.dt
        self.total_cost += fl.cost
        return self.state.copy()

    def evaluate_error(self) -> float:
        fl = self.levels[self.current_level]
        return float((1 - fl.accuracy) * np.linalg.norm(self.state))


class MultiFidelitySim:
    def __init__(self, n_drones=10, seed=42):
        self.rng = np.random.default_rng(seed)
        self.sim = AdaptiveSimulator(seed)
        self.n_drones = n_drones
        self.steps = 0
        self.history: list[dict] = []
        self.fidelity_switches = 0

    def _select_fidelity(self, error: float):
        if error > 5.0:
            target = "high"
        elif error > 2.0:
            target = "medium"
        else:
            target = "low"
        if target != self.sim.current_level:
            self.sim.set_fidelity(target)
            self.fidelity_switches += 1

    def run(self, steps=200):
        for _ in range(steps):
            state = self.sim.step()
            error = self.sim.evaluate_error()
            self._select_fidelity(error)
            self.history.append({
                "step": self.steps,
                "fidelity": self.sim.current_level,
                "error": error,
                "cost": self.sim.total_cost,
            })
            self.steps += 1

    def summary(self):
        fidelities = [h["fidelity"] for h in self.history]
        return {
            "drones": self.n_drones,
            "steps": self.steps,
            "total_cost": round(self.sim.total_cost, 2),
            "fidelity_switches": self.fidelity_switches,
            "final_fidelity": self.sim.current_level,
            "low_pct": round(fidelities.count("low") / len(fidelities) * 100, 1) if fidelities else 0,
            "high_pct": round(fidelities.count("high") / len(fidelities) * 100, 1) if fidelities else 0,
        }


if __name__ == "__main__":
    mf = MultiFidelitySim(10, 42)
    mf.run(200)
    for k, v in mf.summary().items():
        print(f"  {k}: {v}")
