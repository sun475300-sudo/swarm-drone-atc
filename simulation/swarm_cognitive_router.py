"""
Phase 414: Swarm Cognitive Router for Intelligent Network Management
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import time


class RoutingProtocol(Enum):
    OLSR = "olsr"
    AODV = "aodv"
    DSR = "dsr"
    GRADO = "grado"


class PacketPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


@dataclass
class NetworkNode:
    node_id: str
    position: np.ndarray
    neighbors: List[str]
    bandwidth_mbps: float
    latency_ms: float
    packet_loss_rate: float


@dataclass
class RoutingTable:
    destination: str
    next_hop: str
    metric: float
    expires_at: float


class SwarmCognitiveRouter:
    def __init__(
        self,
        network_id: str,
        default_protocol: RoutingProtocol = RoutingProtocol.GRADO,
        qos_enabled: bool = True,
        adaptive_routing: bool = True,
    ):
        self.network_id = network_id
        self.default_protocol = default_protocol
        self.qos_enabled = qos_enabled
        self.adaptive_routing = adaptive_routing

        self.nodes: Dict[str, NetworkNode] = {}
        self.routing_tables: Dict[str, Dict[str, RoutingTable]] = {}

        self.packet_queue: Dict[PacketPriority, List] = {
            pp: [] for pp in PacketPriority
        }

        self.metrics = {
            "packets_routed": 0,
            "packets_dropped": 0,
            "avg_latency": 0.0,
            "routing_changes": 0,
        }

    def add_node(self, node: NetworkNode):
        self.nodes[node.node_id] = node
        self.routing_tables[node.node_id] = {}

    def update_link_quality(self, node1_id: str, node2_id: str, quality: float):
        if node1_id in self.nodes:
            if node2_id not in self.nodes[node1_id].neighbors:
                self.nodes[node1_id].neighbors.append(node2_id)

    def compute_routes(self, source: str, destination: str) -> Optional[List[str]]:
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
        route = self.compute_routes(source, destination)

        if not route:
            self.metrics["packets_dropped"] += 1
            return False

        self.metrics["packets_routed"] += 1

        if self.adaptive_routing:
            self._update_link_metrics(route)

        return True

    def _update_link_metrics(self, route: List[str]):
        self.metrics["routing_changes"] += 1

        for i in range(len(route) - 1):
            node = self.nodes.get(route[i])
            if node:
                node.latency_ms *= 0.99

    def get_optimal_path(self, source: str, destination: str) -> Optional[List[str]]:
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
    ) -> Optional[List[str]]:
        route = self.get_optimal_path(source, destination)

        if not route:
            return None

        for node_id in route:
            node = self.nodes.get(node_id)
            if node and node.bandwidth_mbps < 1.0:
                return None

        return route

    def get_network_topology(self) -> Dict[str, Any]:
        return {
            "network_id": self.network_id,
            "total_nodes": len(self.nodes),
            "total_links": sum(len(n.neighbors) for n in self.nodes.values()) // 2,
            "protocol": self.default_protocol.value,
        }
