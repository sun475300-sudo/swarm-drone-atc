"""
Phase 479: Resilience Orchestrator
카오스 엔지니어링, 자가치유, 장애 주입 및 복구 오케스트레이션.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Callable


class FaultType(Enum):
    NODE_CRASH = "node_crash"
    NETWORK_PARTITION = "network_partition"
    LATENCY_SPIKE = "latency_spike"
    CPU_OVERLOAD = "cpu_overload"
    MEMORY_LEAK = "memory_leak"
    SENSOR_DRIFT = "sensor_drift"
    COMM_LOSS = "comm_loss"


class HealingAction(Enum):
    RESTART = "restart"
    FAILOVER = "failover"
    SCALE_UP = "scale_up"
    REROUTE = "reroute"
    ISOLATE = "isolate"
    RECALIBRATE = "recalibrate"


class SystemHealth(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    RECOVERING = "recovering"


@dataclass
class FaultInjection:
    fault_id: str
    fault_type: FaultType
    target: str
    severity: float  # 0-1
    duration: float
    injected_at: float = 0.0
    resolved: bool = False


@dataclass
class HealingEvent:
    fault_id: str
    action: HealingAction
    success: bool
    latency_ms: float
    timestamp: float


@dataclass
class ServiceNode:
    node_id: str
    health: SystemHealth = SystemHealth.HEALTHY
    cpu_usage: float = 0.2
    memory_usage: float = 0.3
    uptime: float = 0.0
    fault_count: int = 0
    restart_count: int = 0


class ResilienceOrchestrator:
    """Chaos engineering and self-healing orchestrator for drone swarms."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.nodes: Dict[str, ServiceNode] = {}
        self.active_faults: Dict[str, FaultInjection] = {}
        self.fault_history: List[FaultInjection] = []
        self.healing_log: List[HealingEvent] = []
        self.time = 0.0
        self._fault_counter = 0
        self._healing_rules: Dict[FaultType, HealingAction] = {
            FaultType.NODE_CRASH: HealingAction.RESTART,
            FaultType.NETWORK_PARTITION: HealingAction.REROUTE,
            FaultType.LATENCY_SPIKE: HealingAction.SCALE_UP,
            FaultType.CPU_OVERLOAD: HealingAction.SCALE_UP,
            FaultType.MEMORY_LEAK: HealingAction.RESTART,
            FaultType.SENSOR_DRIFT: HealingAction.RECALIBRATE,
            FaultType.COMM_LOSS: HealingAction.FAILOVER,
        }

    def add_node(self, node_id: str) -> ServiceNode:
        node = ServiceNode(node_id)
        self.nodes[node_id] = node
        return node

    def inject_fault(self, target: str, fault_type: FaultType,
                     severity: float = 0.5, duration: float = 10.0) -> Optional[FaultInjection]:
        if target not in self.nodes:
            return None
        self._fault_counter += 1
        fault = FaultInjection(
            fault_id=f"FAULT-{self._fault_counter:04d}",
            fault_type=fault_type, target=target,
            severity=min(1.0, max(0.0, severity)),
            duration=duration, injected_at=self.time
        )
        self.active_faults[fault.fault_id] = fault
        self.fault_history.append(fault)

        node = self.nodes[target]
        node.fault_count += 1
        if fault_type == FaultType.NODE_CRASH:
            node.health = SystemHealth.CRITICAL
        elif fault_type == FaultType.CPU_OVERLOAD:
            node.cpu_usage = min(1.0, node.cpu_usage + severity * 0.6)
            node.health = SystemHealth.DEGRADED
        elif fault_type == FaultType.MEMORY_LEAK:
            node.memory_usage = min(1.0, node.memory_usage + severity * 0.5)
            node.health = SystemHealth.DEGRADED
        elif fault_type in (FaultType.NETWORK_PARTITION, FaultType.COMM_LOSS):
            node.health = SystemHealth.CRITICAL
        else:
            node.health = SystemHealth.DEGRADED

        return fault

    def chaos_monkey(self, intensity: float = 0.3) -> List[FaultInjection]:
        """Random fault injection across the swarm."""
        injected = []
        for nid in list(self.nodes.keys()):
            if self.rng.random() < intensity:
                ft = self.rng.choice(list(FaultType))
                sev = self.rng.uniform(0.3, 0.9)
                dur = self.rng.uniform(5, 30)
                fault = self.inject_fault(nid, ft, sev, dur)
                if fault:
                    injected.append(fault)
        return injected

    def _attempt_healing(self, fault: FaultInjection) -> HealingEvent:
        action = self._healing_rules.get(fault.fault_type, HealingAction.RESTART)
        node = self.nodes.get(fault.target)

        base_success = 0.85
        if fault.severity > 0.7:
            base_success -= 0.2
        if node and node.restart_count > 3:
            base_success -= 0.1
        success = self.rng.random() < max(0.3, base_success)

        latency = self.rng.exponential(200) + 50
        if action == HealingAction.RESTART:
            latency += 500
        elif action == HealingAction.FAILOVER:
            latency += 300

        if success and node:
            fault.resolved = True
            node.health = SystemHealth.RECOVERING
            node.cpu_usage = max(0.1, node.cpu_usage - fault.severity * 0.4)
            node.memory_usage = max(0.1, node.memory_usage - fault.severity * 0.3)
            if action == HealingAction.RESTART:
                node.restart_count += 1

        event = HealingEvent(fault.fault_id, action, success, round(latency, 1), self.time)
        self.healing_log.append(event)
        return event

    def self_heal(self) -> List[HealingEvent]:
        """Attempt to heal all active faults."""
        events = []
        for fid in list(self.active_faults.keys()):
            fault = self.active_faults[fid]
            if fault.resolved:
                continue
            event = self._attempt_healing(fault)
            events.append(event)
            if fault.resolved:
                del self.active_faults[fid]
        return events

    def tick(self, dt: float = 1.0) -> Dict:
        self.time += dt
        expired = []
        for fid, fault in self.active_faults.items():
            if self.time - fault.injected_at >= fault.duration:
                fault.resolved = True
                expired.append(fid)
        for fid in expired:
            del self.active_faults[fid]

        for node in self.nodes.values():
            if node.health == SystemHealth.RECOVERING:
                node.health = SystemHealth.HEALTHY
            node.uptime += dt
            node.cpu_usage += self.rng.standard_normal() * 0.02
            node.cpu_usage = np.clip(node.cpu_usage, 0.05, 0.95)
            node.memory_usage += self.rng.standard_normal() * 0.01
            node.memory_usage = np.clip(node.memory_usage, 0.05, 0.95)

        return {
            "time": self.time,
            "active_faults": len(self.active_faults),
            "healthy_nodes": sum(1 for n in self.nodes.values() if n.health == SystemHealth.HEALTHY),
        }

    def run_chaos_experiment(self, duration: float = 60, intensity: float = 0.2,
                             heal_interval: float = 5.0) -> Dict:
        results = {"faults_injected": 0, "healed": 0, "failed_healing": 0}
        steps = int(duration)
        for step in range(steps):
            self.tick(1.0)
            if step % 10 == 0:
                faults = self.chaos_monkey(intensity)
                results["faults_injected"] += len(faults)
            if step % int(heal_interval) == 0:
                events = self.self_heal()
                for e in events:
                    if e.success:
                        results["healed"] += 1
                    else:
                        results["failed_healing"] += 1
        return results

    def resilience_score(self) -> float:
        if not self.fault_history:
            return 1.0
        resolved = sum(1 for f in self.fault_history if f.resolved)
        score = resolved / len(self.fault_history)
        if self.healing_log:
            avg_latency = np.mean([e.latency_ms for e in self.healing_log])
            latency_penalty = min(0.2, avg_latency / 5000)
            score -= latency_penalty
        return round(max(0, score), 4)

    def summary(self) -> Dict:
        return {
            "nodes": len(self.nodes),
            "total_faults": len(self.fault_history),
            "active_faults": len(self.active_faults),
            "healing_events": len(self.healing_log),
            "resilience_score": self.resilience_score(),
            "avg_healing_latency_ms": round(
                float(np.mean([e.latency_ms for e in self.healing_log])), 1
            ) if self.healing_log else 0,
        }
