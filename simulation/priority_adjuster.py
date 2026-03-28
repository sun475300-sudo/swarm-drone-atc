"""
동적 우선순위 재조정
===================
상황 인지 기반 실시간 임무 우선순위 변경.

사용법:
    pa = PriorityAdjuster()
    pa.register_mission("m1", base_priority=5)
    pa.update_context("m1", battery_pct=15, distance_to_goal=100)
    new_priority = pa.adjusted_priority("m1")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MissionContext:
    """임무 컨텍스트"""
    mission_id: str
    base_priority: int = 5  # 1(low) ~ 10(high)
    battery_pct: float = 100.0
    distance_to_goal: float = 0.0
    time_remaining_s: float = 3600.0
    is_emergency: bool = False
    payload_value: float = 1.0
    weather_risk: float = 0.0
    adjusted: int = 5
    adjustment_count: int = 0


class PriorityAdjuster:
    """동적 우선순위 재조정."""

    WEIGHTS = {
        "battery": 2.0,
        "time_pressure": 1.5,
        "emergency": 3.0,
        "payload": 1.0,
        "weather": 1.0,
    }

    def __init__(self) -> None:
        self._missions: dict[str, MissionContext] = {}
        self._history: list[dict[str, Any]] = []

    def register_mission(
        self, mission_id: str, base_priority: int = 5,
        payload_value: float = 1.0,
    ) -> None:
        self._missions[mission_id] = MissionContext(
            mission_id=mission_id,
            base_priority=base_priority,
            payload_value=payload_value,
            adjusted=base_priority,
        )

    def update_context(
        self, mission_id: str,
        battery_pct: float | None = None,
        distance_to_goal: float | None = None,
        time_remaining_s: float | None = None,
        is_emergency: bool | None = None,
        weather_risk: float | None = None,
    ) -> None:
        m = self._missions.get(mission_id)
        if not m:
            return
        if battery_pct is not None:
            m.battery_pct = battery_pct
        if distance_to_goal is not None:
            m.distance_to_goal = distance_to_goal
        if time_remaining_s is not None:
            m.time_remaining_s = time_remaining_s
        if is_emergency is not None:
            m.is_emergency = is_emergency
        if weather_risk is not None:
            m.weather_risk = weather_risk

    def adjusted_priority(self, mission_id: str) -> int:
        m = self._missions.get(mission_id)
        if not m:
            return 5

        boost = 0.0

        # 배터리 낮음 → 우선순위 증가
        if m.battery_pct < 20:
            boost += self.WEIGHTS["battery"] * (1 - m.battery_pct / 20)

        # 시간 촉박
        if m.time_remaining_s < 300:
            boost += self.WEIGHTS["time_pressure"] * (1 - m.time_remaining_s / 300)

        # 비상
        if m.is_emergency:
            boost += self.WEIGHTS["emergency"]

        # 화물 가치
        if m.payload_value > 5:
            boost += self.WEIGHTS["payload"] * min(1, m.payload_value / 10)

        # 기상 위험
        if m.weather_risk > 0.5:
            boost += self.WEIGHTS["weather"] * m.weather_risk

        old = m.adjusted
        m.adjusted = min(10, max(1, int(m.base_priority + boost)))

        if m.adjusted != old:
            m.adjustment_count += 1
            self._history.append({
                "mission_id": mission_id,
                "old": old,
                "new": m.adjusted,
                "reason": self._reason(m),
            })

        return m.adjusted

    def _reason(self, m: MissionContext) -> str:
        reasons = []
        if m.battery_pct < 20:
            reasons.append(f"배터리 {m.battery_pct:.0f}%")
        if m.is_emergency:
            reasons.append("비상")
        if m.time_remaining_s < 300:
            reasons.append("시간 촉박")
        return ", ".join(reasons) if reasons else "컨텍스트 변경"

    def ranking(self) -> list[tuple[str, int]]:
        """우선순위 순 정렬"""
        items = [(mid, self.adjusted_priority(mid)) for mid in self._missions]
        items.sort(key=lambda x: -x[1])
        return items

    def emergency_missions(self) -> list[str]:
        return [mid for mid, m in self._missions.items() if m.is_emergency]

    def adjustment_history(self, n: int = 20) -> list[dict[str, Any]]:
        return self._history[-n:]

    def summary(self) -> dict[str, Any]:
        return {
            "missions": len(self._missions),
            "adjustments": len(self._history),
            "emergencies": len(self.emergency_missions()),
        }
