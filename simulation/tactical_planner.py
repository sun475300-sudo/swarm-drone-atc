"""
Phase 508: Tactical Mission Planner
다중 목표 할당, 시간-공간 최적화, 동적 재계획.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple
import heapq


class MissionPriority(Enum):
    CRITICAL = 4
    HIGH = 3
    MEDIUM = 2
    LOW = 1
    ROUTINE = 0


class TaskStatus(Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    REASSIGNED = "reassigned"


@dataclass
class MissionTask:
    task_id: str
    position: np.ndarray
    priority: MissionPriority
    duration_s: float
    deadline_s: float
    status: TaskStatus = TaskStatus.PENDING
    assigned_drone: str = ""
    reward: float = 1.0


@dataclass
class DroneCapability:
    drone_id: str
    position: np.ndarray
    speed_ms: float
    endurance_s: float
    payload_kg: float
    sensors: List[str] = field(default_factory=list)


@dataclass
class Assignment:
    drone_id: str
    task_id: str
    eta_s: float
    cost: float
    path: List[np.ndarray] = field(default_factory=list)


class HungarianAssigner:
    """Task assignment using auction-based approximation."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)

    def compute_cost_matrix(self, drones: List[DroneCapability],
                            tasks: List[MissionTask]) -> np.ndarray:
        n_d = len(drones)
        n_t = len(tasks)
        cost = np.full((n_d, n_t), 1e6)
        for i, d in enumerate(drones):
            for j, t in enumerate(tasks):
                dist = np.linalg.norm(d.position - t.position)
                travel_time = dist / max(d.speed_ms, 0.1)
                if travel_time + t.duration_s <= d.endurance_s:
                    priority_bonus = t.priority.value * 100
                    cost[i, j] = travel_time - priority_bonus + t.duration_s
        return cost

    def assign(self, drones: List[DroneCapability],
               tasks: List[MissionTask]) -> List[Assignment]:
        if not drones or not tasks:
            return []
        cost = self.compute_cost_matrix(drones, tasks)
        assignments = []
        assigned_tasks = set()

        for _ in range(min(len(drones), len(tasks))):
            best_val = 1e6
            best_i, best_j = -1, -1
            for i in range(len(drones)):
                for j in range(len(tasks)):
                    if j not in assigned_tasks and cost[i, j] < best_val:
                        best_val = cost[i, j]
                        best_i, best_j = i, j
            if best_i >= 0 and best_val < 1e5:
                d = drones[best_i]
                t = tasks[best_j]
                dist = np.linalg.norm(d.position - t.position)
                eta = dist / max(d.speed_ms, 0.1)
                assignments.append(Assignment(d.drone_id, t.task_id, eta, best_val))
                assigned_tasks.add(best_j)
                cost[best_i, :] = 1e6
        return assignments


class TemporalScheduler:
    """Time-window based scheduling with conflict avoidance."""

    def __init__(self):
        self.timeline: List[Tuple[float, float, str, str]] = []

    def schedule(self, assignments: List[Assignment],
                 tasks: Dict[str, MissionTask]) -> List[Tuple[str, float, float]]:
        schedule = []
        for a in sorted(assignments, key=lambda x: x.eta_s):
            task = tasks.get(a.task_id)
            if not task:
                continue
            start = a.eta_s
            for _, end, _, existing_drone in self.timeline:
                if existing_drone == a.drone_id and end > start:
                    start = end
            end_time = start + task.duration_s
            self.timeline.append((start, end_time, a.task_id, a.drone_id))
            schedule.append((a.task_id, start, end_time))
        return schedule


class TacticalPlanner:
    """Integrated tactical mission planning system."""

    def __init__(self, n_drones: int = 20, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_drones = n_drones
        self.assigner = HungarianAssigner(seed)
        self.scheduler = TemporalScheduler()
        self.tasks: Dict[str, MissionTask] = {}
        self.drones: Dict[str, DroneCapability] = {}
        self.assignments: List[Assignment] = []
        self._task_counter = 0

        for i in range(n_drones):
            pos = self.rng.uniform(-500, 500, 3)
            pos[2] = self.rng.uniform(30, 120)
            self.drones[f"drone_{i}"] = DroneCapability(
                f"drone_{i}", pos, self.rng.uniform(5, 15),
                self.rng.uniform(600, 1800), self.rng.uniform(0.5, 5),
                self.rng.choice(["camera", "lidar", "thermal", "radio"],
                               size=self.rng.integers(1, 4)).tolist())

    def add_task(self, position: np.ndarray, priority: MissionPriority = MissionPriority.MEDIUM,
                 duration: float = 60, deadline: float = 600) -> MissionTask:
        self._task_counter += 1
        task = MissionTask(f"TASK-{self._task_counter:04d}", position,
                          priority, duration, deadline,
                          reward=priority.value * 10 + 10)
        self.tasks[task.task_id] = task
        return task

    def generate_mission(self, n_tasks: int = 15) -> List[MissionTask]:
        tasks = []
        for _ in range(n_tasks):
            pos = self.rng.uniform(-1000, 1000, 3)
            pos[2] = self.rng.uniform(30, 150)
            pri = self.rng.choice(list(MissionPriority))
            task = self.add_task(pos, pri,
                               self.rng.uniform(30, 300),
                               self.rng.uniform(300, 1800))
            tasks.append(task)
        return tasks

    def plan(self) -> Dict:
        drone_list = list(self.drones.values())
        task_list = [t for t in self.tasks.values() if t.status == TaskStatus.PENDING]
        self.assignments = self.assigner.assign(drone_list, task_list)

        for a in self.assignments:
            if a.task_id in self.tasks:
                self.tasks[a.task_id].status = TaskStatus.ASSIGNED
                self.tasks[a.task_id].assigned_drone = a.drone_id

        schedule = self.scheduler.schedule(self.assignments, self.tasks)
        return {
            "assigned": len(self.assignments),
            "unassigned": len(task_list) - len(self.assignments),
            "schedule_entries": len(schedule),
            "avg_eta": round(np.mean([a.eta_s for a in self.assignments]), 1) if self.assignments else 0,
        }

    def replan(self, failed_drone: str) -> Dict:
        affected = [a for a in self.assignments if a.drone_id == failed_drone]
        for a in affected:
            if a.task_id in self.tasks:
                self.tasks[a.task_id].status = TaskStatus.PENDING
                self.tasks[a.task_id].assigned_drone = ""
        self.assignments = [a for a in self.assignments if a.drone_id != failed_drone]
        if failed_drone in self.drones:
            del self.drones[failed_drone]
        return self.plan()

    def summary(self) -> Dict:
        return {
            "drones": len(self.drones),
            "tasks": len(self.tasks),
            "assigned": sum(1 for t in self.tasks.values() if t.status == TaskStatus.ASSIGNED),
            "completed": sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED),
            "assignments": len(self.assignments),
        }
