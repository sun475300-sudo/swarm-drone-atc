"""P695: RTL/Geofence 5단계 Failsafe 체인.

emergency_recovery_system.py의 일반 복구와 구별되는
하드웨어 연동 전용 Failsafe 체인.
- Level 1 (경고): 첫 번째 이상 감지, 로그·알림
- Level 2 (제한): 속도·고도 제한, 자동 귀환 대기
- Level 3 (RTL): Return-to-Launch 명령 발행
- Level 4 (Geofence): Geofence 경계 내 강제 착륙
- Level 5 (Emergency land): 즉시 착륙 (배터리 극단적 방전 등)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


_logger = logging.getLogger(__name__)


class FailsafeLevel(Enum):
    NOMINAL = 0
    WARNING = 1
    RESTRICTED = 2
    RTL = 3
    GEOFENCE_LAND = 4
    EMERGENCY_LAND = 5


class FailsafeTrigger(Enum):
    BATTERY_LOW = auto()
    BATTERY_CRITICAL = auto()
    GPS_LOSS = auto()
    COMM_LOSS = auto()
    GEOFENCE_BREACH = auto()
    MOTOR_DEGRADED = auto()
    SENSOR_FAILURE = auto()
    EXTERNAL_COMMAND = auto()


@dataclass
class FailsafeEvent:
    drone_id: str
    trigger: FailsafeTrigger
    level: FailsafeLevel
    timestamp: float = field(default_factory=time.monotonic)
    detail: str = ""


@dataclass
class DroneFailsafeState:
    drone_id: str
    level: FailsafeLevel = FailsafeLevel.NOMINAL
    active_triggers: set[FailsafeTrigger] = field(default_factory=set)
    events: list[FailsafeEvent] = field(default_factory=list)

    def add_trigger(self, trigger: FailsafeTrigger, new_level: FailsafeLevel, detail: str = "") -> FailsafeEvent:
        self.active_triggers.add(trigger)
        # 레벨은 단방향 상승 (더 위험한 상태로만 전환)
        if new_level.value > self.level.value:
            self.level = new_level
        evt = FailsafeEvent(self.drone_id, trigger, self.level, detail=detail)
        self.events.append(evt)
        return evt

    def clear_trigger(self, trigger: FailsafeTrigger) -> None:
        self.active_triggers.discard(trigger)
        if not self.active_triggers:
            self.level = FailsafeLevel.NOMINAL


# 트리거별 기본 Failsafe 레벨 매핑
TRIGGER_LEVEL_MAP: dict[FailsafeTrigger, FailsafeLevel] = {
    FailsafeTrigger.BATTERY_LOW: FailsafeLevel.WARNING,
    FailsafeTrigger.BATTERY_CRITICAL: FailsafeLevel.EMERGENCY_LAND,
    FailsafeTrigger.GPS_LOSS: FailsafeLevel.RTL,
    FailsafeTrigger.COMM_LOSS: FailsafeLevel.RTL,
    FailsafeTrigger.GEOFENCE_BREACH: FailsafeLevel.GEOFENCE_LAND,
    FailsafeTrigger.MOTOR_DEGRADED: FailsafeLevel.RESTRICTED,
    FailsafeTrigger.SENSOR_FAILURE: FailsafeLevel.WARNING,
    FailsafeTrigger.EXTERNAL_COMMAND: FailsafeLevel.EMERGENCY_LAND,
}


class FailsafeManager:
    """군집 전체의 Failsafe 상태 추적 및 체인 관리."""

    def __init__(self) -> None:
        self._states: dict[str, DroneFailsafeState] = {}
        self._callbacks: list[Any] = []

    def register_drone(self, drone_id: str) -> None:
        if drone_id not in self._states:
            self._states[drone_id] = DroneFailsafeState(drone_id)

    def trigger(self, drone_id: str, trigger: FailsafeTrigger, detail: str = "") -> FailsafeEvent:
        """Failsafe 트리거 발화."""
        if drone_id not in self._states:
            self.register_drone(drone_id)
        level = TRIGGER_LEVEL_MAP.get(trigger, FailsafeLevel.WARNING)
        state = self._states[drone_id]
        evt = state.add_trigger(trigger, level, detail)
        _logger.warning("Failsafe [%s] %s → Level %s: %s", drone_id, trigger.name, level.name, detail)
        for cb in self._callbacks:
            cb(evt)
        return evt

    def clear(self, drone_id: str, trigger: FailsafeTrigger) -> None:
        """트리거 해제 (조건 해소 후)."""
        if drone_id in self._states:
            self._states[drone_id].clear_trigger(trigger)

    def get_level(self, drone_id: str) -> FailsafeLevel:
        return self._states.get(drone_id, DroneFailsafeState("")).level

    def register_callback(self, fn: Any) -> None:
        """Failsafe 이벤트 발화 시 호출되는 콜백 등록."""
        self._callbacks.append(fn)

    def summary(self) -> dict[str, Any]:
        return {
            did: {"level": s.level.name, "triggers": [t.name for t in s.active_triggers]}
            for did, s in self._states.items()
        }

    def active_failsafes(self) -> list[str]:
        return [did for did, s in self._states.items() if s.level != FailsafeLevel.NOMINAL]
