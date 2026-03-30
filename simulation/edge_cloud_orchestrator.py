"""
Phase 409: Edge-Cloud Orchestrator for Dynamic Resource Allocation
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import time
from collections import defaultdict


class ResourceType(Enum):
    COMPUTE = "compute"
    STORAGE = "storage"
    BANDWIDTH = "bandwidth"
    MEMORY = "memory"


class DeploymentTier(Enum):
    DRONE = "drone"
    EDGE = "edge"
    CLOUD = "cloud"


@dataclass
class ComputeNode:
    node_id: str
    tier: DeploymentTier
    capacity: Dict[ResourceType, float]
    available: Dict[ResourceType, float]
    latency_to_drones: Dict[str, float]
    cost_per_unit: float
    is_active: bool = True


@dataclass
class Workload:
    workload_id: str
    drone_id: str
    required_resources: Dict[ResourceType, float]
    priority: int
    deadline: float
    created_at: float
    tier_preference: List[DeploymentTier] = field(default_factory=list)


@dataclass
class Placement:
    workload_id: str
    node_id: str
    allocated_resources: Dict[ResourceType, float]
    start_time: float
    estimated_completion: float


class EdgeCloudOrchestrator:
    def __init__(
        self,
        latency_threshold_ms: float = 50.0,
        cost_weight: float = 0.3,
        latency_weight: float = 0.5,
        availability_weight: float = 0.2,
    ):
        self.latency_threshold_ms = latency_threshold_ms
        self.cost_weight = cost_weight
        self.latency_weight = latency_weight
        self.availability_weight = availability_weight

        self.nodes: Dict[str, ComputeNode] = {}
        self.workloads: Dict[str, Workload] = {}
        self.placements: Dict[str, Placement] = {}

        self.resource_history: Dict[
            str, List[Tuple[float, Dict[ResourceType, float]]]
        ] = []

        self._initialize_infrastructure()

    def _initialize_infrastructure(self):
        edge_nodes = [
            ("edge_1", "192.168.1.10", 100),
            ("edge_2", "192.168.1.11", 100),
            ("edge_3", "192.168.1.12", 80),
        ]

        for node_id, ip, capacity in edge_nodes:
            self.add_node(
                node_id=node_id,
                tier=DeploymentTier.EDGE,
                compute_capacity=capacity,
                storage_capacity=capacity * 10,
                bandwidth_capacity=capacity * 0.5,
                memory_capacity=capacity * 2,
                cost_per_unit=0.01,
            )

        cloud_nodes = [
            ("cloud_1", "10.0.0.1", 500),
            ("cloud_2", "10.0.0.2", 500),
        ]

        for node_id, ip, capacity in cloud_nodes:
            self.add_node(
                node_id=node_id,
                tier=DeploymentTier.CLOUD,
                compute_capacity=capacity,
                storage_capacity=capacity * 20,
                bandwidth_capacity=capacity * 1.0,
                memory_capacity=capacity * 4,
                cost_per_unit=0.001,
            )

    def add_node(
        self,
        node_id: str,
        tier: DeploymentTier,
        compute_capacity: float,
        storage_capacity: float,
        bandwidth_capacity: float,
        memory_capacity: float,
        cost_per_unit: float,
    ):
        capacity = {
            ResourceType.COMPUTE: compute_capacity,
            ResourceType.STORAGE: storage_capacity,
            ResourceType.BANDWIDTH: bandwidth_capacity,
            ResourceType.MEMORY: memory_capacity,
        }

        node = ComputeNode(
            node_id=node_id,
            tier=tier,
            capacity=capacity.copy(),
            available=capacity.copy(),
            latency_to_drones={},
            cost_per_unit=cost_per_unit,
        )

        self.nodes[node_id] = node

    def update_drone_latency(self, node_id: str, drone_id: str, latency_ms: float):
        if node_id in self.nodes:
            self.nodes[node_id].latency_to_drones[drone_id] = latency_ms

    def submit_workload(self, workload: Workload) -> bool:
        self.workloads[workload.workload_id] = workload
        return True

    def schedule_workload(self, workload_id: str) -> Optional[Placement]:
        if workload_id not in self.workloads:
            return None

        workload = self.workloads[workload_id]

        if workload.tier_preference:
            candidate_nodes = [
                node
                for node in self.nodes.values()
                if node.is_active and node.tier in workload.tier_preference
            ]
        else:
            candidate_nodes = [node for node in self.nodes.values() if node.is_active]

        best_node = None
        best_score = float("inf")

        for node in candidate_nodes:
            if not self._can_allocate(node, workload.required_resources):
                continue

            latency = node.latency_to_drones.get(workload.drone_id, 100.0)

            if latency > self.latency_threshold_ms and node.tier == DeploymentTier.EDGE:
                continue

            score = self._calculate_placement_score(node, workload, latency)

            if score < best_score:
                best_score = score
                best_node = node

        if best_node is None:
            return None

        placement = self._allocate_resources(best_node, workload)

        self.placements[workload_id] = placement

        return placement

    def _can_allocate(
        self,
        node: ComputeNode,
        required: Dict[ResourceType, float],
    ) -> bool:
        for resource_type, amount in required.items():
            if node.available.get(resource_type, 0) < amount:
                return False
        return True

    def _calculate_placement_score(
        self,
        node: ComputeNode,
        workload: Workload,
        latency_ms: float,
    ) -> float:
        utilization = 1.0 - (
            node.available[ResourceType.COMPUTE] / node.capacity[ResourceType.COMPUTE]
        )

        cost_score = node.cost_per_unit * workload.required_resources.get(
            ResourceType.COMPUTE, 0
        )

        latency_score = latency_ms / 100.0

        availability_score = utilization

        total_score = (
            self.cost_weight * cost_score
            + self.latency_weight * latency_score
            + self.availability_weight * availability_score
        )

        return total_score

    def _allocate_resources(self, node: ComputeNode, workload: Workload) -> Placement:
        allocated = {}

        for resource_type, amount in workload.required_resources.items():
            node.available[resource_type] -= amount
            allocated[resource_type] = amount

        now = time.time()
        estimated_completion = now + (workload.deadline - now) * 0.5

        return Placement(
            workload_id=workload.workload_id,
            node_id=node.node_id,
            allocated_resources=allocated,
            start_time=now,
            estimated_completion=estimated_completion,
        )

    def complete_workload(self, workload_id: str):
        if workload_id not in self.placements:
            return

        placement = self.placements[workload_id]

        if placement.node_id in self.nodes:
            node = self.nodes[placement.node_id]
            for resource_type, amount in placement.allocated_resources.items():
                node.available[resource_type] = min(
                    node.available.get(resource_type, 0) + amount,
                    node.capacity[resource_type],
                )

        if workload_id in self.workloads:
            del self.workloads[workload_id]

        del self.placements[workload_id]

    def get_system_status(self) -> Dict[str, Any]:
        status = {
            "total_nodes": len(self.nodes),
            "active_nodes": len([n for n in self.nodes.values() if n.is_active]),
            "total_workloads": len(self.workloads),
            "running_placements": len(self.placements),
            "nodes": {},
        }

        for node_id, node in self.nodes.items():
            utilization = {
                resource: 1.0
                - (node.available.get(resource, 0) / node.capacity.get(resource, 1))
                for resource in ResourceType
            }
            status["nodes"][node_id] = {
                "tier": node.tier.value,
                "utilization": utilization,
                "is_active": node.is_active,
            }

        return status

    def scale_node(self, node_id: str, scale_factor: float):
        if node_id not in self.nodes:
            return

        node = self.nodes[node_id]

        for resource in ResourceType:
            node.capacity[resource] *= scale_factor
            node.available[resource] *= scale_factor

    def failover_node(self, failed_node_id: str) -> List[str]:
        if failed_node_id not in self.nodes:
            return []

        self.nodes[failed_node_id].is_active = False

        relocated_workloads = []

        for workload_id, placement in list(self.placements.items()):
            if placement.node_id == failed_node_id:
                new_placement = self.schedule_workload(workload_id)
                if new_placement:
                    relocated_workloads.append(workload_id)
                else:
                    del self.placements[workload_id]

        return relocated_workloads
