# Phase 565: Drone Swarm OS Kernel — Microkernel Scheduler
"""
군집 드론 운영체제 커널: 라운드로빈/우선순위 스케줄러,
IPC 메시지 큐, 간이 메모리 관리.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum


class ProcessState(Enum):
    READY = "ready"
    RUNNING = "running"
    BLOCKED = "blocked"
    TERMINATED = "terminated"


@dataclass
class Process:
    pid: int
    name: str
    priority: int
    state: ProcessState = ProcessState.READY
    cpu_time: float = 0.0
    memory_kb: int = 0
    messages: list = field(default_factory=list)


@dataclass
class IPCMessage:
    sender: int
    receiver: int
    msg_type: str
    data: str
    timestamp: float


class Scheduler:
    """라운드로빈 + 우선순위 스케줄러."""

    def __init__(self, quantum_ms=10.0):
        self.quantum = quantum_ms
        self.ready_queue: list[Process] = []
        self.current: Process | None = None
        self.context_switches = 0

    def add(self, proc: Process):
        self.ready_queue.append(proc)
        self.ready_queue.sort(key=lambda p: p.priority, reverse=True)

    def schedule(self) -> Process | None:
        if self.current:
            if self.current.state == ProcessState.RUNNING:
                self.current.state = ProcessState.READY
                self.ready_queue.append(self.current)
        ready = [p for p in self.ready_queue if p.state == ProcessState.READY]
        if not ready:
            self.current = None
            return None
        proc = ready[0]
        self.ready_queue.remove(proc)
        proc.state = ProcessState.RUNNING
        self.current = proc
        self.context_switches += 1
        return proc

    def tick(self, dt=1.0):
        if self.current and self.current.state == ProcessState.RUNNING:
            self.current.cpu_time += dt


class MemoryManager:
    """간이 메모리 할당기."""

    def __init__(self, total_kb=1024):
        self.total = total_kb
        self.used = 0
        self.allocations: dict[int, int] = {}  # pid -> kb

    def allocate(self, pid: int, size_kb: int) -> bool:
        if self.used + size_kb > self.total:
            return False
        self.allocations[pid] = self.allocations.get(pid, 0) + size_kb
        self.used += size_kb
        return True

    def free(self, pid: int):
        freed = self.allocations.pop(pid, 0)
        self.used -= freed

    def usage_pct(self) -> float:
        return self.used / self.total * 100


class MessageQueue:
    """IPC 메시지 큐."""

    def __init__(self):
        self.queue: list[IPCMessage] = []
        self.delivered = 0

    def send(self, msg: IPCMessage):
        self.queue.append(msg)

    def receive(self, pid: int) -> list[IPCMessage]:
        msgs = [m for m in self.queue if m.receiver == pid]
        self.queue = [m for m in self.queue if m.receiver != pid]
        self.delivered += len(msgs)
        return msgs


class DroneSwarmOS:
    """군집 드론 OS 시뮬레이션."""

    def __init__(self, n_drones=10, seed=42):
        self.rng = np.random.default_rng(seed)
        self.scheduler = Scheduler()
        self.memory = MemoryManager(2048)
        self.ipc = MessageQueue()
        self.processes: list[Process] = []
        self.tick_count = 0

        # 드론별 프로세스 생성
        pid = 0
        for i in range(n_drones):
            for name in ["nav", "comm", "sensor"]:
                p = Process(pid, f"drone_{i}_{name}", int(self.rng.integers(1, 10)))
                self.processes.append(p)
                self.scheduler.add(p)
                self.memory.allocate(pid, int(self.rng.integers(10, 50)))
                pid += 1

    def step(self):
        self.tick_count += 1
        proc = self.scheduler.schedule()
        if proc:
            self.scheduler.tick(1.0)
            # 랜덤 IPC
            if self.rng.random() < 0.3 and len(self.processes) > 1:
                target = int(self.rng.integers(0, len(self.processes)))
                if target != proc.pid:
                    self.ipc.send(IPCMessage(proc.pid, target, "data", f"tick_{self.tick_count}", self.tick_count))
            # 메시지 수신
            msgs = self.ipc.receive(proc.pid)
            proc.messages.extend(msgs)

    def run(self, steps=100):
        for _ in range(steps):
            self.step()

    def summary(self):
        active = sum(1 for p in self.processes if p.state != ProcessState.TERMINATED)
        total_cpu = sum(p.cpu_time for p in self.processes)
        return {
            "processes": len(self.processes),
            "active": active,
            "context_switches": self.scheduler.context_switches,
            "total_cpu_time": round(total_cpu, 1),
            "memory_usage_pct": round(self.memory.usage_pct(), 1),
            "messages_delivered": self.ipc.delivered,
            "ticks": self.tick_count,
        }


if __name__ == "__main__":
    os_sim = DroneSwarmOS(10, 42)
    os_sim.run(200)
    for k, v in os_sim.summary().items():
        print(f"  {k}: {v}")
