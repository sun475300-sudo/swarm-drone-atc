"""Simulation recorder for Phase 172.

Records timeline events and supports replay/export for scenario audits.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SimEvent:
    """``SimEvent`` 데이터를 표현한다."""
    t_sec: float
    event_type: str
    payload: dict[str, Any]


class SimRecorder:
    """``SimRecorder`` 관련 기능을 제공한다."""
    def __init__(self) -> None:
        """인스턴스를 초기화한다."""
        self._events: list[SimEvent] = []

    def record(self, t_sec: float, event_type: str, **payload: Any) -> None:
        """`대상` 정보를 기록한다."""
        self._events.append(
            SimEvent(
                t_sec=max(0.0, float(t_sec)),
                event_type=str(event_type),
                payload=dict(payload),
            )
        )

    def events(self) -> list[SimEvent]:
        """``events`` 동작을 수행한다."""
        return list(self._events)

    def replay(self, start_sec: float = 0.0, end_sec: float | None = None) -> list[SimEvent]:
        """``replay`` 동작을 수행한다."""
        s = max(0.0, float(start_sec))
        e = None if end_sec is None else float(end_sec)
        return [ev for ev in self._events if ev.t_sec >= s and (e is None or ev.t_sec <= e)]

    def export(self) -> list[dict[str, Any]]:
        """`대상` 결과를 저장한다."""
        return [
            {"t_sec": ev.t_sec, "event_type": ev.event_type, "payload": ev.payload}
            for ev in self._events
        ]

    def import_events(self, rows: list[dict[str, Any]]) -> None:
        """`events` 입력을 해석한다."""
        self._events = [
            SimEvent(
                t_sec=float(row.get("t_sec", 0.0)),
                event_type=str(row.get("event_type", "UNKNOWN")),
                payload=dict(row.get("payload", {})),
            )
            for row in rows
        ]

    def summary(self) -> dict[str, Any]:
        """현재 상태 요약을 반환한다."""
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
        """`대상` 상태를 정리한다."""
        self._events.clear()
