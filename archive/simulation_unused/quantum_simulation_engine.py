"""
Phase 400: Quantum Simulation Engine
Advanced quantum circuit simulation for drone swarm optimization.
Supports quantum gates, entanglement, error correction, and hybrid computing.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Optional, Tuple, Callable, Any
from collections import defaultdict


class GateType(Enum):
    """Quantum gate types."""

    HADAMARD = auto()
    PAULI_X = auto()
    PAULI_Y = auto()
    PAULI_Z = auto()
    CNOT = auto()
    SWAP = auto()
    PHASE = auto()
    ROTATION_X = auto()
    ROTATION_Y = auto()
    ROTATION_Z = auto()
    TOFFOLI = auto()
    CUSTOM = auto()


class ErrorModel(Enum):
    """Quantum error models."""

    NONE = auto()
    DEPOLARIZING = auto()
    AMPLITUDE_DAMPING = auto()
    PHASE_DAMPING = auto()
    BIT_FLIP = auto()
    PHASE_FLIP = auto()


@dataclass
class QuantumGate:
    """Quantum gate representation."""

    gate_type: GateType
    target_qubits: List[int]
    control_qubits: List[int] = field(default_factory=list)
    params: Dict[str, float] = field(default_factory=dict)
    matrix: Optional[np.ndarray] = None


@dataclass
class QuantumState:
    """Quantum state vector representation."""

    n_qubits: int
    state_vector: np.ndarray = field(default_factory=lambda: np.array([1.0 + 0j]))
    density_matrix: Optional[np.ndarray] = None
    is_mixed: bool = False

    def __post_init__(self):
        if len(self.state_vector) == 1:
            self.state_vector = np.zeros(2**self.n_qubits, dtype=complex)
            self.state_vector[0] = 1.0


@dataclass
class MeasurementResult:
    """Quantum measurement result."""

    bitstring: List[int]
    probability: float
    counts: Dict[str, int] = field(default_factory=dict)
    shots: int = 1


@dataclass
class CircuitMetrics:
    """Quantum circuit performance metrics."""

    gate_count: int = 0
    depth: int = 0
    two_qubit_gates: int = 0
    execution_time_ms: float = 0.0
    fidelity: float = 1.0
    error_rate: float = 0.0


class QuantumGateLibrary:
    """Library of quantum gates."""

    @staticmethod
    def hadamard() -> np.ndarray:
        return np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)

    @staticmethod
    def pauli_x() -> np.ndarray:
        return np.array([[0, 1], [1, 0]], dtype=complex)

    @staticmethod
    def pauli_y() -> np.ndarray:
        return np.array([[0, -1j], [1j, 0]], dtype=complex)

    @staticmethod
    def pauli_z() -> np.ndarray:
        return np.array([[1, 0], [0, -1]], dtype=complex)

    @staticmethod
    def cnot() -> np.ndarray:
        return np.array(
            [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]], dtype=complex
        )

    @staticmethod
    def swap() -> np.ndarray:
        return np.array(
            [[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], dtype=complex
        )

    @staticmethod
    def phase(theta: float) -> np.ndarray:
        return np.array([[1, 0], [0, np.exp(1j * theta)]], dtype=complex)

    @staticmethod
    def rotation_x(theta: float) -> np.ndarray:
        return np.array(
            [
                [np.cos(theta / 2), -1j * np.sin(theta / 2)],
                [-1j * np.sin(theta / 2), np.cos(theta / 2)],
            ],
            dtype=complex,
        )

    @staticmethod
    def rotation_y(theta: float) -> np.ndarray:
        return np.array(
            [
                [np.cos(theta / 2), -np.sin(theta / 2)],
                [np.sin(theta / 2), np.cos(theta / 2)],
            ],
            dtype=complex,
        )

    @staticmethod
    def rotation_z(theta: float) -> np.ndarray:
        return np.array(
            [[np.exp(-1j * theta / 2), 0], [0, np.exp(1j * theta / 2)]], dtype=complex
        )

    @staticmethod
    def toffoli() -> np.ndarray:
        mat = np.eye(8, dtype=complex)
        mat[6, 6] = 0
        mat[7, 7] = 0
        mat[6, 7] = 1
        mat[7, 6] = 1
        return mat


class QuantumCircuitSimulator:
    """Advanced quantum circuit simulator."""

    def __init__(self, n_qubits: int, seed: int = 42):
        self.n_qubits = n_qubits
        self.rng = np.random.default_rng(seed)
        self.state = QuantumState(n_qubits)
        self.gates: List[QuantumGate] = []
        self.gate_library = QuantumGateLibrary()
        self.metrics = CircuitMetrics()
        self._noise_model = ErrorModel.NONE
        self._noise_strength = 0.001

    def set_noise_model(self, model: ErrorModel, strength: float = 0.001) -> None:
        self._noise_model = model
        self._noise_strength = strength

    def reset(self) -> None:
        self.state = QuantumState(self.n_qubits)
        self.gates = []
        self.metrics = CircuitMetrics()

    def hadamard(self, qubit: int) -> "QuantumCircuitSimulator":
        gate = QuantumGate(GateType.HADAMARD, [qubit])
        self.gates.append(gate)
        return self

    def pauli_x(self, qubit: int) -> "QuantumCircuitSimulator":
        gate = QuantumGate(GateType.PAULI_X, [qubit])
        self.gates.append(gate)
        return self

    def pauli_y(self, qubit: int) -> "QuantumCircuitSimulator":
        gate = QuantumGate(GateType.PAULI_Y, [qubit])
        self.gates.append(gate)
        return self

    def pauli_z(self, qubit: int) -> "QuantumCircuitSimulator":
        gate = QuantumGate(GateType.PAULI_Z, [qubit])
        self.gates.append(gate)
        return self

    def cnot(self, control: int, target: int) -> "QuantumCircuitSimulator":
        gate = QuantumGate(GateType.CNOT, [target], [control])
        self.gates.append(gate)
        return self

    def swap(self, q1: int, q2: int) -> "QuantumCircuitSimulator":
        gate = QuantumGate(GateType.SWAP, [q1, q2])
        self.gates.append(gate)
        return self

    def phase(self, qubit: int, theta: float) -> "QuantumCircuitSimulator":
        gate = QuantumGate(GateType.PHASE, [qubit], params={"theta": theta})
        self.gates.append(gate)
        return self

    def rx(self, qubit: int, theta: float) -> "QuantumCircuitSimulator":
        gate = QuantumGate(GateType.ROTATION_X, [qubit], params={"theta": theta})
        self.gates.append(gate)
        return self

    def ry(self, qubit: int, theta: float) -> "QuantumCircuitSimulator":
        gate = QuantumGate(GateType.ROTATION_Y, [qubit], params={"theta": theta})
        self.gates.append(gate)
        return self

    def rz(self, qubit: int, theta: float) -> "QuantumCircuitSimulator":
        gate = QuantumGate(GateType.ROTATION_Z, [qubit], params={"theta": theta})
        self.gates.append(gate)
        return self

    def toffoli(
        self, control1: int, control2: int, target: int
    ) -> "QuantumCircuitSimulator":
        gate = QuantumGate(GateType.TOFFOLI, [target], [control1, control2])
        self.gates.append(gate)
        return self

    def _get_gate_matrix(self, gate: QuantumGate) -> np.ndarray:
        gate_map = {
            GateType.HADAMARD: self.gate_library.hadamard(),
            GateType.PAULI_X: self.gate_library.pauli_x(),
            GateType.PAULI_Y: self.gate_library.pauli_y(),
            GateType.PAULI_Z: self.gate_library.pauli_z(),
            GateType.CNOT: self.gate_library.cnot(),
            GateType.SWAP: self.gate_library.swap(),
            GateType.TOFFOLI: self.gate_library.toffoli(),
        }
        if gate.gate_type in gate_map:
            return gate_map[gate.gate_type]
        if gate.gate_type == GateType.PHASE:
            return self.gate_library.phase(gate.params["theta"])
        if gate.gate_type == GateType.ROTATION_X:
            return self.gate_library.rotation_x(gate.params["theta"])
        if gate.gate_type == GateType.ROTATION_Y:
            return self.gate_library.rotation_y(gate.params["theta"])
        if gate.gate_type == GateType.ROTATION_Z:
            return self.gate_library.rotation_z(gate.params["theta"])
        return gate.matrix if gate.matrix is not None else np.eye(2, dtype=complex)

    def _apply_single_qubit_gate(self, gate_matrix: np.ndarray, target: int) -> None:
        n = self.n_qubits
        full_matrix = np.eye(1, dtype=complex)
        for q in range(n):
            if q == target:
                full_matrix = np.kron(full_matrix, gate_matrix)
            else:
                full_matrix = np.kron(full_matrix, np.eye(2, dtype=complex))
        self.state.state_vector = full_matrix @ self.state.state_vector

    def _apply_two_qubit_gate(
        self, gate_matrix: np.ndarray, control: int, target: int
    ) -> None:
        n = self.n_qubits
        dim = 2**n
        new_state = self.state.state_vector.copy()
        for i in range(dim):
            bits = [(i >> (n - 1 - q)) & 1 for q in range(n)]
            if bits[control] == 1:
                j = i ^ (1 << (n - 1 - target))
                new_state[j] = (
                    gate_matrix[0, 0] * self.state.state_vector[i]
                    + gate_matrix[0, 1] * self.state.state_vector[j]
                )
                new_state[i] = (
                    gate_matrix[1, 0] * self.state.state_vector[i]
                    + gate_matrix[1, 1] * self.state.state_vector[j]
                )
        self.state.state_vector = new_state

    def _apply_noise(self) -> None:
        if self._noise_model == ErrorModel.NONE:
            return
        noise = (
            self.rng.standard_normal(len(self.state.state_vector))
            * self._noise_strength
        )
        self.state.state_vector += noise * (1 + 0j)
        norm = np.linalg.norm(self.state.state_vector)
        if norm > 0:
            self.state.state_vector /= norm

    def execute(self) -> QuantumState:
        import time

        start = time.time()
        for gate in self.gates:
            matrix = self._get_gate_matrix(gate)
            if len(gate.target_qubits) == 1 and not gate.control_qubits:
                self._apply_single_qubit_gate(matrix, gate.target_qubits[0])
            elif len(gate.target_qubits) == 1 and len(gate.control_qubits) == 1:
                self._apply_two_qubit_gate(
                    matrix, gate.control_qubits[0], gate.target_qubits[0]
                )
            self._apply_noise()
            self.metrics.gate_count += 1
        self.metrics.depth = len(self.gates)
        self.metrics.execution_time_ms = (time.time() - start) * 1000
        return self.state

    def measure(
        self, qubit: Optional[int] = None, shots: int = 1024
    ) -> MeasurementResult:
        probs = np.abs(self.state.state_vector) ** 2
        probs = probs / probs.sum()
        if qubit is not None:
            prob_0 = sum(
                probs[i]
                for i in range(len(probs))
                if (i >> (self.n_qubits - 1 - qubit)) & 1 == 0
            )
            prob_1 = 1.0 - prob_0
            result = 0 if self.rng.random() < prob_0 else 1
            return MeasurementResult(
                [result], prob_0 if result == 0 else prob_1, shots=shots
            )
        indices = self.rng.choice(len(probs), size=shots, p=probs)
        counts = defaultdict(int)
        for idx in indices:
            bitstring = format(idx, f"0{self.n_qubits}b")
            counts[bitstring] += 1
        most_common = max(counts.items(), key=lambda x: x[1])
        bits = [int(b) for b in most_common[0]]
        return MeasurementResult(bits, most_common[1] / shots, dict(counts), shots)

    def create_bell_state(self) -> None:
        self.reset()
        self.hadamard(0)
        self.cnot(0, 1)
        self.execute()

    def create_ghz_state(self) -> None:
        self.reset()
        self.hadamard(0)
        for i in range(self.n_qubits - 1):
            self.cnot(i, i + 1)
        self.execute()

    def get_fidelity(self, target_state: np.ndarray) -> float:
        overlap = np.abs(np.vdot(self.state.state_vector, target_state)) ** 2
        return float(overlap)

    def get_entanglement_entropy(self, subsystem: List[int]) -> float:
        n = self.n_qubits
        other = [q for q in range(n) if q not in subsystem]
        dim_sub = 2 ** len(subsystem)
        dim_other = 2 ** len(other)
        psi = self.state.state_vector.reshape(dim_other, dim_sub)
        rho = psi @ psi.conj().T
        eigenvalues = np.linalg.eigvalsh(rho)
        eigenvalues = eigenvalues[eigenvalues > 1e-12]
        entropy = -np.sum(eigenvalues * np.log2(eigenvalues))
        return float(entropy)

    def get_metrics(self) -> CircuitMetrics:
        return self.metrics


class QuantumEntanglementSimulator:
    """Simulates quantum entanglement for distributed drone coordination."""

    def __init__(self, n_nodes: int, seed: int = 42):
        self.n_nodes = n_nodes
        self.rng = np.random.default_rng(seed)
        self.entanglement_pairs: List[Tuple[int, int]] = []
        self.entanglement_fidelity: Dict[Tuple[int, int], float] = {}

    def create_entanglement(
        self, node1: int, node2: int, fidelity: float = 0.95
    ) -> bool:
        if node1 == node2 or node1 >= self.n_nodes or node2 >= self.n_nodes:
            return False
        pair = (min(node1, node2), max(node1, node2))
        self.entanglement_pairs.append(pair)
        self.entanglement_fidelity[pair] = fidelity
        return True

    def measure_correlation(
        self, node1: int, node2: int, basis: str = "z"
    ) -> Tuple[int, int]:
        pair = (min(node1, node2), max(node1, node2))
        fidelity = self.entanglement_fidelity.get(pair, 0.5)
        if self.rng.random() < fidelity:
            result = 0 if self.rng.random() < 0.5 else 1
            return (result, result)
        return (0, 1) if self.rng.random() < 0.5 else (1, 0)

    def distribute_entanglement(
        self, topology: str = "linear"
    ) -> List[Tuple[int, int]]:
        pairs = []
        if topology == "linear":
            for i in range(self.n_nodes - 1):
                if self.create_entanglement(i, i + 1):
                    pairs.append((i, i + 1))
        elif topology == "star":
            center = 0
            for i in range(1, self.n_nodes):
                if self.create_entanglement(center, i):
                    pairs.append((center, i))
        elif topology == "full":
            for i in range(self.n_nodes):
                for j in range(i + 1, self.n_nodes):
                    if self.create_entanglement(i, j):
                        pairs.append((i, j))
        return pairs

    def get_entanglement_graph(self) -> Dict[int, List[int]]:
        graph = defaultdict(list)
        for n1, n2 in self.entanglement_pairs:
            graph[n1].append(n2)
            graph[n2].append(n1)
        return dict(graph)


class QuantumErrorCorrection:
    """Quantum error correction codes."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)

    def encode_bit_flip(self, state: np.ndarray) -> np.ndarray:
        n = len(state)
        encoded = np.zeros(3 * n, dtype=complex)
        for i in range(n):
            encoded[3 * i] = state[i]
            encoded[3 * i + 1] = state[i]
            encoded[3 * i + 2] = state[i]
        return encoded / np.linalg.norm(encoded)

    def decode_bit_flip(self, encoded: np.ndarray) -> np.ndarray:
        n = len(encoded) // 3
        decoded = np.zeros(n, dtype=complex)
        for i in range(n):
            votes = [encoded[3 * i], encoded[3 * i + 1], encoded[3 * i + 2]]
            decoded[i] = votes[np.argmax(np.abs(votes))]
        return decoded / np.linalg.norm(decoded)

    def encode_phase_flip(self, state: np.ndarray) -> np.ndarray:
        h = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)
        encoded = self.encode_bit_flip(state)
        for i in range(0, len(encoded), 3):
            encoded[i : i + 3] = (
                np.kron(h, np.eye(1, dtype=complex)).flatten()[:3] * encoded[i : i + 3]
            )
        return encoded / np.linalg.norm(encoded)

    def syndrome_measurement(self, encoded: np.ndarray) -> List[int]:
        n = len(encoded) // 3
        syndromes = []
        for i in range(n):
            s1 = 1 if np.real(encoded[3 * i] * encoded[3 * i + 1].conj()) < 0 else 0
            s2 = 1 if np.real(encoded[3 * i + 1] * encoded[3 * i + 2].conj()) < 0 else 0
            syndromes.extend([s1, s2])
        return syndromes

    def correct_errors(self, encoded: np.ndarray, syndromes: List[int]) -> np.ndarray:
        corrected = encoded.copy()
        n = len(encoded) // 3
        for i in range(n):
            s1, s2 = syndromes[2 * i], syndromes[2 * i + 1]
            if s1 == 1 and s2 == 0:
                corrected[3 * i] *= -1
            elif s1 == 0 and s2 == 1:
                corrected[3 * i + 2] *= -1
            elif s1 == 1 and s2 == 1:
                corrected[3 * i + 1] *= -1
        return corrected / np.linalg.norm(corrected)


