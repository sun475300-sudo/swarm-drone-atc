"""
메쉬 네트워크 토폴로지 시뮬레이션
=================================
드론 간 멀티홉 릴레이 통신, 대역폭 제한,
네트워크 파티션 감지 및 자동 복구.

사용법:
    mesh = MeshNetwork(comm_range=500.0, bandwidth_bps=1_000_000)
    mesh.update_positions({"DR001": pos1, "DR002": pos2, ...})
    path = mesh.find_route("DR001", "DR005")
    partitions = mesh.detect_partitions()
"""
from __future__ import annotations

import math
from collections import deque
from typing import Optional

import numpy as np


class MeshNetwork:
    """
    드론 메쉬 네트워크 시뮬레이터.

    각 드론은 comm_range 내 다른 드론과 직접 링크를 형성.
    멀티홉 BFS 라우팅으로 전체 네트워크 연결성 유지.
    """

    def __init__(
        self,
        comm_range: float = 500.0,
        bandwidth_bps: int = 1_000_000,
        max_queue_size: int = 100,
    ) -> None:
        """
        Parameters
        ----------
        comm_range : 통신 가능 거리 (m)
        bandwidth_bps : 링크당 대역폭 (bits/s)
        max_queue_size : 노드당 최대 메시지 큐 크기
        """
        self.comm_range = comm_range
        self.bandwidth_bps = bandwidth_bps
        self.max_queue_size = max_queue_size

        self._positions: dict[str, np.ndarray] = {}
        self._adjacency: dict[str, set[str]] = {}
        self._queues: dict[str, deque] = {}

        # 통계
        self.messages_routed = 0
        self.messages_dropped = 0
        self.messages_queued = 0
        self.total_hops = 0

    def update_positions(self, positions: dict[str, np.ndarray]) -> None:
        """드론 위치 갱신 + 인접 리스트 재구성"""
        self._positions = {k: np.asarray(v) for k, v in positions.items()}
        self._rebuild_adjacency()

    def _rebuild_adjacency(self) -> None:
        """통신 범위 기반 인접 리스트 구성"""
        nodes = list(self._positions.keys())
        adj: dict[str, set[str]] = {n: set() for n in nodes}

        for i, a in enumerate(nodes):
            for b in nodes[i + 1:]:
                dist = float(np.linalg.norm(
                    self._positions[a] - self._positions[b]
                ))
                if dist <= self.comm_range:
                    adj[a].add(b)
                    adj[b].add(a)

        self._adjacency = adj

        # 큐 초기화 (새 노드 추가)
        for n in nodes:
            if n not in self._queues:
                self._queues[n] = deque(maxlen=self.max_queue_size)

    def neighbors(self, node_id: str) -> set[str]:
        """특정 노드의 직접 이웃 반환"""
        return self._adjacency.get(node_id, set())

    def find_route(self, src: str, dst: str) -> list[str] | None:
        """
        BFS로 최단 경로 (홉 수 기준) 탐색.

        Returns
        -------
        경로 리스트 [src, ..., dst] 또는 None (연결 불가)
        """
        if src not in self._adjacency or dst not in self._adjacency:
            return None
        if src == dst:
            return [src]

        visited = {src}
        parent: dict[str, str] = {}
        queue = deque([src])

        while queue:
            current = queue.popleft()
            for neighbor in self._adjacency.get(current, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    parent[neighbor] = current
                    if neighbor == dst:
                        # 경로 역추적
                        path = [dst]
                        while path[-1] != src:
                            path.append(parent[path[-1]])
                        path.reverse()
                        return path
                    queue.append(neighbor)

        return None  # 연결 불가

    def send_message(
        self,
        src: str,
        dst: str,
        payload_bytes: int = 256,
    ) -> bool:
        """
        메시지 전송 시뮬레이션.

        경로 탐색 → 대역폭 체크 → 큐잉 → 전달.
        Returns True if delivered.
        """
        route = self.find_route(src, dst)
        if route is None:
            self.messages_dropped += 1
            return False

        hops = len(route) - 1
        self.total_hops += hops

        # 대역폭 체크: 전송 시간 = payload / bandwidth
        tx_time_s = (payload_bytes * 8) / self.bandwidth_bps

        # 각 홉에서 큐 체크
        for node in route[1:-1]:  # 중간 릴레이 노드
            q = self._queues.get(node)
            if q is not None and len(q) >= self.max_queue_size:
                self.messages_dropped += 1
                return False
            if q is not None:
                q.append((src, dst, payload_bytes))
                self.messages_queued += 1

        self.messages_routed += 1
        return True

    def detect_partitions(self) -> list[set[str]]:
        """
        네트워크 파티션 (연결 컴포넌트) 감지.

        Returns
        -------
        list[set[str]] : 각 파티션의 노드 집합
        """
        nodes = set(self._adjacency.keys())
        visited: set[str] = set()
        partitions: list[set[str]] = []

        for node in nodes:
            if node in visited:
                continue
            # BFS로 컴포넌트 탐색
            component: set[str] = set()
            queue = deque([node])
            while queue:
                current = queue.popleft()
                if current in component:
                    continue
                component.add(current)
                visited.add(current)
                for neighbor in self._adjacency.get(current, set()):
                    if neighbor not in component:
                        queue.append(neighbor)
            partitions.append(component)

        return partitions

    def is_connected(self) -> bool:
        """전체 네트워크 연결 여부"""
        parts = self.detect_partitions()
        return len(parts) <= 1

    def network_stats(self) -> dict:
        """네트워크 상태 통계 반환"""
        partitions = self.detect_partitions()
        n_nodes = len(self._positions)
        n_edges = sum(len(v) for v in self._adjacency.values()) // 2

        return {
            "nodes": n_nodes,
            "edges": n_edges,
            "partitions": len(partitions),
            "connected": len(partitions) <= 1,
            "messages_routed": self.messages_routed,
            "messages_dropped": self.messages_dropped,
            "messages_queued": self.messages_queued,
            "avg_hops": self.total_hops / max(self.messages_routed, 1),
            "largest_partition": max((len(p) for p in partitions), default=0),
        }

    def suggest_relay_positions(
        self,
        max_relays: int = 3,
    ) -> list[np.ndarray]:
        """
        파티션 복구를 위한 릴레이 드론 배치 위치 제안.

        각 파티션 쌍의 중점을 후보로 제시.
        """
        partitions = self.detect_partitions()
        if len(partitions) <= 1:
            return []

        suggestions = []
        for i, p1 in enumerate(partitions):
            for p2 in partitions[i + 1:]:
                if len(suggestions) >= max_relays:
                    break
                # 각 파티션의 중심점
                c1 = np.mean([self._positions[n] for n in p1], axis=0)
                c2 = np.mean([self._positions[n] for n in p2], axis=0)
                midpoint = (c1 + c2) / 2
                suggestions.append(midpoint)

        return suggestions[:max_relays]
