"""Phase 319: Dynamic Spectrum Access — 동적 주파수 스펙트럼 접근.

인지 무선 채널 감지, 스펙트럼 홀 탐지,
동적 채널 할당, 간섭 회피.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class ChannelStatus(Enum):
    IDLE = "idle"
    OCCUPIED = "occupied"
    SENSING = "sensing"
    TRANSMITTING = "transmitting"


class SpectrumBand(Enum):
    ISM_2_4GHZ = "ism_2.4ghz"
    ISM_5GHZ = "ism_5ghz"
    LTE_B7 = "lte_b7"
    CBRS = "cbrs_3.5ghz"
    TVWS = "tv_whitespace"


@dataclass
class Channel:
    channel_id: str
    center_freq_mhz: float
    bandwidth_mhz: float
    band: SpectrumBand
    status: ChannelStatus = ChannelStatus.IDLE
    primary_user_active: bool = False
    snr_db: float = 20.0
    interference_level: float = 0.0
    last_sensed: float = 0.0


@dataclass
class SpectrumHole:
    channel_id: str
    start_time: float
    duration_sec: float
    predicted_availability: float  # 0-1
    capacity_mbps: float


@dataclass
class SpectrumAllocation:
    drone_id: str
    channel_id: str
    start_time: float
    duration_sec: float
    tx_power_dbm: float
    data_rate_mbps: float


class DynamicSpectrumAccess:
    """동적 주파수 스펙트럼 접근 시스템.

    - 에너지 감지 기반 스펙트럼 센싱
    - 스펙트럼 홀 탐지 및 예측
    - 동적 채널 할당 (가용 최적 채널)
    - 간섭 회피 및 전력 제어
    """

    NOISE_FLOOR_DBM = -100.0

    def __init__(self, rng_seed: int = 42):
        self._rng = np.random.default_rng(rng_seed)
        self._channels: Dict[str, Channel] = {}
        self._allocations: Dict[str, SpectrumAllocation] = {}
        self._spectrum_holes: List[SpectrumHole] = []
        self._sensing_history: Dict[str, List[float]] = {}
        self._step_count = 0

    def add_channel(self, channel: Channel):
        self._channels[channel.channel_id] = channel

    def init_default_channels(self):
        """Initialize default channel set."""
        channels = [
            Channel("ch1", 2412, 20, SpectrumBand.ISM_2_4GHZ),
            Channel("ch6", 2437, 20, SpectrumBand.ISM_2_4GHZ),
            Channel("ch11", 2462, 20, SpectrumBand.ISM_2_4GHZ),
            Channel("ch36", 5180, 40, SpectrumBand.ISM_5GHZ),
            Channel("ch40", 5200, 40, SpectrumBand.ISM_5GHZ),
            Channel("ch44", 5220, 40, SpectrumBand.ISM_5GHZ),
            Channel("cbrs1", 3550, 10, SpectrumBand.CBRS),
            Channel("cbrs2", 3560, 10, SpectrumBand.CBRS),
            Channel("tvws1", 600, 6, SpectrumBand.TVWS),
            Channel("tvws2", 606, 6, SpectrumBand.TVWS),
        ]
        for ch in channels:
            self._channels[ch.channel_id] = ch

    def sense_channel(self, channel_id: str, timestamp: float) -> float:
        """Energy detection based spectrum sensing. Returns detected energy level."""
        ch = self._channels.get(channel_id)
        if not ch:
            return 0.0

        ch.status = ChannelStatus.SENSING
        ch.last_sensed = timestamp

        # Simulate primary user activity
        noise = self._rng.normal(0, 3)  # noise in dB
        if ch.primary_user_active:
            energy = -60.0 + noise  # strong primary user signal
        else:
            energy = self.NOISE_FLOOR_DBM + noise

        ch.snr_db = energy - self.NOISE_FLOOR_DBM
        self._sensing_history.setdefault(channel_id, []).append(energy)

        if energy > -80:  # detection threshold
            ch.status = ChannelStatus.OCCUPIED
        else:
            ch.status = ChannelStatus.IDLE

        return float(energy)

    def sense_all(self, timestamp: float) -> Dict[str, float]:
        """Sense all channels."""
        return {ch_id: self.sense_channel(ch_id, timestamp)
                for ch_id in self._channels}

    def detect_spectrum_holes(self, timestamp: float) -> List[SpectrumHole]:
        """Find available spectrum holes."""
        holes = []
        for ch in self._channels.values():
            if ch.status == ChannelStatus.IDLE:
                # Predict availability based on sensing history
                history = self._sensing_history.get(ch.channel_id, [])
                if len(history) >= 3:
                    idle_ratio = sum(1 for e in history[-10:] if e < -80) / min(len(history), 10)
                else:
                    idle_ratio = 0.5

                capacity = ch.bandwidth_mhz * np.log2(1 + 10 ** (ch.snr_db / 10))
                holes.append(SpectrumHole(
                    channel_id=ch.channel_id,
                    start_time=timestamp,
                    duration_sec=idle_ratio * 10.0,  # predicted duration
                    predicted_availability=round(idle_ratio, 4),
                    capacity_mbps=round(float(capacity), 2),
                ))
        self._spectrum_holes = holes
        return holes

    def allocate_channel(self, drone_id: str, timestamp: float,
                         preferred_band: Optional[SpectrumBand] = None) -> Optional[SpectrumAllocation]:
        """Allocate best available channel to drone."""
        holes = self.detect_spectrum_holes(timestamp)
        if preferred_band:
            holes = [h for h in holes
                     if self._channels[h.channel_id].band == preferred_band] or holes

        if not holes:
            return None

        # Select best hole (highest capacity * availability)
        best = max(holes, key=lambda h: h.capacity_mbps * h.predicted_availability)
        ch = self._channels[best.channel_id]
        ch.status = ChannelStatus.TRANSMITTING

        alloc = SpectrumAllocation(
            drone_id=drone_id, channel_id=best.channel_id,
            start_time=timestamp, duration_sec=best.duration_sec,
            tx_power_dbm=20.0, data_rate_mbps=best.capacity_mbps,
        )
        self._allocations[drone_id] = alloc
        return alloc

    def release_channel(self, drone_id: str):
        alloc = self._allocations.pop(drone_id, None)
        if alloc:
            ch = self._channels.get(alloc.channel_id)
            if ch:
                ch.status = ChannelStatus.IDLE

    def set_primary_user(self, channel_id: str, active: bool):
        ch = self._channels.get(channel_id)
        if ch:
            ch.primary_user_active = active
            if active:
                ch.status = ChannelStatus.OCCUPIED
                # Evict secondary users
                for drone_id, alloc in list(self._allocations.items()):
                    if alloc.channel_id == channel_id:
                        self.release_channel(drone_id)

    def get_allocation(self, drone_id: str) -> Optional[SpectrumAllocation]:
        return self._allocations.get(drone_id)

    def summary(self) -> dict:
        idle = sum(1 for ch in self._channels.values() if ch.status == ChannelStatus.IDLE)
        return {
            "total_channels": len(self._channels),
            "idle_channels": idle,
            "active_allocations": len(self._allocations),
            "spectrum_holes": len(self._spectrum_holes),
            "sensing_events": sum(len(h) for h in self._sensing_history.values()),
        }
