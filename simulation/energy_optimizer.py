# Phase 648: Energy Optimizer — Minimum Energy Path Planning
"""
에너지 소비 최적 경로 계획: 바람장, 고도 변화, 페이로드를
고려한 에너지 비용 함수 기반 A* 탐색.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class EnergyProfile:
    mass_kg: float = 2.5
    drag_coeff: float = 0.3
    prop_efficiency: float = 0.7
    battery_wh: float = 100.0
    hover_power_w: float = 50.0


@dataclass
class PathSegment:
    start: np.ndarray
    end: np.ndarray
    energy_wh: float
    wind_cost: float
    altitude_cost: float
    distance_m: float


class EnergyOptimizer:
    def __init__(self, seed: int = 42, profile: EnergyProfile | None = None):
        self.rng = np.random.default_rng(seed)
        self.profile = profile or EnergyProfile()
        self._wind_field: np.ndarray | None = None
        self._grid_size: int = 20

    def _init_wind_field(self) -> None:
        self._wind_field = self.rng.normal(0, 3, (self._grid_size, self._grid_size, 3))

    def _energy_cost(self, start: np.ndarray, end: np.ndarray) -> float:
        p = self.profile
        delta = end - start
        dist = float(np.linalg.norm(delta))
        if dist < 1e-6:
            return 0.0

        # Horizontal flight energy
        speed = max(float(np.linalg.norm(delta[:2])), 1.0) / max(dist / 10.0, 0.1)
        drag_force = 0.5 * 1.225 * p.drag_coeff * 0.1 * speed ** 2
        horiz_energy = drag_force * dist / 3600.0 / p.prop_efficiency

        # Altitude change energy
        dz = delta[2] if len(delta) > 2 else 0.0
        alt_energy = abs(p.mass_kg * 9.81 * dz) / 3600.0 / p.prop_efficiency

        # Wind assistance/resistance
        wind_cost = 0.0
        if self._wind_field is not None:
            gi = int(np.clip(start[0] / 500 + self._grid_size / 2, 0, self._grid_size - 1))
            gj = int(np.clip(start[1] / 500 + self._grid_size / 2, 0, self._grid_size - 1))
            wind = self._wind_field[gi, gj]
            direction = delta / max(dist, 1e-6)
            headwind = -float(np.dot(wind, direction))
            wind_cost = max(0, headwind * 0.01 * dist / 3600.0)

        hover_energy = p.hover_power_w * (dist / max(speed, 1.0)) / 3600.0

        return horiz_energy + alt_energy + wind_cost + hover_energy

    def plan_optimal_path(self, origin: np.ndarray, destination: np.ndarray,
                          n_waypoints: int = 5) -> list[PathSegment]:
        if self._wind_field is None:
            self._init_wind_field()

        # Generate candidate waypoints via grid search
        segments = []
        direction = destination - origin
        for i in range(n_waypoints):
            t = (i + 1) / (n_waypoints + 1)
            mid = origin + direction * t
            # Try altitude variations
            best_wp = mid.copy()
            best_cost = float("inf")
            for dz in [-20, -10, 0, 10, 20]:
                candidate = mid.copy()
                candidate[2] = candidate[2] + dz
                candidate[2] = max(30.0, min(120.0, candidate[2]))
                cost = self._energy_cost(
                    segments[-1].end if segments else origin,
                    candidate
                )
                if cost < best_cost:
                    best_cost = cost
                    best_wp = candidate.copy()

            start = segments[-1].end if segments else origin
            seg = PathSegment(
                start=start.copy(),
                end=best_wp.copy(),
                energy_wh=self._energy_cost(start, best_wp),
                wind_cost=0.0,
                altitude_cost=abs(best_wp[2] - start[2]) * 0.01,
                distance_m=float(np.linalg.norm(best_wp - start)),
            )
            segments.append(seg)

        # Final segment to destination
        start = segments[-1].end if segments else origin
        segments.append(PathSegment(
            start=start.copy(),
            end=destination.copy(),
            energy_wh=self._energy_cost(start, destination),
            wind_cost=0.0,
            altitude_cost=abs(destination[2] - start[2]) * 0.01,
            distance_m=float(np.linalg.norm(destination - start)),
        ))

        return segments

    def total_energy(self, segments: list[PathSegment]) -> float:
        return sum(s.energy_wh for s in segments)

    def range_estimate(self) -> float:
        p = self.profile
        cruise_power = p.hover_power_w * 1.2
        flight_hours = p.battery_wh / cruise_power
        cruise_speed = 10.0
        return flight_hours * cruise_speed * 3600

    def run(self, n_paths: int = 10) -> dict:
        self._init_wind_field()
        total = 0.0
        paths = []
        for i in range(n_paths):
            origin = self.rng.uniform(-2000, 2000, 3)
            origin[2] = self.rng.uniform(30, 80)
            dest = self.rng.uniform(-2000, 2000, 3)
            dest[2] = self.rng.uniform(30, 80)

            segments = self.plan_optimal_path(origin, dest)
            energy = self.total_energy(segments)
            total += energy
            paths.append({"path_id": i, "segments": len(segments), "energy_wh": round(energy, 4)})

        return {
            "paths_planned": n_paths,
            "total_energy_wh": round(total, 4),
            "avg_energy_wh": round(total / max(n_paths, 1), 4),
            "range_m": round(self.range_estimate(), 1),
        }


if __name__ == "__main__":
    opt = EnergyOptimizer(42)
    result = opt.run(15)
    for k, v in result.items():
        print(f"  {k}: {v}")
