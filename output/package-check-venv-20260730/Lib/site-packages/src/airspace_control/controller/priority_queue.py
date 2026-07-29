"""비행 우선순위 큐."""
from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Any

PRIORITY_LABELS = {
    0: "EMERGENCY",
    1: "MEDICAL",
    2: "COMMERCIAL",
    3: "RECREATIONAL",
}


@dataclass(order=True)
class _PrioritizedItem:
    """``_PrioritizedItem`` 관련 기능을 제공한다."""
    priority: int
    tie_breaker: float   # 요청 시각 (낮을수록 먼저)
    item: Any = field(compare=False)


class FlightPriorityQueue:
    """
    비행 허가 요청을 우선순위 순으로 처리.
    Route 또는 ClearanceRequest 등 .priority 속성을 가진 객체를 지원.
    우선순위: 0(EMERGENCY) > 1(MEDICAL) > 2(COMMERCIAL) > 3(RECREATIONAL)
    동순위면 요청 시각 빠른 것 먼저.
    """

    def __init__(self):
        """인스턴스를 초기화한다."""
        self._heap: list[_PrioritizedItem] = []
        self._counter = 0.0

    def push(self, item: Any, request_time: float) -> None:
        """``push`` 동작을 수행한다."""
        entry = _PrioritizedItem(
            priority=item.priority,
            tie_breaker=request_time,
            item=item,
        )
        heapq.heappush(self._heap, entry)

    def pop(self) -> Any | None:
        """``pop`` 동작을 수행한다."""
        if not self._heap:
            return None
        return heapq.heappop(self._heap).item

    def peek(self) -> Any | None:
        """``peek`` 동작을 수행한다."""
        if not self._heap:
            return None
        return self._heap[0].item

    def __len__(self) -> int:
        return len(self._heap)

    def is_empty(self) -> bool:
        """`empty` 여부를 반환한다."""
        return len(self._heap) == 0
