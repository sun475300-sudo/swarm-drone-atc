"""
Phase 472: Swarm Operating System
군집 드론 운영체제 — 프로세스 스케줄러, IPC, 자원 관리.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Deque
from collections import deque


class ProcessState(Enum):
    READY = "ready"
    RUNNING = "running"
    BLOCKED = "blocked"
    TERMINATED = "terminated"


class Priority(Enum):
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3


class SchedulerPolicy(Enum):
    ROUND_ROBIN = "rr"
    PRIORITY = "priority"
    EDF = "edf"  # Earliest Deadline First
    RMS = "rms"  # Rate-Monotonic


@dataclass
class SwarmProcess:
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
    sender_pid: int
    receiver_pid: int
    msg_type: str
    payload: Dict
    timestamp: float


@dataclass
class ResourceAllocation:
    resource_id: str
    owner_pid: int
    amount: float
    max_amount: float


class SwarmScheduler:
    """Process scheduler for swarm OS."""

    def __init__(self, policy: SchedulerPolicy = SchedulerPolicy.PRIORITY,
                 quantum: float = 0.1):
        self.policy = policy
        self.quantum = quantum
        self.ready_queue: Deque[SwarmProcess] = deque()
        self.running: Optional[SwarmProcess] = None
        self.current_time = 0.0
        self.context_switches = 0

    def admit(self, process: SwarmProcess) -> None:
        process.state = ProcessState.READY
        process.arrival_time = self.current_time
        self.ready_queue.append(process)

    def schedule(self) -> Optional[SwarmProcess]:
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

    def tick(self, dt: float = 0.1) -> Optional[SwarmProcess]:
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

            if self.policy == SchedulerPolicy.ROUND_ROBIN:
                if (self.current_time % self.quantum) < dt:
                    self.schedule()
        elif self.ready_queue:
            self.schedule()

        return None


class SwarmIPC:
    """Inter-Process Communication for swarm."""

    def __init__(self):
        self.mailboxes: Dict[int, Deque[IPCMessage]] = {}
        self.shared_memory: Dict[str, bytes] = {}
        self.msg_count = 0

    def register(self, pid: int) -> None:
        self.mailboxes[pid] = deque()

    def send(self, sender: int, receiver: int, msg_type: str,
             payload: Dict, timestamp: float = 0) -> bool:
        if receiver not in self.mailboxes:
            return False
        msg = IPCMessage(sender, receiver, msg_type, payload, timestamp)
        self.mailboxes[receiver].append(msg)
        self.msg_count += 1
        return True

    def receive(self, pid: int) -> Optional[IPCMessage]:
        if pid in self.mailboxes and self.mailboxes[pid]:
            return self.mailboxes[pid].popleft()
        return None

    def broadcast(self, sender: int, msg_type: str, payload: Dict, timestamp: float = 0) -> int:
        count = 0
        for pid in self.mailboxes:
            if pid != sender:
                self.send(sender, pid, msg_type, payload, timestamp)
                count += 1
        return count


class SwarmResourceManager:
    """Resource management for swarm OS."""

    def __init__(self, total_cpu: float = 100.0, total_memory_kb: int = 65536):
        self.total_cpu = total_cpu
        self.total_memory = total_memory_kb
        self.used_cpu = 0.0
        self.used_memory = 0
        self.allocations: Dict[int, Dict[str, float]] = {}

    def allocate(self, pid: int, cpu: float, memory_kb: int) -> bool:
        if self.used_cpu + cpu > self.total_cpu:
            return False
        if self.used_memory + memory_kb > self.total_memory:
            return False
        self.used_cpu += cpu
        self.used_memory += memory_kb
        self.allocations[pid] = {"cpu": cpu, "memory": memory_kb}
        return True

    def release(self, pid: int) -> bool:
        if pid not in self.allocations:
            return False
        alloc = self.allocations.pop(pid)
        self.used_cpu -= alloc["cpu"]
        self.used_memory -= int(alloc["memory"])
        return True

    def utilization(self) -> Dict[str, float]:
        return {
            "cpu_pct": self.used_cpu / self.total_cpu * 100,
            "mem_pct": self.used_memory / self.total_memory * 100,
            "processes": len(self.allocations),
        }


class SwarmOperatingSystem:
    """Complete swarm operating system."""

    def __init__(self, policy: SchedulerPolicy = SchedulerPolicy.PRIORITY, seed: int = 42):
        self.scheduler = SwarmScheduler(policy)
        self.ipc = SwarmIPC()
        self.resources = SwarmResourceManager()
        self.rng = np.random.default_rng(seed)
        self._pid_counter = 0
        self.processes: Dict[int, SwarmProcess] = {}
        self.completed: List[SwarmProcess] = []

    def spawn(self, name: str, priority: Priority = Priority.MEDIUM,
              cpu_burst: float = 1.0, memory_kb: int = 64,
              deadline: float = float('inf')) -> Optional[SwarmProcess]:
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

    def tick(self, dt: float = 0.1) -> Optional[SwarmProcess]:
        completed = self.scheduler.tick(dt)
        if completed:
            self.resources.release(completed.pid)
            self.completed.append(completed)
        return completed

    def run_for(self, duration: float, dt: float = 0.1) -> List[SwarmProcess]:
        results = []
        steps = int(duration / dt)
        for _ in range(steps):
            c = self.tick(dt)
            if c:
                results.append(c)
        return results

    def summary(self) -> Dict:
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
