"""
Mesh Network Protocol
Phase 363 - P2P Communication, Multi-hop Routing, Mesh Formation
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Set
from enum import Enum
import random
import time


class NodeState(Enum):
    IDLE = "idle"
    DISCOVERING = "discovering"
    CONNECTED = "connected"
    ROUTING = "routing"
    FAILED = "failed"


class MessageType(Enum):
    HELLO = "hello"
    HELLO_ACK = "hello_ack"
    ROUTE_REQUEST = "route_request"
    ROUTE_REPLY = "route_reply"
    ROUTE_ERROR = "route_error"
    DATA = "data"
    BEACON = "beacon"


@dataclass
class NetworkPacket:
    msg_type: MessageType
    source_id: str
    dest_id: str
    payload: Dict
    hop_count: int
    seq_num: int
    timestamp: float


@dataclass
class MeshNode:
    node_id: str
    position: Tuple[float, float, float]
    neighbors: Set[str]
    routing_table: Dict[str, str]
    state: NodeState
    battery_percent: float
    tx_power: float
    rx_sensitivity: float


class LinkQualityEstimator:
    def __init__(self):
        self.history: Dict[Tuple[str, str], List[float]] = {}

    def estimate(
        self, node1: str, node2: str, distance: float, interference: float = 0.0
    ) -> float:
        key = (min(node1, node2), max(node1, node2))

        freq_mhz = 2400
        wavelength = 300 / freq_mhz
        pl_free = (
            20 * np.log10(4 * np.pi * distance / wavelength) if distance > 0 else -60
        )

        tx_power_dbm = 20
        rx_power = tx_power_dbm - pl_free - interference

        rx_sensitivity = -85
        if rx_power < rx_sensitivity:
            return 0.0

        snr = rx_power - (-100)
        link_quality = min(1.0, snr / 40)

        if key not in self.history:
            self.history[key] = []
        self.history[key].append(link_quality)
        if len(self.history[key]) > 10:
            self.history[key].pop(0)

        return np.mean(self.history[key]) if self.history[key] else link_quality


class RoutingProtocol:
    def __init__(self, mesh: "MeshNetwork"):
        self.mesh = mesh
        self.route_cache: Dict[Tuple[str, str], List[str]] = {}
        self.seq_numbers: Dict[str, int] = {}

    def find_route(self, source: str, dest: str) -> Optional[List[str]]:
        if source == dest:
            return [source]

        if (source, dest) in self.route_cache:
            return self.route_cache[(source, dest)]

        path = self._aodv_route_discovery(source, dest)

        if path:
            self.route_cache[(source, dest)] = path

        return path

    def _aodv_route_discovery(self, source: str, dest: str) -> Optional[List[str]]:
        visited = {source}
        queue = [(source, [source])]

        while queue:
            current, path = queue.pop(0)

            node = self.mesh.nodes[current]
            for neighbor_id in node.neighbors:
                if neighbor_id in visited:
                    continue

                visited.add(neighbor_id)
                new_path = path + [neighbor_id]

                if neighbor_id == dest:
                    return new_path

                if len(new_path) < 10:
                    queue.append((neighbor_id, new_path))

        return None

    def handle_route_request(self, packet: NetworkPacket) -> Optional[NetworkPacket]:
        route = self.find_route(packet.source_id, packet.dest_id)

        if route:
            return NetworkPacket(
                msg_type=MessageType.ROUTE_REPLY,
                source_id=packet.dest_id,
                dest_id=packet.source_id,
                payload={"route": route},
                hop_count=0,
                seq_num=self.mesh.seq_counter,
                timestamp=time.time(),
            )

        return None


class MeshNetwork:
    def __init__(self, max_range: float = 100.0):
        self.nodes: Dict[str, MeshNode] = {}
        self.max_range = max_range
        self.link_estimator = LinkQualityEstimator()
        self.routing = RoutingProtocol(self)
        self.seq_counter = 0
        self.packet_history: List[NetworkPacket] = []

    def add_node(self, node_id: str, position: Tuple[float, float, float]):
        node = MeshNode(
            node_id=node_id,
            position=position,
            neighbors=set(),
            routing_table={},
            state=NodeState.IDLE,
            battery_percent=100.0,
            tx_power=20.0,
            rx_sensitivity=-85.0,
        )
        self.nodes[node_id] = node

    def update_positions(self, positions: Dict[str, Tuple[float, float, float]]):
        for node_id, pos in positions.items():
            if node_id in self.nodes:
                self.nodes[node_id].position = pos

    def discover_neighbors(self):
        for node_id, node in self.nodes.items():
            node.neighbors.clear()

            for other_id, other in self.nodes.items():
                if node_id == other_id:
                    continue

                distance = self._calculate_distance(node.position, other.position)

                if distance < self.max_range:
                    link_quality = self.link_estimator.estimate(
                        node_id, other_id, distance
                    )

                    if link_quality > 0.3:
                        node.neighbors.add(other_id)

    def _calculate_distance(self, pos1: Tuple, pos2: Tuple) -> float:
        return np.sqrt(sum((a - b) ** 2 for a, b in zip(pos1, pos2)))

    def send_packet(self, source_id: str, dest_id: str, payload: Dict) -> bool:
        if source_id not in self.nodes or dest_id not in self.nodes:
            return False

        route = self.routing.find_route(source_id, dest_id)

        if not route:
            return False

        packet = NetworkPacket(
            msg_type=MessageType.DATA,
            source_id=source_id,
            dest_id=dest_id,
            payload=payload,
            hop_count=0,
            seq_num=self.seq_counter,
            timestamp=time.time(),
        )

        self.seq_counter += 1
        self.packet_history.append(packet)

        self._forward_packet(packet, route)

        return True

    def _forward_packet(self, packet: NetworkPacket, route: List[str]):
        for i, node_id in enumerate(route[:-1]):
            packet.hop_count = i

            self.nodes[node_id].battery_percent -= 0.01

    def broadcast_beacon(self):
        beacon = NetworkPacket(
            msg_type=MessageType.BEACON,
            source_id="broadcast",
            dest_id="all",
            payload={},
            hop_count=0,
            seq_num=self.seq_counter,
            timestamp=time.time(),
        )

        for node in self.nodes.values():
            if node.battery_percent > 10:
                node.state = NodeState.ROUTING

    def get_network_stats(self) -> Dict:
        total_links = sum(len(n.neighbors) for n in self.nodes.values()) // 2

        connected_nodes = sum(1 for n in self.nodes.values() if len(n.neighbors) > 0)

        avg_battery = (
            np.mean([n.battery_percent for n in self.nodes.values()])
            if self.nodes
            else 0
        )

        return {
            "total_nodes": len(self.nodes),
            "connected_nodes": connected_nodes,
            "total_links": total_links,
            "avg_battery": avg_battery,
            "packets_sent": len(self.packet_history),
        }


class MeshFormationController:
    def __init__(self, network: MeshNetwork):
        self.network = network

    def form_mesh(self, leader_id: str) -> Dict:
        leader = self.network.nodes.get(leader_id)
        if not leader:
            return {"status": "error", "message": "Leader not found"}

        leader.state = NodeState.ROUTING

        formation = {leader_id: 0}

        visited = {leader_id}
        queue = [(neighbor, 1) for neighbor in leader.neighbors]

        while queue:
            node_id, hop = queue.pop(0)

            if node_id in visited:
                continue

            visited.add(node_id)
            formation[node_id] = hop

            node = self.network.nodes[node_id]
            node.state = NodeState.ROUTING

            for neighbor in node.neighbors:
                if neighbor not in visited:
                    queue.append((neighbor, hop + 1))

        return {
            "status": "success",
            "leader": leader_id,
            "formation": formation,
            "total_nodes": len(formation),
        }

    def optimize_topology(self) -> List[Tuple[str, str]]:
        suggestions = []

        isolated = [
            n_id for n_id, n in self.network.nodes.items() if len(n.neighbors) == 1
        ]

        for node_id in isolated:
            node = self.network.nodes[node_id]
            if node.battery_percent > 50:
                best_neighbor = None
                best_quality = 0

                for other_id in self.network.nodes:
                    if other_id == node_id or other_id in node.neighbors:
                        continue

                    distance = self._calculate_distance(
                        node.position, self.network.nodes[other_id].position
                    )
                    if distance < self.network.max_range:
                        quality = self.network.link_estimator.estimate(
                            node_id, other_id, distance
                        )
                        if quality > best_quality:
                            best_quality = quality
                            best_neighbor = other_id

                if best_neighbor and best_quality > 0.3:
                    suggestions.append((node_id, best_neighbor))

        return suggestions

    def _calculate_distance(self, pos1: Tuple, pos2: Tuple) -> float:
        return np.sqrt(sum((a - b) ** 2 for a, b in zip(pos1, pos2)))


def simulate_mesh_network():
    print("=== Mesh Network Protocol Simulation ===")

    network = MeshNetwork(max_range=80)

    print("\n--- Creating Network ---")
    for i in range(10):
        x = np.random.uniform(0, 200)
        y = np.random.uniform(0, 200)
        z = np.random.uniform(20, 80)
        network.add_node(f"drone_{i}", (x, y, z))

    network.discover_neighbors()

    stats = network.get_network_stats()
    print(
        f"Initial: {stats['connected_nodes']}/{stats['total_nodes']} connected, {stats['total_links']} links"
    )

    print("\n--- Network Formation ---")
    controller = MeshFormationController(network)
    formation = controller.form_mesh("drone_0")
    print(f"Formation: {formation['total_nodes']} nodes, leader={formation['leader']}")

    print("\n--- Sending Packets ---")
    success_count = 0
    for i in range(20):
        source = f"drone_{random.randint(0, 4)}"
        dest = f"drone_{random.randint(5, 9)}"

        if source != dest:
            payload = {"message": f"data_{i}", "timestamp": time.time()}
            if network.send_packet(source, dest, payload):
                success_count += 1

    print(f"Packets delivered: {success_count}/20")

    print("\n--- Topology Optimization ---")
    suggestions = controller.optimize_topology()
    print(f"Optimization suggestions: {len(suggestions)}")

    final_stats = network.get_network_stats()
    print(f"\n--- Final Stats ---")
    print(f"Nodes: {final_stats['total_nodes']}")
    print(f"Connected: {final_stats['connected_nodes']}")
    print(f"Links: {final_stats['total_links']}")
    print(f"Avg Battery: {final_stats['avg_battery']:.1f}%")

    return final_stats


if __name__ == "__main__":
    simulate_mesh_network()
