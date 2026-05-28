"""
실시간 리포트 스트림
===================
이벤트 스트림 + 실시간 대시보드 피드 + 버퍼 관리.

사용법:
    rs = ReportStream()
    rs.push("collision_alert", {"drone": "d1", "cpa": 5.0})
    events = rs.consume("dashboard")
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any


@dataclass
class StreamEvent:
    """스트림 이벤트"""
    event_type: str
    data: dict[str, Any]
    t: float = 0.0
    seq: int = 0


class ReportStream:
    """실시간 리포트 스트림."""

    def __init__(self, buffer_size: int = 500) -> None:
        """인스턴스를 초기화한다."""
        self.buffer_size = buffer_size
        self._buffer: deque[StreamEvent] = deque(maxlen=buffer_size)
        self._subscribers: dict[str, int] = {}  # subscriber → last_seq
        self._seq = 0
        self._total_pushed = 0

    def push(self, event_type: str, data: dict[str, Any] | None = None, t: float = 0.0) -> StreamEvent:
        """``push`` 동작을 수행한다."""
        self._seq += 1
        self._total_pushed += 1
        event = StreamEvent(
            event_type=event_type, data=data or {},
            t=t, seq=self._seq,
        )
        self._buffer.append(event)
        return event

    def subscribe(self, subscriber_id: str) -> None:
        """`대상` 항목을 추가한다."""
        self._subscribers[subscriber_id] = self._seq

    def unsubscribe(self, subscriber_id: str) -> None:
        """`대상` 상태를 정리한다."""
        self._subscribers.pop(subscriber_id, None)

    def consume(self, subscriber_id: str, max_events: int = 50) -> list[StreamEvent]:
        """``consume`` 동작을 수행한다."""
        last_seq = self._subscribers.get(subscriber_id, 0)
        events = [e for e in self._buffer if e.seq > last_seq][:max_events]
        if events:
            self._subscribers[subscriber_id] = events[-1].seq
        return events

    def peek(self, n: int = 10) -> list[StreamEvent]:
        """``peek`` 동작을 수행한다."""
        return list(self._buffer)[-n:]

    def filter_by_type(self, event_type: str, n: int = 50) -> list[StreamEvent]:
        """``filter_by_type`` 동작을 수행한다."""
        return [e for e in self._buffer if e.event_type == event_type][-n:]

    def event_counts(self) -> dict[str, int]:
        """``event_counts`` 동작을 수행한다."""
        counts: dict[str, int] = {}
        for e in self._buffer:
            counts[e.event_type] = counts.get(e.event_type, 0) + 1
        return counts

    def lag(self, subscriber_id: str) -> int:
        """``lag`` 동작을 수행한다."""
        last_seq = self._subscribers.get(subscriber_id, 0)
        return self._seq - last_seq

    def summary(self) -> dict[str, Any]:
        """현재 상태 요약을 반환한다."""
        return {
            "buffer_size": len(self._buffer),
            "total_pushed": self._total_pushed,
            "subscribers": len(self._subscribers),
            "event_types": len(self.event_counts()),
        }
