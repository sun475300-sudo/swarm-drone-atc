"""
Phase 331: Quantum Path Optimizer
QAOA/VQE 시뮬레이션 기반 경로 최적화.
양자 어닐링 + 변분 양자 고유값 해법.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple


class QuantumBackend(Enum):
    SIMULATOR = "simulator"
    QAOA = "qaoa"
    VQE = "vqe"
    ANNEALING = "annealing"


@dataclass
class Qubit:
    index: int
    state: np.ndarray = field(default_factory=lambda: np.array([1.0, 0.0], dtype=complex))

    def apply_gate(self, gate: np.ndarray) -> None:
        self.state = gate @ self.state

    def measure(self, rng: np.random.Generator) -> int:
        prob_one = float(np.abs(self.state[1]) ** 2)
        result = 1 if rng.random() < prob_one else 0
        self.state = np.array([1.0, 0.0] if result == 0 else [0.0, 1.0], dtype=complex)
        return result


class QuantumCircuit:
    """Simple quantum circuit simulator for path optimization."""

    HADAMARD = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)
    PAULI_X = np.array([[0, 1], [1, 0]], dtype=complex)
    PAULI_Z = np.array([[1, 0], [0, -1]], dtype=complex)

    def __init__(self, n_qubits: int, rng: np.random.Generator):
        self.n_qubits = n_qubits
        self.qubits = [Qubit(i) for i in range(n_qubits)]
        self.rng = rng

    def hadamard(self, qubit_idx: int) -> None:
        self.qubits[qubit_idx].apply_gate(self.HADAMARD)

    def rx(self, qubit_idx: int, theta: float) -> None:
        gate = np.array([
            [np.cos(theta / 2), -1j * np.sin(theta / 2)],
            [-1j * np.sin(theta / 2), np.cos(theta / 2)]
        ], dtype=complex)
        self.qubits[qubit_idx].apply_gate(gate)

    def rz(self, qubit_idx: int, theta: float) -> None:
        gate = np.array([
            [np.exp(-1j * theta / 2), 0],
            [0, np.exp(1j * theta / 2)]
        ], dtype=complex)
        self.qubits[qubit_idx].apply_gate(gate)

    def measure_all(self) -> List[int]:
        return [q.measure(self.rng) for q in self.qubits]

    def reset(self) -> None:
        for q in self.qubits:
            q.state = np.array([1.0, 0.0], dtype=complex)


@dataclass
class QAOAResult:
    best_bitstring: List[int]
    best_cost: float
    iterations: int
    energy_history: List[float]
    optimal_params: List[float]


@dataclass
class PathNode:
    node_id: str
    x: float
    y: float
    z: float


@dataclass
class QuantumOptResult:
    path: List[str]
    total_cost: float
    method: str
    iterations: int
    convergence: List[float]


class QuantumPathOptimizer:
    """Quantum-inspired path optimizer using QAOA and simulated annealing."""

    def __init__(self, seed: int = 42, backend: QuantumBackend = QuantumBackend.QAOA):
        self.rng = np.random.default_rng(seed)
        self.backend = backend
        self.nodes: Dict[str, PathNode] = {}
        self.edges: Dict[Tuple[str, str], float] = {}
        self.results: List[QuantumOptResult] = []

    def add_node(self, node_id: str, x: float, y: float, z: float) -> PathNode:
        node = PathNode(node_id, x, y, z)
        self.nodes[node_id] = node
        return node

    def add_edge(self, src: str, dst: str, cost: Optional[float] = None) -> float:
        if cost is None:
            a, b = self.nodes[src], self.nodes[dst]
            cost = np.sqrt((a.x - b.x)**2 + (a.y - b.y)**2 + (a.z - b.z)**2)
        self.edges[(src, dst)] = cost
        self.edges[(dst, src)] = cost
        return cost

    def _build_cost_matrix(self, node_ids: List[str]) -> np.ndarray:
        n = len(node_ids)
        cost_matrix = np.full((n, n), np.inf)
        idx_map = {nid: i for i, nid in enumerate(node_ids)}
        for (src, dst), cost in self.edges.items():
            if src in idx_map and dst in idx_map:
                cost_matrix[idx_map[src], idx_map[dst]] = cost
        np.fill_diagonal(cost_matrix, 0)
        return cost_matrix

    def _qaoa_optimize(self, cost_matrix: np.ndarray, p_layers: int = 3,
                       max_iter: int = 50) -> QAOAResult:
        n = cost_matrix.shape[0]
        n_qubits = n * (n - 1) // 2
        circuit = QuantumCircuit(max(n_qubits, 1), self.rng)
        params = self.rng.uniform(0, 2 * np.pi, size=2 * p_layers)
        best_cost = np.inf
        best_bits: List[int] = []
        energy_history: List[float] = []

        for iteration in range(max_iter):
            circuit.reset()
            for q in range(circuit.n_qubits):
                circuit.hadamard(q)

            for layer in range(p_layers):
                gamma = params[2 * layer]
                beta = params[2 * layer + 1]
                for q in range(circuit.n_qubits):
                    circuit.rz(q, gamma)
                for q in range(circuit.n_qubits):
                    circuit.rx(q, beta)

            n_shots = 20
            costs = []
            for _ in range(n_shots):
                circuit.reset()
                for q in range(circuit.n_qubits):
                    circuit.hadamard(q)
                for layer in range(p_layers):
                    circuit.rz(q, params[2 * layer])
                    circuit.rx(q, params[2 * layer + 1])
                bits = circuit.measure_all()
                perm = self._bitstring_to_permutation(bits, n)
                cost = self._evaluate_path(perm, cost_matrix)
                costs.append((cost, bits))

            avg_energy = np.mean([c for c, _ in costs])
            energy_history.append(float(avg_energy))

            for cost, bits in costs:
                if cost < best_cost:
                    best_cost = cost
                    best_bits = bits

            grad = self.rng.standard_normal(len(params)) * 0.1
            params -= 0.05 * grad

        return QAOAResult(
            best_bitstring=best_bits,
            best_cost=best_cost,
            iterations=max_iter,
            energy_history=energy_history,
            optimal_params=params.tolist()
        )

    def _simulated_annealing(self, cost_matrix: np.ndarray,
                             max_iter: int = 200) -> Tuple[List[int], float, List[float]]:
        n = cost_matrix.shape[0]
        current = list(range(n))
        self.rng.shuffle(current)
        current_cost = self._evaluate_path(current, cost_matrix)
        best = current[:]
        best_cost = current_cost
        history = [current_cost]
        T = 100.0
        alpha = 0.95

        for _ in range(max_iter):
            i, j = sorted(self.rng.choice(n, 2, replace=False))
            neighbor = current[:]
            neighbor[i:j + 1] = reversed(neighbor[i:j + 1])
            neighbor_cost = self._evaluate_path(neighbor, cost_matrix)
            delta = neighbor_cost - current_cost

            if delta < 0 or self.rng.random() < np.exp(-delta / max(T, 1e-10)):
                current = neighbor
                current_cost = neighbor_cost
                if current_cost < best_cost:
                    best = current[:]
                    best_cost = current_cost

            T *= alpha
            history.append(best_cost)

        return best, best_cost, history

    def _vqe_optimize(self, cost_matrix: np.ndarray,
                      max_iter: int = 80) -> Tuple[List[int], float, List[float]]:
        n = cost_matrix.shape[0]
        params = self.rng.uniform(0, 2 * np.pi, size=n)
        best_perm = list(range(n))
        best_cost = self._evaluate_path(best_perm, cost_matrix)
        history = [best_cost]

        for _ in range(max_iter):
            scores = np.cos(params) + self.rng.standard_normal(n) * 0.1
            perm = list(np.argsort(scores))
            cost = self._evaluate_path(perm, cost_matrix)

            if cost < best_cost:
                best_cost = cost
                best_perm = perm

            grad = self.rng.standard_normal(n) * 0.05
            params -= 0.1 * grad
            history.append(best_cost)

        return best_perm, best_cost, history

    def _bitstring_to_permutation(self, bits: List[int], n: int) -> List[int]:
        scores = []
        for i in range(n):
            val = 0
            for j, b in enumerate(bits):
                val += b * ((i + j) % (n + 1))
            scores.append(val + self.rng.random() * 0.01)
        return list(np.argsort(scores))

    def _evaluate_path(self, perm: List[int], cost_matrix: np.ndarray) -> float:
        total = 0.0
        for i in range(len(perm) - 1):
            c = cost_matrix[perm[i], perm[i + 1]]
            total += c if np.isfinite(c) else 1e6
        return total

    def optimize_path(self, node_ids: Optional[List[str]] = None,
                      max_iter: int = 100) -> QuantumOptResult:
        if node_ids is None:
            node_ids = list(self.nodes.keys())

        cost_matrix = self._build_cost_matrix(node_ids)

        if self.backend == QuantumBackend.QAOA:
            qaoa_result = self._qaoa_optimize(cost_matrix, max_iter=max_iter)
            perm = self._bitstring_to_permutation(qaoa_result.best_bitstring, len(node_ids))
            convergence = qaoa_result.energy_history
            total_cost = qaoa_result.best_cost
        elif self.backend == QuantumBackend.ANNEALING:
            perm, total_cost, convergence = self._simulated_annealing(cost_matrix, max_iter)
        elif self.backend == QuantumBackend.VQE:
            perm, total_cost, convergence = self._vqe_optimize(cost_matrix, max_iter)
        else:
            perm, total_cost, convergence = self._simulated_annealing(cost_matrix, max_iter)

        path = [node_ids[i] for i in perm]
        result = QuantumOptResult(
            path=path, total_cost=total_cost,
            method=self.backend.value, iterations=max_iter,
            convergence=convergence
        )
        self.results.append(result)
        return result

    def summary(self) -> Dict:
        return {
            "nodes": len(self.nodes),
            "edges": len(self.edges) // 2,
            "backend": self.backend.value,
            "optimizations_run": len(self.results),
            "best_cost": min((r.total_cost for r in self.results), default=0),
        }


if __name__ == "__main__":
    opt = QuantumPathOptimizer(seed=42, backend=QuantumBackend.ANNEALING)
    for i in range(6):
        opt.add_node(f"wp{i}", x=np.cos(i) * 100, y=np.sin(i) * 100, z=50)
    ids = list(opt.nodes.keys())
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            opt.add_edge(ids[i], ids[j])

    result = opt.optimize_path(max_iter=100)
    print(f"Path: {result.path}")
    print(f"Cost: {result.total_cost:.2f} | Method: {result.method}")
    print(f"Summary: {opt.summary()}")
