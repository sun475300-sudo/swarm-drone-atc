"""
이벤트 타임라인 + 사고 조사 도구
=================================
모든 이벤트(충돌, 경고, 어드바이저리, 장애)를 시계열 저장하고
사후 조사를 위한 쿼리 인터페이스 제공.

사용법:
    timeline = EventTimeline()
    timeline.add("COLLISION", t=42.3, drone_ids=["DR001", "DR002"], ...)
    events = timeline.query(t_start=40, t_end=45, event_type="COLLISION")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class TimelineEvent:
    """타임라인 이벤트"""
    event_type: str       # COLLISION, NEAR_MISS, ADVISORY, FAILURE, HANDOFF, etc.
    t: float              # 이벤트 발생 시각 (s)
    drone_ids: list[str]  # 관련 드론 ID
    severity: str = "INFO"  # INFO, WARNING, CRITICAL
    details: dict[str, Any] = field(default_factory=dict)
    message: str = ""


class EventTimeline:
    """
    이벤트 시계열 저장 및 조사 도구.

    모든 이벤트를 시간순 저장하고
    다양한 필터로 조회할 수 있다.
    """

    def __init__(self) -> None:
        self._events: list[TimelineEvent] = []
        self._by_type: dict[str, list[TimelineEvent]] = {}
        self._by_drone: dict[str, list[TimelineEvent]] = {}

    def add(
        self,
        event_type: str,
        t: float,
        drone_ids: list[str] | None = None,
        severity: str = "INFO",
        details: dict[str, Any] | None = None,
        message: str = "",
    ) -> TimelineEvent:
        """이벤트 추가"""
        drone_ids = drone_ids or []
        details = details or {}

        event = TimelineEvent(
            event_type=event_type,
            t=t,
            drone_ids=list(drone_ids),
            severity=severity,
            details=details,
            message=message,
        )

        self._events.append(event)

        # 타입별 인덱스
        if event_type not in self._by_type:
            self._by_type[event_type] = []
        self._by_type[event_type].append(event)

        # 드론별 인덱스
        for did in drone_ids:
            if did not in self._by_drone:
                self._by_drone[did] = []
            self._by_drone[did].append(event)

        return event

    def query(
        self,
        t_start: float | None = None,
        t_end: float | None = None,
        event_type: str | None = None,
        drone_id: str | None = None,
        severity: str | None = None,
    ) -> list[TimelineEvent]:
        """
        조건 기반 이벤트 조회.

        모든 조건은 AND로 결합.
        """
        results = self._events

        if event_type is not None:
            results = [e for e in results if e.event_type == event_type]

        if drone_id is not None:
            results = [e for e in results if drone_id in e.drone_ids]

        if severity is not None:
            results = [e for e in results if e.severity == severity]

        if t_start is not None:
            results = [e for e in results if e.t >= t_start]

        if t_end is not None:
            results = [e for e in results if e.t <= t_end]

        return results

    def drone_history(self, drone_id: str) -> list[TimelineEvent]:
        """특정 드론의 이벤트 이력"""
        return list(self._by_drone.get(drone_id, []))

    def event_types(self) -> list[str]:
        """기록된 이벤트 타입 목록"""
        return sorted(self._by_type.keys())

    def count_by_type(self) -> dict[str, int]:
        """타입별 이벤트 수"""
        return {k: len(v) for k, v in self._by_type.items()}

    def total_events(self) -> int:
        """전체 이벤트 수"""
        return len(self._events)

    def time_range(self) -> tuple[float, float] | None:
        """기록된 시간 범위"""
        if not self._events:
            return None
        return (self._events[0].t, self._events[-1].t)

    def critical_events(self) -> list[TimelineEvent]:
        """CRITICAL 이벤트만 반환"""
        return [e for e in self._events if e.severity == "CRITICAL"]

    def summary(self) -> dict[str, Any]:
        """이벤트 요약"""
        return {
            "total_events": len(self._events),
            "event_types": self.count_by_type(),
            "critical_count": len(self.critical_events()),
            "time_range": self.time_range(),
            "drones_involved": sorted(self._by_drone.keys()),
        }

    def clear(self) -> None:
        """이력 초기화"""
        self._events.clear()
        self._by_type.clear()
        self._by_drone.clear()
