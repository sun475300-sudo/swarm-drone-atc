# Phase 561: Reaction-Diffusion Morphogenesis — Turing Pattern Formation
"""
반응-확산 형태발생: 튜링 패턴 기반 군집 자기조직화,
2D Gray-Scott 모델 시뮬레이션.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class RDParams:
    Du: float = 0.16      # U 확산 계수
    Dv: float = 0.08      # V 확산 계수
    feed: float = 0.035   # 공급률
    kill: float = 0.065   # 소멸률
    dt: float = 1.0
    dx: float = 1.0


class GrayScottModel:
    """Gray-Scott 반응-확산 모델."""

    def __init__(self, size=64, params: RDParams = None, seed=42):
        self.size = size
        self.params = params or RDParams()
        self.rng = np.random.default_rng(seed)
        self.U = np.ones((size, size))
        self.V = np.zeros((size, size))
        # 중앙 시드 영역
        c = size // 2
        r = size // 8
        self.U[c-r:c+r, c-r:c+r] = 0.50
        self.V[c-r:c+r, c-r:c+r] = 0.25
        self.V += self.rng.uniform(0, 0.01, (size, size))

    def _laplacian(self, grid: np.ndarray) -> np.ndarray:
        return (
            np.roll(grid, 1, axis=0) + np.roll(grid, -1, axis=0)
            + np.roll(grid, 1, axis=1) + np.roll(grid, -1, axis=1)
            - 4 * grid
        ) / (self.params.dx ** 2)

    def step(self):
        p = self.params
        lap_u = self._laplacian(self.U)
        lap_v = self._laplacian(self.V)
        uvv = self.U * self.V * self.V
        self.U += p.dt * (p.Du * lap_u - uvv + p.feed * (1 - self.U))
        self.V += p.dt * (p.Dv * lap_v + uvv - (p.feed + p.kill) * self.V)
        self.U = np.clip(self.U, 0, 1)
        self.V = np.clip(self.V, 0, 1)

    def pattern_entropy(self) -> float:
        hist, _ = np.histogram(self.V.ravel(), bins=50, density=True)
        hist = hist[hist > 0]
        return float(-np.sum(hist * np.log(hist + 1e-12)))


@dataclass
class MorphoAgent:
    agent_id: int
    x: float
    y: float
    morphogen_u: float = 1.0
    morphogen_v: float = 0.0


class ReactionDiffusionMorpho:
    """반응-확산 형태발생 시뮬레이션."""

    def __init__(self, grid_size=64, n_agents=20, seed=42):
        self.rng = np.random.default_rng(seed)
        self.model = GrayScottModel(grid_size, seed=seed)
        self.grid_size = grid_size
        self.agents: list[MorphoAgent] = []
        self.steps_run = 0

        for i in range(n_agents):
            self.agents.append(MorphoAgent(
                i,
                float(self.rng.uniform(0, grid_size)),
                float(self.rng.uniform(0, grid_size)),
            ))

    def step(self):
        self.model.step()
        self.steps_run += 1
        for a in self.agents:
            gx = int(a.x) % self.grid_size
            gy = int(a.y) % self.grid_size
            a.morphogen_u = float(self.model.U[gx, gy])
            a.morphogen_v = float(self.model.V[gx, gy])
            # 구배 추적 이동
            if gx + 1 < self.grid_size:
                grad = self.model.V[gx + 1, gy] - self.model.V[gx, gy]
                a.x += float(grad * 2.0)
            if gy + 1 < self.grid_size:
                grad = self.model.V[gx, gy + 1] - self.model.V[gx, gy]
                a.y += float(grad * 2.0)
            a.x = float(np.clip(a.x, 0, self.grid_size - 1))
            a.y = float(np.clip(a.y, 0, self.grid_size - 1))

    def run(self, steps=100):
        for _ in range(steps):
            self.step()

    def summary(self):
        positions = [(a.x, a.y) for a in self.agents]
        xs = [p[0] for p in positions]
        ys = [p[1] for p in positions]
        return {
            "grid_size": self.grid_size,
            "agents": len(self.agents),
            "steps": self.steps_run,
            "pattern_entropy": round(self.model.pattern_entropy(), 4),
            "mean_v": round(float(np.mean(self.model.V)), 6),
            "agent_spread_x": round(float(np.std(xs)), 2),
            "agent_spread_y": round(float(np.std(ys)), 2),
        }


if __name__ == "__main__":
    rdm = ReactionDiffusionMorpho(64, 20, 42)
    rdm.run(100)
    for k, v in rdm.summary().items():
        print(f"  {k}: {v}")
