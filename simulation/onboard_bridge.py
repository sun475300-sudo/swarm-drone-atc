"""Jetson Orin Nano MAVLink UART↔UDP 브리지 시뮬레이션."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np


@dataclass
class BridgeStats:
    total: int = 0
    dropped: int = 0
    avg_latency_ms: float = 0.0

    @property
    def drop_rate(self) -> float:
        return self.dropped / self.total if self.total > 0 else 0.0


class OnboardBridge:
    """MAVLink 패킷 릴레이를 시뮬레이션하는 UART↔UDP 브리지.

    실제 하드웨어 없이 지연 및 패킷 손실을 모의한다.
    """

    def __init__(
        self,
        simulate_latency_ms: float = 5.0,
        simulate_packet_loss_rate: float = 0.01,
        seed: int = 42,
    ) -> None:
        if not (0.0 <= simulate_packet_loss_rate <= 1.0):
            raise ValueError("packet_loss_rate는 0~1 사이여야 합니다")
        if simulate_latency_ms < 0:
            raise ValueError("latency_ms는 0 이상이어야 합니다")

        self.simulate_latency_ms = simulate_latency_ms
        self.simulate_packet_loss_rate = simulate_packet_loss_rate
        self._rng = np.random.default_rng(seed)

        self._stats = BridgeStats()
        self._latency_history: list[float] = []

    def relay(self, packet: bytes) -> bytes | None:
        """패킷을 릴레이한다. 시뮬레이션된 손실 시 None 반환.

        Args:
            packet: 전달할 원시 MAVLink 바이트.

        Returns:
            릴레이된 패킷 또는 패킷 손실 시 None.
        """
        if not isinstance(packet, (bytes, bytearray)):
            raise TypeError(f"packet은 bytes여야 합니다, 받은 타입: {type(packet)}")

        self._stats.total += 1

        # 패킷 손실 시뮬레이션
        if self._rng.random() < self.simulate_packet_loss_rate:
            self._stats.dropped += 1
            return None

        # 지연 시뮬레이션 (가우시안 지터 포함)
        jitter = float(self._rng.normal(0, self.simulate_latency_ms * 0.1))
        latency = max(0.0, self.simulate_latency_ms + jitter)
        self._latency_history.append(latency)

        # 누적 평균 지연 갱신
        n = len(self._latency_history)
        self._stats.avg_latency_ms = sum(self._latency_history) / n

        return bytes(packet)

    @property
    def stats(self) -> BridgeStats:
        """현재 브리지 통계 반환 (복사본)."""
        return BridgeStats(
            total=self._stats.total,
            dropped=self._stats.dropped,
            avg_latency_ms=self._stats.avg_latency_ms,
        )

    def reset_stats(self) -> None:
        """통계 및 이력 초기화."""
        self._stats = BridgeStats()
        self._latency_history.clear()
