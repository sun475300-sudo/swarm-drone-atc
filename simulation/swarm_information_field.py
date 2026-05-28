# Phase 603: Swarm Information Field — Fisher Information
"""
정보장 군집: 피셔 정보 기반 탐색,
정보 밀도 경사 추종, 센서 융합.
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class InfoAgent:
    """``InfoAgent`` 역할을 담당한다."""
    agent_id: int
    position: np.ndarray
    measurement: float = 0.0


class InformationField:
    """``InformationField`` 관련 기능을 제공한다."""
    def __init__(self, n_agents=10, seed=42):
        """인스턴스를 초기화한다."""
        self.rng = np.random.default_rng(seed)
        self.n = n_agents
        self.agents = [
            InfoAgent(i, self.rng.uniform(-50, 50, 2))
            for i in range(n_agents)
        ]
        self.source = np.array([20.0, 20.0])
        self.noise_std = 5.0

    def _measure(self, agent: InfoAgent) -> float:
        dist = np.linalg.norm(agent.position - self.source)
        signal = 100.0 / (1 + dist)
        noise = self.rng.normal(0, self.noise_std)
        return float(signal + noise)

    def compute_fisher_info(self) -> float:
        """`fisher info` 값을 계산한다."""
        measurements = [self._measure(a) for a in self.agents]
        if len(measurements) < 2:
            return 0.0
        var = float(np.var(measurements))
        return 1.0 / (var + 1e-6)

    def step(self, dt=0.5):
        """`대상` 실행 상태를 제어한다."""
        for a in self.agents:
            a.measurement = self._measure(a)
            grad = np.zeros(2)
            for other in self.agents:
                if other.agent_id != a.agent_id:
                    diff = other.position - a.position
                    dist = np.linalg.norm(diff) + 1e-6
                    weight = other.measurement - a.measurement
                    grad += weight * diff / dist
            a.position += grad * dt * 0.01


class SwarmInformationField:
    """``SwarmInformationField`` 관련 기능을 제공한다."""
    def __init__(self, n_agents=15, seed=42):
        """인스턴스를 초기화한다."""
        self.field = InformationField(n_agents, seed)
        self.steps = 0
        self.fisher_history: list[float] = []

    def run(self, steps=50):
        """메인 실행 루프를 수행한다."""
        for _ in range(steps):
            self.field.step()
            self.fisher_history.append(self.field.compute_fisher_info())
            self.steps += 1

    def summary(self):
        """현재 상태 요약을 반환한다."""
        return {
            "agents": self.field.n,
            "steps": self.steps,
            "initial_fisher": round(self.fisher_history[0], 6) if self.fisher_history else 0,
            "final_fisher": round(self.fisher_history[-1], 6) if self.fisher_history else 0,
        }


if __name__ == "__main__":
    sif = SwarmInformationField(15, 42)
    sif.run(50)
    for k, v in sif.summary().items():
        print(f"  {k}: {v}")
