"""
비상 방송 시스템
===============
구역별 브로드캐스트 + 우선순위 인터럽트 + 확인 응답.

사용법:
    eb = EmergencyBroadcast()
    eb.register_receiver("d1", sector="A")
    eb.broadcast("WEATHER_ALERT", sectors=["A", "B"], priority=1)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Receiver:
    """수신기"""
    node_id: str
    sector: str = "default"
    active: bool = True


@dataclass
class Broadcast:
    """방송"""
    broadcast_id: int
    message: str
    priority: int  # 1(highest) ~ 5(lowest)
    sectors: list[str]
    recipients: list[str] = field(default_factory=list)
    acknowledged: list[str] = field(default_factory=list)
    t: float = 0.0


class EmergencyBroadcast:
    """비상 방송."""

    def __init__(self) -> None:
        self._receivers: dict[str, Receiver] = {}
        self._broadcasts: list[Broadcast] = []
        self._broadcast_id = 0

    def register_receiver(self, node_id: str, sector: str = "default") -> None:
        self._receivers[node_id] = Receiver(node_id=node_id, sector=sector)

    def deactivate_receiver(self, node_id: str) -> None:
        r = self._receivers.get(node_id)
        if r:
            r.active = False

    def broadcast(
        self, message: str, sectors: list[str] | None = None,
        priority: int = 3, t: float = 0.0,
    ) -> Broadcast:
        self._broadcast_id += 1

        # 대상 수신기 결정
        recipients = []
        for nid, r in self._receivers.items():
            if not r.active:
                continue
            if sectors is None or r.sector in sectors:
                recipients.append(nid)

        bc = Broadcast(
            broadcast_id=self._broadcast_id,
            message=message, priority=priority,
            sectors=sectors or ["ALL"],
            recipients=recipients, t=t,
        )
        self._broadcasts.append(bc)
        return bc

    def acknowledge(self, broadcast_id: int, node_id: str) -> bool:
        for bc in reversed(self._broadcasts):
            if bc.broadcast_id == broadcast_id:
                if node_id in bc.recipients and node_id not in bc.acknowledged:
                    bc.acknowledged.append(node_id)
                    return True
                return False
        return False

    def ack_rate(self, broadcast_id: int) -> float:
        for bc in reversed(self._broadcasts):
            if bc.broadcast_id == broadcast_id:
                if not bc.recipients:
                    return 0.0
                return round(len(bc.acknowledged) / len(bc.recipients) * 100, 1)
        return 0.0

    def unacknowledged(self, broadcast_id: int) -> list[str]:
        for bc in reversed(self._broadcasts):
            if bc.broadcast_id == broadcast_id:
                return [r for r in bc.recipients if r not in bc.acknowledged]
        return []

    def recent_broadcasts(self, n: int = 10) -> list[Broadcast]:
        return self._broadcasts[-n:]

    def high_priority_pending(self) -> list[Broadcast]:
        return [
            bc for bc in self._broadcasts
            if bc.priority <= 2 and len(bc.acknowledged) < len(bc.recipients)
        ]

    def summary(self) -> dict[str, Any]:
        return {
            "receivers": len(self._receivers),
            "active_receivers": sum(1 for r in self._receivers.values() if r.active),
            "total_broadcasts": len(self._broadcasts),
            "high_priority_pending": len(self.high_priority_pending()),
        }
