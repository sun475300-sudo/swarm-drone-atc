"""
Phase 466: Communication Relay System for Extended Range
"""

import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
import time


@dataclass
class RelayNode:
    node_id: str
    position: np.ndarray
    bandwidth_mbps: float
    active: bool


class CommunicationRelaySystem:
    def __init__(self, max_hops: int = 3):
        self.max_hops = max_hops
        self.relay_nodes: Dict[str, RelayNode] = {}
        self.active_connections: Dict[str, List[str]] = {}

    def add_relay(self, node: RelayNode):
        self.relay_nodes[node.node_id] = node

    def find_route(self, source: str, destination: str) -> Optional[List[str]]:
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

    def estimate_latency(self, route: List[str]) -> float:
        return len(route) * 5.0
