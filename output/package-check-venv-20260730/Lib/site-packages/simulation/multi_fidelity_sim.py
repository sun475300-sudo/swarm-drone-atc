# Phase 607: Multi-Fidelity Simulation — Adaptive LOD
"""
다중 충실도 시뮬레이션: 저/중/고 충실도 전환,
비용-정확도 트레이드오프, 적응형 LOD.
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class FidelityLevel:
    """``FidelityLevel`` 관련 기능을 제공한다."""
    name: str
    cost: float  # relative compute cost
    accuracy: float  # 0-1
    dt: float  # time step


class AdaptiveSimulator:
    """``AdaptiveSimulator`` 관련 기능을 제공한다."""
    def __init__(self, seed=42):
        """인스턴스를 초기화한다."""
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
        """`fidelity` 상태를 갱신한다."""
        if level in self.levels:
            self.current_level = level

    def step(self) -> np.ndarray:
        """`대상` 실행 상태를 제어한다."""
        fl = self.levels[self.current_level]
        noise = self.rng.normal(0, 1 - fl.accuracy, len(self.state))
        dynamics = -0.1 * self.state + noise
        self.state = self.state + dynamics * fl.dt
        self.total_cost += fl.cost
        return self.state.copy()

    def evaluate_error(self) -> float:
        """`error` 결과를 계산하거나 판정한다."""
        fl = self.levels[self.current_level]
        return float((1 - fl.accuracy) * np.linalg.norm(self.state))


class MultiFidelitySim:
    """``MultiFidelitySim`` 관련 기능을 제공한다."""
    def __init__(self, n_drones=10, seed=42):
        """인스턴스를 초기화한다."""
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
        """메인 실행 루프를 수행한다."""
        for _ in range(steps):
            self.sim.step()
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
        """현재 상태 요약을 반환한다."""
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
