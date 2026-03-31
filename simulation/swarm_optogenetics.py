# Phase 606: Swarm Optogenetics — Light-Inspired Swarm Control
"""
광유전학 영감 군집 제어: 광 자극/억제 모델,
흥분/억제 상태 전이, 파동 전파.
"""

import numpy as np
from dataclasses import dataclass


@dataclass
class OptoAgent:
    agent_id: int
    x: float
    y: float
    excitation: float = 0.0  # 0-1
    inhibition: float = 0.0  # 0-1
    channel_state: str = "closed"  # closed, open, inactivated


class OptogeneticController:
    def __init__(self, n_agents=20, seed=42):
        self.rng = np.random.default_rng(seed)
        self.agents = [
            OptoAgent(i, float(self.rng.uniform(0, 100)), float(self.rng.uniform(0, 100)))
            for i in range(n_agents)
        ]
        self.n = n_agents
        self.light_sources: list[tuple] = []  # (x, y, intensity, type)

    def add_light(self, x: float, y: float, intensity: float, light_type="excite"):
        self.light_sources.append((x, y, intensity, light_type))

    def step(self, dt=0.1):
        for a in self.agents:
            total_excite = 0.0
            total_inhibit = 0.0
            for lx, ly, intensity, ltype in self.light_sources:
                dist = np.sqrt((a.x - lx)**2 + (a.y - ly)**2)
                effect = intensity * np.exp(-dist / 30.0)
                if ltype == "excite":
                    total_excite += effect
                else:
                    total_inhibit += effect
            # Channel dynamics
            a.excitation = float(np.clip(a.excitation + dt * (total_excite - 0.5 * a.excitation), 0, 1))
            a.inhibition = float(np.clip(a.inhibition + dt * (total_inhibit - 0.5 * a.inhibition), 0, 1))
            net = a.excitation - a.inhibition
            if net > 0.5:
                a.channel_state = "open"
            elif net < -0.2:
                a.channel_state = "inactivated"
            else:
                a.channel_state = "closed"
            # Movement based on state
            if a.channel_state == "open":
                # Move toward nearest light
                if self.light_sources:
                    nearest = min(self.light_sources, key=lambda l: (a.x-l[0])**2 + (a.y-l[1])**2)
                    dx = nearest[0] - a.x
                    dy = nearest[1] - a.y
                    d = np.sqrt(dx**2 + dy**2) + 1e-6
                    a.x += float(dx / d * 2 * dt)
                    a.y += float(dy / d * 2 * dt)
            elif a.channel_state == "inactivated":
                a.x += float(self.rng.normal(0, 0.5))
                a.y += float(self.rng.normal(0, 0.5))


class SwarmOptogenetics:
    def __init__(self, n_agents=20, seed=42):
        self.controller = OptogeneticController(n_agents, seed)
        self.steps = 0
        self.controller.add_light(50, 50, 1.0, "excite")
        self.controller.add_light(80, 20, 0.5, "inhibit")

    def run(self, steps=100):
        for _ in range(steps):
            self.controller.step()
            self.steps += 1

    def summary(self):
        states = [a.channel_state for a in self.controller.agents]
        return {
            "agents": self.controller.n,
            "steps": self.steps,
            "open": states.count("open"),
            "closed": states.count("closed"),
            "inactivated": states.count("inactivated"),
            "avg_excitation": round(float(np.mean([a.excitation for a in self.controller.agents])), 4),
        }


if __name__ == "__main__":
    so = SwarmOptogenetics(20, 42)
    so.run(100)
    for k, v in so.summary().items():
        print(f"  {k}: {v}")
