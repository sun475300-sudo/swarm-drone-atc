"""
City map generator.
===================
Generates urban obstacles, corridors, and landing pads for scenario simulation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import random


@dataclass
class Building:
    x: float
    y: float
    width: float
    height: float
    altitude: float


@dataclass
class Corridor:
    start: tuple[float, float]
    end: tuple[float, float]
    width: float


@dataclass
class LandingPad:
    pad_id: str
    x: float
    y: float
    capacity: int


class CityMapGenerator:
    def __init__(self, width_m: float = 2000.0, height_m: float = 2000.0, seed: int | None = 42) -> None:
        self.width_m = max(100.0, float(width_m))
        self.height_m = max(100.0, float(height_m))
        self.seed = seed
        self._rng = random.Random(seed)

    def _rand(self, lo: float, hi: float) -> float:
        return self._rng.uniform(lo, hi)

    def generate_buildings(self, count: int = 40) -> list[Building]:
        out: list[Building] = []
        n = max(0, int(count))
        for _ in range(n):
            w = self._rand(20.0, 90.0)
            h = self._rand(20.0, 90.0)
            x = self._rand(w / 2.0, self.width_m - w / 2.0)
            y = self._rand(h / 2.0, self.height_m - h / 2.0)
            alt = self._rand(20.0, 180.0)
            out.append(Building(x=x, y=y, width=w, height=h, altitude=alt))
        return out

    def generate_corridors(self, count: int = 6) -> list[Corridor]:
        out: list[Corridor] = []
        n = max(1, int(count))
        for idx in range(n):
            # Alternate horizontal and vertical lanes to distribute traffic paths.
            if idx % 2 == 0:
                y = self._rand(100.0, self.height_m - 100.0)
                out.append(Corridor(start=(0.0, y), end=(self.width_m, y), width=80.0))
            else:
                x = self._rand(100.0, self.width_m - 100.0)
                out.append(Corridor(start=(x, 0.0), end=(x, self.height_m), width=80.0))
        return out

    def generate_landing_pads(self, count: int = 8) -> list[LandingPad]:
        out: list[LandingPad] = []
        n = max(1, int(count))
        for i in range(n):
            x = self._rand(80.0, self.width_m - 80.0)
            y = self._rand(80.0, self.height_m - 80.0)
            cap = int(self._rand(2.0, 6.0))
            out.append(LandingPad(pad_id=f"PAD-{i+1:02d}", x=x, y=y, capacity=cap))
        return out

    def generate_map(
        self,
        buildings: int = 40,
        corridors: int = 6,
        pads: int = 8,
    ) -> dict[str, Any]:
        b = self.generate_buildings(buildings)
        c = self.generate_corridors(corridors)
        p = self.generate_landing_pads(pads)
        return {
            "bounds": {"width_m": self.width_m, "height_m": self.height_m},
            "buildings": [vars(it) for it in b],
            "corridors": [
                {"start": it.start, "end": it.end, "width": it.width} for it in c
            ],
            "landing_pads": [vars(it) for it in p],
        }

    def summary(self) -> dict[str, Any]:
        return {
            "width_m": self.width_m,
            "height_m": self.height_m,
            "seed": self.seed,
        }
