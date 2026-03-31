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
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Event:
    seq: int
    event_type: str
    data: dict[str, Any]
    t: float = 0.0


class EventArchitecture:
    def __init__(self) -> None:
        self._events: list[Event] = []
        self._seq = 0
        self._handlers: dict[str, list] = {}

    def emit(self, event_type: str, data: dict[str, Any] | None = None, t: float = 0.0) -> Event:
        self._seq += 1
        event = Event(seq=self._seq, event_type=event_type, data=data or {}, t=t)
        self._events.append(event)
        for handler in self._handlers.get(event_type, []):
            try:
                handler(event)
            except (TypeError, ValueError, RuntimeError):
                pass
        return event

    def on(self, event_type: str, handler) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def replay(self, from_seq: int = 0) -> list[Event]:
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
        counts: dict[str, int] = {}
        for e in self._events:
            counts[e.event_type] = counts.get(e.event_type, 0) + 1
        return counts

    def summary(self) -> dict[str, Any]:
        return {
            "total_events": len(self._events),
            "event_types": len(self.events_by_type()),
            "handlers": sum(len(h) for h in self._handlers.values()),
        }
