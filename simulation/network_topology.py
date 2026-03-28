"""
네트워크 토폴로지
=================
통신 그래프 분석 + 중심성 + 취약 노드 감지.

사용법:
    nt = NetworkTopology()
    nt.update_links(positions, comm_range=300)
    central = nt.most_central()
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class NodeInfo:
    """노드 정보"""
    node_id: str
    degree: int
    betweenness: float
    is_bridge: bool
    cluster_id: int = -1


class NetworkTopology:
    """통신 네트워크 토폴로지 분석."""

    def __init__(self, comm_range: float = 300.0) -> None:
        self._comm_range = comm_range
        self._nodes: set[str] = set()
        self._edges: dict[str, set[str]] = {}

    def update_links(
        self,
        positions: dict[str, tuple[float, float, float]],
        comm_range: float | None = None,
    ) -> None:
        """위치 기반 통신 링크 갱신"""
        rng = comm_range or self._comm_range
        self._nodes = set(positions.keys())
        self._edges = {n: set() for n in self._nodes}

        ids = list(positions.keys())
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                dist = float(np.linalg.norm(
                    np.array(positions[ids[i]]) - np.array(positions[ids[j]])
                ))
                if dist <= rng:
                    self._edges[ids[i]].add(ids[j])
                    self._edges[ids[j]].add(ids[i])

    def degree(self, node_id: str) -> int:
        return len(self._edges.get(node_id, set()))

    def neighbors(self, node_id: str) -> set[str]:
        return self._edges.get(node_id, set())

    def is_connected(self) -> bool:
        """그래프 연결 여부"""
        if not self._nodes:
            return True
        visited = set()
        queue = [next(iter(self._nodes))]
        while queue:
            node = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            queue.extend(self._edges.get(node, set()) - visited)
        return len(visited) == len(self._nodes)

    def connected_components(self) -> list[set[str]]:
        """연결 컴포넌트"""
        visited: set[str] = set()
        components = []
        for node in self._nodes:
            if node in visited:
                continue
            component: set[str] = set()
            queue = [node]
            while queue:
                n = queue.pop(0)
                if n in component:
                    continue
                component.add(n)
                queue.extend(self._edges.get(n, set()) - component)
            visited |= component
            components.append(component)
        return components

    def bridges(self) -> list[tuple[str, str]]:
        """브릿지 엣지 (제거 시 분리되는 엣지)"""
        bridge_list = []
        original_components = len(self.connected_components())

        for node in self._nodes:
            for neighbor in list(self._edges.get(node, set())):
                if neighbor > node:  # 중복 방지
                    # 엣지 제거
                    self._edges[node].discard(neighbor)
                    self._edges[neighbor].discard(node)

                    if len(self.connected_components()) > original_components:
                        bridge_list.append((node, neighbor))

                    # 복원
                    self._edges[node].add(neighbor)
                    self._edges[neighbor].add(node)

        return bridge_list

    def most_central(self, top_n: int = 3) -> list[str]:
        """차수 중심성 기준 상위 노드"""
        if not self._nodes:
            return []
        ranked = sorted(self._nodes, key=lambda n: self.degree(n), reverse=True)
        return ranked[:top_n]

    def vulnerable_nodes(self) -> list[str]:
        """제거 시 네트워크 분리되는 노드"""
        vulnerable = []
        for node in self._nodes:
            # 노드 제거 시뮬레이션
            saved_edges = self._edges.pop(node, set())
            for n in saved_edges:
                self._edges.get(n, set()).discard(node)
            self._nodes.discard(node)

            if not self.is_connected() and len(self._nodes) > 0:
                vulnerable.append(node)

            # 복원
            self._nodes.add(node)
            self._edges[node] = saved_edges
            for n in saved_edges:
                self._edges.setdefault(n, set()).add(node)

        return vulnerable

    def density(self) -> float:
        """그래프 밀도"""
        n = len(self._nodes)
        if n <= 1:
            return 0.0
        max_edges = n * (n - 1) / 2
        actual = sum(len(e) for e in self._edges.values()) / 2
        return actual / max_edges

    def summary(self) -> dict[str, Any]:
        components = self.connected_components()
        return {
            "nodes": len(self._nodes),
            "edges": sum(len(e) for e in self._edges.values()) // 2,
            "connected": self.is_connected(),
            "components": len(components),
            "density": round(self.density(), 3),
            "avg_degree": round(
                sum(self.degree(n) for n in self._nodes) / max(len(self._nodes), 1), 1
            ),
        }
