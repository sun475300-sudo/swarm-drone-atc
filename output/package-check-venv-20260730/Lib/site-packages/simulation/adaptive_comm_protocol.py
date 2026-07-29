"""
Phase 420: Adaptive Communication Protocol for Dynamic Networks
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ProtocolMode(Enum):
    """``ProtocolMode`` 관련 기능을 제공한다."""
    LOW_LATENCY = "low_latency"
    HIGH_RELIABILITY = "high_reliability"
    BALANCED = "balanced"
    EMERGENCY = "emergency"


@dataclass
class LinkQuality:
    """``LinkQuality`` 관련 기능을 제공한다."""
    snr_db: float
    packet_loss_rate: float
    latency_ms: float
    bandwidth_mbps: float


@dataclass
class TransmissionConfig:
    """``TransmissionConfig`` 데이터를 표현한다."""
    modulation: str
    coding_rate: str
    power_dbm: float
    frequency_mhz: float
    bandwidth_mhz: float


class AdaptiveCommProtocol:
    """``AdaptiveCommProtocol`` 관련 기능을 제공한다."""
    def __init__(
        self,
        default_mode: ProtocolMode = ProtocolMode.BALANCED,
        adaptation_interval: float = 1.0,
    ):
        """인스턴스를 초기화한다."""
        self.default_mode = default_mode
        self.adaptation_interval = adaptation_interval

        self.link_qualities: dict[tuple[str, str], LinkQuality] = {}
        self.transmission_configs: dict[tuple[str, str], TransmissionConfig] = {}

        self.metrics = {
            "packets_sent": 0,
            "packets_received": 0,
            "adaptation_events": 0,
        }

    def update_link_quality(
        self,
        node1: str,
        node2: str,
        snr_db: float,
        packet_loss: float,
        latency: float,
        bandwidth: float,
    ):
        """`link quality` 상태를 갱신한다."""
        key = tuple(sorted([node1, node2]))

        self.link_qualities[key] = LinkQuality(
            snr_db=snr_db,
            packet_loss_rate=packet_loss,
            latency_ms=latency,
            bandwidth_mbps=bandwidth,
        )

        self._adapt_transmission_config(key)

    def _adapt_transmission_config(self, link: tuple[str, str]):
        if link not in self.link_qualities:
            return

        quality = self.link_qualities[link]

        if quality.snr_db > 20:
            modulation = "256-QAM"
            coding_rate = "5/6"
            power_dbm = 20
        elif quality.snr_db > 15:
            modulation = "64-QAM"
            coding_rate = "3/4"
            power_dbm = 23
        elif quality.snr_db > 10:
            modulation = "16-QAM"
            coding_rate = "1/2"
            power_dbm = 26
        else:
            modulation = "QPSK"
            coding_rate = "1/2"
            power_dbm = 30

        if quality.packet_loss_rate > 0.1:
            coding_rate = "3/4" if coding_rate == "5/6" else "1/2"
            power_dbm += 3

        config = TransmissionConfig(
            modulation=modulation,
            coding_rate=coding_rate,
            power_dbm=power_dbm,
            frequency_mhz=5800,
            bandwidth_mhz=20,
        )

        self.transmission_configs[link] = config
        self.metrics["adaptation_events"] += 1

    def get_config(self, node1: str, node2: str) -> TransmissionConfig | None:
        """`config` 정보를 조회한다."""
        key = tuple(sorted([node1, node2]))
        return self.transmission_configs.get(key)

    def select_best_neighbor(self, node: str, neighbors: list[str]) -> str | None:
        """`best neighbor` 동작을 수행한다."""
        if not neighbors:
            return None

        best_neighbor = None
        best_score = -float("inf")

        for neighbor in neighbors:
            key = tuple(sorted([node, neighbor]))
            quality = self.link_qualities.get(key)

            if not quality:
                continue

            score = (
                quality.snr_db
                - quality.latency_ms * 0.1
                - quality.packet_loss_rate * 100
            )

            if score > best_score:
                best_score = score
                best_neighbor = neighbor

        return best_neighbor

    def get_protocol_stats(self) -> dict[str, Any]:
        """`protocol stats` 정보를 조회한다."""
        return {
            "mode": self.default_mode.value,
            "active_links": len(self.link_qualities),
            "adaptation_events": self.metrics["adaptation_events"],
            "packets_sent": self.metrics["packets_sent"],
            "packets_received": self.metrics["packets_received"],
        }
