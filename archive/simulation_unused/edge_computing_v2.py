"""
Phase 441: Edge Computing v2 Engine
Advanced edge computing for drone swarm: MEC, fog computing, task offloading.
"""

import numpy as np
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Optional, Tuple, Any, Callable


class ComputeType(Enum):
    """Edge compute types."""

    MEC = auto()  # Mobile Edge Computing
    FOG = auto()  # Fog Computing
    CLOUD = auto()  # Cloud
    LOCAL = auto()  # On-device


class TaskPriority(Enum):
    """Task priority levels."""

    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class ComputeNode:
    """Edge compute node."""

    node_id: str
    compute_type: ComputeType
    position: np.ndarray
    cpu_cores: int = 8
    memory_gb: float = 16.0
    gpu_count: int = 0
    bandwidth_mbps: float = 1000.0
    latency_ms: float = 1.0
    load_percent: float = 0.0
    is_active: bool = True


@dataclass
class ComputeTask:
    """Compute task."""

    task_id: str
    drone_id: str
    task_type: str
    compute_demand: float
    memory_demand: float
    data_size_mb: float
    deadline_ms: float
    priority: TaskPriority = TaskPriority.MEDIUM
    assigned_node: Optional[str] = None
    status: str = "pending"
    start_time: float = 0.0
    end_time: float = 0.0


@dataclass
class OffloadingDecision:
    """Task offloading decision."""

    task_id: str
    source_drone: str
    target_node: str
    estimated_latency: float
    estimated_energy: float
    success_probability: float


class EdgeComputingEngine:
    """Edge computing engine for drone swarm."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.nodes: Dict[str, ComputeNode] = {}
        self.tasks: Dict[str, ComputeTask] = {}
        self.task_queue: List[str] = []
        self.completed_tasks: List[str] = []
        self.offloading_decisions: List[OffloadingDecision] = []

    def add_node(
        self, node_id: str, compute_type: ComputeType, position: np.ndarray, **kwargs
    ) -> ComputeNode:
        node = ComputeNode(node_id, compute_type, position, **kwargs)
        self.nodes[node_id] = node
        return node

    def submit_task(self, task: ComputeTask) -> str:
        self.tasks[task.task_id] = task
        self.task_queue.append(task.task_id)
        return task.task_id

    def find_optimal_node(
        self, task: ComputeTask, drone_position: np.ndarray
    ) -> Optional[str]:
        best_node = None
        best_score = -np.inf
        for node_id, node in self.nodes.items():
            if not node.is_active:
                continue
            if node.load_percent > 90:
                continue
            distance = np.linalg.norm(node.position - drone_position)
            latency = node.latency_ms + distance / 3e5
            score = -latency - node.load_percent * 0.1
            if task.priority == TaskPriority.CRITICAL:
                score -= latency * 10
            if score > best_score:
                best_score = score
                best_node = node_id
        return best_node

    def make_offloading_decision(
        self, task: ComputeTask, drone_position: np.ndarray
    ) -> OffloadingDecision:
        target = self.find_optimal_node(task, drone_position)
        if target is None:
            target = "local"
        node = self.nodes.get(target)
        if node:
            distance = np.linalg.norm(node.position - drone_position)
            latency = (
                node.latency_ms
                + distance / 3e5
                + task.data_size_mb / node.bandwidth_mbps
            )
            energy = task.compute_demand * 0.01 + distance * 0.001
            success_prob = max(0, 1 - node.load_percent / 100)
        else:
            latency = 0.1
            energy = task.compute_demand * 0.1
            success_prob = 0.99
        decision = OffloadingDecision(
            task.task_id, task.drone_id, target, latency, energy, success_prob
        )
        self.offloading_decisions.append(decision)
        return decision

    def execute_task(self, task_id: str) -> bool:
        if task_id not in self.tasks:
            return False
        task = self.tasks[task_id]
        decision = self.make_offloading_decision(task, np.zeros(3))
        task.assigned_node = decision.target_node
        task.status = "running"
        task.start_time = time.time()
        if decision.target_node in self.nodes:
            self.nodes[decision.target_node].load_percent += task.compute_demand
        task.end_time = task.start_time + decision.estimated_latency / 1000
        task.status = "completed"
        self.completed_tasks.append(task_id)
        if task_id in self.task_queue:
            self.task_queue.remove(task_id)
        return True

    def process_queue(self, max_tasks: int = 10) -> int:
        processed = 0
        for task_id in list(self.task_queue[:max_tasks]):
            if self.execute_task(task_id):
                processed += 1
        return processed

    def get_stats(self) -> Dict[str, Any]:
        active_nodes = sum(1 for n in self.nodes.values() if n.is_active)
        avg_load = (
            np.mean([n.load_percent for n in self.nodes.values()]) if self.nodes else 0
        )
        return {
            "total_nodes": len(self.nodes),
            "active_nodes": active_nodes,
            "pending_tasks": len(self.task_queue),
            "completed_tasks": len(self.completed_tasks),
            "avg_node_load": avg_load,
            "offloading_decisions": len(self.offloading_decisions),
        }


class DroneEdgeOrchestrator:
    """Edge orchestrator for drone swarm."""

    def __init__(self, n_drones: int, seed: int = 42):
        self.n_drones = n_drones
        self.rng = np.random.default_rng(seed)
        self.engine = EdgeComputingEngine(seed)
        self._init_infrastructure()

    def _init_infrastructure(self) -> None:
        self.engine.add_node(
            "mec_0",
            ComputeType.MEC,
            np.array([500, 500, 0]),
            cpu_cores=32,
            memory_gb=64,
            gpu_count=4,
            bandwidth_mbps=10000,
        )
        self.engine.add_node(
            "fog_0",
            ComputeType.FOG,
            np.array([250, 250, 50]),
            cpu_cores=16,
            memory_gb=32,
            gpu_count=1,
            bandwidth_mbps=5000,
        )
        self.engine.add_node(
            "fog_1",
            ComputeType.FOG,
            np.array([750, 750, 50]),
            cpu_cores=16,
            memory_gb=32,
            gpu_count=1,
            bandwidth_mbps=5000,
        )

    def submit_drone_task(
        self, drone_id: str, task_type: str, compute_demand: float = 10.0
    ) -> str:
        task = ComputeTask(
            task_id=f"task_{drone_id}_{int(time.time() * 1000)}",
            drone_id=drone_id,
            task_type=task_type,
            compute_demand=compute_demand,
            memory_demand=compute_demand * 0.5,
            data_size_mb=compute_demand * 10,
            deadline_ms=100.0,
            priority=TaskPriority.MEDIUM,
        )
        return self.engine.submit_task(task)

    def process_all_tasks(self) -> int:
        return self.engine.process_queue(100)

    def get_orchestration_stats(self) -> Dict[str, Any]:
        return self.engine.get_stats()


if __name__ == "__main__":
    orchestrator = DroneEdgeOrchestrator(n_drones=10, seed=42)
    for i in range(10):
        orchestrator.submit_drone_task(f"drone_{i}", "vision_processing", 15.0)
    processed = orchestrator.process_all_tasks()
    print(f"Processed: {processed}")
    print(f"Stats: {orchestrator.get_orchestration_stats()}")
