"""
비상 프로토콜 관리자
====================
6종 비상 시나리오 정의 + 자동 대응 절차 + 우선순위 복구.
통신 두절, 엔진 고장, 침입자 등 비상 상황 체계적 관리.

사용법:
    em = EmergencyManager()
    em.declare_emergency("drone_1", EmergencyType.ENGINE_FAILURE, t=10.0)
    actions = em.get_response("drone_1")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class EmergencyType(IntEnum):
    COMM_LOSS = 1       # 통신 두절
    ENGINE_FAILURE = 2  # 엔진 고장
    BATTERY_CRITICAL = 3  # 배터리 위급
    GPS_FAILURE = 4     # GPS 장애
    INTRUDER = 5        # 침입자 탐지
    MIDAIR_COLLISION = 6  # 공중 충돌 임박


class EmergencyState(IntEnum):
    DECLARED = 1   # 선언됨
    RESPONDING = 2  # 대응 중
    CONTAINED = 3  # 억제됨
    RESOLVED = 4   # 해결됨
    ESCALATED = 5  # 상위 에스컬레이션


@dataclass
class ResponseAction:
    """대응 조치"""
    action_id: str
    description: str
    priority: int  # 1=최우선
    auto_execute: bool = True
    executed: bool = False
    result: str = ""


@dataclass
class Emergency:
    """비상 이벤트"""
    emergency_id: str
    drone_id: str
    emergency_type: EmergencyType
    state: EmergencyState = EmergencyState.DECLARED
    t_declared: float = 0.0
    t_resolved: float | None = None
    severity: int = 1  # 1~5
    actions: list[ResponseAction] = field(default_factory=list)
    affected_drones: list[str] = field(default_factory=list)
    description: str = ""


# 비상 유형별 표준 대응 절차
RESPONSE_PROTOCOLS: dict[EmergencyType, list[dict[str, Any]]] = {
    EmergencyType.COMM_LOSS: [
        {"id": "CL1", "desc": "마지막 알려진 위치에서 호버링", "priority": 1},
        {"id": "CL2", "desc": "자동 RTL (60초 후)", "priority": 2},
        {"id": "CL3", "desc": "주변 드론에 회피 경고", "priority": 1},
        {"id": "CL4", "desc": "중계 드론 배치", "priority": 3},
    ],
    EmergencyType.ENGINE_FAILURE: [
        {"id": "EF1", "desc": "즉시 오토로테이션/활공 모드", "priority": 1},
        {"id": "EF2", "desc": "비상 착륙 지점 탐색", "priority": 1},
        {"id": "EF3", "desc": "하방 공역 클리어", "priority": 2},
        {"id": "EF4", "desc": "지상 구조팀 알림", "priority": 2},
    ],
    EmergencyType.BATTERY_CRITICAL: [
        {"id": "BC1", "desc": "최단 경로 RTL", "priority": 1},
        {"id": "BC2", "desc": "불필요 시스템 셧다운", "priority": 1},
        {"id": "BC3", "desc": "저전력 비행 모드 전환", "priority": 2},
        {"id": "BC4", "desc": "가장 가까운 착륙 지점 탐색", "priority": 2},
    ],
    EmergencyType.GPS_FAILURE: [
        {"id": "GF1", "desc": "관성 항법 전환", "priority": 1},
        {"id": "GF2", "desc": "고도 유지 호버링", "priority": 1},
        {"id": "GF3", "desc": "시각 기반 위치 추정", "priority": 2},
        {"id": "GF4", "desc": "ATC 수동 유도 요청", "priority": 3},
    ],
    EmergencyType.INTRUDER: [
        {"id": "IN1", "desc": "침입자 추적 및 식별", "priority": 1},
        {"id": "IN2", "desc": "영향 구역 드론 대피", "priority": 1},
        {"id": "IN3", "desc": "안전 구역 설정 (200m 반경)", "priority": 2},
        {"id": "IN4", "desc": "관제 당국 통보", "priority": 2},
    ],
    EmergencyType.MIDAIR_COLLISION: [
        {"id": "MC1", "desc": "즉시 수직 분리 실행", "priority": 1},
        {"id": "MC2", "desc": "관련 드론 정지/호버링", "priority": 1},
        {"id": "MC3", "desc": "충돌 구역 공역 봉쇄", "priority": 1},
        {"id": "MC4", "desc": "대체 경로 계산 및 배포", "priority": 2},
        {"id": "MC5", "desc": "피해 평가 및 보고", "priority": 3},
    ],
}


class EmergencyManager:
    """
    비상 프로토콜 관리자.

    비상 선언 → 자동 대응 → 상태 추적 → 해결.
    """

    def __init__(self) -> None:
        self._emergencies: dict[str, Emergency] = {}
        self._counter = 0
        self._resolved_count = 0

    def declare_emergency(
        self,
        drone_id: str,
        emergency_type: EmergencyType,
        t: float = 0.0,
        severity: int = 3,
        affected_drones: list[str] | None = None,
        description: str = "",
    ) -> Emergency:
        """비상 선언"""
        self._counter += 1
        eid = f"EMG_{self._counter:04d}"

        # 표준 대응 절차 생성
        protocol = RESPONSE_PROTOCOLS.get(emergency_type, [])
        actions = [
            ResponseAction(
                action_id=p["id"],
                description=p["desc"],
                priority=p["priority"],
            )
            for p in protocol
        ]

        emergency = Emergency(
            emergency_id=eid,
            drone_id=drone_id,
            emergency_type=emergency_type,
            state=EmergencyState.DECLARED,
            t_declared=t,
            severity=severity,
            actions=actions,
            affected_drones=affected_drones or [drone_id],
            description=description or f"{emergency_type.name} - {drone_id}",
        )

        self._emergencies[eid] = emergency
        return emergency

    def respond(self, emergency_id: str) -> list[ResponseAction]:
        """비상 대응 시작 (자동 실행 가능 액션 실행)"""
        em = self._emergencies.get(emergency_id)
        if not em:
            return []

        em.state = EmergencyState.RESPONDING
        executed = []

        for action in sorted(em.actions, key=lambda a: a.priority):
            if action.auto_execute and not action.executed:
                action.executed = True
                action.result = "자동 실행 완료"
                executed.append(action)

        return executed

    def resolve(self, emergency_id: str, t: float = 0.0) -> bool:
        """비상 해결"""
        em = self._emergencies.get(emergency_id)
        if not em:
            return False

        em.state = EmergencyState.RESOLVED
        em.t_resolved = t
        self._resolved_count += 1
        return True

    def escalate(self, emergency_id: str) -> bool:
        """상위 에스컬레이션"""
        em = self._emergencies.get(emergency_id)
        if not em:
            return False

        em.state = EmergencyState.ESCALATED
        em.severity = min(5, em.severity + 1)
        return True

    def get_active(self) -> list[Emergency]:
        """활성 비상 목록"""
        return [
            e for e in self._emergencies.values()
            if e.state not in (EmergencyState.RESOLVED,)
        ]

    def get_by_drone(self, drone_id: str) -> list[Emergency]:
        """드론별 비상 목록"""
        return [
            e for e in self._emergencies.values()
            if drone_id in e.affected_drones
        ]

    def get_response(self, drone_id: str) -> list[ResponseAction]:
        """드론에 대한 모든 대응 조치"""
        actions = []
        for em in self.get_by_drone(drone_id):
            if em.state != EmergencyState.RESOLVED:
                actions.extend(em.actions)
        return sorted(actions, key=lambda a: a.priority)

    def is_affected(self, drone_id: str) -> bool:
        """드론이 비상 영향 받는지"""
        return any(
            drone_id in e.affected_drones
            for e in self.get_active()
        )

    @property
    def active_count(self) -> int:
        return len(self.get_active())

    def response_time(self, emergency_id: str) -> float:
        """대응 시간 (초)"""
        em = self._emergencies.get(emergency_id)
        if not em or em.t_resolved is None:
            return -1.0
        return em.t_resolved - em.t_declared

    def avg_response_time(self) -> float:
        """평균 대응 시간"""
        times = [
            self.response_time(eid)
            for eid in self._emergencies
            if self.response_time(eid) > 0
        ]
        return sum(times) / len(times) if times else 0.0

    def summary(self) -> dict[str, Any]:
        by_type: dict[str, int] = {}
        for e in self._emergencies.values():
            name = e.emergency_type.name
            by_type[name] = by_type.get(name, 0) + 1

        by_state: dict[str, int] = {}
        for e in self._emergencies.values():
            name = e.state.name
            by_state[name] = by_state.get(name, 0) + 1

        return {
            "total_emergencies": len(self._emergencies),
            "active": self.active_count,
            "resolved": self._resolved_count,
            "avg_response_time_s": round(self.avg_response_time(), 2),
            "by_type": by_type,
            "by_state": by_state,
        }

    def clear(self) -> None:
        self._emergencies.clear()
        self._counter = 0
        self._resolved_count = 0
