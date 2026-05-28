"""
Phase 472: Swarm Operating System
군집 드론 운영체제 — 프로세스 스케줄러, IPC, 자원 관리.
"""

from collections import deque
from dataclasses import dataclass
from enum import Enum

import numpy as np


class ProcessState(Enum):
    """``ProcessState`` 데이터를 표현한다."""
    READY = "ready"
    RUNNING = "running"
    BLOCKED = "blocked"
    TERMINATED = "terminated"


class Priority(Enum):
    """``Priority`` 관련 기능을 제공한다."""
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3


class SchedulerPolicy(Enum):
    """``SchedulerPolicy`` 관련 기능을 제공한다."""
    ROUND_ROBIN = "rr"
    PRIORITY = "priority"
    EDF = "edf"  # Earliest Deadline First
    RMS = "rms"  # Rate-Monotonic


@dataclass
class SwarmProcess:
    """``SwarmProcess`` 관련 기능을 제공한다."""
    pid: int
    name: str
    priority: Priority
    state: ProcessState = ProcessState.READY
    cpu_burst: float = 1.0
    remaining: float = 1.0
    deadline: float = float('inf')
    period: float = 0.0
    arrival_time: float = 0.0
    completion_time: float = 0.0
    wait_time: float = 0.0
    memory_kb: int = 64


@dataclass
class IPCMessage:
    """``IPCMessage`` 데이터를 표현한다."""
    sender_pid: int
    receiver_pid: int
    msg_type: str
    payload: dict
    timestamp: float


@dataclass
class ResourceAllocation:
    """``ResourceAllocation`` 관련 기능을 제공한다."""
    resource_id: str
    owner_pid: int
    amount: float
    max_amount: float


class SwarmScheduler:
    """Process scheduler for swarm OS."""

    def __init__(self, policy: SchedulerPolicy = SchedulerPolicy.PRIORITY,
                 quantum: float = 0.1):
        """인스턴스를 초기화한다."""
        self.policy = policy
        self.quantum = quantum
        self.ready_queue: deque[SwarmProcess] = deque()
        self.running: SwarmProcess | None = None
        self.current_time = 0.0
        self.context_switches = 0

    def admit(self, process: SwarmProcess) -> None:
        """``admit`` 동작을 수행한다."""
        process.state = ProcessState.READY
        process.arrival_time = self.current_time
        self.ready_queue.append(process)

    def schedule(self) -> SwarmProcess | None:
        """`대상` 작업을 계획한다."""
        if not self.ready_queue:
            return None

        if self.policy == SchedulerPolicy.PRIORITY:
            best = min(self.ready_queue, key=lambda p: p.priority.value)
            self.ready_queue.remove(best)
        elif self.policy == SchedulerPolicy.EDF:
            best = min(self.ready_queue, key=lambda p: p.deadline)
            self.ready_queue.remove(best)
        elif self.policy == SchedulerPolicy.RMS:
            best = min(self.ready_queue, key=lambda p: p.period if p.period > 0 else float('inf'))
            self.ready_queue.remove(best)
        else:  # RR
            best = self.ready_queue.popleft()

        if self.running and self.running.state == ProcessState.RUNNING:
            self.running.state = ProcessState.READY
            self.ready_queue.append(self.running)

        best.state = ProcessState.RUNNING
        self.running = best
        self.context_switches += 1
        return best

    def tick(self, dt: float = 0.1) -> SwarmProcess | None:
        """``tick`` 동작을 수행한다."""
        self.current_time += dt

        for p in self.ready_queue:
            p.wait_time += dt

        if self.running:
            self.running.remaining -= dt
            if self.running.remaining <= 0:
                self.running.state = ProcessState.TERMINATED
                self.running.completion_time = self.current_time
                completed = self.running
                self.running = None
                if self.ready_queue:
                    self.schedule()
                return completed

            if self.policy == SchedulerPolicy.ROUND_ROBIN and (self.current_time % self.quantum) < dt:
                self.schedule()
        elif self.ready_queue:
            self.schedule()

        return None


