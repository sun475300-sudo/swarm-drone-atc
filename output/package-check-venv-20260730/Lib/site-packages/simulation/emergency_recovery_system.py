"""Phase 284: Emergency Recovery System — 비상 복구 시스템.

드론 장애 감지, 자동 복구 시퀀스, 안전 착륙 유도,
군집 재편성 및 미션 재할당을 수행합니다.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

_logger = logging.getLogger(__name__)


class EmergencyType(Enum):
    """``EmergencyType`` 관련 기능을 제공한다."""
    MOTOR_FAILURE = "motor_failure"
    BATTERY_CRITICAL = "battery_critical"
    GPS_LOSS = "gps_loss"
    COMM_LOSS = "comm_loss"
    COLLISION_IMMINENT = "collision_imminent"
    GEOFENCE_BREACH = "geofence_breach"
    SENSOR_MALFUNCTION = "sensor_malfunction"
    WEATHER_EXTREME = "weather_extreme"


class RecoveryAction(Enum):
    """``RecoveryAction`` 관련 기능을 제공한다."""
    EMERGENCY_LAND = "emergency_land"
    RETURN_TO_BASE = "return_to_base"
    HOVER_IN_PLACE = "hover_in_place"
    ALTITUDE_CHANGE = "altitude_change"
    SPEED_REDUCTION = "speed_reduction"
    MISSION_ABORT = "mission_abort"
    FAILSAFE_DESCEND = "failsafe_descend"
    PARACHUTE_DEPLOY = "parachute_deploy"


class RecoveryStatus(Enum):
    """``RecoveryStatus`` 관련 기능을 제공한다."""
    DETECTED = "detected"
    RESPONDING = "responding"
    EXECUTING = "executing"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


@dataclass
class EmergencyEvent:
    """``EmergencyEvent`` 데이터를 표현한다."""
    event_id: str
    drone_id: str
    etype: EmergencyType
    severity: float  # 0-1
    position: np.ndarray
    timestamp: float = 0.0
    status: RecoveryStatus = RecoveryStatus.DETECTED
    actions_taken: list[RecoveryAction] = field(default_factory=list)
    resolved: bool = False


@dataclass
class RecoveryPlan:
    """``RecoveryPlan`` 관련 기능을 제공한다."""
    event_id: str
    actions: list[RecoveryAction]
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
        """`plan` 결과를 생성한다."""
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
        """인스턴스를 초기화한다."""
        self._rng = np.random.default_rng(rng_seed)
        self._events: dict[str, EmergencyEvent] = {}
        self._plans: dict[str, RecoveryPlan] = {}
        self._callbacks: list[Callable] = []
        self._resolved_count = 0
        self._escalated_count = 0
        self._event_counter = 0

    def register_callback(self, cb: Callable):
        """`callback` 항목을 추가한다."""
        self._callbacks.append(cb)

    def detect_emergency(
        self, drone_id: str, etype: EmergencyType, severity: float,
        position: np.ndarray, timestamp: float = 0.0,
    ) -> EmergencyEvent:
        """`emergency` 결과를 계산하거나 판정한다."""
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
        """``execute_recovery`` 동작을 수행한다."""
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
        """``resolve_event`` 동작을 수행한다."""
        event = self._events.get(event_id)
        if not event:
            return False
        event.status = RecoveryStatus.RESOLVED
        event.resolved = True
        self._resolved_count += 1
        return True

    def get_active_emergencies(self) -> list[EmergencyEvent]:
        """`active emergencies` 정보를 조회한다."""
        return [e for e in self._events.values() if not e.resolved]

    def get_event(self, event_id: str) -> EmergencyEvent | None:
        """`event` 정보를 조회한다."""
        return self._events.get(event_id)

    def get_plan(self, event_id: str) -> RecoveryPlan | None:
        """`plan` 정보를 조회한다."""
        return self._plans.get(event_id)

    def get_drone_emergencies(self, drone_id: str) -> list[EmergencyEvent]:
        """`drone emergencies` 정보를 조회한다."""
        return [e for e in self._events.values() if e.drone_id == drone_id]

    def summary(self) -> dict:
        """현재 상태 요약을 반환한다."""
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
