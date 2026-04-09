"""Phase 291: Protocol Optimizer — 통신 프로토콜 최적화.

적응형 전송률 제어, QoS 관리, 패킷 압축,
우선순위 큐잉 및 프로토콜 스위칭을 구현합니다.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Deque
from collections import deque


class Protocol(Enum):
    UDP_LITE = "udp_lite"
    TCP = "tcp"
    QUIC = "quic"
    MQTT = "mqtt"
    COAP = "coap"
    CUSTOM_LOW_LATENCY = "custom_ll"


class QoSLevel(Enum):
    BEST_EFFORT = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3
    REAL_TIME = 4


@dataclass
class Packet:
    packet_id: str
    source: str
    destination: str
    payload_bytes: int
    qos: QoSLevel = QoSLevel.NORMAL
    protocol: Protocol = Protocol.UDP_LITE
    timestamp: float = 0.0
    retries: int = 0
    compressed: bool = False


@dataclass
class ChannelState:
    bandwidth_bps: float = 10e6  # 10 Mbps
    utilization: float = 0.0
    packet_loss_rate: float = 0.01
    latency_base_ms: float = 5.0
    jitter_ms: float = 2.0


@dataclass
class TransmissionResult:
    packet_id: str
    success: bool
    latency_ms: float
    actual_bytes: int
    protocol_used: Protocol


class AdaptiveRateController:
    """적응형 전송률 제어기 (AIMD 기반)."""

    def __init__(self, initial_rate_bps: float = 1e6):
        self.rate_bps = initial_rate_bps
        self.max_rate_bps = 10e6
        self.min_rate_bps = 100e3
        self._window_size = 10
        self._loss_history: Deque[bool] = deque(maxlen=self._window_size)

    def on_ack(self):
        self._loss_history.append(False)
        # Additive increase
        self.rate_bps = min(self.max_rate_bps, self.rate_bps + 50e3)

    def on_loss(self):
        self._loss_history.append(True)
        # Multiplicative decrease
        self.rate_bps = max(self.min_rate_bps, self.rate_bps * 0.5)

    def current_rate(self) -> float:
        return self.rate_bps

    def loss_ratio(self) -> float:
        if not self._loss_history:
            return 0.0
        return sum(self._loss_history) / len(self._loss_history)


class PacketCompressor:
    """패킷 압축기."""

    @staticmethod
    def compress(payload_bytes: int, data_type: str = "telemetry") -> int:
        ratios = {"telemetry": 0.4, "video": 0.7, "command": 0.3, "status": 0.35}
        ratio = ratios.get(data_type, 0.5)
        return max(8, int(payload_bytes * ratio))

    @staticmethod
    def decompress_overhead_ms(compressed_bytes: int) -> float:
        return compressed_bytes * 0.001  # ~1us per byte


class ProtocolOptimizer:
    """통신 프로토콜 최적화기.

    - 적응형 전송률 제어 (AIMD)
    - QoS 기반 패킷 스케줄링
    - 자동 프로토콜 선택
    - 패킷 압축/전송 최적화
    """

    def __init__(self, rng_seed: int = 42):
        self._rng = np.random.default_rng(rng_seed)
        self._channel = ChannelState()
        self._rate_ctrl = AdaptiveRateController()
        self._compressor = PacketCompressor()
        self._queue: List[Packet] = []
        self._results: List[TransmissionResult] = []
        self._stats = {"sent": 0, "delivered": 0, "lost": 0, "compressed": 0}

    def set_channel(self, channel: ChannelState):
        self._channel = channel

    def select_protocol(self, qos: QoSLevel, payload_bytes: int) -> Protocol:
        if qos == QoSLevel.REAL_TIME:
            return Protocol.CUSTOM_LOW_LATENCY
        elif qos == QoSLevel.CRITICAL:
            return Protocol.QUIC
        elif payload_bytes < 64:
            return Protocol.COAP
        elif qos.value >= QoSLevel.HIGH.value:
            return Protocol.TCP
        return Protocol.UDP_LITE

    def enqueue(self, packet: Packet):
        packet.protocol = self.select_protocol(packet.qos, packet.payload_bytes)
        self._queue.append(packet)
        # Sort by QoS priority (highest first)
        self._queue.sort(key=lambda p: p.qos.value, reverse=True)

    def transmit_next(self) -> Optional[TransmissionResult]:
        if not self._queue:
            return None
        packet = self._queue.pop(0)
        # Compress if beneficial
        actual_bytes = packet.payload_bytes
        if not packet.compressed and actual_bytes > 32:
            actual_bytes = self._compressor.compress(actual_bytes)
            packet.compressed = True
            self._stats["compressed"] += 1

        # Simulate transmission
        loss = self._rng.random() < self._channel.packet_loss_rate * (1 + self._channel.utilization)
        if loss and packet.retries < 3 and packet.qos.value >= QoSLevel.HIGH.value:
            packet.retries += 1
            self._queue.insert(0, packet)
            self._rate_ctrl.on_loss()
            loss = False  # Will retry

        latency = self._channel.latency_base_ms + self._rng.normal(0, self._channel.jitter_ms)
        latency = max(0.1, latency)
        if packet.compressed:
            latency += self._compressor.decompress_overhead_ms(actual_bytes)

        self._stats["sent"] += 1
        success = not loss
        if success:
            self._stats["delivered"] += 1
            self._rate_ctrl.on_ack()
        else:
            self._stats["lost"] += 1
            self._rate_ctrl.on_loss()

        result = TransmissionResult(
            packet_id=packet.packet_id, success=success,
            latency_ms=round(latency, 2), actual_bytes=actual_bytes,
            protocol_used=packet.protocol,
        )
        self._results.append(result)
        return result

    def flush_queue(self) -> List[TransmissionResult]:
        results = []
        while self._queue:
            r = self.transmit_next()
            if r:
                results.append(r)
        return results

    def get_queue_depth(self) -> int:
        return len(self._queue)

    def summary(self) -> dict:
        avg_latency = np.mean([r.latency_ms for r in self._results]) if self._results else 0
        return {
            "total_sent": self._stats["sent"],
            "delivered": self._stats["delivered"],
            "lost": self._stats["lost"],
            "compressed": self._stats["compressed"],
            "delivery_ratio": round(self._stats["delivered"] / max(self._stats["sent"], 1), 3),
            "avg_latency_ms": round(float(avg_latency), 2),
            "current_rate_mbps": round(self._rate_ctrl.current_rate() / 1e6, 2),
            "queue_depth": len(self._queue),
        }
