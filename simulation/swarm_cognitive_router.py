"""
Phase 414: Swarm Cognitive Router for Intelligent Network Management
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np


class RoutingProtocol(Enum):
    """``RoutingProtocol`` 관련 기능을 제공한다."""
    OLSR = "olsr"
    AODV = "aodv"
    DSR = "dsr"
    GRADO = "grado"


class PacketPriority(Enum):
    """``PacketPriority`` 관련 기능을 제공한다."""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


@dataclass
class NetworkNode:
    """``NetworkNode`` 관련 기능을 제공한다."""
    node_id: str
    position: np.ndarray
    neighbors: list[str]
    bandwidth_mbps: float
    latency_ms: float
    packet_loss_rate: float


@dataclass
class RoutingTable:
    """``RoutingTable`` 관련 기능을 제공한다."""
    destination: str
    next_hop: str
    metric: float
    expires_at: float


class SwarmCognitiveRouter:
    """``SwarmCognitiveRouter`` 관련 기능을 제공한다."""
    def __init__(
        self,
        network_id: str,
        default_protocol: RoutingProtocol = RoutingProtocol.GRADO,
        qos_enabled: bool = True,
        adaptive_routing: bool = True,
    ):
        """인스턴스를 초기화한다."""
        self.network_id = network_id
        self.default_protocol = default_protocol
        self.qos_enabled = qos_enabled
        self.adaptive_routing = adaptive_routing

        self.nodes: dict[str, NetworkNode] = {}
        self.routing_tables: dict[str, dict[str, RoutingTable]] = {}

        self.packet_queue: dict[PacketPriority, list] = {
            pp: [] for pp in PacketPriority
        }

        self.metrics = {
            "packets_routed": 0,
            "packets_dropped": 0,
            "avg_latency": 0.0,
            "routing_changes": 0,
        }

    def add_node(self, node: NetworkNode):
        """`node` 항목을 추가한다."""
        self.nodes[node.node_id] = node
        self.routing_tables[node.node_id] = {}

    def update_link_quality(self, node1_id: str, node2_id: str, quality: float):
        """`link quality` 상태를 갱신한다."""
        if node1_id in self.nodes and node2_id not in self.nodes[node1_id].neighbors:
            self.nodes[node1_id].neighbors.append(node2_id)

    def compute_routes(self, source: str, destination: str) -> list[str] | None:
        """`routes` 값을 계산한다."""
        if source not in self.nodes or destination not in self.nodes:
            return None

        if source == destination:
            return [source]

        visited = set()
        queue = [(source, [source])]

        while queue:
            current, path = queue.pop(0)

            if current in visited:
                continue
            visited.add(current)

            if current == destination:
                return path

            neighbors = self.nodes[current].neighbors
            for neighbor in neighbors:
                if neighbor not in visited:
                    queue.append((neighbor, path + [neighbor]))

        return None

    def route_packet(self, source: str, destination: str, packet_data: Any) -> bool:
        """`packet` 작업을 계획한다."""
        route = self.compute_routes(source, destination)

        if not route:
            self.metrics["packets_dropped"] += 1
            return False

        self.metrics["packets_routed"] += 1

        if self.adaptive_routing:
            self._update_link_metrics(route)

        return True

    def _update_link_metrics(self, route: list[str]):
        self.metrics["routing_changes"] += 1

        for i in range(len(route) - 1):
            node = self.nodes.get(route[i])
            if node:
                node.latency_ms *= 0.99

    def get_optimal_path(self, source: str, destination: str) -> list[str] | None:
        """`optimal path` 정보를 조회한다."""
        routes = self.compute_routes(source, destination)

        if not routes:
            return None

        total_cost = 0
        for i in range(len(routes) - 1):
            node = self.nodes.get(routes[i])
            if node:
                latency = node.latency_ms
                loss = node.packet_loss_rate
                total_cost += latency * (1 + loss)

        return routes

    def qos_route(
        self, source: str, destination: str, priority: PacketPriority
    ) -> list[str] | None:
        """``qos_route`` 동작을 수행한다."""
        route = self.get_optimal_path(source, destination)

        if not route:
            return None

        for node_id in route:
            node = self.nodes.get(node_id)
            if node and node.bandwidth_mbps < 1.0:
                return None

        return route

    def get_network_topology(self) -> dict[str, Any]:
        """`network topology` 정보를 조회한다."""
        return {
            "network_id": self.network_id,
            "total_nodes": len(self.nodes),
            "total_links": sum(len(n.neighbors) for n in self.nodes.values()) // 2,
            "protocol": self.default_protocol.value,
        }
