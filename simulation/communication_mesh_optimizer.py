"""Phase 289: Communication Mesh Optimizer — 통신 메시 최적화.

자가 치유 메시 네트워크 토폴로지 최적화, 중계 드론 배치,
링크 품질 기반 라우팅, 대역폭 할당 최적화.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
import heapq


class LinkQuality(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    DISCONNECTED = "disconnected"


@dataclass
class MeshNode:
    node_id: str
    position: np.ndarray
    is_relay: bool = False
    tx_power_dbm: float = 20.0
    bandwidth_mbps: float = 10.0
    neighbors: Set[str] = field(default_factory=set)
    load: float = 0.0  # 0-1


@dataclass
class MeshLink:
    node_a: str
    node_b: str
    distance_m: float
    rssi_dbm: float
    quality: LinkQuality
    throughput_mbps: float
    latency_ms: float


class PathLossModel:
    """전파 경로 손실 모델 (Free-space + 장애물)."""

    FREQ_GHZ = 2.4
    SPEED_OF_LIGHT = 3e8

    @classmethod
    def free_space_loss(cls, distance_m: float) -> float:
        if distance_m <= 0:
            return 0.0
        wavelength = cls.SPEED_OF_LIGHT / (cls.FREQ_GHZ * 1e9)
        return 20 * np.log10(4 * np.pi * distance_m / wavelength)

    @classmethod
    def rssi(cls, tx_power_dbm: float, distance_m: float, obstacle_loss_db: float = 0.0) -> float:
        return tx_power_dbm - cls.free_space_loss(distance_m) - obstacle_loss_db

    @classmethod
    def quality_from_rssi(cls, rssi_dbm: float) -> LinkQuality:
        if rssi_dbm > -50:
            return LinkQuality.EXCELLENT
        elif rssi_dbm > -70:
            return LinkQuality.GOOD
        elif rssi_dbm > -80:
            return LinkQuality.FAIR
        elif rssi_dbm > -90:
            return LinkQuality.POOR
        return LinkQuality.DISCONNECTED

    @classmethod
    def throughput(cls, rssi_dbm: float, bandwidth_mbps: float = 10.0) -> float:
        if rssi_dbm < -90:
            return 0.0
        snr = rssi_dbm + 90  # simplified SNR
        efficiency = min(1.0, max(0.1, snr / 40.0))
        return bandwidth_mbps * efficiency


class CommunicationMeshOptimizer:
    """통신 메시 최적화기.

    - 노드 간 링크 품질 분석
    - Dijkstra 기반 최적 경로 라우팅
    - 중계 드론 최적 배치
    - 자가 치유 토폴로지 관리
    """

    MAX_RANGE_M = 500.0

    def __init__(self, rng_seed: int = 42):
        self._rng = np.random.default_rng(rng_seed)
        self._nodes: Dict[str, MeshNode] = {}
        self._links: Dict[Tuple[str, str], MeshLink] = {}
        self._path_loss = PathLossModel()
        self._routing_table: Dict[Tuple[str, str], List[str]] = {}
        self._history: List[dict] = []

    def add_node(self, node: MeshNode):
        self._nodes[node.node_id] = node

    def remove_node(self, node_id: str) -> bool:
        if node_id not in self._nodes:
            return False
        # Remove links
        for nid in list(self._nodes[node_id].neighbors):
            key = tuple(sorted([node_id, nid]))
            self._links.pop(key, None)
            if nid in self._nodes:
                self._nodes[nid].neighbors.discard(node_id)
        del self._nodes[node_id]
        return True

    def update_topology(self):
        """전체 토폴로지 갱신: 링크 품질 재계산."""
        self._links.clear()
        node_ids = list(self._nodes.keys())
        for i in range(len(node_ids)):
            self._nodes[node_ids[i]].neighbors.clear()
            for j in range(i + 1, len(node_ids)):
                na = self._nodes[node_ids[i]]
                nb = self._nodes[node_ids[j]]
                dist = np.linalg.norm(na.position - nb.position)
                if dist > self.MAX_RANGE_M:
                    continue
                rssi = self._path_loss.rssi(na.tx_power_dbm, dist)
                quality = self._path_loss.quality_from_rssi(rssi)
                if quality == LinkQuality.DISCONNECTED:
                    continue
                throughput = self._path_loss.throughput(rssi, min(na.bandwidth_mbps, nb.bandwidth_mbps))
                latency = dist / 3e8 * 1000 + 1.0  # propagation + processing
                link = MeshLink(
                    node_a=node_ids[i], node_b=node_ids[j], distance_m=dist,
                    rssi_dbm=rssi, quality=quality, throughput_mbps=throughput, latency_ms=latency,
                )
                key = tuple(sorted([node_ids[i], node_ids[j]]))
                self._links[key] = link
                na.neighbors.add(node_ids[j])
                nb.neighbors.add(node_ids[i])

    def find_route(self, src: str, dst: str) -> List[str]:
        """Dijkstra 기반 최소 지연 경로."""
        if src not in self._nodes or dst not in self._nodes:
            return []
        dist = {src: 0.0}
        prev: Dict[str, Optional[str]] = {src: None}
        pq = [(0.0, src)]
        while pq:
            d, u = heapq.heappop(pq)
            if u == dst:
                path = []
                node = dst
                while node:
                    path.append(node)
                    node = prev.get(node)
                return list(reversed(path))
            if d > dist.get(u, float("inf")):
                continue
            for nb in self._nodes[u].neighbors:
                key = tuple(sorted([u, nb]))
                link = self._links.get(key)
                if not link:
                    continue
                nd = d + link.latency_ms
                if nd < dist.get(nb, float("inf")):
                    dist[nb] = nd
                    prev[nb] = u
                    heapq.heappush(pq, (nd, nb))
        return []

    def find_relay_positions(self, disconnected_nodes: List[str]) -> List[np.ndarray]:
        """단절 노드 연결을 위한 중계 위치 계산."""
        relay_positions = []
        connected = set(self._nodes.keys()) - set(disconnected_nodes)
        for dn_id in disconnected_nodes:
            dn = self._nodes.get(dn_id)
            if not dn:
                continue
            best_pos = None
            best_dist = float("inf")
            for cn_id in connected:
                cn = self._nodes[cn_id]
                mid = (dn.position + cn.position) / 2
                d = np.linalg.norm(dn.position - cn.position)
                if d < best_dist:
                    best_dist = d
                    best_pos = mid
            if best_pos is not None:
                relay_positions.append(best_pos)
        return relay_positions

    def get_network_connectivity(self) -> float:
        """네트워크 연결성 비율 (0-1)."""
        if len(self._nodes) <= 1:
            return 1.0
        # BFS from first node
        start = next(iter(self._nodes))
        visited = {start}
        queue = [start]
        while queue:
            current = queue.pop(0)
            for nb in self._nodes[current].neighbors:
                if nb not in visited:
                    visited.add(nb)
                    queue.append(nb)
        return len(visited) / len(self._nodes)

    def get_link(self, a: str, b: str) -> Optional[MeshLink]:
        key = tuple(sorted([a, b]))
        return self._links.get(key)

    def summary(self) -> dict:
        quality_counts = {}
        for link in self._links.values():
            quality_counts[link.quality.value] = quality_counts.get(link.quality.value, 0) + 1
        avg_throughput = np.mean([l.throughput_mbps for l in self._links.values()]) if self._links else 0
        return {
            "total_nodes": len(self._nodes),
            "relay_nodes": sum(1 for n in self._nodes.values() if n.is_relay),
            "total_links": len(self._links),
            "link_quality": quality_counts,
            "connectivity": round(self.get_network_connectivity(), 3),
            "avg_throughput_mbps": round(float(avg_throughput), 2),
        }
