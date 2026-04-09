# Phase 624: Swarm Hydraulics — Navier-Stokes Analogy
"""
유체역학 비유 군집 흐름 제어:
나비에-스토크스 비유, 압력 구배, 점성 확산.
"""

import numpy as np
from dataclasses import dataclass


class FluidGrid:
    def __init__(self, nx=40, ny=40, viscosity=0.1, seed=42):
        self.rng = np.random.default_rng(seed)
        self.nx, self.ny = nx, ny
        self.viscosity = viscosity
        self.vx = np.zeros((nx, ny))
        self.vy = np.zeros((nx, ny))
        self.pressure = np.zeros((nx, ny))
        self.density = np.ones((nx, ny))

    def apply_source(self, x: int, y: int, fx: float, fy: float):
        x, y = int(np.clip(x, 1, self.nx-2)), int(np.clip(y, 1, self.ny-2))
        self.vx[x, y] += fx
        self.vy[x, y] += fy

    def diffuse(self, dt=0.01):
        a = self.viscosity * dt
        for _ in range(5):
            self.vx[1:-1, 1:-1] = (self.vx[1:-1, 1:-1] + a * (
                self.vx[2:, 1:-1] + self.vx[:-2, 1:-1] +
                self.vx[1:-1, 2:] + self.vx[1:-1, :-2]
            )) / (1 + 4 * a)
            self.vy[1:-1, 1:-1] = (self.vy[1:-1, 1:-1] + a * (
                self.vy[2:, 1:-1] + self.vy[:-2, 1:-1] +
                self.vy[1:-1, 2:] + self.vy[1:-1, :-2]
            )) / (1 + 4 * a)

    def advect(self, dt=0.01):
        new_vx = self.vx.copy()
        new_vy = self.vy.copy()
        for i in range(1, self.nx - 1):
            for j in range(1, self.ny - 1):
                x_back = i - dt * self.vx[i, j] * self.nx
                y_back = j - dt * self.vy[i, j] * self.ny
                x_back = np.clip(x_back, 0.5, self.nx - 1.5)
                y_back = np.clip(y_back, 0.5, self.ny - 1.5)
                i0, j0 = int(x_back), int(y_back)
                i1, j1 = min(i0+1, self.nx-1), min(j0+1, self.ny-1)
                sx, sy = x_back - i0, y_back - j0
                new_vx[i,j] = (1-sx)*((1-sy)*self.vx[i0,j0]+sy*self.vx[i0,j1]) + sx*((1-sy)*self.vx[i1,j0]+sy*self.vx[i1,j1])
                new_vy[i,j] = (1-sx)*((1-sy)*self.vy[i0,j0]+sy*self.vy[i0,j1]) + sx*((1-sy)*self.vy[i1,j0]+sy*self.vy[i1,j1])
        self.vx, self.vy = new_vx, new_vy

    def step(self, dt=0.01):
        self.diffuse(dt)
        self.advect(dt)

    def kinetic_energy(self) -> float:
        return float(0.5 * np.sum(self.vx**2 + self.vy**2))


class SwarmHydraulics:
    def __init__(self, n_drones=15, seed=42):
        self.rng = np.random.default_rng(seed)
        self.fluid = FluidGrid(40, 40, 0.1, seed)
        self.n_drones = n_drones
        self.steps = 0
        self.energy_history: list[float] = []
        self.fluid.apply_source(10, 20, 5.0, 0.0)
        self.fluid.apply_source(30, 20, -3.0, 2.0)

    def run(self, steps=100):
        for _ in range(steps):
            self.fluid.step()
            self.energy_history.append(self.fluid.kinetic_energy())
            self.steps += 1

    def summary(self):
        return {
            "drones": self.n_drones,
            "grid": f"{self.fluid.nx}x{self.fluid.ny}",
            "steps": self.steps,
            "initial_energy": round(self.energy_history[0], 4) if self.energy_history else 0,
            "final_energy": round(self.energy_history[-1], 4) if self.energy_history else 0,
        }


if __name__ == "__main__":
    sh = SwarmHydraulics(15, 42)
    sh.run(100)
    for k, v in sh.summary().items():
        print(f"  {k}: {v}")
