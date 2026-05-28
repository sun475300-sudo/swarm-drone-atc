"""
Traffic simulator.
==================
Models hourly traffic demand, congestion, and incident probability for urban airspace.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any


@dataclass
class TrafficState:
    """``TrafficState`` 데이터를 표현한다."""
    hour: int
    demand: int
    congestion: float
    incident_probability: float


class TrafficSimulator:
    """``TrafficSimulator`` 관련 기능을 제공한다."""
    def __init__(self, base_demand: int = 120, seed: int | None = 42) -> None:
        """인스턴스를 초기화한다."""
        self.base_demand = max(1, int(base_demand))
        self.seed = seed
        self._rng = random.Random(seed)
        self._states: list[TrafficState] = []

    def _peak_multiplier(self, hour: int) -> float:
        h = int(hour) % 24
        if 7 <= h <= 9:
            return 1.45
        if 17 <= h <= 20:
            return 1.6
        if 0 <= h <= 5:
            return 0.55
        return 1.0

    def demand_at(self, hour: int, weather_factor: float = 1.0) -> int:
        """``demand_at`` 동작을 수행한다."""
        factor = max(0.4, min(2.5, float(weather_factor)))
        baseline = self.base_demand * self._peak_multiplier(hour) * factor
        noise = self._rng.uniform(-0.08, 0.08)
        return max(1, int(round(baseline * (1.0 + noise))))

    def congestion_index(self, demand: int, capacity: int = 200) -> float:
        """``congestion_index`` 동작을 수행한다."""
        cap = max(1, int(capacity))
        return min(1.0, max(0.0, float(demand) / float(cap)))

    def incident_probability(self, congestion: float) -> float:
        """``incident_probability`` 동작을 수행한다."""
        c = min(1.0, max(0.0, float(congestion)))
        return min(0.35, 0.01 + (c ** 2) * 0.28)

    def step(self, hour: int, weather_factor: float = 1.0, capacity: int = 200) -> TrafficState:
        """`대상` 실행 상태를 제어한다."""
        demand = self.demand_at(hour=hour, weather_factor=weather_factor)
        congestion = self.congestion_index(demand=demand, capacity=capacity)
        p_incident = self.incident_probability(congestion)
        state = TrafficState(
            hour=int(hour) % 24,
            demand=demand,
            congestion=congestion,
            incident_probability=p_incident,
        )
        self._states.append(state)
        return state

    def simulate_day(self, weather_factors: list[float] | None = None, capacity: int = 200) -> list[TrafficState]:
        """``simulate_day`` 동작을 수행한다."""
        factors = weather_factors or [1.0] * 24
        out: list[TrafficState] = []
        for hour in range(24):
            wf = factors[hour] if hour < len(factors) else 1.0
            out.append(self.step(hour=hour, weather_factor=wf, capacity=capacity))
        return out

    def summary(self) -> dict[str, Any]:
        """현재 상태 요약을 반환한다."""
        if not self._states:
            return {
                "states": 0,
                "avg_demand": 0,
                "avg_congestion": 0.0,
                "peak_hour": None,
            }
        avg_demand = sum(s.demand for s in self._states) / len(self._states)
        avg_cong = sum(s.congestion for s in self._states) / len(self._states)
        peak = max(self._states, key=lambda s: s.demand)
        return {
            "states": len(self._states),
            "avg_demand": round(avg_demand, 2),
            "avg_congestion": round(avg_cong, 4),
            "peak_hour": peak.hour,
        }
