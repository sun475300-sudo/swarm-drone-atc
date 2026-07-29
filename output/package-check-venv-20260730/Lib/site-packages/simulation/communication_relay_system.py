"""
Phase 466: Communication Relay System for Extended Range
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class RelayNode:
    """``RelayNode`` 관련 기능을 제공한다."""
    node_id: str
    position: np.ndarray
    bandwidth_mbps: float
    active: bool


class CommunicationRelaySystem:
    """``CommunicationRelaySystem`` 역할을 담당한다."""
    def __init__(self, max_hops: int = 3):
        """인스턴스를 초기화한다."""
        self.max_hops = max_hops
        self.relay_nodes: dict[str, RelayNode] = {}
        self.active_connections: dict[str, list[str]] = {}

    def add_relay(self, node: RelayNode):
        """`relay` 항목을 추가한다."""
        self.relay_nodes[node.node_id] = node

    def find_route(self, source: str, destination: str) -> list[str] | None:
        """``find_route`` 동작을 수행한다."""
        if source not in self.relay_nodes or destination not in self.relay_nodes:
            return None

        visited = {source}
        queue = [(source, [source])]

        while queue:
            current, path = queue.pop(0)

            if current == destination:
                return path

            if len(path) >= self.max_hops:
                continue

            for node_id, node in self.relay_nodes.items():
                if node_id not in visited and node.active:
                    visited.add(node_id)
                    queue.append((node_id, path + [node_id]))

        return None

    def estimate_latency(self, route: list[str]) -> float:
        """`latency` 결과를 계산하거나 판정한다."""
        return len(route) * 5.0
