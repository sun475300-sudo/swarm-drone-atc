"""
Phase 443: Load Balancing Controller for Swarm Tasks
"""

import numpy as np
from typing import Dict, List
from dataclasses import dataclass
import time


@dataclass
class TaskLoad:
    task_id: str
    compute_required: float
    memory_required_mb: float
    priority: int


@dataclass
class DroneLoad:
    drone_id: str
    current_compute: float
    current_memory_mb: float
    available: bool


class LoadBalancingController:
    def __init__(self):
        self.task_queue: List[TaskLoad] = []
        self.drone_loads: Dict[str, DroneLoad] = {}
        self.assignments: Dict[str, str] = {}

    def register_drone(
        self, drone_id: str, capacity_compute: float, capacity_memory: float
    ):
        self.drone_loads[drone_id] = DroneLoad(
            drone_id=drone_id, current_compute=0, current_memory_mb=0, available=True
        )

    def submit_task(self, task: TaskLoad):
        self.task_queue.append(task)
        self.task_queue.sort(key=lambda t: -t.priority)

    def balance(self) -> Dict[str, str]:
        new_assignments = {}

        while self.task_queue and any(d.available for d in self.drone_loads.values()):
            task = self.task_queue.pop(0)

            best_drone = None
            best_score = float("inf")

            for drone_id, load in self.drone_loads.items():
                if not load.available:
                    continue

                score = load.current_compute + load.current_memory_mb / 1000

                if score < best_score:
                    best_score = score
                    best_drone = drone_id

            if best_drone:
                new_assignments[task.task_id] = best_drone
                self.drone_loads[best_drone].current_compute += task.compute_required
                self.drone_loads[
                    best_drone
                ].current_memory_mb += task.memory_required_mb

        self.assignments.update(new_assignments)
        return new_assignments

    def get_load_stats(self) -> Dict:
        total_compute = sum(d.current_compute for d in self.drone_loads.values())
        total_memory = sum(d.current_memory_mb for d in self.drone_loads.values())

        return {
            "pending_tasks": len(self.task_queue),
            "active_drones": len(self.drone_loads),
            "total_compute_load": total_compute,
            "total_memory_load_mb": total_memory,
        }
