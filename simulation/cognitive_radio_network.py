# Phase 539: Cognitive Radio Network — Dynamic Spectrum Access
"""
인지 무선 네트워크: 동적 주파수 할당, 스펙트럼 센싱,
주 사용자 보호 및 기회적 접근 스케줄링.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum


class ChannelState(Enum):
    IDLE = "idle"
    OCCUPIED_PRIMARY = "occupied_primary"
    OCCUPIED_SECONDARY = "occupied_secondary"


class SensingMethod(Enum):
    ENERGY_DETECTION = "energy"
    MATCHED_FILTER = "matched_filter"
    CYCLOSTATIONARY = "cyclostationary"


@dataclass
class Channel:
    channel_id: int
    freq_mhz: float
    bandwidth_mhz: float
    state: ChannelState = ChannelState.IDLE
    noise_floor_dbm: float = -100.0
    primary_activity: float = 0.0  # 주 사용자 점유 확률


@dataclass
class SecondaryUser:
    su_id: str
    assigned_channel: int = -1
    throughput_mbps: float = 0.0
    handoffs: int = 0
    collisions: int = 0


@dataclass
class SpectrumSensingResult:
    channel_id: int
    detected_power_dbm: float
    is_primary_present: bool
    confidence: float
    method: SensingMethod


class SpectrumSensor:
    """스펙트럼 센싱 엔진."""

    def __init__(self, seed=42):
        self.rng = np.random.default_rng(seed)

    def energy_detect(self, channel: Channel, threshold_dbm=-90.0) -> SpectrumSensingResult:
        if channel.state == ChannelState.OCCUPIED_PRIMARY:
            power = channel.noise_floor_dbm + 20 + self.rng.normal(0, 3)
        else:
            power = channel.noise_floor_dbm + self.rng.normal(0, 5)
        detected = power > threshold_dbm
        conf = min(0.99, 0.5 + abs(power - threshold_dbm) / 30.0)
        return SpectrumSensingResult(
            channel.channel_id, float(power), detected, conf, SensingMethod.ENERGY_DETECTION
        )

    def cooperative_sense(self, results: list[SpectrumSensingResult]) -> bool:
        """협력 센싱: OR 규칙."""
        return any(r.is_primary_present for r in results)


class ChannelAllocator:
    """동적 채널 할당."""

    def __init__(self, seed=42):
        self.rng = np.random.default_rng(seed)

    def allocate(self, channels: list[Channel], users: list[SecondaryUser],
                 sensing_results: dict[int, SpectrumSensingResult]):
        idle_channels = [
            ch for ch in channels
            if not sensing_results.get(ch.channel_id, SpectrumSensingResult(0, 0, True, 0, SensingMethod.ENERGY_DETECTION)).is_primary_present
        ]
        idle_channels.sort(key=lambda c: c.noise_floor_dbm)

        for user in users:
            if idle_channels:
                ch = idle_channels.pop(0)
                if user.assigned_channel != ch.channel_id:
                    if user.assigned_channel >= 0:
                        user.handoffs += 1
                    user.assigned_channel = ch.channel_id
                    ch.state = ChannelState.OCCUPIED_SECONDARY
                # 처리량 계산 (Shannon)
                snr_linear = 10 ** ((ch.noise_floor_dbm + 20 - ch.noise_floor_dbm) / 10.0)
                user.throughput_mbps = ch.bandwidth_mhz * np.log2(1 + snr_linear)
            else:
                user.assigned_channel = -1
                user.throughput_mbps = 0.0


class CognitiveRadioNetwork:
    """인지 무선 네트워크 시뮬레이션."""

    def __init__(self, n_channels=16, n_users=10, seed=42):
        self.rng = np.random.default_rng(seed)
        self.sensor = SpectrumSensor(seed)
        self.allocator = ChannelAllocator(seed)
        self.channels: list[Channel] = []
        self.users: list[SecondaryUser] = []
        self.collisions = 0
        self.time_step = 0

        for i in range(n_channels):
            self.channels.append(Channel(
                i, 900.0 + i * 5.0, 5.0,
                noise_floor_dbm=-100 + self.rng.normal(0, 3),
                primary_activity=self.rng.uniform(0.1, 0.6),
            ))

        for i in range(n_users):
            self.users.append(SecondaryUser(f"SU-{i:03d}"))

    def step(self):
        """한 타임슬롯 진행."""
        self.time_step += 1

        # 주 사용자 활동 업데이트
        for ch in self.channels:
            if self.rng.random() < ch.primary_activity:
                ch.state = ChannelState.OCCUPIED_PRIMARY
            elif ch.state == ChannelState.OCCUPIED_PRIMARY:
                ch.state = ChannelState.IDLE

        # 스펙트럼 센싱
        sensing = {}
        for ch in self.channels:
            sensing[ch.channel_id] = self.sensor.energy_detect(ch)

        # 채널 할당
        self.allocator.allocate(self.channels, self.users, sensing)

        # 충돌 체크: 2차 사용자가 주 사용자 채널에 할당됨
        for user in self.users:
            if user.assigned_channel >= 0:
                ch = self.channels[user.assigned_channel]
                if ch.state == ChannelState.OCCUPIED_PRIMARY:
                    user.collisions += 1
                    self.collisions += 1

    def run(self, steps=50):
        for _ in range(steps):
            self.step()

    def summary(self):
        active = sum(1 for u in self.users if u.assigned_channel >= 0)
        avg_tp = float(np.mean([u.throughput_mbps for u in self.users]))
        total_ho = sum(u.handoffs for u in self.users)
        return {
            "channels": len(self.channels),
            "users": len(self.users),
            "active_users": active,
            "avg_throughput_mbps": round(avg_tp, 2),
            "total_handoffs": total_ho,
            "collisions": self.collisions,
            "time_steps": self.time_step,
        }


if __name__ == "__main__":
    crn = CognitiveRadioNetwork(16, 10, 42)
    crn.run(50)
    s = crn.summary()
    for k, v in s.items():
        print(f"  {k}: {v}")
