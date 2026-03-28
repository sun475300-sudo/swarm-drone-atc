"""
통신 QoS 관리
=============
우선순위별 대역폭 할당 + 트래픽 쉐이핑 + SLA.

사용법:
    qos = CommQoS(total_bandwidth=1000)
    qos.add_class("emergency", priority=1, min_bw=200)
    qos.allocate("d1", "emergency", requested_bw=150)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class QoSClass:
    """QoS 클래스"""
    name: str
    priority: int  # 1(highest) ~ 5(lowest)
    min_bandwidth: float  # Kbps
    max_bandwidth: float = 0  # 0 = unlimited
    current_usage: float = 0.0
    members: list[str] = field(default_factory=list)


@dataclass
class AllocationResult:
    """할당 결과"""
    node_id: str
    qos_class: str
    allocated_bw: float
    requested_bw: float
    satisfied: bool


class CommQoS:
    """통신 QoS 관리."""

    def __init__(self, total_bandwidth: float = 1000.0) -> None:
        self.total_bandwidth = total_bandwidth
        self._classes: dict[str, QoSClass] = {}
        self._allocations: dict[str, AllocationResult] = {}
        self._history: list[AllocationResult] = []

    def add_class(
        self, name: str, priority: int = 3,
        min_bw: float = 0.0, max_bw: float = 0.0,
    ) -> None:
        self._classes[name] = QoSClass(
            name=name, priority=priority,
            min_bandwidth=min_bw, max_bandwidth=max_bw,
        )

    def allocate(self, node_id: str, qos_class: str, requested_bw: float) -> AllocationResult:
        cls = self._classes.get(qos_class)
        if not cls:
            result = AllocationResult(node_id, qos_class, 0, requested_bw, False)
            self._history.append(result)
            return result

        used = sum(a.allocated_bw for a in self._allocations.values())
        available = self.total_bandwidth - used

        # 최대 대역폭 제한
        max_alloc = min(requested_bw, available)
        if cls.max_bandwidth > 0:
            max_alloc = min(max_alloc, cls.max_bandwidth - cls.current_usage)

        allocated = max(0, max_alloc)
        satisfied = allocated >= requested_bw * 0.8

        cls.current_usage += allocated
        if node_id not in cls.members:
            cls.members.append(node_id)

        result = AllocationResult(
            node_id=node_id, qos_class=qos_class,
            allocated_bw=round(allocated, 1),
            requested_bw=requested_bw, satisfied=satisfied,
        )
        self._allocations[node_id] = result
        self._history.append(result)
        return result

    def release(self, node_id: str) -> None:
        alloc = self._allocations.pop(node_id, None)
        if alloc:
            cls = self._classes.get(alloc.qos_class)
            if cls:
                cls.current_usage = max(0, cls.current_usage - alloc.allocated_bw)
                if node_id in cls.members:
                    cls.members.remove(node_id)

    def utilization(self) -> float:
        used = sum(a.allocated_bw for a in self._allocations.values())
        return round(used / max(self.total_bandwidth, 1) * 100, 1)

    def satisfaction_rate(self) -> float:
        if not self._history:
            return 100.0
        return round(sum(1 for a in self._history if a.satisfied) / len(self._history) * 100, 1)

    def class_usage(self) -> dict[str, float]:
        return {name: round(cls.current_usage, 1) for name, cls in self._classes.items()}

    def summary(self) -> dict[str, Any]:
        return {
            "classes": len(self._classes),
            "active_allocations": len(self._allocations),
            "utilization_pct": self.utilization(),
            "satisfaction_rate": self.satisfaction_rate(),
        }
