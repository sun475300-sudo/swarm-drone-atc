"""
디지털 트윈
==========
물리 드론 상태 미러링 + 예측 시뮬레이션.

사용법:
    dt = DigitalTwin()
    dt.register_twin("d1")
    dt.update_state("d1", pos=(100,200,50), battery=85, speed=12)
    pred = dt.predict("d1", t_ahead=60)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import numpy as np


@dataclass
class TwinState:
    drone_id: str
    position: tuple[float, float, float] = (0, 0, 0)
    velocity: tuple[float, float, float] = (0, 0, 0)
    battery_pct: float = 100
    speed_ms: float = 0
    heading_deg: float = 0
    t: float = 0
    history: list[dict] = field(default_factory=list)


class DigitalTwin:
    def __init__(self) -> None:
        self._twins: dict[str, TwinState] = {}

    def register_twin(self, drone_id: str) -> None:
        self._twins[drone_id] = TwinState(drone_id=drone_id)

    def update_state(self, drone_id: str, pos: tuple[float, float, float] | None = None, velocity: tuple[float, float, float] | None = None, battery: float | None = None, speed: float | None = None, heading: float | None = None, t: float = 0) -> None:
        tw = self._twins.get(drone_id)
        if not tw:
            return
        if pos:
            tw.position = pos
        if velocity:
            tw.velocity = velocity
        if battery is not None:
            tw.battery_pct = battery
        if speed is not None:
            tw.speed_ms = speed
        if heading is not None:
            tw.heading_deg = heading
        tw.t = t
        tw.history.append({"pos": tw.position, "battery": tw.battery_pct, "t": t})
        if len(tw.history) > 200:
            tw.history = tw.history[-200:]

    def predict(self, drone_id: str, t_ahead: float = 60) -> dict[str, Any]:
        tw = self._twins.get(drone_id)
        if not tw:
            return {}
        pred_pos = tuple(p + v * t_ahead for p, v in zip(tw.position, tw.velocity))
        battery_drain = tw.speed_ms * 0.01 * t_ahead  # simplified
        pred_battery = max(0, tw.battery_pct - battery_drain)
        return {
            "predicted_pos": tuple(round(p, 1) for p in pred_pos),
            "predicted_battery": round(pred_battery, 1),
            "t_ahead": t_ahead,
        }

    def divergence(self, drone_id: str, actual_pos: tuple[float, float, float]) -> float:
        tw = self._twins.get(drone_id)
        if not tw:
            return 0
        return round(float(np.sqrt(sum((a-b)**2 for a, b in zip(tw.position, actual_pos)))), 2)

    def summary(self) -> dict[str, Any]:
        return {
            "twins": len(self._twins),
            "avg_battery": round(float(np.mean([t.battery_pct for t in self._twins.values()])), 1) if self._twins else 0,
        }
