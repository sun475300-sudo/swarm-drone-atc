"""
Phase 403: Quantum Distributed Computing
Distributed quantum circuits, quantum networks, quantum repeaters for drone swarm.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Optional, Tuple, Set
from collections import defaultdict


class NetworkTopology(Enum):
    """Quantum network topology."""

    LINEAR = auto()
    STAR = auto()
    MESH = auto()
    RING = auto()
    TREE = auto()
    FULL = auto()


class QuantumProtocol(Enum):
    """Quantum communication protocols."""

    TELEPORTATION = auto()
    SUPERDENSE = auto()
    ENTANGLEMENT_DIST = auto()
    QUANTUM_KEY_DIST = auto()
    QUANTUM_REPEATER = auto()


@dataclass
class QuantumNode:
    """Quantum network node."""

    node_id: int
    n_qubits: int
    position: Tuple[float, float, float]
    entangled_with: Set[int] = field(default_factory=set)
    qubits_state: Optional[np.ndarray] = None
    is_active: bool = True

    def __post_init__(self):
        if self.qubits_state is None:
            self.qubits_state = np.zeros(2**self.n_qubits, dtype=complex)
            self.qubits_state[0] = 1.0


@dataclass
class QuantumChannel:
    """Quantum communication channel."""

    source: int
    target: int
    fidelity: float = 0.95
    bandwidth: float = 1000.0
    latency_ms: float = 1.0
    noise_rate: float = 0.01
    is_bidirectional: bool = True


@dataclass
class EntanglementPair:
    """Entanglement pair between nodes."""

    node1: int
    node2: int
    fidelity: float
    creation_time: float
    bell_state: int = 0


@dataclass
class QuantumMessage:
    """Quantum message container."""

    sender: int
    receiver: int
    qubits: np.ndarray
    protocol: QuantumProtocol
    timestamp: float
    fidelity: float = 1.0


@dataclass
class NetworkMetrics:
    """Quantum network metrics."""

    total_nodes: int = 0
    active_nodes: int = 0
    total_channels: int = 0
    avg_fidelity: float = 0.0
    entanglement_pairs: int = 0
    messages_transmitted: int = 0
    teleportation_success_rate: float = 0.0


class QuantumNetworkSimulator:
    """Simulates quantum network for distributed drone computing."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.nodes: Dict[int, QuantumNode] = {}
        self.channels: Dict[Tuple[int, int], QuantumChannel] = {}
        self.entanglement_pairs: List[EntanglementPair] = []
        self.message_queue: List[QuantumMessage] = []
        self.metrics = NetworkMetrics()
        self.time: float = 0.0

    def add_node(
        self,
        node_id: int,
        n_qubits: int,
        position: Tuple[float, float, float] = (0, 0, 0),
    ) -> QuantumNode:
        node = QuantumNode(node_id, n_qubits, position)
        self.nodes[node_id] = node
        self.metrics.total_nodes += 1
        self.metrics.active_nodes += 1
        return node

    def add_channel(
        self,
        source: int,
        target: int,
        fidelity: float = 0.95,
        bandwidth: float = 1000.0,
    ) -> QuantumChannel:
        channel = QuantumChannel(source, target, fidelity, bandwidth)
        self.channels[(source, target)] = channel
        if channel.is_bidirectional:
            self.channels[(target, source)] = QuantumChannel(
                target, source, fidelity, bandwidth
            )
        self.metrics.total_channels += 1
        return channel

    def create_topology(self, topology: NetworkTopology, node_ids: List[int]) -> None:
        n = len(node_ids)
        if topology == NetworkTopology.LINEAR:
            for i in range(n - 1):
                self.add_channel(node_ids[i], node_ids[i + 1])
        elif topology == NetworkTopology.STAR:
            center = node_ids[0]
            for i in range(1, n):
                self.add_channel(center, node_ids[i])
        elif topology == NetworkTopology.RING:
            for i in range(n):
                self.add_channel(node_ids[i], node_ids[(i + 1) % n])
        elif topology == NetworkTopology.FULL:
            for i in range(n):
                for j in range(i + 1, n):
                    self.add_channel(node_ids[i], node_ids[j])
        elif topology == NetworkTopology.MESH:
            for i in range(n - 1):
                self.add_channel(node_ids[i], node_ids[i + 1])
            for i in range(0, n - 2, 2):
                self.add_channel(node_ids[i], node_ids[i + 2])

    def create_entanglement(self, node1: int, node2: int) -> Optional[EntanglementPair]:
        if node1 not in self.nodes or node2 not in self.nodes:
            return None
        if (node1, node2) not in self.channels and (node2, node1) not in self.channels:
            return None
        channel = self.channels.get((node1, node2), self.channels.get((node2, node1)))
        if channel is None:
            return None
        fidelity = channel.fidelity * (1 - channel.noise_rate)
        pair = EntanglementPair(node1, node2, fidelity, self.time)
        self.entanglement_pairs.append(pair)
        self.nodes[node1].entangled_with.add(node2)
        self.nodes[node2].entangled_with.add(node1)
        self.metrics.entanglement_pairs += 1
        return pair

    def distribute_entanglement(
        self, topology: NetworkTopology = NetworkTopology.LINEAR
    ) -> List[EntanglementPair]:
        node_ids = list(self.nodes.keys())
        self.create_topology(topology, node_ids)
        pairs = []
        for i in range(len(node_ids) - 1):
            pair = self.create_entanglement(node_ids[i], node_ids[i + 1])
            if pair:
                pairs.append(pair)
        return pairs

    def quantum_teleportation(
        self, sender: int, receiver: int, state: np.ndarray
    ) -> bool:
        if sender not in self.nodes or receiver not in self.nodes:
            return False
        pair = None
        for p in self.entanglement_pairs:
            if (p.node1 == sender and p.node2 == receiver) or (
                p.node1 == receiver and p.node2 == sender
            ):
                pair = p
                break
        if pair is None:
            pair = self.create_entanglement(sender, receiver)
        if pair is None:
            return False
        success_prob = pair.fidelity**2
        if self.rng.random() < success_prob:
            self.nodes[receiver].qubits_state = state.copy()
            self.metrics.messages_transmitted += 1
            return True
        return False

    def superdense_coding(
        self, sender: int, receiver: int, bits: Tuple[int, int]
    ) -> bool:
        if sender not in self.nodes or receiver not in self.nodes:
            return False
        if receiver not in self.nodes[sender].entangled_with:
            self.create_entanglement(sender, receiver)
        pair = None
        for p in self.entanglement_pairs:
            if (p.node1 == sender and p.node2 == receiver) or (
                p.node1 == receiver and p.node2 == sender
            ):
                pair = p
                break
        if pair is None:
            return False
        success_prob = pair.fidelity
        if self.rng.random() < success_prob:
            self.metrics.messages_transmitted += 1
            return True
        return False

    def quantum_repeater_chain(self, path: List[int]) -> float:
        if len(path) < 2:
            return 1.0
        total_fidelity = 1.0
        for i in range(len(path) - 1):
            channel = self.channels.get(
                (path[i], path[i + 1]), self.channels.get((path[i + 1], path[i]))
            )
            if channel is None:
                return 0.0
            total_fidelity *= channel.fidelity * (1 - channel.noise_rate)
        return total_fidelity

    def find_optimal_path(self, source: int, target: int) -> List[int]:
        visited = set()
        queue = [(source, [source])]
        while queue:
            node, path = queue.pop(0)
            if node == target:
                return path
            visited.add(node)
            for neighbor in self.nodes[node].entangled_with:
                if neighbor not in visited:
                    queue.append((neighbor, path + [neighbor]))
        return []

    def get_network_fidelity(self) -> float:
        if not self.entanglement_pairs:
            return 0.0
        return float(np.mean([p.fidelity for p in self.entanglement_pairs]))

    def update_metrics(self) -> None:
        self.metrics.active_nodes = sum(1 for n in self.nodes.values() if n.is_active)
        self.metrics.avg_fidelity = self.get_network_fidelity()
        success = sum(1 for m in self.message_queue if m.fidelity > 0.5)
        total = len(self.message_queue)
        self.metrics.teleportation_success_rate = success / total if total > 0 else 0.0