class SwarmIPC:
    """Inter-Process Communication for swarm."""

    def __init__(self):
        """인스턴스를 초기화한다."""
        self.mailboxes: dict[int, deque[IPCMessage]] = {}
        self.shared_memory: dict[str, bytes] = {}
        self.msg_count = 0

    def register(self, pid: int) -> None:
        """`대상` 항목을 추가한다."""
        self.mailboxes[pid] = deque()

    def send(self, sender: int, receiver: int, msg_type: str,
             payload: dict, timestamp: float = 0) -> bool:
        """``send`` 동작을 수행한다."""
        if receiver not in self.mailboxes:
            return False
        msg = IPCMessage(sender, receiver, msg_type, payload, timestamp)
        self.mailboxes[receiver].append(msg)
        self.msg_count += 1
        return True

    def receive(self, pid: int) -> IPCMessage | None:
        """``receive`` 동작을 수행한다."""
        if pid in self.mailboxes and self.mailboxes[pid]:
            return self.mailboxes[pid].popleft()
        return None

    def broadcast(self, sender: int, msg_type: str, payload: dict, timestamp: float = 0) -> int:
        """``broadcast`` 동작을 수행한다."""
        count = 0
        for pid in self.mailboxes:
            if pid != sender:
                self.send(sender, pid, msg_type, payload, timestamp)
                count += 1
        return count


class SwarmResourceManager:
    """Resource management for swarm OS."""

    def __init__(self, total_cpu: float = 100.0, total_memory_kb: int = 65536):
        """인스턴스를 초기화한다."""
        self.total_cpu = total_cpu
        self.total_memory = total_memory_kb
        self.used_cpu = 0.0
        self.used_memory = 0
        self.allocations: dict[int, dict[str, float]] = {}

    def allocate(self, pid: int, cpu: float, memory_kb: int) -> bool:
        """``allocate`` 동작을 수행한다."""
        if self.used_cpu + cpu > self.total_cpu:
            return False
        if self.used_memory + memory_kb > self.total_memory:
            return False
        self.used_cpu += cpu
        self.used_memory += memory_kb
        self.allocations[pid] = {"cpu": cpu, "memory": memory_kb}
        return True

    def release(self, pid: int) -> bool:
        """``release`` 동작을 수행한다."""
        if pid not in self.allocations:
            return False
        alloc = self.allocations.pop(pid)
        self.used_cpu -= alloc["cpu"]
        self.used_memory -= int(alloc["memory"])
        return True

    def utilization(self) -> dict[str, float]:
        """``utilization`` 동작을 수행한다."""
        return {
            "cpu_pct": self.used_cpu / self.total_cpu * 100,
            "mem_pct": self.used_memory / self.total_memory * 100,
            "processes": len(self.allocations),
        }


class SwarmOperatingSystem:
    """Complete swarm operating system."""

    def __init__(self, policy: SchedulerPolicy = SchedulerPolicy.PRIORITY, seed: int = 42):
        """인스턴스를 초기화한다."""
        self.scheduler = SwarmScheduler(policy)
        self.ipc = SwarmIPC()
        self.resources = SwarmResourceManager()
        self.rng = np.random.default_rng(seed)
        self._pid_counter = 0
        self.processes: dict[int, SwarmProcess] = {}
        self.completed: list[SwarmProcess] = []

    def spawn(self, name: str, priority: Priority = Priority.MEDIUM,
              cpu_burst: float = 1.0, memory_kb: int = 64,
              deadline: float = float('inf')) -> SwarmProcess | None:
        """`대상` 결과를 생성한다."""
        self._pid_counter += 1
        pid = self._pid_counter
        proc = SwarmProcess(pid, name, priority, cpu_burst=cpu_burst,
                           remaining=cpu_burst, deadline=deadline, memory_kb=memory_kb)

        if not self.resources.allocate(pid, 10, memory_kb):
            return None

        self.ipc.register(pid)
        self.processes[pid] = proc
        self.scheduler.admit(proc)
        return proc

    def tick(self, dt: float = 0.1) -> SwarmProcess | None:
        """``tick`` 동작을 수행한다."""
        completed = self.scheduler.tick(dt)
        if completed:
            self.resources.release(completed.pid)
            self.completed.append(completed)
        return completed

    def run_for(self, duration: float, dt: float = 0.1) -> list[SwarmProcess]:
        """``run_for`` 동작을 수행한다."""
        results = []
        steps = int(duration / dt)
        for _ in range(steps):
            c = self.tick(dt)
            if c:
                results.append(c)
        return results

    def summary(self) -> dict:
        """현재 상태 요약을 반환한다."""
        avg_wait = np.mean([p.wait_time for p in self.completed]) if self.completed else 0
        avg_turnaround = np.mean([p.completion_time - p.arrival_time for p in self.completed]) if self.completed else 0
        return {
            "policy": self.scheduler.policy.value,
            "total_spawned": self._pid_counter,
            "completed": len(self.completed),
            "pending": len(self.scheduler.ready_queue),
            "context_switches": self.scheduler.context_switches,
            "avg_wait_time": round(float(avg_wait), 4),
            "avg_turnaround": round(float(avg_turnaround), 4),
            **self.resources.utilization(),
        }
