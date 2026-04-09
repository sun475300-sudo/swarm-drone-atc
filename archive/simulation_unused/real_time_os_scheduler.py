"""
Real-Time OS Scheduler
Phase 352 - EDF, RMS, Priority Ceiling for drone flight control
"""

import heapq
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from enum import Enum
import numpy as np


class TaskState(Enum):
    READY = "ready"
    RUNNING = "running"
    BLOCKED = "blocked"
    SUSPENDED = "suspended"
    FINISHED = "finished"


@dataclass
class RealTimeTask:
    task_id: str
    period: float
    execution_time: float
    deadline: float
    priority: int = 0
    state: TaskState = TaskState.READY
    remaining_time: float = 0.0
    release_time: float = 0.0
    start_time: float = 0.0
    finish_time: float = 0.0
    wcet: float = 0.0
    callback: Optional[Callable] = None
    cpu_affinity: int = 0

    def __post_init__(self):
        self.remaining_time = self.execution_time
        self.wcet = self.execution_time
        self.deadline = self.period


class SchedulerMetrics:
    def __init__(self):
        self.cpu_utilization: float = 0.0
        self.task_misses: int = 0
        self.task_completions: int = 0
        self.response_times: Dict[str, List[float]] = {}
        self.schedulability: bool = False

    def to_dict(self) -> Dict:
        return {
            "cpu_utilization": self.cpu_utilization,
            "task_misses": self.task_misses,
            "task_completions": self.task_completions,
            "schedulability": self.schedulability,
        }


class EDFScheduler:
    def __init__(self, num_processors: int = 1):
        self.num_processors = num_processors
        self.ready_queue: List[tuple] = []
        self.running_tasks: Dict[int, RealTimeTask] = {}
        self.completed_tasks: List[RealTimeTask] = []
        self.current_time: float = 0.0
        self.metrics = SchedulerMetrics()

    def add_task(self, task: RealTimeTask):
        heapq.heappush(self.ready_queue, (task.deadline, task.release_time, task))

    def schedule(self) -> Optional[RealTimeTask]:
        while self.ready_queue:
            deadline, release, task = heapq.heappop(self.ready_queue)

            if task.state == TaskState.FINISHED:
                continue

            if self.current_time >= task.release_time:
                return task
            else:
                heapq.heappush(self.ready_queue, (deadline, release, task))

        return None

    def execute(self, task: RealTimeTask, time_slice: float = 0.001):
        if task.state == TaskState.READY:
            task.state = TaskState.RUNNING
            task.start_time = self.current_time

        task.remaining_time -= time_slice
        self.current_time += time_slice

        if task.remaining_time <= 0:
            task.state = TaskState.FINISHED
            task.finish_time = self.current_time
            self.completed_tasks.append(task)
            self.metrics.task_completions += 1

            response_time = task.finish_time - task.release_time
            if task.task_id not in self.metrics.response_times:
                self.metrics.response_times[task.task_id] = []
            self.metrics.response_times[task.task_id].append(response_time)

            return None

        if self.current_time > task.deadline:
            self.metrics.task_misses += 1
            task.state = TaskState.FINISHED
            return None

        heapq.heappush(self.ready_queue, (task.deadline, task.release_time, task))
        return task


class RMSScheduler:
    def __init__(self, num_processors: int = 1):
        self.num_processors = num_processors
        self.ready_queue: List[RealTimeTask] = []
        self.running_tasks: Dict[int, RealTimeTask] = {}
        self.completed_tasks: List[RealTimeTask] = []
        self.current_time: float = 0.0
        self.metrics = SchedulerMetrics()

    def add_task(self, task: RealTimeTask):
        self.ready_queue.append(task)
        self.ready_queue.sort(key=lambda t: t.priority, reverse=True)

    def schedule(self) -> Optional[RealTimeTask]:
        for task in self.ready_queue:
            if task.state == TaskState.READY and self.current_time >= task.release_time:
                return task
        return None

    def execute(self, task: RealTimeTask, time_slice: float = 0.001):
        if task.state == TaskState.READY:
            task.state = TaskState.RUNNING
            task.start_time = self.current_time

        task.remaining_time -= time_slice
        self.current_time += time_slice

        if task.remaining_time <= 0:
            task.state = TaskState.FINISHED
            task.finish_time = self.current_time
            self.completed_tasks.append(task)
            self.metrics.task_completions += 1
            self.ready_queue.remove(task)
            return None

        if self.current_time > task.deadline:
            self.metrics.task_misses += 1
            task.state = TaskState.FINISHED
            if task in self.ready_queue:
                self.ready_queue.remove(task)
            return None

        return task

    def check_schedulability(self, tasks: List[RealTimeTask]) -> bool:
        n = len(tasks)
        if n == 0:
            return True

        utilization = sum(t.execution_time / t.period for t in tasks)
        bound = n * (2 ** (1 / n) - 1)

        self.metrics.cpu_utilization = utilization
        self.metrics.schedulability = utilization <= bound

        return self.metrics.schedulability


