"""Phase 290: V2X Communication — 드론-기반시설 통신 시스템.

V2I(Vehicle-to-Infrastructure), V2V(Vehicle-to-Vehicle),
V2N(Vehicle-to-Network) 통신 프로토콜 시뮬레이션.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class V2XMode(Enum):
    V2V = "v2v"  # Drone-to-Drone
    V2I = "v2i"  # Drone-to-Infrastructure
    V2N = "v2n"  # Drone-to-Network
    V2P = "v2p"  # Drone-to-Pedestrian (warning)


class MessageType(Enum):
    BSM = "basic_safety_message"
    CAM = "cooperative_awareness"
    DENM = "decentralized_event_notification"
    CPM = "collective_perception"
    HEARTBEAT = "heartbeat"


@dataclass
class V2XMessage:
    msg_id: str
    sender: str
    msg_type: MessageType
    mode: V2XMode
    position: np.ndarray
    velocity: np.ndarray
    timestamp: float
    payload: dict = field(default_factory=dict)
    ttl: int = 3  # hops
    priority: int = 5


@dataclass
class V2XEndpoint:
    endpoint_id: str
    position: np.ndarray
    mode: V2XMode
    range_m: float = 300.0
    channel_busy_ratio: float = 0.0
    messages_sent: int = 0
    messages_received: int = 0


class ChannelModel:
    """V2X 채널 모델 (C-V2X / DSRC)."""

    @staticmethod
    def packet_delivery_ratio(distance_m: float, max_range: float = 300.0) -> float:
        if distance_m > max_range:
            return 0.0
        return max(0.0, 1.0 - (distance_m / max_range) ** 2)

    @staticmethod
    def latency_ms(distance_m: float, mode: V2XMode) -> float:
        base = {"v2v": 2.0, "v2i": 5.0, "v2n": 20.0, "v2p": 10.0}
        return base.get(mode.value, 10.0) + distance_m / 3e5


class V2XCommunicationSystem:
    """V2X 통신 시스템.

    - BSM/CAM/DENM/CPM 메시지 교환
    - 채널 모델 기반 전달 시뮬레이션
    - 멀티홉 릴레이
    - 통신 통계 분석
    """

    def __init__(self, rng_seed: int = 42):
        self._rng = np.random.default_rng(rng_seed)
        self._endpoints: Dict[str, V2XEndpoint] = {}
        self._message_log: List[V2XMessage] = []
        self._delivery_log: List[dict] = []
        self._channel = ChannelModel()
        self._msg_counter = 0

    def register_endpoint(self, endpoint: V2XEndpoint):
        self._endpoints[endpoint.endpoint_id] = endpoint

    def send_bsm(self, sender_id: str, position: np.ndarray, velocity: np.ndarray, timestamp: float = 0.0) -> V2XMessage:
        self._msg_counter += 1
        msg = V2XMessage(
            msg_id=f"BSM-{self._msg_counter:06d}", sender=sender_id,
            msg_type=MessageType.BSM, mode=V2XMode.V2V,
            position=position, velocity=velocity, timestamp=timestamp,
            payload={"speed": float(np.linalg.norm(velocity)), "heading": float(np.arctan2(velocity[1], velocity[0]))},
        )
        ep = self._endpoints.get(sender_id)
        if ep:
            ep.messages_sent += 1
        self._message_log.append(msg)
        return msg

    def send_denm(self, sender_id: str, event_type: str, position: np.ndarray, timestamp: float = 0.0) -> V2XMessage:
        self._msg_counter += 1
        msg = V2XMessage(
            msg_id=f"DENM-{self._msg_counter:06d}", sender=sender_id,
            msg_type=MessageType.DENM, mode=V2XMode.V2V,
            position=position, velocity=np.zeros(3), timestamp=timestamp,
            payload={"event": event_type}, priority=9, ttl=5,
        )
        self._message_log.append(msg)
        return msg

    def broadcast(self, msg: V2XMessage) -> List[str]:
        """메시지 브로드캐스트: 수신 가능한 엔드포인트에 전달."""
        delivered_to = []
        sender_ep = self._endpoints.get(msg.sender)
        if not sender_ep:
            return delivered_to
        for eid, ep in self._endpoints.items():
            if eid == msg.sender:
                continue
            dist = np.linalg.norm(msg.position - ep.position)
            pdr = self._channel.packet_delivery_ratio(dist, sender_ep.range_m)
            if self._rng.random() < pdr:
                ep.messages_received += 1
                delivered_to.append(eid)
                latency = self._channel.latency_ms(dist, msg.mode)
                self._delivery_log.append({
                    "msg_id": msg.msg_id, "from": msg.sender, "to": eid,
                    "distance_m": round(dist, 1), "latency_ms": round(latency, 2),
                })
        return delivered_to

    def multicast(self, msg: V2XMessage, targets: List[str]) -> List[str]:
        delivered = []
        sender_ep = self._endpoints.get(msg.sender)
        if not sender_ep:
            return delivered
        for tid in targets:
            ep = self._endpoints.get(tid)
            if not ep:
                continue
            dist = np.linalg.norm(msg.position - ep.position)
            pdr = self._channel.packet_delivery_ratio(dist, sender_ep.range_m)
            if self._rng.random() < pdr:
                ep.messages_received += 1
                delivered.append(tid)
        return delivered

    def get_neighbors(self, endpoint_id: str) -> List[str]:
        ep = self._endpoints.get(endpoint_id)
        if not ep:
            return []
        neighbors = []
        for eid, other in self._endpoints.items():
            if eid == endpoint_id:
                continue
            if np.linalg.norm(ep.position - other.position) <= ep.range_m:
                neighbors.append(eid)
        return neighbors

    def get_delivery_stats(self) -> dict:
        if not self._delivery_log:
            return {"total": 0, "avg_latency_ms": 0, "avg_distance_m": 0}
        latencies = [d["latency_ms"] for d in self._delivery_log]
        distances = [d["distance_m"] for d in self._delivery_log]
        return {
            "total": len(self._delivery_log),
            "avg_latency_ms": round(np.mean(latencies), 2),
            "avg_distance_m": round(np.mean(distances), 1),
            "max_latency_ms": round(max(latencies), 2),
        }

    def summary(self) -> dict:
        total_sent = sum(ep.messages_sent for ep in self._endpoints.values())
        total_recv = sum(ep.messages_received for ep in self._endpoints.values())
        return {
            "total_endpoints": len(self._endpoints),
            "total_messages_sent": total_sent,
            "total_messages_received": total_recv,
            "delivery_ratio": round(total_recv / max(total_sent, 1), 3),
            "delivery_stats": self.get_delivery_stats(),
        }
