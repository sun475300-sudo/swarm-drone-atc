"""
배터리 열화 모델
===============
사이클/온도 기반 용량 감소 + 교체 예측.

사용법:
    bd = BatteryDegradation()
    bd.register_battery("b1", initial_capacity=80.0)
    bd.record_cycle("b1", depth=0.8, temp_c=35)
    cap = bd.current_capacity("b1")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class BatteryState:
    """배터리 상태"""
    battery_id: str
    initial_capacity_wh: float
    current_capacity_wh: float
    total_cycles: int = 0
    total_depth: float = 0.0
    temp_history: list[float] = field(default_factory=list)
    soh: float = 100.0  # State of Health %


class BatteryDegradation:
    """배터리 열화 모델."""

    def __init__(self, cycle_degradation: float = 0.02, temp_factor: float = 0.001) -> None:
        self.cycle_degradation = cycle_degradation  # % per cycle
        self.temp_factor = temp_factor  # additional % per degree above 25C
        self._batteries: dict[str, BatteryState] = {}

    def register_battery(self, battery_id: str, initial_capacity: float = 80.0) -> None:
        self._batteries[battery_id] = BatteryState(
            battery_id=battery_id,
            initial_capacity_wh=initial_capacity,
            current_capacity_wh=initial_capacity,
        )

    def record_cycle(self, battery_id: str, depth: float = 0.8, temp_c: float = 25.0) -> None:
        b = self._batteries.get(battery_id)
        if not b:
            return
        b.total_cycles += 1
        b.total_depth += depth
        b.temp_history.append(temp_c)
        if len(b.temp_history) > 500:
            b.temp_history = b.temp_history[-500:]

        # 열화 계산
        base_deg = self.cycle_degradation * depth
        temp_deg = max(0, (temp_c - 25)) * self.temp_factor
        total_deg = base_deg + temp_deg

        b.soh = max(0, b.soh - total_deg)
        b.current_capacity_wh = b.initial_capacity_wh * (b.soh / 100)

    def current_capacity(self, battery_id: str) -> float:
        b = self._batteries.get(battery_id)
        return round(b.current_capacity_wh, 2) if b else 0

    def state_of_health(self, battery_id: str) -> float:
        b = self._batteries.get(battery_id)
        return round(b.soh, 1) if b else 0

    def remaining_cycles(self, battery_id: str, eol_soh: float = 80.0) -> int:
        b = self._batteries.get(battery_id)
        if not b or b.soh <= eol_soh:
            return 0
        avg_depth = b.total_depth / max(b.total_cycles, 1)
        avg_temp = float(np.mean(b.temp_history)) if b.temp_history else 25
        deg_per_cycle = self.cycle_degradation * avg_depth + max(0, avg_temp - 25) * self.temp_factor
        if deg_per_cycle <= 0:
            return 9999
        return int((b.soh - eol_soh) / deg_per_cycle)

    def needs_replacement(self, eol_soh: float = 80.0) -> list[str]:
        return [bid for bid, b in self._batteries.items() if b.soh <= eol_soh]

    def summary(self) -> dict[str, Any]:
        return {
            "batteries": len(self._batteries),
            "avg_soh": round(float(np.mean([b.soh for b in self._batteries.values()])), 1) if self._batteries else 100,
            "needs_replacement": len(self.needs_replacement()),
        }
