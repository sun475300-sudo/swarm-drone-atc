"""
Multi-UAV Coordination Protocol
Phase 375 - Task Allocation, Collision Avoidance, Cooperative Sensing
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Tuple
import random


@dataclass
class UAVTask:
    task_id: str
    position: Tuple[float, float, float]
    priority: int
    duration: float


class TaskAllocator:
    def __init__(self):
        self.tasks: List[UAVTask] = []
        self.assignments: Dict[str, str] = {}

    def add_task(self, task: UAVTask):
        self.tasks.append(task)

    def allocate(self, uavs: List[str]) -> Dict[str, str]:
        self.tasks.sort(key=lambda t: t.priority, reverse=True)
        for task in self.tasks:
            if not uavs:
                break
            uav = uavs.pop(0)
            self.assignments[task.task_id] = uav
        return self.assignments


class CollisionAvoider:
    def __init__(self, safe_distance: float = 5.0):
        self.safe_distance = safe_distance

    def check_collision(self, pos1: Tuple, pos2: Tuple) -> bool:
        d = np.linalg.norm(np.array(pos1) - np.array(pos2))
        return d < self.safe_distance


def simulate_coordination():
    print("=== Multi-UAV Coordination ===")
    allocator = TaskAllocator()
    for i in range(5):
        allocator.add_task(
            UAVTask(f"task_{i}", (i * 10, 0, 50), random.randint(1, 10), 5.0)
        )

    uavs = [f"uav_{i}" for i in range(5)]
    assignments = allocator.allocate(uavs)
    print(f"Assignments: {len(assignments)}")
    return {"assignments": len(assignments)}


if __name__ == "__main__":
    simulate_coordination()
