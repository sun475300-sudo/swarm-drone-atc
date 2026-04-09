"""Simulation recorder for Phase 172.

Records timeline events and supports replay/export for scenario audits.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SimEvent:
    t_sec: float
    event_type: str
    payload: dict[str, Any]


class SimRecorder:
    def __init__(self) -> None:
        self._events: list[SimEvent] = []

    def record(self, t_sec: float, event_type: str, **payload: Any) -> None:
        self._events.append(
            SimEvent(
                t_sec=max(0.0, float(t_sec)),
                event_type=str(event_type),
                payload=dict(payload),
            )
        )

    def events(self) -> list[SimEvent]:
        return list(self._events)

    def replay(self, start_sec: float = 0.0, end_sec: float | None = None) -> list[SimEvent]:
        s = max(0.0, float(start_sec))
        e = None if end_sec is None else float(end_sec)
        return [ev for ev in self._events if ev.t_sec >= s and (e is None or ev.t_sec <= e)]

    def export(self) -> list[dict[str, Any]]:
        return [
            {"t_sec": ev.t_sec, "event_type": ev.event_type, "payload": ev.payload}
            for ev in self._events
        ]

    def import_events(self, rows: list[dict[str, Any]]) -> None:
        self._events = [
            SimEvent(
                t_sec=float(row.get("t_sec", 0.0)),
                event_type=str(row.get("event_type", "UNKNOWN")),
                payload=dict(row.get("payload", {})),
            )
            for row in rows
        ]

    def summary(self) -> dict[str, Any]:
        by_type: dict[str, int] = {}
        for ev in self._events:
            by_type[ev.event_type] = by_type.get(ev.event_type, 0) + 1
        duration = 0.0 if not self._events else max(ev.t_sec for ev in self._events)
        return {
            "events": len(self._events),
            "duration_sec": round(duration, 3),
            "by_type": by_type,
        }

    def clear(self) -> None:
        self._events.clear()
