"""
Phase 450: Network Topology Manager for Mesh Networks
"""

import time
from dataclasses import dataclass

import numpy as np


@dataclass
class NetworkNode:
    """``NetworkNode`` 관련 기능을 제공한다."""
    node_id: str
    position: np.ndarray
    neighbors: set[str]
    bandwidth_mbps: float
    latency_ms: float


class NetworkTopologyManager:
    """``NetworkTopologyManager`` 역할을 담당한다."""
    def __init__(self, max_neighbors: int = 10):
        """인스턴스를 초기화한다."""
        self.nodes: dict[str, NetworkNode] = {}
        self.max_neighbors = max_neighbors
        self.topology_history: list[dict] = []

    def add_node(self, node_id: str, position: np.ndarray, bandwidth: float = 100):
        """`node` 항목을 추가한다."""
        node = NetworkNode(
            node_id=node_id,
            position=position,
            neighbors=set(),
            bandwidth_mbps=bandwidth,
            latency_ms=np.random.uniform(1, 10),
        )
        self.nodes[node_id] = node

    def update_topology(self):
        """`topology` 상태를 갱신한다."""
        for node_id, node in self.nodes.items():
            node.neighbors.clear()

            for other_id, other in self.nodes.items():
                if node_id == other_id:
                    continue

                dist = np.linalg.norm(node.position - other.position)

                if dist < 100 and len(node.neighbors) < self.max_neighbors:
                    node.neighbors.add(other_id)

        self.topology_history.append(
            {
                "timestamp": time.time(),
                "edges": sum(len(n.neighbors) for n in self.nodes.values()) // 2,
            }
        )

    def find_path(self, source: str, destination: str) -> list[str]:
        """``find_path`` 동작을 수행한다."""
        if source not in self.nodes or destination not in self.nodes:
            return []

        visited = {source}
        queue = [(source, [source])]

        while queue:
            current, path = queue.pop(0)

            if current == destination:
                return path

            for neighbor in self.nodes[current].neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return []

    def get_connectivity(self) -> float:
        """`connectivity` 정보를 조회한다."""
        if not self.nodes:
            return 0.0

        total_possible = len(self.nodes) * self.max_neighbors
        actual_edges = sum(len(n.neighbors) for n in self.nodes.values()) // 2

        return actual_edges / total_possible if total_possible > 0 else 0.0
