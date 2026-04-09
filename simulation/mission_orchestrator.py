"""Phase 296: Mission Orchestrator — 미션 오케스트레이터.

복합 미션 분해, DAG 기반 작업 스케줄링,
실시간 미션 진행 추적, 동적 재계획.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple


class MissionType(Enum):
    SURVEILLANCE = "surveillance"
    DELIVERY = "delivery"
    SEARCH_RESCUE = "search_rescue"
    MAPPING = "mapping"
    INSPECTION = "inspection"
    PATROL = "patrol"
    RELAY = "relay"
    CUSTOM = "custom"


class TaskState(Enum):
    WAITING = "waiting"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class MissionTask:
    task_id: str
    mission_id: str
    task_type: str
    position: Optional[np.ndarray] = None
    duration_sec: float = 60.0
    state: TaskState = TaskState.WAITING
    assigned_drone: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    progress: float = 0.0
    priority: int = 5


@dataclass
class Mission:
    mission_id: str
    mission_type: MissionType
    tasks: List[MissionTask] = field(default_factory=list)
    created_at: float = 0.0
    deadline: Optional[float] = None
    status: str = "pending"
    priority: int = 5


class DAGScheduler:
    """DAG 기반 작업 스케줄러."""

    @staticmethod
    def topological_sort(tasks: List[MissionTask]) -> List[str]:
        task_map = {t.task_id: t for t in tasks}
        in_degree = {t.task_id: 0 for t in tasks}
        for t in tasks:
            for dep in t.dependencies:
                if dep in in_degree:
                    in_degree[t.task_id] += 1
        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        result = []
        while queue:
            queue.sort(key=lambda tid: task_map[tid].priority, reverse=True)
            tid = queue.pop(0)
            result.append(tid)
            for t in tasks:
                if tid in t.dependencies:
                    in_degree[t.task_id] -= 1
                    if in_degree[t.task_id] == 0:
                        queue.append(t.task_id)
        return result

    @staticmethod
    def get_ready_tasks(tasks: List[MissionTask]) -> List[MissionTask]:
        completed = {t.task_id for t in tasks if t.state == TaskState.COMPLETED}
        ready = []
        for t in tasks:
            if t.state != TaskState.WAITING:
                continue
            if all(dep in completed for dep in t.dependencies):
                t.state = TaskState.READY
                ready.append(t)
        return ready


class MissionOrchestrator:
    """미션 오케스트레이터.

    - 복합 미션 정의 및 분해
    - DAG 기반 의존성 관리
    - 동적 드론 할당
    - 실시간 진행 추적
    """

    def __init__(self, rng_seed: int = 42):
        self._rng = np.random.default_rng(rng_seed)
        self._missions: Dict[str, Mission] = {}
        self._scheduler = DAGScheduler()
        self._drone_assignments: Dict[str, str] = {}  # drone -> task
        self._history: List[dict] = []

    def create_mission(self, mission_id: str, mission_type: MissionType, priority: int = 5) -> Mission:
        mission = Mission(mission_id=mission_id, mission_type=mission_type, priority=priority)
        self._missions[mission_id] = mission
        return mission

    def add_task(self, mission_id: str, task: MissionTask) -> bool:
        mission = self._missions.get(mission_id)
        if not mission:
            return False
        task.mission_id = mission_id
        mission.tasks.append(task)
        return True

    def start_mission(self, mission_id: str) -> List[MissionTask]:
        mission = self._missions.get(mission_id)
        if not mission:
            return []
        mission.status = "active"
        ready = self._scheduler.get_ready_tasks(mission.tasks)
        self._history.append({"event": "mission_start", "mission": mission_id, "ready_tasks": len(ready)})
        return ready

    def assign_drone(self, task_id: str, drone_id: str) -> bool:
        for mission in self._missions.values():
            for task in mission.tasks:
                if task.task_id == task_id:
                    task.assigned_drone = drone_id
                    task.state = TaskState.RUNNING
                    self._drone_assignments[drone_id] = task_id
                    return True
        return False

    def update_progress(self, task_id: str, progress: float) -> bool:
        for mission in self._missions.values():
            for task in mission.tasks:
                if task.task_id == task_id:
                    task.progress = min(1.0, max(0.0, progress))
                    return True
        return False

    def complete_task(self, task_id: str) -> List[MissionTask]:
        """작업 완료 처리 후 새로 준비된 작업 반환."""
        newly_ready = []
        for mission in self._missions.values():
            for task in mission.tasks:
                if task.task_id == task_id:
                    task.state = TaskState.COMPLETED
                    task.progress = 1.0
                    if task.assigned_drone:
                        self._drone_assignments.pop(task.assigned_drone, None)
                    self._history.append({"event": "task_complete", "task": task_id, "mission": mission.mission_id})
                    newly_ready = self._scheduler.get_ready_tasks(mission.tasks)
                    # Check if mission complete
                    if all(t.state == TaskState.COMPLETED for t in mission.tasks):
                        mission.status = "completed"
                        self._history.append({"event": "mission_complete", "mission": mission.mission_id})
        return newly_ready

    def fail_task(self, task_id: str) -> bool:
        for mission in self._missions.values():
            for task in mission.tasks:
                if task.task_id == task_id:
                    task.state = TaskState.FAILED
                    if task.assigned_drone:
                        self._drone_assignments.pop(task.assigned_drone, None)
                    return True
        return False

    def get_mission_progress(self, mission_id: str) -> float:
        mission = self._missions.get(mission_id)
        if not mission or not mission.tasks:
            return 0.0
        completed = sum(1 for t in mission.tasks if t.state == TaskState.COMPLETED)
        return completed / len(mission.tasks)

    def get_active_missions(self) -> List[Mission]:
        return [m for m in self._missions.values() if m.status == "active"]

    def get_mission(self, mission_id: str) -> Optional[Mission]:
        return self._missions.get(mission_id)

    def summary(self) -> dict:
        statuses = {}
        total_tasks = 0
        completed_tasks = 0
        for m in self._missions.values():
            statuses[m.status] = statuses.get(m.status, 0) + 1
            total_tasks += len(m.tasks)
            completed_tasks += sum(1 for t in m.tasks if t.state == TaskState.COMPLETED)
        return {
            "total_missions": len(self._missions),
            "mission_statuses": statuses,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "active_drone_assignments": len(self._drone_assignments),
            "history_events": len(self._history),
        }
