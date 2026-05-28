"""
이벤트 기반 아키텍처
===================
CQRS 패턴 + 이벤트 소싱 + 상태 복원.

사용법:
    ea = EventArchitecture()
    ea.emit("DroneCreated", {"drone_id": "d1", "type": "DELIVERY"})
    state = ea.replay()
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

_logger = logging.getLogger(__name__)


@dataclass
class Event:
    """``Event`` 데이터를 표현한다."""
    seq: int
    event_type: str
    data: dict[str, Any]
    t: float = 0.0


class EventArchitecture:
    """``EventArchitecture`` 관련 기능을 제공한다."""
    def __init__(self) -> None:
        """인스턴스를 초기화한다."""
        self._events: list[Event] = []
        self._seq = 0
        self._handlers: dict[str, list] = {}

    def emit(self, event_type: str, data: dict[str, Any] | None = None, t: float = 0.0) -> Event:
        """``emit`` 동작을 수행한다."""
        self._seq += 1
        event = Event(seq=self._seq, event_type=event_type, data=data or {}, t=t)
        self._events.append(event)
        for handler in self._handlers.get(event_type, []):
            try:
                handler(event)
            except Exception as exc:
                # Subscriber 실패가 emit 전체를 막으면 안 됨(이벤트 fan-out 보장).
                # 다만 silent swallow 는 디버깅을 어렵게 하므로 WARN 로그.
                _logger.warning(
                    "event handler failed for %s seq=%d: %s",
                    event_type, event.seq, exc, exc_info=True,
                )
        return event

    def on(self, event_type: str, handler) -> None:
        """``on`` 동작을 수행한다."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def replay(self, from_seq: int = 0) -> list[Event]:
        """``replay`` 동작을 수행한다."""
        return [e for e in self._events if e.seq >= from_seq]

    def snapshot(self) -> dict[str, Any]:
        """현재 상태 스냅샷"""
        state: dict[str, Any] = {"drones": {}, "events_count": len(self._events)}
        for e in self._events:
            if "drone_id" in e.data:
                did = e.data["drone_id"]
                if did not in state["drones"]:
                    state["drones"][did] = {}
                state["drones"][did]["last_event"] = e.event_type
                state["drones"][did].update(e.data)
        return state

    def events_by_type(self) -> dict[str, int]:
        """``events_by_type`` 동작을 수행한다."""
        counts: dict[str, int] = {}
        for e in self._events:
            counts[e.event_type] = counts.get(e.event_type, 0) + 1
        return counts

    def summary(self) -> dict[str, Any]:
        """현재 상태 요약을 반환한다."""
        return {
            "total_events": len(self._events),
            "event_types": len(self.events_by_type()),
            "handlers": sum(len(h) for h in self._handlers.values()),
        }