class PriorityCeilingProtocol:
    def __init__(self):
        self.system_ceiling: int = 0
        self.resource_ceilings: Dict[str, int] = {}
        self.resource_locks: Dict[str, str] = {}
        self.task_locks: Dict[str, List[str]] = {}

    def init_resource(self, resource_id: str, ceiling: int):
        self.resource_ceilings[resource_id] = ceiling

    def request_resource(self, task: RealTimeTask, resource_id: str) -> bool:
        if resource_id not in self.resource_ceilings:
            return False

        ceiling = self.resource_ceilings[resource_id]

        if resource_id in self.resource_locks:
            if self.resource_locks[resource_id] == task.task_id:
                return True
            return False

        if task.priority > self.system_ceiling:
            self.resource_locks[resource_id] = task.task_id
            self.system_ceiling = max(self.system_ceiling, ceiling)

            if task.task_id not in self.task_locks:
                self.task_locks[task.task_id] = []
            self.task_locks[task.task_id].append(resource_id)
            return True

        return False

    def release_resource(self, task: RealTimeTask, resource_id: str):
        if resource_id in self.resource_locks:
            if self.resource_locks[resource_id] == task.task_id:
                del self.resource_locks[resource_id]

                if task.task_id in self.task_locks:
                    self.task_locks[task.task_id].remove(resource_id)

                self.system_ceiling = (
                    max(
                        self.resource_ceilings.get(r, 0)
                        for r in self.resource_locks.keys()
                    )
                    if self.resource_locks
                    else 0
                )


class DroneFlightController:
    def __init__(self, scheduler_type: str = "EDF"):
        if scheduler_type == "EDF":
            self.scheduler = EDFScheduler()
        elif scheduler_type == "RMS":
            self.scheduler = RMSScheduler()
        else:
            self.scheduler = EDFScheduler()

        self.pcp = PriorityCeilingProtocol()
        self.tasks: Dict[str, RealTimeTask] = {}

    def register_flight_task(
        self,
        task_id: str,
        period: float,
        execution_time: float,
        priority: int = 0,
        callback: Optional[Callable] = None,
    ):
        task = RealTimeTask(
            task_id=task_id,
            period=period,
            execution_time=execution_time,
            deadline=period,
            priority=priority,
            callback=callback,
        )
        self.tasks[task_id] = task
        self.scheduler.add_task(task)

    def run_simulation(self, duration: float = 1.0, time_slice: float = 0.001):
        print(f"=== Real-Time Scheduler Simulation ({duration}s) ===")
        print(f"Scheduler: {self.scheduler.__class__.__name__}")

        current_time = 0.0
        step = 0

        while current_time < duration:
            task = self.scheduler.schedule()

            if task:
                task = self.scheduler.execute(task, time_slice)
                step += 1

                if step % 100 == 0:
                    print(
                        f"t={current_time:.3f}s: Executing {task.task_id if task else 'idle'}"
                    )
            else:
                current_time += time_slice
                self.scheduler.current_time = current_time

        metrics = self.scheduler.metrics
        print(f"\n=== Results ===")
        print(f"CPU Utilization: {metrics.cpu_utilization:.2%}")
        print(f"Task Completions: {metrics.task_completions}")
        print(f"Task Misses: {metrics.task_misses}")

        if isinstance(self.scheduler, RMSScheduler):
            print(f"RMS Schedulable: {metrics.schedulability}")

        return metrics


def create_drone_flight_controller() -> DroneFlightController:
    controller = DroneFlightController(scheduler_type="EDF")

    controller.register_flight_task(
        "navigation", period=0.01, execution_time=0.002, priority=10
    )
    controller.register_flight_task(
        "sensor_fusion", period=0.02, execution_time=0.005, priority=8
    )
    controller.register_flight_task(
        "collision_avoidance", period=0.005, execution_time=0.001, priority=9
    )
    controller.register_flight_task(
        "telemetry", period=0.1, execution_time=0.01, priority=3
    )
    controller.register_flight_task(
        "mission_planning", period=0.5, execution_time=0.05, priority=5
    )

    return controller


if __name__ == "__main__":
    print("=== Drone Flight Control with Real-Time OS Scheduler ===")

    print("\n--- EDF Scheduler ---")
    edf_controller = DroneFlightController(scheduler_type="EDF")
    edf_metrics = edf_controller.run_simulation(duration=0.5)

    print("\n--- RMS Scheduler ---")
    rms_controller = DroneFlightController(scheduler_type="RMS")
    rms_tasks = list(rms_controller.tasks.values())
    rms_controller.scheduler.check_schedulability(rms_tasks)
    rms_metrics = rms_controller.run_simulation(duration=0.5)
