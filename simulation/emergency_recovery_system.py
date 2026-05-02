"""Phase 284: Emergency Recovery System — 비상 복구 시스템.

드론 장애 감지, 자동 복구 시퀀스, 안전 착륙 유도,
군집 재편성 및 미션 재할당을 수행합니다.
"""

from __future__ import annotations

import logging
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Callable

_logger = logging.getLogger(__name__)


class EmergencyType(Enum):
    MOTOR_FAILURE = "motor_failure"
    BATTERY_CRITICAL = "battery_critical"
    GPS_LOSS = "gps_loss"
    COMM_LOSS = "comm_loss"
    COLLISION_IMMINENT = "collision_imminent"
    GEOFENCE_BREACH = "geofence_breach"
    SENSOR_MALFUNCTION = "sensor_malfunction"
    WEATHER_EXTREME = "weather_extreme"


class RecoveryAction(Enum):
    EMERGENCY_LAND = "emergency_land"
    RETURN_TO_BASE = "return_to_base"
    HOVER_IN_PLACE = "hover_in_place"
    ALTITUDE_CHANGE = "altitude_change"
    SPEED_REDUCTION = "speed_reduction"
    MISSION_ABORT = "mission_abort"
    FAILSAFE_DESCEND = "failsafe_descend"
    PARACHUTE_DEPLOY = "parachute_deploy"


class RecoveryStatus(Enum):
    DETECTED = "detected"
    RESPONDING = "responding"
    EXECUTING = "executing"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


@dataclass
class EmergencyEvent:
    event_id: str
    drone_id: str
    etype: EmergencyType
    severity: float  # 0-1
    position: np.ndarray
    timestamp: float = 0.0
    status: RecoveryStatus = RecoveryStatus.DETECTED
    actions_taken: List[RecoveryAction] = field(default_factory=list)
    resolved: bool = False


@dataclass
class RecoveryPlan:
    event_id: str
    actions: List[RecoveryAction]
    priority: int = 0
    estimated_time_sec: float = 0.0
    success_probability: float = 0.8


class RecoveryPlanner:
    """비상 상황별 복구 계획 생성기."""

    RECOVERY_MATRIX = {
        EmergencyType.MOTOR_FAILURE: [RecoveryAction.EMERGENCY_LAND, RecoveryAction.PARACHUTE_DEPLOY],
        EmergencyType.BATTERY_CRITICAL: [RecoveryAction.RETURN_TO_BASE, RecoveryAction.EMERGENCY_LAND],
        EmergencyType.GPS_LOSS: [RecoveryAction.HOVER_IN_PLACE, RecoveryAction.FAILSAFE_DESCEND],
        EmergencyType.COMM_LOSS: [RecoveryAction.RETURN_TO_BASE, RecoveryAction.HOVER_IN_PLACE],
        EmergencyType.COLLISION_IMMINENT: [RecoveryAction.ALTITUDE_CHANGE, RecoveryAction.SPEED_REDUCTION],
        EmergencyType.GEOFENCE_BREACH: [RecoveryAction.RETURN_TO_BASE, RecoveryAction.MISSION_ABORT],
        EmergencyType.SENSOR_MALFUNCTION: [RecoveryAction.HOVER_IN_PLACE, RecoveryAction.RETURN_TO_BASE],
        EmergencyType.WEATHER_EXTREME: [RecoveryAction.EMERGENCY_LAND, RecoveryAction.ALTITUDE_CHANGE],
    }

    @staticmethod
    def create_plan(event: EmergencyEvent) -> RecoveryPlan:
        actions = RecoveryPlanner.RECOVERY_MATRIX.get(event.etype, [RecoveryAction.HOVER_IN_PLACE])
        priority = int(event.severity * 10)
        est_time = 30.0 if event.severity < 0.5 else 60.0
        prob = max(0.3, 1.0 - event.severity * 0.5)
        return RecoveryPlan(
            event_id=event.event_id, actions=actions, priority=priority,
            estimated_time_sec=est_time, success_probability=prob,
        )


class EmergencyRecoverySystem:
    """비상 복구 시스템.

    - 비상 상황 감지 및 분류
    - 자동 복구 계획 생성
    - 복구 시퀀스 실행 추적
    - 군집 재편성 트리거
    """

    def __init__(self, rng_seed: int = 42):
        self._rng = np.random.default_rng(rng_seed)
        self._events: Dict[str, EmergencyEvent] = {}
        self._plans: Dict[str, RecoveryPlan] = {}
        self._callbacks: List[Callable] = []
        self._resolved_count = 0
        self._escalated_count = 0
        self._event_counter = 0

    def register_callback(self, cb: Callable):
        self._callbacks.append(cb)

    def detect_emergency(
        self, drone_id: str, etype: EmergencyType, severity: float,
        position: np.ndarray, timestamp: float = 0.0,
    ) -> EmergencyEvent:
        self._event_counter += 1
        eid = f"EMG-{self._event_counter:04d}"
        event = EmergencyEvent(
            event_id=eid, drone_id=drone_id, etype=etype,
            severity=min(1.0, max(0.0, severity)), position=position, timestamp=timestamp,
        )
        self._events[eid] = event
        plan = RecoveryPlanner.create_plan(event)
        self._plans[eid] = plan
        for cb in self._callbacks:
            try:
                cb(event, plan)
            except Exception as exc:
                # Callback 실패가 비상 복구 흐름을 막지 않도록 swallow 유지하되,
                # silent 는 디버깅을 어렵게 하므로 WARN 로그.
                _logger.warning(
                    "emergency callback failed for event %s: %s",
                    event.event_id, exc, exc_info=True,
                )
        return event

    def execute_recovery(self, event_id: str) -> bool:
        event = self._events.get(event_id)
        plan = self._plans.get(event_id)
        if not event or not plan:
            return False
        event.status = RecoveryStatus.EXECUTING
        event.actions_taken = plan.actions.copy()
        success = self._rng.random() < plan.success_probability
        if success:
            event.status = RecoveryStatus.RESOLVED
            event.resolved = True
            self._resolved_count += 1
        else:
            event.status = RecoveryStatus.ESCALATED
            self._escalated_count += 1
        return success

    def resolve_event(self, event_id: str) -> bool:
        event = self._events.get(event_id)
        if not event:
            return False
        event.status = RecoveryStatus.RESOLVED
        event.resolved = True
        self._resolved_count += 1
        return True

    def get_active_emergencies(self) -> List[EmergencyEvent]:
        return [e for e in self._events.values() if not e.resolved]

    def get_event(self, event_id: str) -> Optional[EmergencyEvent]:
        return self._events.get(event_id)

    def get_plan(self, event_id: str) -> Optional[RecoveryPlan]:
        return self._plans.get(event_id)

    def get_drone_emergencies(self, drone_id: str) -> List[EmergencyEvent]:
        return [e for e in self._events.values() if e.drone_id == drone_id]

    def summary(self) -> dict:
        active = sum(1 for e in self._events.values() if not e.resolved)
        by_type = {}
        for e in self._events.values():
            by_type[e.etype.value] = by_type.get(e.etype.value, 0) + 1
        return {
            "total_events": len(self._events),
            "active_emergencies": active,
            "resolved": self._resolved_count,
            "escalated": self._escalated_count,
            "by_type": by_type,
        }
