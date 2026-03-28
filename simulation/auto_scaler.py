"""
자동 스케일링
=============
드론 수 동적 조절 + 수요 예측 + 스케일 정책.

사용법:
    scaler = AutoScaler(min_drones=10, max_drones=200)
    scaler.update_demand(current_demand=50, t=10.0)
    action = scaler.evaluate()
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np


class ScaleAction(Enum):
    NONE = "NONE"
    SCALE_UP = "SCALE_UP"
    SCALE_DOWN = "SCALE_DOWN"


@dataclass
class ScaleDecision:
    """스케일링 결정"""
    action: ScaleAction
    current_count: int
    target_count: int
    reason: str
    demand: float
    utilization: float


class AutoScaler:
    """드론 수 동적 조절."""

    def __init__(
        self,
        min_drones: int = 10,
        max_drones: int = 200,
        scale_up_threshold: float = 0.8,
        scale_down_threshold: float = 0.3,
        cooldown_s: float = 30.0,
    ) -> None:
        self.min_drones = min_drones
        self.max_drones = max_drones
        self.scale_up_threshold = scale_up_threshold
        self.scale_down_threshold = scale_down_threshold
        self.cooldown_s = cooldown_s

        self._current_count = min_drones
        self._demand_history: list[tuple[float, float]] = []  # (t, demand)
        self._last_scale_t = -float("inf")
        self._decisions: list[ScaleDecision] = []

    def update_demand(self, current_demand: float, t: float) -> None:
        self._demand_history.append((t, current_demand))
        if len(self._demand_history) > 500:
            self._demand_history = self._demand_history[-500:]

    def set_count(self, count: int) -> None:
        self._current_count = max(self.min_drones, min(count, self.max_drones))

    def utilization(self) -> float:
        if self._current_count == 0:
            return 0.0
        if not self._demand_history:
            return 0.0
        latest_demand = self._demand_history[-1][1]
        return latest_demand / self._current_count

    def predict_demand(self, horizon_s: float = 60.0) -> float:
        """선형 트렌드 기반 수요 예측"""
        if len(self._demand_history) < 3:
            return self._demand_history[-1][1] if self._demand_history else 0.0

        recent = self._demand_history[-min(20, len(self._demand_history)):]
        times = np.array([t for t, _ in recent])
        demands = np.array([d for _, d in recent])

        if times[-1] - times[0] < 1e-6:
            return float(demands[-1])

        slope = np.polyfit(times, demands, 1)[0]
        return max(0, float(demands[-1] + slope * horizon_s))

    def evaluate(self, t: float = 0.0) -> ScaleDecision:
        """스케일링 평가"""
        util = self.utilization()
        predicted = self.predict_demand()

        # 쿨다운 체크
        if t - self._last_scale_t < self.cooldown_s:
            decision = ScaleDecision(
                action=ScaleAction.NONE,
                current_count=self._current_count,
                target_count=self._current_count,
                reason="쿨다운 대기 중",
                demand=predicted,
                utilization=util,
            )
            self._decisions.append(decision)
            return decision

        target = self._current_count

        if util >= self.scale_up_threshold:
            # 수요의 1.3배로 스케일 업
            target = min(self.max_drones, int(predicted * 1.3))
            target = max(target, self._current_count + 5)
            action = ScaleAction.SCALE_UP
            reason = f"사용률 {util:.0%} ≥ {self.scale_up_threshold:.0%}"
        elif util <= self.scale_down_threshold and self._current_count > self.min_drones:
            target = max(self.min_drones, int(predicted * 1.1))
            target = min(target, self._current_count - 3)
            action = ScaleAction.SCALE_DOWN
            reason = f"사용률 {util:.0%} ≤ {self.scale_down_threshold:.0%}"
        else:
            action = ScaleAction.NONE
            reason = "적정 범위"

        target = max(self.min_drones, min(target, self.max_drones))

        if action != ScaleAction.NONE:
            self._last_scale_t = t
            self._current_count = target

        decision = ScaleDecision(
            action=action,
            current_count=self._current_count,
            target_count=target,
            reason=reason,
            demand=predicted,
            utilization=util,
        )
        self._decisions.append(decision)
        return decision

    @property
    def current_count(self) -> int:
        return self._current_count

    def summary(self) -> dict[str, Any]:
        return {
            "current_count": self._current_count,
            "utilization": round(self.utilization(), 3),
            "total_decisions": len(self._decisions),
            "scale_ups": sum(1 for d in self._decisions if d.action == ScaleAction.SCALE_UP),
            "scale_downs": sum(1 for d in self._decisions if d.action == ScaleAction.SCALE_DOWN),
        }
