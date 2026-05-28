"""
Event replayer infrastructure.
==============================
Event sourcing replay with sequence/time filtering and deterministic state restore.
"""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

T = TypeVar("T")


@dataclass
class ReplayEvent:
    """``ReplayEvent`` 데이터를 표현한다."""
    seq: int
    event_type: str
    payload: dict[str, Any]
    ts: float


class EventReplayer:
    """``EventReplayer`` 관련 기능을 제공한다."""
    def __init__(self) -> None:
        """인스턴스를 초기화한다."""
        self._events: list[ReplayEvent] = []
        self._seq = 0

    def append(self, event_type: str, payload: dict[str, Any], ts: float | None = None) -> ReplayEvent:
        """`대상` 항목을 추가한다."""
        self._seq += 1
        event = ReplayEvent(
            seq=self._seq,
            event_type=event_type,
            payload=dict(payload),
            ts=time.monotonic() if ts is None else float(ts),
        )
        self._events.append(event)
        return event

    def replay(
        self,
        from_seq: int = 1,
        to_seq: int | None = None,
        event_type: str | None = None,
        until_ts: float | None = None,
    ) -> list[ReplayEvent]:
        """``replay`` 동작을 수행한다."""
        items = [e for e in self._events if e.seq >= max(1, int(from_seq))]
        if to_seq is not None:
            items = [e for e in items if e.seq <= int(to_seq)]
        if event_type is not None:
            items = [e for e in items if e.event_type == event_type]
        if until_ts is not None:
            items = [e for e in items if e.ts <= float(until_ts)]
        return items

    def restore_state(
        self,
        reducer: Callable[[T, ReplayEvent], T],
        initial_state: T,
        from_seq: int = 1,
        to_seq: int | None = None,
    ) -> T:
        """``restore_state`` 동작을 수행한다."""
        state = initial_state
        for event in self.replay(from_seq=from_seq, to_seq=to_seq):
            state = reducer(state, event)
        return state

    def snapshot(self, at_seq: int | None = None) -> dict[str, Any]:
        """``snapshot`` 동작을 수행한다."""
        if not self._events:
            return {"events": 0, "last_seq": 0, "last_type": None}
        if at_seq is None:
            e = self._events[-1]
        else:
            seq = max(1, int(at_seq))
            matching = [it for it in self._events if it.seq <= seq]
            if not matching:
                return {"events": 0, "last_seq": 0, "last_type": None}
            e = matching[-1]
        return {
            "events": len([it for it in self._events if it.seq <= e.seq]),
            "last_seq": e.seq,
            "last_type": e.event_type,
        }

    def summary(self) -> dict[str, Any]:
        """현재 상태 요약을 반환한다."""
        return {
            "events": len(self._events),
            "next_seq": self._seq + 1,
            "types": len({e.event_type for e in self._events}),
        }
