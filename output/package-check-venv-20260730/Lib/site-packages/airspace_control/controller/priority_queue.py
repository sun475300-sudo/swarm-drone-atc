"""비행 우선순위 큐."""
from __future__ import annotations
import heapq
from dataclasses import dataclass, field
from ..planning.waypoint import Route


PRIORITY_LABELS = {
    0: "EMERGENCY",
    1: "MEDICAL",
    2: "COMMERCIAL",
    3: "RECREATIONAL",
}


@dataclass(order=True)
class _PrioritizedRoute:
    priority: int
    tie_breaker: float   # 요청 시각 (낮을수록 먼저)
    route: Route = field(compare=False)


class FlightPriorityQueue:
    """
    비행 허가 요청을 우선순위 순으로 처리.
    우선순위: 0(EMERGENCY) > 1(MEDICAL) > 2(COMMERCIAL) > 3(RECREATIONAL)
    동순위면 요청 시각 빠른 것 먼저.
    """

    def __init__(self):
        self._heap: list[_PrioritizedRoute] = []
        self._counter = 0.0

    def push(self, route: Route, request_time: float) -> None:
        item = _PrioritizedRoute(
            priority=route.priority,
            tie_breaker=request_time,
            route=route,
        )
        heapq.heappush(self._heap, item)

    def pop(self) -> Route | None:
        if not self._heap:
            return None
        return heapq.heappop(self._heap).route

    def peek(self) -> Route | None:
        if not self._heap:
            return None
        return self._heap[0].route

    def __len__(self) -> int:
        return len(self._heap)

    def is_empty(self) -> bool:
        return len(self._heap) == 0
