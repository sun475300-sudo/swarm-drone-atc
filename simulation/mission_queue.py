"""
임무 우선순위 큐
================
우선순위 기반 임무 대기열 + SLA 기한 + 재할당.

사용법:
    mq = MissionQueue()
    mq.enqueue("mission_1", priority=1, deadline=300.0)
    next_mission = mq.dequeue()
"""
from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Any


@dataclass(order=True)
class QueuedMission:
    """큐 임무"""
    priority: int
    enqueue_time: float
    mission_id: str = field(compare=False)
    drone_id: str = field(compare=False, default="")
    deadline: float = field(compare=False, default=float("inf"))
    mission_type: str = field(compare=False, default="DELIVERY")
    status: str = field(compare=False, default="PENDING")  # PENDING, ASSIGNED, COMPLETED, EXPIRED


class MissionQueue:
    """우선순위 기반 임무 큐."""

    def __init__(self) -> None:
        self._queue: list[QueuedMission] = []
        self._all_missions: dict[str, QueuedMission] = {}
        self._completed: list[QueuedMission] = []

    def enqueue(
        self,
        mission_id: str,
        priority: int = 3,
        deadline: float = float("inf"),
        mission_type: str = "DELIVERY",
        enqueue_time: float = 0.0,
    ) -> QueuedMission:
        mission = QueuedMission(
            priority=priority,
            enqueue_time=enqueue_time,
            mission_id=mission_id,
            deadline=deadline,
            mission_type=mission_type,
        )
        heapq.heappush(self._queue, mission)
        self._all_missions[mission_id] = mission
        return mission

    def dequeue(self) -> QueuedMission | None:
        while self._queue:
            mission = heapq.heappop(self._queue)
            if mission.status == "PENDING":
                mission.status = "ASSIGNED"
                return mission
        return None

    def peek(self) -> QueuedMission | None:
        for m in self._queue:
            if m.status == "PENDING":
                return m
        return None

    def assign(self, mission_id: str, drone_id: str) -> bool:
        mission = self._all_missions.get(mission_id)
        if mission:
            mission.drone_id = drone_id
            mission.status = "ASSIGNED"
            return True
        return False

    def complete(self, mission_id: str) -> bool:
        mission = self._all_missions.get(mission_id)
        if mission:
            mission.status = "COMPLETED"
            self._completed.append(mission)
            return True
        return False

    def reassign(self, mission_id: str, new_drone_id: str) -> bool:
        mission = self._all_missions.get(mission_id)
        if mission and mission.status == "ASSIGNED":
            mission.drone_id = new_drone_id
            return True
        return False

    def expire_overdue(self, current_time: float) -> list[str]:
        """기한 초과 임무 만료 처리"""
        expired = []
        for mid, m in self._all_missions.items():
            if m.status == "PENDING" and m.deadline < current_time:
                m.status = "EXPIRED"
                expired.append(mid)
        return expired

    def pending_count(self) -> int:
        return sum(1 for m in self._all_missions.values() if m.status == "PENDING")

    def assigned_count(self) -> int:
        return sum(1 for m in self._all_missions.values() if m.status == "ASSIGNED")

    def by_priority(self, priority: int) -> list[QueuedMission]:
        return [m for m in self._all_missions.values() if m.priority == priority]

    def sla_compliance(self, current_time: float) -> float:
        """SLA 준수율 (기한 내 완료 비율)"""
        completed_with_deadline = [
            m for m in self._completed if m.deadline < float("inf")
        ]
        if not completed_with_deadline:
            return 100.0
        on_time = sum(1 for m in completed_with_deadline if m.enqueue_time <= m.deadline)
        return (on_time / len(completed_with_deadline)) * 100

    def summary(self) -> dict[str, Any]:
        status_counts: dict[str, int] = {}
        for m in self._all_missions.values():
            status_counts[m.status] = status_counts.get(m.status, 0) + 1
        return {
            "total_missions": len(self._all_missions),
            "by_status": status_counts,
            "completed": len(self._completed),
            "pending": self.pending_count(),
        }
