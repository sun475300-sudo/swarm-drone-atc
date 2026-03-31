"""
Phase 485: Drone Swarm Communication Protocol
TDMA/CDMA 하이브리드 MAC, 우선순위 메시징, 릴레이 라우팅.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Deque
from collections import deque
import hashlib


class MACProtocol(Enum):
    TDMA = "tdma"
    CDMA = "cdma"
    CSMA = "csma"
    HYBRID = "hybrid"


class MessagePriority(Enum):
    EMERGENCY = 0
    COLLISION_AVOID = 1
    CONTROL = 2
    TELEMETRY = 3
    STATUS = 4
    BULK = 5


@dataclass
class SwarmMessage:
    msg_id: str
    src: int
    dst: int  # -1 for broadcast
    priority: MessagePriority
    payload: bytes
    timestamp: float
    ttl: int = 5
    hops: int = 0
    delivered: bool = False
    checksum: str = ""

    def __post_init__(self):
        if not self.checksum:
            self.checksum = hashlib.md5(self.payload).hexdigest()[:8]


@dataclass
class TimeSlot:
    slot_id: int
    owner: int  # drone_id
    start_us: int
    duration_us: int = 1000


@dataclass
class ChannelStats:
    throughput_kbps: float = 0.0
    latency_ms: float = 0.0
    packet_loss: float = 0.0
    collisions: int = 0
    messages_sent: int = 0
    messages_delivered: int = 0


class TDMAScheduler:
    """Time-Division Multiple Access scheduler."""

    def __init__(self, n_drones: int, frame_duration_us: int = 10000):
        self.n_drones = n_drones
        self.frame_duration = frame_duration_us
        self.slot_duration = frame_duration_us // max(n_drones, 1)
        self.slots: List[TimeSlot] = []
        for i in range(n_drones):
            self.slots.append(TimeSlot(i, i, i * self.slot_duration, self.slot_duration))

    def get_slot(self, drone_id: int, time_us: int) -> Optional[TimeSlot]:
        frame_offset = time_us % self.frame_duration
        for slot in self.slots:
            if slot.owner == drone_id:
                if slot.start_us <= frame_offset < slot.start_us + slot.duration_us:
                    return slot
        return None

    def can_transmit(self, drone_id: int, time_us: int) -> bool:
        return self.get_slot(drone_id, time_us) is not None


class CDMAEncoder:
    """Code-Division Multiple Access with Walsh codes."""

    def __init__(self, n_codes: int = 8):
        self.n_codes = n_codes
        self.codes = self._generate_walsh(n_codes)

    def _generate_walsh(self, n: int) -> np.ndarray:
        if n == 1:
            return np.array([[1]])
        half = self._generate_walsh(n // 2)
        return np.block([[half, half], [half, -half]])

    def encode(self, data: np.ndarray, code_idx: int) -> np.ndarray:
        code = self.codes[code_idx % self.n_codes]
        encoded = np.outer(data, code).flatten()
        return encoded

    def decode(self, signal: np.ndarray, code_idx: int) -> np.ndarray:
        code = self.codes[code_idx % self.n_codes]
        n = len(code)
        chunks = len(signal) // n
        decoded = np.array([np.dot(signal[i*n:(i+1)*n], code) / n for i in range(chunks)])
        return decoded


class SwarmProtocol:
    """Hybrid MAC protocol for drone swarm communication."""

    def __init__(self, n_drones: int = 20, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_drones = n_drones
        self.tdma = TDMAScheduler(n_drones)
        self.cdma = CDMAEncoder(max(8, n_drones))
        self.mac_mode = MACProtocol.HYBRID
        self.queues: Dict[int, Deque[SwarmMessage]] = {i: deque(maxlen=100) for i in range(n_drones)}
        self.delivered: List[SwarmMessage] = []
        self.stats = ChannelStats()
        self.time_us = 0
        self._msg_counter = 0
        self.routing_table: Dict[int, Dict[int, int]] = {}  # src -> {dst: next_hop}

        for i in range(n_drones):
            self.routing_table[i] = {}
            for j in range(n_drones):
                if i != j:
                    self.routing_table[i][j] = j  # direct by default

    def send(self, src: int, dst: int, payload: bytes,
             priority: MessagePriority = MessagePriority.TELEMETRY) -> SwarmMessage:
        self._msg_counter += 1
        msg = SwarmMessage(
            f"MSG-{self._msg_counter:06d}", src, dst, priority,
            payload, self.time_us / 1e6)
        self.queues[src].append(msg)
        self.stats.messages_sent += 1
        return msg

    def broadcast(self, src: int, payload: bytes,
                  priority: MessagePriority = MessagePriority.STATUS) -> SwarmMessage:
        return self.send(src, -1, payload, priority)

    def _process_queue(self, drone_id: int) -> List[SwarmMessage]:
        delivered = []
        queue = self.queues[drone_id]
        sorted_msgs = sorted(queue, key=lambda m: m.priority.value)

        for msg in sorted_msgs[:3]:
            can_send = False
            if self.mac_mode == MACProtocol.TDMA:
                can_send = self.tdma.can_transmit(drone_id, self.time_us)
            elif self.mac_mode == MACProtocol.CDMA:
                can_send = True
            elif self.mac_mode == MACProtocol.HYBRID:
                if msg.priority.value <= MessagePriority.COLLISION_AVOID.value:
                    can_send = True  # CDMA for emergency
                else:
                    can_send = self.tdma.can_transmit(drone_id, self.time_us)
                    if not can_send and self.rng.random() < 0.3:
                        can_send = True  # CSMA backoff success

            if can_send:
                if self.rng.random() > self.stats.packet_loss:
                    msg.delivered = True
                    msg.hops += 1
                    delivered.append(msg)
                    self.stats.messages_delivered += 1
                else:
                    self.stats.collisions += 1

        for msg in delivered:
            if msg in queue:
                queue.remove(msg)
        return delivered

    def tick(self, dt_us: int = 1000) -> Dict:
        self.time_us += dt_us
        all_delivered = []
        for i in range(self.n_drones):
            msgs = self._process_queue(i)
            all_delivered.extend(msgs)
        self.delivered.extend(all_delivered)

        if self.stats.messages_sent > 0:
            self.stats.throughput_kbps = (self.stats.messages_delivered * 64 * 8) / (self.time_us / 1e6) / 1000
            self.stats.latency_ms = self.rng.exponential(2) + 0.5
        return {"delivered": len(all_delivered), "time_us": self.time_us}

    def run(self, duration_ms: int = 1000) -> ChannelStats:
        steps = duration_ms
        for _ in range(steps):
            self.tick(1000)
            if self.rng.random() < 0.3:
                src = self.rng.integers(0, self.n_drones)
                dst = self.rng.integers(0, self.n_drones)
                while dst == src:
                    dst = self.rng.integers(0, self.n_drones)
                self.send(src, dst, b"telemetry_data_packet")
        return self.stats

    def summary(self) -> Dict:
        return {
            "protocol": self.mac_mode.value,
            "drones": self.n_drones,
            "messages_sent": self.stats.messages_sent,
            "messages_delivered": self.stats.messages_delivered,
            "throughput_kbps": round(self.stats.throughput_kbps, 2),
            "collisions": self.stats.collisions,
            "delivery_rate": round(self.stats.messages_delivered / max(self.stats.messages_sent, 1), 4),
        }
