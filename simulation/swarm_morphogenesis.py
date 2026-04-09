"""
Phase 487: Swarm Morphogenesis
반응-확산 패턴 형성, 형태발생 기반 군집 자기조직화.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple


class MorphogenType(Enum):
    ACTIVATOR = "activator"
    INHIBITOR = "inhibitor"


class FormationType(Enum):
    CIRCLE = "circle"
    LINE = "line"
    GRID = "grid"
    V_SHAPE = "v_shape"
    SPIRAL = "spiral"
    RING = "ring"
    CUSTOM = "custom"


@dataclass
class Morphogen:
    name: str
    mtype: MorphogenType
    diffusion_rate: float
    decay_rate: float
    production_rate: float


@dataclass
class CellState:
    drone_id: int
    position: np.ndarray
    activator: float = 0.0
    inhibitor: float = 0.0
    fate: str = "undifferentiated"


class ReactionDiffusion:
    """Turing pattern reaction-diffusion system."""

    def __init__(self, n_cells: int = 30, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_cells = n_cells
        self.activator = self.rng.uniform(0, 1, n_cells)
        self.inhibitor = self.rng.uniform(0, 1, n_cells)
        self.Da = 0.1   # activator diffusion
        self.Di = 0.4   # inhibitor diffusion
        self.f = 0.055  # feed rate
        self.k = 0.062  # kill rate

    def step(self, dt: float = 0.1) -> Tuple[np.ndarray, np.ndarray]:
        a, b = self.activator, self.inhibitor
        lap_a = np.roll(a, 1) + np.roll(a, -1) - 2 * a
        lap_b = np.roll(b, 1) + np.roll(b, -1) - 2 * b
        reaction = a * a * b
        da = self.Da * lap_a - reaction + self.f * (1 - a)
        db = self.Di * lap_b + reaction - (self.f + self.k) * b
        self.activator = np.clip(a + da * dt, 0, 1)
        self.inhibitor = np.clip(b + db * dt, 0, 1)
        return self.activator.copy(), self.inhibitor.copy()

    def run(self, steps: int = 100, dt: float = 0.1) -> List[np.ndarray]:
        history = []
        for _ in range(steps):
            a, _ = self.step(dt)
            history.append(a)
        return history


class SwarmMorphogenesis:
    """Formation control via morphogenetic fields."""

    def __init__(self, n_drones: int = 20, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_drones = n_drones
        self.cells: List[CellState] = []
        self.rd = ReactionDiffusion(n_drones, seed)
        self.target_formation = FormationType.CIRCLE
        self.time = 0.0

        for i in range(n_drones):
            pos = self.rng.uniform(-50, 50, 3)
            pos[2] = self.rng.uniform(10, 50)
            self.cells.append(CellState(i, pos))

    def _target_positions(self, formation: FormationType) -> List[np.ndarray]:
        n = self.n_drones
        targets = []
        if formation == FormationType.CIRCLE:
            for i in range(n):
                angle = 2 * np.pi * i / n
                targets.append(np.array([30 * np.cos(angle), 30 * np.sin(angle), 30.0]))
        elif formation == FormationType.LINE:
            for i in range(n):
                targets.append(np.array([i * 5 - n * 2.5, 0, 30.0]))
        elif formation == FormationType.V_SHAPE:
            for i in range(n):
                side = 1 if i % 2 == 0 else -1
                idx = i // 2
                targets.append(np.array([idx * 5, side * idx * 3, 30.0]))
        elif formation == FormationType.GRID:
            cols = int(np.ceil(np.sqrt(n)))
            for i in range(n):
                r, c = divmod(i, cols)
                targets.append(np.array([c * 8, r * 8, 30.0]))
        elif formation == FormationType.SPIRAL:
            for i in range(n):
                t = i * 0.5
                targets.append(np.array([t * 3 * np.cos(t), t * 3 * np.sin(t), 30.0]))
        elif formation == FormationType.RING:
            for i in range(n):
                angle = 2 * np.pi * i / n
                r = 20 + 10 * np.sin(3 * angle)
                targets.append(np.array([r * np.cos(angle), r * np.sin(angle), 30.0]))
        else:
            for i in range(n):
                targets.append(self.rng.uniform(-30, 30, 3))
                targets[-1][2] = abs(targets[-1][2]) + 10
        return targets

    def _assign_roles(self):
        a, b = self.rd.activator, self.rd.inhibitor
        for i, cell in enumerate(self.cells):
            cell.activator = float(a[i])
            cell.inhibitor = float(b[i])
            if a[i] > 0.6:
                cell.fate = "leader"
            elif b[i] > 0.5:
                cell.fate = "scout"
            else:
                cell.fate = "follower"

    def step(self, dt: float = 0.1) -> Dict:
        self.time += dt
        self.rd.step(dt)
        self._assign_roles()
        targets = self._target_positions(self.target_formation)

        total_error = 0.0
        for i, cell in enumerate(self.cells):
            if i < len(targets):
                error = targets[i] - cell.position
                gain = 0.5 if cell.fate == "leader" else 0.3
                noise = self.rng.standard_normal(3) * 0.1
                cell.position += (error * gain + noise) * dt
                total_error += np.linalg.norm(error)

        return {
            "time": round(self.time, 2),
            "avg_error": round(total_error / self.n_drones, 3),
            "leaders": sum(1 for c in self.cells if c.fate == "leader"),
            "scouts": sum(1 for c in self.cells if c.fate == "scout"),
        }

    def morph_to(self, formation: FormationType, steps: int = 100, dt: float = 0.1) -> List[Dict]:
        self.target_formation = formation
        history = []
        for _ in range(steps):
            info = self.step(dt)
            history.append(info)
        return history

    def formation_quality(self) -> float:
        targets = self._target_positions(self.target_formation)
        errors = []
        for i, cell in enumerate(self.cells):
            if i < len(targets):
                errors.append(np.linalg.norm(cell.position - targets[i]))
        if not errors:
            return 0.0
        avg_error = np.mean(errors)
        return round(float(max(0, 1.0 - avg_error / 50.0)), 4)

    def summary(self) -> Dict:
        roles = {}
        for c in self.cells:
            roles[c.fate] = roles.get(c.fate, 0) + 1
        return {
            "drones": self.n_drones,
            "formation": self.target_formation.value,
            "quality": self.formation_quality(),
            "roles": roles,
            "time": round(self.time, 2),
        }
