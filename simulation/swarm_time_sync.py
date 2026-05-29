"""Phase 696: 다중 기체 스웜 프레임 시간 동기화 (PTP / NTP, <10ms jitter)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np


class SyncProtocol(Enum):
    """시간 동기화 프로토콜."""
    PTP = "ptp_ieee1588"
    NTP = "ntp"


class ClockState(Enum):
    """클록 동기화 상태."""
    UNSYNCHRONIZED = "unsynchronized"
    SYNCING = "syncing"
    LOCKED = "locked"
    HOLDOVER = "holdover"


@dataclass
class ClockNode:
    """클록 노드 (마스터 또는 슬레이브)."""
    node_id: str
    is_master: bool = False
    offset_us: float = 0.0
    drift_us_per_s: float = 0.0
    state: ClockState = ClockState.UNSYNCHRONIZED
    last_sync: float = 0.0
    sync_count: int = 0
    jitter_us: float = 0.0


@dataclass
class SyncMessage:
    """PTP / NTP 동기화 메시지."""
    src: str
    dst: str
    t1: float
    t2: float | None = None
    t3: float | None = None
    t4: float | None = None

    @property
    def offset_us(self) -> float:
        if self.t2 is None or self.t3 is None or self.t4 is None:
            return 0.0
        return ((self.t2 - self.t1) - (self.t4 - self.t3)) / 2 * 1e6

    @property
    def delay_us(self) -> float:
        if self.t2 is None or self.t3 is None or self.t4 is None:
            return 0.0
        return ((self.t4 - self.t1) - (self.t3 - self.t2)) * 1e6


JITTER_TARGET_US = 10_000.0
SYNC_INTERVAL_S = 0.125
HOLDOVER_TIMEOUT_S = 5.0


class SwarmTimeSync:
    """스웜 PTP/NTP 시간 동기화 시뮬레이터."""

    def __init__(
        self,
        protocol: SyncProtocol = SyncProtocol.PTP,
        network_delay_us: float = 500.0,
        seed: int = 42,
    ) -> None:
        self.protocol = protocol
        self.network_delay_us = network_delay_us
        self.rng = np.random.default_rng(seed)
        self._nodes: dict[str, ClockNode] = {}
        self._master_id: str | None = None
        self._sync_log: list[SyncMessage] = []

    def add_node(self, node_id: str, is_master: bool = False) -> ClockNode:
        """노드 등록."""
        initial_offset = float(self.rng.normal(0, 5000)) if not is_master else 0.0
        node = ClockNode(
            node_id=node_id,
            is_master=is_master,
            offset_us=initial_offset,
            drift_us_per_s=float(self.rng.normal(0, 0.5)),
        )
        self._nodes[node_id] = node
        if is_master:
            self._master_id = node_id
            node.state = ClockState.LOCKED
        return node

    def elect_master(self) -> str | None:
        """최소 오프셋 노드를 마스터로 선출 (BMCA 단순화)."""
        if not self._nodes:
            return None
        master = min(self._nodes.values(), key=lambda n: abs(n.offset_us))
        master.is_master = True
        master.state = ClockState.LOCKED
        if self._master_id and self._master_id in self._nodes:
            self._nodes[self._master_id].is_master = False
        self._master_id = master.node_id
        return master.node_id

    def sync_step(self, slave_id: str) -> SyncMessage | None:
        """슬레이브 노드 1회 동기화 스텝."""
        if self._master_id is None or slave_id == self._master_id:
            return None
        slave = self._nodes.get(slave_id)
        master = self._nodes.get(self._master_id)
        if slave is None or master is None:
            return None

        now = time.time()
        net_jitter = float(self.rng.normal(0, self.network_delay_us * 0.1)) * 1e-6

        t1 = now
        t2 = t1 + self.network_delay_us * 1e-6 + net_jitter + slave.offset_us * 1e-6
        t3 = t2 + float(self.rng.uniform(50, 200)) * 1e-6
        t4 = t3 + self.network_delay_us * 1e-6 + net_jitter

        msg = SyncMessage(src=self._master_id, dst=slave_id, t1=t1, t2=t2, t3=t3, t4=t4)
        self._sync_log.append(msg)

        alpha = 0.125
        slave.offset_us = (1 - alpha) * slave.offset_us + alpha * msg.offset_us
        slave.jitter_us = abs(msg.offset_us)
        slave.sync_count += 1
        slave.last_sync = now

        if abs(slave.offset_us) <= JITTER_TARGET_US:
            slave.state = ClockState.LOCKED
        else:
            slave.state = ClockState.SYNCING

        return msg

    def sync_all(self, steps: int = 1) -> dict[str, float]:
        """전체 슬레이브 노드 일괄 동기화."""
        if self._master_id is None:
            self.elect_master()
        for _ in range(steps):
            for node_id in list(self._nodes):
                if node_id != self._master_id:
                    self.sync_step(node_id)
        return {nid: n.offset_us for nid, n in self._nodes.items()}

    def check_jitter_compliance(self) -> dict[str, Any]:
        """jitter <10ms 준수 여부 검증."""
        compliant_count = sum(
            1 for n in self._nodes.values()
            if abs(n.offset_us) <= JITTER_TARGET_US
        )
        return {
            "total_nodes": len(self._nodes),
            "compliant_nodes": compliant_count,
            "compliant_ratio": compliant_count / max(len(self._nodes), 1),
            "max_offset_us": max((abs(n.offset_us) for n in self._nodes.values()), default=0.0),
            "target_us": JITTER_TARGET_US,
            "all_compliant": compliant_count == len(self._nodes),
        }

    def get_node_status(self) -> list[dict[str, Any]]:
        return [
            {
                "node_id": n.node_id,
                "master": n.is_master,
                "state": n.state.value,
                "offset_us": round(n.offset_us, 2),
                "jitter_us": round(n.jitter_us, 2),
                "sync_count": n.sync_count,
            }
            for n in self._nodes.values()
        ]
