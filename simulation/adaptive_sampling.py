# Phase 644: Adaptive Sampling — Density-Aware Telemetry Rate
"""
고밀도 공역에서는 높은 빈도(10Hz), 저밀도에서는 낮은 빈도(1Hz)로
텔레메트리 샘플링 주기를 동적 조절하여 대역폭 최적화.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class SamplingConfig:
    min_rate_hz: float = 1.0
    max_rate_hz: float = 10.0
    density_threshold: float = 0.5  # 밀도 0-1 스케일
    proximity_radius_m: float = 100.0


@dataclass
class DroneRate:
    drone_id: str
    current_rate_hz: float
    density_score: float
    neighbors: int


class AdaptiveSampler:
    def __init__(self, seed: int = 42, config: SamplingConfig | None = None):
        self.rng = np.random.default_rng(seed)
        self.config = config or SamplingConfig()
        self._rates: dict[str, DroneRate] = {}
        self._positions: dict[str, np.ndarray] = {}

    def update_positions(self, positions: dict[str, np.ndarray]) -> None:
        self._positions = positions

    def compute_density(self, drone_id: str) -> tuple[float, int]:
        if drone_id not in self._positions or len(self._positions) < 2:
            return 0.0, 0

        pos = self._positions[drone_id]
        count = 0
        for did, p in self._positions.items():
            if did == drone_id:
                continue
            dist = float(np.linalg.norm(pos - p))
            if dist < self.config.proximity_radius_m:
                count += 1

        max_neighbors = max(len(self._positions) - 1, 1)
        density = min(1.0, count / max(max_neighbors * 0.3, 1))
        return density, count

    def compute_rate(self, drone_id: str) -> float:
        density, neighbors = self.compute_density(drone_id)
        cfg = self.config

        # Linear interpolation based on density
        rate = cfg.min_rate_hz + density * (cfg.max_rate_hz - cfg.min_rate_hz)
        rate = max(cfg.min_rate_hz, min(cfg.max_rate_hz, rate))

        self._rates[drone_id] = DroneRate(drone_id, rate, density, neighbors)
        return rate

    def update_all(self) -> dict[str, float]:
        rates = {}
        for drone_id in self._positions:
            rates[drone_id] = self.compute_rate(drone_id)
        return rates

    def bandwidth_savings(self) -> dict:
        if not self._rates:
            return {"total_drones": 0, "avg_rate_hz": 0, "savings_pct": 0}

        rates = [r.current_rate_hz for r in self._rates.values()]
        avg_rate = float(np.mean(rates))
        max_rate = self.config.max_rate_hz
        savings = (1.0 - avg_rate / max_rate) * 100

        return {
            "total_drones": len(self._rates),
            "avg_rate_hz": round(avg_rate, 2),
            "max_rate_hz": max_rate,
            "savings_pct": round(savings, 1),
            "high_density_count": sum(1 for r in self._rates.values() if r.density_score > 0.5),
        }

    def simulate(self, n_drones: int = 50, n_steps: int = 30) -> list[dict]:
        history = []
        positions = {
            f"D-{i:04d}": self.rng.uniform(-2000, 2000, 3)
            for i in range(n_drones)
        }
        velocities = {
            did: self.rng.uniform(-10, 10, 3) for did in positions
        }

        for step in range(n_steps):
            for did in positions:
                positions[did] = positions[did] + velocities[did] * 0.1
            self.update_positions(positions)
            rates = self.update_all()
            savings = self.bandwidth_savings()
            history.append({"step": step, **savings})

        return history


if __name__ == "__main__":
    sampler = AdaptiveSampler(42)
    history = sampler.simulate(80, 20)
    for h in history[-5:]:
        print(f"Step {h['step']}: avg={h['avg_rate_hz']}Hz, "
              f"savings={h['savings_pct']}%, high_density={h['high_density_count']}")