class QuantumRepeater:
    """Quantum repeater for long-distance entanglement."""

    def __init__(self, repeater_id: int, seed: int = 42):
        self.repeater_id = repeater_id
        self.rng = np.random.default_rng(seed)
        self.entanglement_memory: List[EntanglementPair] = []
        self.max_memory = 10
        self.swapping_success_rate = 0.85

    def store_entanglement(self, pair: EntanglementPair) -> bool:
        if len(self.entanglement_memory) >= self.max_memory:
            self.entanglement_memory.pop(0)
        self.entanglement_memory.append(pair)
        return True

    def entanglement_swapping(
        self, pair1: EntanglementPair, pair2: EntanglementPair
    ) -> Optional[EntanglementPair]:
        if self.rng.random() > self.swapping_success_rate:
            return None
        new_fidelity = pair1.fidelity * pair2.fidelity * 0.9
        if pair1.node2 == self.repeater_id:
            new_pair = EntanglementPair(
                pair1.node1, pair2.node2, new_fidelity, pair1.creation_time
            )
        else:
            new_pair = EntanglementPair(
                pair2.node1, pair1.node2, new_fidelity, pair1.creation_time
            )
        return new_pair

    def purify_entanglement(
        self, pair1: EntanglementPair, pair2: EntanglementPair
    ) -> Optional[EntanglementPair]:
        if pair1.node1 != pair2.node1 or pair1.node2 != pair2.node2:
            return None
        if self.rng.random() < pair1.fidelity * pair2.fidelity:
            new_fidelity = min(1.0, (pair1.fidelity + pair2.fidelity) / 2 + 0.1)
            return EntanglementPair(
                pair1.node1, pair1.node2, new_fidelity, pair1.creation_time
            )
        return None


