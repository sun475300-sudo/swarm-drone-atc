"""
Phase 419: Federated Edge Computer for Distributed Inference
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import time


class EdgeDeviceType(Enum):
    DRONE = "drone"
    EDGE_SERVER = "edge_server"
    GATEWAY = "gateway"


@dataclass
class EdgeDevice:
    device_id: str
    device_type: EdgeDeviceType
    compute_capacity: float
    memory_mb: float
    battery_level: float
    is_online: bool


@dataclass
class InferenceTask:
    task_id: str
    model_name: str
    input_data: np.ndarray
    priority: int
    deadline: float


class FederatedEdgeComputer:
    def __init__(
        self,
        federation_id: str,
        load_balancing: str = "memory_based",
    ):
        self.federation_id = federation_id
        self.load_balancing = load_balancing

        self.devices: Dict[str, EdgeDevice] = {}
        self.task_queue: List[InferenceTask] = []
        self.active_tasks: Dict[str, str] = {}

        self._initialize_devices()

    def _initialize_devices(self):
        for i in range(10):
            device_id = f"drone_{i}"
            self.register_device(
                device_id=device_id,
                device_type=EdgeDeviceType.DRONE,
                compute_capacity=np.random.uniform(1, 5),
                memory_mb=np.random.uniform(512, 2048),
                battery_level=np.random.uniform(0.5, 1.0),
            )

        for i in range(3):
            device_id = f"edge_{i}"
            self.register_device(
                device_id=device_id,
                device_type=EdgeDeviceType.EDGE_SERVER,
                compute_capacity=np.random.uniform(20, 50),
                memory_mb=np.random.uniform(8192, 32768),
                battery_level=1.0,
            )

    def register_device(
        self,
        device_id: str,
        device_type: EdgeDeviceType,
        compute_capacity: float,
        memory_mb: float,
        battery_level: float,
    ):
        device = EdgeDevice(
            device_id=device_id,
            device_type=device_type,
            compute_capacity=compute_capacity,
            memory_mb=memory_mb,
            battery_level=battery_level,
            is_online=True,
        )
        self.devices[device_id] = device

    def submit_task(self, task: InferenceTask):
        self.task_queue.append(task)
        self.task_queue.sort(key=lambda t: t.priority)

    def schedule_task(self, task_id: str) -> Optional[str]:
        for task in self.task_queue:
            if task.task_id == task_id:
                break
        else:
            return None

        target_device = self._select_device(task)

        if target_device:
            self.task_queue = [t for t in self.task_queue if t.task_id != task_id]
            self.active_tasks[task_id] = target_device.device_id
            return target_device.device_id

        return None

    def _select_device(self, task: InferenceTask) -> Optional[EdgeDevice]:
        candidates = [d for d in self.devices.values() if d.is_online]

        if not candidates:
            return None

        if self.load_balancing == "memory_based":
            return max(candidates, key=lambda d: d.memory_mb)
        elif self.load_balancing == "compute_based":
            return max(candidates, key=lambda d: d.compute_capacity)
        else:
            return candidates[0]

    def complete_task(self, task_id: str):
        if task_id in self.active_tasks:
            del self.active_tasks[task_id]

    def get_federation_status(self) -> Dict[str, Any]:
        return {
            "federation_id": self.federation_id,
            "total_devices": len(self.devices),
            "online_devices": sum(1 for d in self.devices.values() if d.is_online),
            "queued_tasks": len(self.task_queue),
            "active_tasks": len(self.active_tasks),
        }
