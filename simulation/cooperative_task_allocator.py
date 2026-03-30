"""Phase 281: Cooperative Task Allocation — 협력적 작업 할당 시스템.

Hungarian Algorithm + Auction 기반의 다중 드론 작업 분배.
드론 능력, 배터리, 거리를 고려한 최적 할당을 수행합니다.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class TaskPriority(Enum):
    CRITICAL = 4
    HIGH = 3
    MEDIUM = 2
    LOW = 1


class TaskStatus(Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    task_id: str
    position: np.ndarray
    priority: TaskPriority = TaskPriority.MEDIUM
    required_payload: float = 0.0
    deadline_sec: float = 300.0
    status: TaskStatus = TaskStatus.PENDING
    assigned_drone: Optional[str] = None
    reward: float = 1.0


@dataclass
class DroneCapability:
    drone_id: str
    position: np.ndarray
    battery_pct: float = 100.0
    max_payload: float = 5.0
    speed_ms: float = 15.0
    available: bool = True


class HungarianSolver:
    """간이 Hungarian 알고리즘 (비용 행렬 기반)."""

    @staticmethod
    def solve(cost_matrix: np.ndarray) -> List[Tuple[int, int]]:
        n, m = cost_matrix.shape
        assignments = []
        used_cols = set()
        for _ in range(min(n, m)):
            best_val = np.inf
            best_r, best_c = -1, -1
            for r in range(n):
                if any(a[0] == r for a in assignments):
                    continue
                for c in range(m):
                    if c in used_cols:
                        continue
                    if cost_matrix[r, c] < best_val:
                        best_val = cost_matrix[r, c]
                        best_r, best_c = r, c
            if best_r >= 0:
                assignments.append((best_r, best_c))
                used_cols.add(best_c)
        return assignments


class AuctionAllocator:
    """경매 기반 분산 할당."""

    def __init__(self, epsilon: float = 0.1):
        self.epsilon = epsilon

    def allocate(self, bids: Dict[str, Dict[str, float]]) -> Dict[str, str]:
        """bids: {drone_id: {task_id: bid_value}}. Returns {task_id: drone_id}."""
        allocation: Dict[str, str] = {}
        task_prices: Dict[str, float] = {}
        for drone_id, task_bids in bids.items():
            for task_id, bid in task_bids.items():
                current_price = task_prices.get(task_id, 0.0)
                if bid > current_price + self.epsilon:
                    # Remove previous winner
                    if task_id in allocation:
                        pass  # previous drone loses
                    allocation[task_id] = drone_id
                    task_prices[task_id] = bid
        return allocation


class CooperativeTaskAllocator:
    """협력적 작업 할당기.

    - 비용 행렬 기반 할당 (Hungarian)
    - 경매 기반 분산 할당
    - 동적 재할당 (드론 장애 시)
    - 우선순위 기반 스케줄링
    """

    def __init__(self, rng_seed: int = 42):
        self._rng = np.random.default_rng(rng_seed)
        self._tasks: Dict[str, Task] = {}
        self._drones: Dict[str, DroneCapability] = {}
        self._allocations: Dict[str, str] = {}  # task_id -> drone_id
        self._history: List[dict] = []
        self._auction = AuctionAllocator()

    def add_task(self, task: Task):
        self._tasks[task.task_id] = task

    def register_drone(self, drone: DroneCapability):
        self._drones[drone.drone_id] = drone

    def _compute_cost(self, drone: DroneCapability, task: Task) -> float:
        dist = np.linalg.norm(drone.position - task.position)
        time_cost = dist / max(drone.speed_ms, 0.1)
        battery_cost = max(0, 50.0 - drone.battery_pct) * 2.0
        payload_penalty = 0.0 if drone.max_payload >= task.required_payload else 1000.0
        priority_bonus = -task.priority.value * 10.0
        return time_cost + battery_cost + payload_penalty + priority_bonus

    def allocate_hungarian(self) -> Dict[str, str]:
        available_drones = [d for d in self._drones.values() if d.available]
        pending_tasks = [t for t in self._tasks.values() if t.status == TaskStatus.PENDING]
        if not available_drones or not pending_tasks:
            return {}
        n_d, n_t = len(available_drones), len(pending_tasks)
        cost = np.full((n_d, n_t), 1e6)
        for i, drone in enumerate(available_drones):
            for j, task in enumerate(pending_tasks):
                cost[i, j] = self._compute_cost(drone, task)
        assignments = HungarianSolver.solve(cost)
        result = {}
        for di, ti in assignments:
            drone = available_drones[di]
            task = pending_tasks[ti]
            if cost[di, ti] < 1e5:
                task.status = TaskStatus.ASSIGNED
                task.assigned_drone = drone.drone_id
                self._allocations[task.task_id] = drone.drone_id
                result[task.task_id] = drone.drone_id
                self._history.append({"event": "assign", "task": task.task_id, "drone": drone.drone_id, "method": "hungarian"})
        return result

    def allocate_auction(self) -> Dict[str, str]:
        available_drones = [d for d in self._drones.values() if d.available]
        pending_tasks = [t for t in self._tasks.values() if t.status == TaskStatus.PENDING]
        if not available_drones or not pending_tasks:
            return {}
        bids: Dict[str, Dict[str, float]] = {}
        for drone in available_drones:
            bids[drone.drone_id] = {}
            for task in pending_tasks:
                cost = self._compute_cost(drone, task)
                bids[drone.drone_id][task.task_id] = 1000.0 - cost  # higher bid = lower cost
        allocation = self._auction.allocate(bids)
        for task_id, drone_id in allocation.items():
            task = self._tasks[task_id]
            task.status = TaskStatus.ASSIGNED
            task.assigned_drone = drone_id
            self._allocations[task_id] = drone_id
            self._history.append({"event": "assign", "task": task_id, "drone": drone_id, "method": "auction"})
        return allocation

    def complete_task(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if not task:
            return False
        task.status = TaskStatus.COMPLETED
        self._history.append({"event": "complete", "task": task_id})
        return True

    def fail_task(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if not task:
            return False
        task.status = TaskStatus.FAILED
        task.assigned_drone = None
        if task_id in self._allocations:
            del self._allocations[task_id]
        self._history.append({"event": "fail", "task": task_id})
        return True

    def reallocate(self) -> Dict[str, str]:
        """실패한 작업을 재할당."""
        failed = [t for t in self._tasks.values() if t.status == TaskStatus.FAILED]
        for t in failed:
            t.status = TaskStatus.PENDING
        return self.allocate_hungarian()

    def get_allocation(self, task_id: str) -> Optional[str]:
        return self._allocations.get(task_id)

    def summary(self) -> dict:
        statuses = {}
        for t in self._tasks.values():
            statuses[t.status.value] = statuses.get(t.status.value, 0) + 1
        return {
            "total_tasks": len(self._tasks),
            "total_drones": len(self._drones),
            "allocations": len(self._allocations),
            "task_statuses": statuses,
            "history_events": len(self._history),
        }
