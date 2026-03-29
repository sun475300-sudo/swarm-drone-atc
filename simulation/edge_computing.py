"""Edge Computing Module for Phase 240-259.

Provides edge computing capabilities for drone swarm ATC operations.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import numpy as np


class EdgeDeviceType(Enum):
    """Types of edge devices."""

    DRONE = "drone"
    GATEWAY = "gateway"
    ACCESS_POINT = "access_point"
    EDGE_SERVER = "edge_server"
    FOG_NODE = "fog_node"


class TaskOffloadStrategy(Enum):
    """Task offloading strategies."""

    LOCAL = "local"
    EDGE = "edge"
    CLOUD = "cloud"
    HYBRID = "hybrid"


@dataclass
class EdgeDevice:
    """Represents an edge computing device."""

    device_id: str
    device_type: EdgeDeviceType
    compute_capacity: float
    memory_capacity: float
    storage_capacity: float
    bandwidth: float
    latency: float
    battery_level: float = 100.0
    is_active: bool = True
    current_load: float = 0.0


@dataclass
class OffloadTask:
    """Represents a task that can be offloaded."""

    task_id: str
    task_type: str
    compute_requirement: float
    memory_requirement: float
    deadline: float
    priority: int = 1
    data_size: float = 0.0


class EdgeComputingManager:
    """Manages edge computing resources and task offloading."""

    def __init__(self):
        self.devices: dict[str, EdgeDevice] = {}
        self.task_queue: list[OffloadTask] = []
        self.offload_history: list[dict] = []

    def register_device(self, device: EdgeDevice) -> None:
        """Register an edge device."""
        self.devices[device.device_id] = device

    def select_offload_strategy(self, task: OffloadTask) -> TaskOffloadStrategy:
        """Select optimal offload strategy for a task."""
        if task.deadline < time.time() + 0.1:
            return TaskOffloadStrategy.LOCAL

        if self._has_sufficient_edge_capacity(task):
            return TaskOffloadStrategy.EDGE

        return TaskOffloadStrategy.CLOUD

    def _has_sufficient_edge_capacity(self, task: OffloadTask) -> bool:
        """Check if edge has sufficient capacity."""
        for device in self.devices.values():
            if device.is_active and device.current_load < 80:
                if device.compute_capacity >= task.compute_requirement:
                    return True
        return False

    def offload_task(self, task: OffloadTask, target_device_id: str) -> bool:
        """Offload task to a target device."""
        device = self.devices.get(target_device_id)
        if not device or not device.is_active:
            return False

        if device.current_load + task.compute_requirement > 100:
            return False

        device.current_load += task.compute_requirement
        self.offload_history.append(
            {
                "task_id": task.task_id,
                "target_device": target_device_id,
                "timestamp": time.time(),
            }
        )
        return True


def create_edge_network(
    num_gateways: int = 3, num_edge_servers: int = 2
) -> EdgeComputingManager:
    """Create an edge computing network."""
    manager = EdgeComputingManager()

    for i in range(num_gateways):
        manager.register_device(
            EdgeDevice(
                device_id=f"gateway_{i}",
                device_type=EdgeDeviceType.GATEWAY,
                compute_capacity=5000,
                memory_capacity=8192,
                storage_capacity=32768,
                bandwidth=1000,
                latency=5.0,
            )
        )

    for i in range(num_edge_servers):
        manager.register_device(
            EdgeDevice(
                device_id=f"edge_server_{i}",
                device_type=EdgeDeviceType.EDGE_SERVER,
                compute_capacity=20000,
                memory_capacity=32768,
                storage_capacity=1048576,
                bandwidth=10000,
                latency=2.0,
            )
        )

    return manager
