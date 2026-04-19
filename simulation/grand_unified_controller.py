"""
Phase 490: Grand Unified Controller
전체 시스템 통합 오케스트레이터, 모든 서브시스템 조율.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any


class SystemModule(Enum):
    FLIGHT_CONTROL = "flight_control"
    PATH_PLANNING = "path_planning"
    COLLISION_AVOID = "collision_avoidance"
    COMMUNICATION = "communication"
    WEATHER = "weather"
    BATTERY = "battery"
    MISSION = "mission"
    DEFENSE = "defense"
    COMPLIANCE = "compliance"
    TELEMETRY = "telemetry"
    AI_DECISION = "ai_decision"
    SWARM_COORD = "swarm_coordination"


class SystemState(Enum):
    NOMINAL = "nominal"
    DEGRADED = "degraded"
    EMERGENCY = "emergency"
    SHUTDOWN = "shutdown"


class Priority(Enum):
    SAFETY = 0
    MISSION = 1
    EFFICIENCY = 2
    COMFORT = 3


@dataclass
class ModuleStatus:
    module: SystemModule
    health: float  # 0-1
    latency_ms: float
    last_update: float
    active: bool = True
    error_count: int = 0


@dataclass
class SystemEvent:
    event_id: str
    source: SystemModule
    priority: Priority
    message: str
    timestamp: float
    data: Dict = field(default_factory=dict)


@dataclass
class ControlDecision:
    decision_id: str
    affected_drones: List[str]
    action: str
    priority: Priority
    reason: str
    timestamp: float
    overrides: Dict = field(default_factory=dict)


class GrandUnifiedController:
    """Master orchestrator integrating all swarm subsystems."""

    def __init__(self, n_drones: int = 20, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_drones = n_drones
        self.state = SystemState.NOMINAL
        self.modules: Dict[SystemModule, ModuleStatus] = {}
        self.event_log: List[SystemEvent] = []
        self.decisions: List[ControlDecision] = []
        self.drone_states: Dict[str, Dict] = {}
        self.time = 0.0
        self._event_counter = 0
        self._decision_counter = 0

        for mod in SystemModule:
            self.modules[mod] = ModuleStatus(
                mod, 1.0, self.rng.exponential(5) + 1, 0.0)

        for i in range(n_drones):
            did = f"drone_{i:03d}"
            self.drone_states[did] = {
                "position": self.rng.uniform(-100, 100, 3).tolist(),
                "velocity": [0, 0, 0],
                "battery": self.rng.uniform(60, 100),
                "status": "nominal",
                "mission": None,
            }

    def _emit_event(self, source: SystemModule, priority: Priority,
                    message: str, data: Dict = None) -> SystemEvent:
        self._event_counter += 1
        event = SystemEvent(
            f"EVT-{self._event_counter:06d}", source, priority,
            message, self.time, data or {})
        self.event_log.append(event)
        return event

    def _make_decision(self, drones: List[str], action: str,
                       priority: Priority, reason: str) -> ControlDecision:
        self._decision_counter += 1
        decision = ControlDecision(
            f"DEC-{self._decision_counter:06d}", drones, action,
            priority, reason, self.time)
        self.decisions.append(decision)
        return decision

    def update_module(self, module: SystemModule, health: float, latency_ms: float):
        if module in self.modules:
            ms = self.modules[module]
            ms.health = np.clip(health, 0, 1)
            ms.latency_ms = latency_ms
            ms.last_update = self.time
            if health < 0.3:
                self._emit_event(module, Priority.SAFETY,
                               f"{module.value} health critical: {health:.2f}")

    def _assess_system_state(self) -> SystemState:
        healths = [m.health for m in self.modules.values() if m.active]
        if not healths:
            return SystemState.SHUTDOWN
        avg = np.mean(healths)
        min_h = min(healths)
        critical_modules = [SystemModule.FLIGHT_CONTROL, SystemModule.COLLISION_AVOID,
                          SystemModule.COMMUNICATION]
        critical_down = any(self.modules[m].health < 0.3 for m in critical_modules
                          if m in self.modules)

        if critical_down or min_h < 0.1:
            return SystemState.EMERGENCY
        elif avg < 0.6 or min_h < 0.3:
            return SystemState.DEGRADED
        return SystemState.NOMINAL

    def _safety_checks(self) -> List[ControlDecision]:
        decisions = []
        for did, state in self.drone_states.items():
            if state["battery"] < 15:
                decisions.append(self._make_decision(
                    [did], "RETURN_TO_HOME", Priority.SAFETY,
                    f"Battery critical: {state['battery']:.0f}%"))
            pos = np.array(state["position"])
            if np.linalg.norm(pos[:2]) > 3000:
                decisions.append(self._make_decision(
                    [did], "GEOFENCE_RETURN", Priority.SAFETY,
                    f"Outside geofence: {np.linalg.norm(pos[:2]):.0f}m"))
        return decisions

    def _optimize_swarm(self) -> List[ControlDecision]:
        decisions = []
        if self.state != SystemState.NOMINAL:
            return decisions
        positions = {did: np.array(s["position"]) for did, s in self.drone_states.items()}
        drones = list(positions.keys())
        for i in range(len(drones)):
            for j in range(i + 1, len(drones)):
                dist = np.linalg.norm(positions[drones[i]] - positions[drones[j]])
                if dist < 5.0:
                    decisions.append(self._make_decision(
                        [drones[i], drones[j]], "SEPARATION_INCREASE",
                        Priority.SAFETY, f"Proximity alert: {dist:.1f}m"))
        return decisions

    def tick(self, dt: float = 1.0) -> Dict:
        self.time += dt

        for mod in self.modules.values():
            mod.health += self.rng.standard_normal() * 0.01
            mod.health = np.clip(mod.health, 0, 1)
            mod.latency_ms = max(0.5, mod.latency_ms + self.rng.standard_normal() * 0.5)

        for state in self.drone_states.values():
            state["battery"] -= self.rng.uniform(0.01, 0.05)
            pos = state["position"]
            for k in range(3):
                pos[k] += self.rng.standard_normal() * 0.5

        old_state = self.state
        self.state = self._assess_system_state()
        if self.state != old_state:
            self._emit_event(SystemModule.FLIGHT_CONTROL, Priority.SAFETY,
                           f"System state: {old_state.value} → {self.state.value}")

        safety = self._safety_checks()
        optim = self._optimize_swarm()

        return {
            "time": round(self.time, 1),
            "state": self.state.value,
            "safety_decisions": len(safety),
            "optimization_decisions": len(optim),
            "active_modules": sum(1 for m in self.modules.values() if m.active),
        }

    def run(self, duration: float = 60, dt: float = 1.0) -> Dict:
        steps = int(duration / dt)
        state_counts = {s.value: 0 for s in SystemState}
        total_decisions = 0
        for _ in range(steps):
            info = self.tick(dt)
            state_counts[self.state.value] += 1
            total_decisions += info["safety_decisions"] + info["optimization_decisions"]
        return {
            "duration": duration,
            "state_distribution": state_counts,
            "total_decisions": total_decisions,
            "total_events": len(self.event_log),
        }

    def summary(self) -> Dict:
        return {
            "state": self.state.value,
            "drones": self.n_drones,
            "modules": len(self.modules),
            "avg_module_health": round(float(np.mean(
                [m.health for m in self.modules.values()])), 4),
            "total_events": len(self.event_log),
            "total_decisions": len(self.decisions),
        }