class DistributedQuantumComputer:
    """Distributed quantum computing coordinator."""

    def __init__(self, n_nodes: int, seed: int = 42):
        self.n_nodes = n_nodes
        self.rng = np.random.default_rng(seed)
        self.network = QuantumNetworkSimulator(seed)
        self.repeaters: Dict[int, QuantumRepeater] = {}
        self._init_network()

    def _init_network(self) -> None:
        for i in range(self.n_nodes):
            pos = (float(i * 100), float(i * 50), 0.0)
            self.network.add_node(i, n_qubits=4, position=pos)
        self.network.distribute_entanglement(NetworkTopology.MESH)

    def execute_distributed_circuit(
        self,
        circuit_assignments: Dict[int, List[int]],
        entanglement_needed: List[Tuple[int, int]],
    ) -> Dict[int, np.ndarray]:
        results = {}
        for node_id, gate_indices in circuit_assignments.items():
            if node_id in self.network.nodes:
                state = self.network.nodes[node_id].qubits_state
                results[node_id] = state
        for n1, n2 in entanglement_needed:
            self.network.create_entanglement(n1, n2)
        return results

    def distributed_optimization(
        self, cost_function: callable, max_iter: int = 100
    ) -> Tuple[np.ndarray, float]:
        best_solution = None
        best_cost = np.inf
        for node_id in self.network.nodes:
            solution = self.rng.standard_normal(4)
            cost = cost_function(solution)
            if cost < best_cost:
                best_cost = cost
                best_solution = solution.copy()
        for iteration in range(max_iter):
            for node_id in self.network.nodes:
                perturbation = self.rng.standard_normal(4) * 0.1
                if best_solution is not None:
                    candidate = best_solution + perturbation
                    cost = cost_function(candidate)
                    if cost < best_cost:
                        best_cost = cost
                        best_solution = candidate.copy()
        return best_solution if best_solution is not None else np.zeros(4), best_cost

    def get_network_status(self) -> Dict:
        self.network.update_metrics()
        return {
            "nodes": self.network.metrics.active_nodes,
            "channels": self.network.metrics.total_channels,
            "entanglement_pairs": self.network.metrics.entanglement_pairs,
            "avg_fidelity": self.network.metrics.avg_fidelity,
            "messages": self.network.metrics.messages_transmitted,
        }


class QuantumDroneSwarmNetwork:
    """Quantum network for drone swarm coordination."""

    def __init__(self, n_drones: int, seed: int = 42):
        self.n_drones = n_drones
        self.rng = np.random.default_rng(seed)
        self.distributed_qc = DistributedQuantumComputer(n_drones, seed)
        self.coordination_state: Dict[int, np.ndarray] = {}

    def initialize_swarm(self, positions: np.ndarray) -> None:
        for i in range(min(self.n_drones, len(positions))):
            pos = tuple(positions[i])
            if i in self.distributed_qc.network.nodes:
                self.distributed_qc.network.nodes[i].position = pos

    def quantum_consensus(self, proposals: Dict[int, np.ndarray]) -> np.ndarray:
        if not proposals:
            return np.zeros(3)
        values = list(proposals.values())
        return np.mean(values, axis=0)

    def quantum_formation_sync(
        self, target_formation: np.ndarray
    ) -> Dict[int, np.ndarray]:
        corrections = {}
        for i in range(self.n_drones):
            if i in self.distributed_qc.network.nodes:
                current_pos = np.array(self.distributed_qc.network.nodes[i].position)
                if i < len(target_formation):
                    correction = target_formation[i] - current_pos
                    corrections[i] = correction * 0.5
        return corrections

    def get_swarm_entanglement_map(self) -> Dict[int, List[int]]:
        return {
            node_id: list(node.entangled_with)
            for node_id, node in self.distributed_qc.network.nodes.items()
        }


if __name__ == "__main__":
    network = QuantumNetworkSimulator(seed=42)
    for i in range(5):
        network.add_node(i, n_qubits=4, position=(float(i * 100), 0, 0))
    network.distribute_entanglement(NetworkTopology.MESH)
    print(f"Nodes: {network.metrics.total_nodes}")
    print(f"Channels: {network.metrics.total_channels}")
    print(f"Entanglement pairs: {network.metrics.entanglement_pairs}")
    print(f"Avg fidelity: {network.get_network_fidelity():.4f}")
    success = network.quantum_teleportation(0, 4, np.array([1, 0, 0, 0], dtype=complex))
    print(f"Teleportation success: {success}")
