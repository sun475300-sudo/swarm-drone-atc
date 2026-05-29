"""P696: 스웜 프레임 시간 동기화 — NTP-스타일 오프셋 보정 (<10ms jitter 목표).

실제 IEEE 1588 PTP가 아닌 시뮬레이션 목적의 오프셋-보정 모델.
각 드론은 마스터 기준 시계 대비 고정 오프셋 + 가우시안 지터를 갖고,
동기화 루프를 통해 오프셋을 추정·보정.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

SYNC_JITTER_TARGET_MS = 10.0   # 목표 jitter 상한 (ms)
DEFAULT_ALPHA = 0.125           # NTP 가중 평균 계수 (1/8)
DEFAULT_BETA = 0.25             # NTP 분산 업데이트 계수


@dataclass
class ClockState:
    """드론 단일 시계 상태."""
    drone_id: str
    offset_sec: float = 0.0     # 마스터 대비 오프셋 (초)
    jitter_sec: float = 0.0     # 현재 추정 jitter (초)
    stratum: int = 2            # NTP stratum (마스터=1)
    sync_count: int = 0

    @property
    def offset_ms(self) -> float:
        return self.offset_sec * 1000.0

    @property
    def jitter_ms(self) -> float:
        return self.jitter_sec * 1000.0

    @property
    def is_synced(self) -> bool:
        """jitter가 목표 이하이면 동기화 완료."""
        return self.jitter_ms <= SYNC_JITTER_TARGET_MS


@dataclass
class SyncPacket:
    """마스터 → 드론 동기화 패킷 (NTP Reference Timestamp 모델)."""
    master_tx: float        # 마스터 송신 시간
    client_rx: float        # 클라이언트 수신 시간
    client_tx: float        # 클라이언트 응답 송신 시간
    master_rx: float        # 마스터 응답 수신 시간

    @property
    def offset(self) -> float:
        """4-타임스탬프 오프셋 계산 (NTP 공식)."""
        return ((self.client_rx - self.master_tx) + (self.client_tx - self.master_rx)) / 2.0

    @property
    def delay(self) -> float:
        """왕복 지연 시간."""
        return (self.master_rx - self.master_tx) - (self.client_tx - self.client_rx)


class SwarmTimeSyncManager:
    """군집 시간 동기화 관리자.

    rng를 주입받아 재현 가능한 jitter 시뮬레이션.
    """

    def __init__(self, rng: np.random.Generator | None = None) -> None:
        self._rng = rng if rng is not None else np.random.default_rng(0)
        self._clocks: dict[str, ClockState] = {}
        self._master_time: float = 0.0

    def register_drone(self, drone_id: str, initial_offset_ms: float = 0.0) -> ClockState:
        """드론 등록 (초기 오프셋 설정)."""
        state = ClockState(drone_id=drone_id, offset_sec=initial_offset_ms / 1000.0)
        self._clocks[drone_id] = state
        return state

    def step_master(self, dt: float) -> None:
        """마스터 시계 진행."""
        self._master_time += dt

    def simulate_sync_round(self, drone_id: str, network_delay_ms: float = 1.0) -> SyncPacket:
        """동기화 라운드 시뮬레이션 — 네트워크 지연 포함."""
        clock = self._clocks[drone_id]
        jitter = self._rng.normal(0, network_delay_ms / 1000.0)
        master_tx = self._master_time
        client_rx = master_tx + network_delay_ms / 1000.0 + jitter + clock.offset_sec
        client_tx = client_rx + 0.001   # 처리 시간 1ms
        master_rx = client_tx + network_delay_ms / 1000.0 + jitter

        pkt = SyncPacket(master_tx, client_rx, client_tx, master_rx)
        self._apply_sync(clock, pkt)
        return pkt

    def _apply_sync(self, clock: ClockState, pkt: SyncPacket) -> None:
        """NTP-스타일 오프셋 필터 업데이트."""
        measured_offset = pkt.offset
        # 이동 평균으로 오프셋 보정
        clock.offset_sec = (1 - DEFAULT_ALPHA) * clock.offset_sec + DEFAULT_ALPHA * measured_offset
        new_jitter = abs(measured_offset - clock.offset_sec)
        clock.jitter_sec = (1 - DEFAULT_BETA) * clock.jitter_sec + DEFAULT_BETA * new_jitter
        clock.sync_count += 1

    def get_clock(self, drone_id: str) -> ClockState | None:
        return self._clocks.get(drone_id)

    def all_synced(self) -> bool:
        return all(c.is_synced for c in self._clocks.values())

    def summary(self) -> dict[str, Any]:
        return {
            did: {
                "offset_ms": round(c.offset_ms, 3),
                "jitter_ms": round(c.jitter_ms, 3),
                "synced": c.is_synced,
                "sync_count": c.sync_count,
            }
            for did, c in self._clocks.items()
        }
