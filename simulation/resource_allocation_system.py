"""
Phase 457: Resource Allocation System for Efficient Computing
"""

import numpy as np
from typing import Dict, List
from dataclasses import dataclass
import time


@dataclass
class ResourceRequest:
    request_id: str
    task_type: str
    compute_units: float
    memory_mb: float
    priority: int


class ResourceAllocationSystem:
    def __init__(self, total_compute: float = 1000, total_memory: float = 10000):
        self.total_compute = total_compute
        self.total_memory = total_memory
        self.allocated_compute = 0
        self.allocated_memory = 0
        self.pending_requests: List[ResourceRequest] = []
        self.active_allocations: Dict[str, ResourceRequest] = {}

    def request_resources(self, request: ResourceRequest) -> bool:
        available_compute = self.total_compute - self.allocated_compute
        available_memory = self.total_memory - self.allocated_memory

        if (
            request.compute_units <= available_compute
            and request.memory_mb <= available_memory
        ):
            self.active_allocations[request.request_id] = request
            self.allocated_compute += request.compute_units
            self.allocated_memory += request.memory_mb
            return True

        self.pending_requests.append(request)
        self.pending_requests.sort(key=lambda r: -r.priority)
        return False

    def release_resources(self, request_id: str):
        if request_id in self.active_allocations:
            req = self.active_allocations[request_id]
            self.allocated_compute -= req.compute_units
            self.allocated_memory -= req.memory_mb
            del self.active_allocations[request_id]

    def get_available_resources(self) -> Dict:
        return {
            "compute": self.total_compute - self.allocated_compute,
            "memory": self.total_memory - self.allocated_memory,
        }