class QuantumDroneOptimizer:
    """Quantum-enhanced drone swarm optimizer."""

    def __init__(self, n_drones: int, seed: int = 42):
        self.n_drones = n_drones
        self.rng = np.random.default_rng(seed)
        self.circuit = QuantumCircuitSimulator(
            max(4, int(np.ceil(np.log2(n_drones)))), seed
        )
        self.entanglement = QuantumEntanglementSimulator(n_drones, seed)
        self.error_correction = QuantumErrorCorrection(seed)

    def quantum_route_optimization(
        self, distance_matrix: np.ndarray, max_iter: int = 100
    ) -> Tuple[List[int], float]:
        n = self.n_drones
        best_route = list(range(n))
        best_cost = sum(
            distance_matrix[best_route[i], best_route[i + 1]] for i in range(n - 1)
        )
        for iteration in range(max_iter):
            self.circuit.reset()
            for q in range(self.circuit.n_qubits):
                self.circuit.hadamard(q)
            for q in range(self.circuit.n_qubits - 1):
                self.circuit.cnot(q, q + 1)
            for q in range(self.circuit.n_qubits):
                self.circuit.rz(q, self.rng.uniform(0, 2 * np.pi))
            self.circuit.execute()
            measurement = self.circuit.measure(shots=100)
            bits = measurement.bitstring
            route = self._bits_to_route(bits, n)
            cost = sum(distance_matrix[route[i], route[i + 1]] for i in range(n - 1))
            if cost < best_cost:
                best_cost = cost
                best_route = route[:]
        return best_route, best_cost

    def _bits_to_route(self, bits: List[int], n: int) -> List[int]:
        scores = [0.0] * n
        for i in range(n):
            for j, b in enumerate(bits):
                scores[i] += b * ((i + j) % (n + 1))
            scores[i] += self.rng.random() * 0.01
        return list(np.argsort(scores))

    def quantum_conflict_resolution(
        self, conflicts: List[Tuple[int, int]]
    ) -> List[Tuple[int, int]]:
        resolutions = []
        for drone1, drone2 in conflicts:
            result = self.entanglement.measure_correlation(drone1, drone2)
            if result[0] == result[1]:
                resolutions.append((drone1, drone2, "cooperative"))
            else:
                resolutions.append((drone1, drone2, "competitive"))
        return resolutions

    def quantum_formation_control(
        self, target_positions: np.ndarray, current_positions: np.ndarray
    ) -> np.ndarray:
        n = self.n_drones
        corrections = np.zeros_like(current_positions)
        for i in range(n):
            self.circuit.reset()
            self.circuit.hadamard(0)
            self.circuit.rx(
                0, np.linalg.norm(target_positions[i] - current_positions[i]) * 0.1
            )
            self.circuit.execute()
            m = self.circuit.measure(0)
            if m.bitstring[0] == 0:
                corrections[i] = (target_positions[i] - current_positions[i]) * 0.5
            else:
                corrections[i] = (target_positions[i] - current_positions[i]) * 0.8
        return current_positions + corrections

    def get_entanglement_topology(self) -> Dict[int, List[int]]:
        return self.entanglement.get_entanglement_graph()


if __name__ == "__main__":
    sim = QuantumCircuitSimulator(n_qubits=3, seed=42)
    sim.hadamard(0)
    sim.cnot(0, 1)
    sim.cnot(1, 2)
    sim.execute()
    result = sim.measure(shots=1024)
    print(f"Measurement: {result.bitstring}")
    print(f"Probability: {result.probability:.4f}")
    print(f"Counts: {dict(list(result.counts.items())[:5])}")
    entropy = sim.get_entanglement_entropy([0])
    print(f"Entanglement entropy: {entropy:.4f}")
    metrics = sim.get_metrics()
    print(f"Gates: {metrics.gate_count}, Depth: {metrics.depth}")
    print(f"Execution time: {metrics.execution_time_ms:.2f} ms")
