"""
실시간 이벤트 버스
==================
Pub/Sub 이벤트 브로커 + 필터 + 이력.

사용법:
    bus = EventBus()
    bus.subscribe("COLLISION", handler)
    bus.publish("COLLISION", {"drones": ["d1", "d2"]})
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Event:
    """이벤트"""
    event_type: str
    data: dict[str, Any]
    t: float = 0.0
    source: str = ""
    priority: int = 3  # 1=highest


EventHandler = Callable[[Event], None]


class EventBus:
    """Pub/Sub 이벤트 브로커."""

    def __init__(self, max_history: int = 500) -> None:
        self._subscribers: dict[str, list[EventHandler]] = {}
        self._global_subscribers: list[EventHandler] = []
        self._history: list[Event] = []
        self._max_history = max_history
        self._published = 0
        self._delivered = 0

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def subscribe_all(self, handler: EventHandler) -> None:
        self._global_subscribers.append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> bool:
        subs = self._subscribers.get(event_type, [])
        if handler in subs:
            subs.remove(handler)
            return True
        return False

    def publish(
        self,
        event_type: str,
        data: dict[str, Any] | None = None,
        t: float = 0.0,
        source: str = "",
        priority: int = 3,
    ) -> int:
        """이벤트 발행, 배달된 수 반환"""
        event = Event(
            event_type=event_type,
            data=data or {},
            t=t,
            source=source,
            priority=priority,
        )

        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        self._published += 1
        delivered = 0

        for handler in self._subscribers.get(event_type, []):
            handler(event)
            delivered += 1

        for handler in self._global_subscribers:
            handler(event)
            delivered += 1

        self._delivered += delivered
        return delivered

    def query(
        self,
        event_type: str | None = None,
        source: str | None = None,
        t_start: float | None = None,
        t_end: float | None = None,
        limit: int = 50,
    ) -> list[Event]:
        """이력 조회"""
        result = self._history
        if event_type:
            result = [e for e in result if e.event_type == event_type]
        if source:
            result = [e for e in result if e.source == source]
        if t_start is not None:
            result = [e for e in result if e.t >= t_start]
        if t_end is not None:
            result = [e for e in result if e.t <= t_end]
        return result[-limit:]

    def event_types(self) -> list[str]:
        """발행된 이벤트 타입 목록"""
        return list(set(e.event_type for e in self._history))

    def clear_history(self) -> None:
        self._history.clear()

    def summary(self) -> dict[str, Any]:
        type_counts: dict[str, int] = {}
        for e in self._history:
            type_counts[e.event_type] = type_counts.get(e.event_type, 0) + 1
        return {
            "published": self._published,
            "delivered": self._delivered,
            "history_size": len(self._history),
            "subscriber_count": sum(len(s) for s in self._subscribers.values()),
            "event_types": type_counts,
        }
