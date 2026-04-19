# Phase 588: Swarm Calculus — Continuum Dynamics Model
"""
군집 미적분: 연속체 역학 모델,
밀도장/속도장 PDE 시뮬레이션, 유체 근사.
"""

import numpy as np
from dataclasses import dataclass


@dataclass
class FieldState:
    time: float
    density: np.ndarray
    velocity_x: np.ndarray
    velocity_y: np.ndarray
    total_mass: float


class ContinuumField:
    """연속체 밀도/속도장."""

    def __init__(self, nx=32, ny=32, seed=42):
        self.rng = np.random.default_rng(seed)
        self.nx, self.ny = nx, ny
        self.dx = 1.0
        # 밀도장: 중앙 집중
        x = np.linspace(-1, 1, nx)
        y = np.linspace(-1, 1, ny)
        X, Y = np.meshgrid(x, y)
        self.rho = np.exp(-(X**2 + Y**2) / 0.3) * 10  # 밀도
        self.vx = np.zeros((nx, ny))  # X 속도
        self.vy = np.zeros((nx, ny))  # Y 속도
        self.diffusion = 0.05

    def advection_step(self, dt=0.1):
        """이류 스텝 (업윈드)."""
        rho_new = self.rho.copy()
        for i in range(1, self.nx - 1):
            for j in range(1, self.ny - 1):
                fx = self.vx[i, j] * (self.rho[i, j] - self.rho[i - 1, j]) / self.dx if self.vx[i, j] > 0 \
                    else self.vx[i, j] * (self.rho[i + 1, j] - self.rho[i, j]) / self.dx
                fy = self.vy[i, j] * (self.rho[i, j] - self.rho[i, j - 1]) / self.dx if self.vy[i, j] > 0 \
                    else self.vy[i, j] * (self.rho[i, j + 1] - self.rho[i, j]) / self.dx
                rho_new[i, j] -= dt * (fx + fy)
        self.rho = np.maximum(rho_new, 0)

    def diffusion_step(self, dt=0.1):
        """확산 스텝 (라플라시안)."""
        lap = np.zeros_like(self.rho)
        lap[1:-1, 1:-1] = (
            self.rho[2:, 1:-1] + self.rho[:-2, 1:-1]
            + self.rho[1:-1, 2:] + self.rho[1:-1, :-2]
            - 4 * self.rho[1:-1, 1:-1]
        ) / (self.dx ** 2)
        self.rho += self.diffusion * dt * lap
        self.rho = np.maximum(self.rho, 0)

    def apply_potential(self, target_x=0.7, target_y=0.0, strength=2.0):
        """목표점 포텐셜로 속도장 생성."""
        x = np.linspace(-1, 1, self.nx)
        y = np.linspace(-1, 1, self.ny)
        X, Y = np.meshgrid(x, y)
        dx = target_x - X
        dy = target_y - Y
        dist = np.sqrt(dx**2 + dy**2) + 1e-6
        self.vx = strength * dx / dist
        self.vy = strength * dy / dist

    def total_mass(self) -> float:
        return float(np.sum(self.rho) * self.dx ** 2)


class SwarmCalculus:
    """군집 미적분 시뮬레이션."""

    def __init__(self, nx=32, ny=32, seed=42):
        self.field = ContinuumField(nx, ny, seed)
        self.history: list[FieldState] = []
        self.time = 0.0
        self.field.apply_potential(0.7, 0.0, 2.0)

    def step(self, dt=0.1):
        self.field.advection_step(dt)
        self.field.diffusion_step(dt)
        self.time += dt
        self.history.append(FieldState(
            self.time, self.field.rho.copy(),
            self.field.vx.copy(), self.field.vy.copy(),
            self.field.total_mass()
        ))

    def run(self, steps=100, dt=0.1):
        for _ in range(steps):
            self.step(dt)

    def summary(self):
        masses = [h.total_mass for h in self.history]
        return {
            "grid": f"{self.field.nx}x{self.field.ny}",
            "steps": len(self.history),
            "initial_mass": round(masses[0], 4) if masses else 0,
            "final_mass": round(masses[-1], 4) if masses else 0,
            "mass_conservation": round(masses[-1] / (masses[0] + 1e-10), 4) if masses else 0,
            "peak_density": round(float(np.max(self.field.rho)), 4),
        }


if __name__ == "__main__":
    sc = SwarmCalculus(32, 32, 42)
    sc.run(100)
    for k, v in sc.summary().items():
        print(f"  {k}: {v}")
