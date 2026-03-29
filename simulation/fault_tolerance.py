"""Fault Tolerance System for Phase 220-239.

Provides fault detection, recovery mechanisms, and resilience
strategies for drone swarm ATC operations.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

import numpy as np


class FaultType(Enum):
    """Types of faults that can occur."""

    HARDWARE_FAILURE = "hardware_failure"
    SOFTWARE_CRASH = "software_crash"
    COMMUNICATION_LOSS = "communication_loss"
    GPS_SIGNAL_LOSS = "gps_signal_loss"
    BATTERY_FAILURE = "battery_failure"
    SENSOR_MALFUNCTION = "sensor_malfunction"
    ACTUATOR_FAILURE = "actuator_failure"
    NETWORK_PARTITION = "network_partition"
    OVERLOAD = "overload"
    DATA_CORRUPTION = "data_corruption"


class Severity(Enum):
    """Fault severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ComponentType(Enum):
    """Types of system components."""

    DRONE = "drone"
    CONTROLLER = "controller"
    COMMUNICATION = "communication"
    SENSOR = "sensor"
    ACTUATOR = "actuator"
    NETWORK = "network"
    DATABASE = "database"


class RecoveryStrategy(Enum):
    """Recovery strategies."""

    RESTART = "restart"
    FAILOVER = "failover"
    ROLLBACK = "rollback"
    ISOLATION = "isolation"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    SELF_HEALING = "self_healing"


class HealthStatus(Enum):
    """Health status of components."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    FAILED = "failed"
    RECOVERING = "recovering"


@dataclass
class Fault:
    """Represents a detected fault."""

    fault_id: str
    fault_type: FaultType
    severity: Severity
    component_id: str
    component_type: ComponentType
    timestamp: float = field(default_factory=time.time)
    description: str = ""
    recovery_strategy: Optional[RecoveryStrategy] = None
    resolved: bool = False
    resolved_at: Optional[float] = None


@dataclass
class HealthMetric:
    """Health metric for a component."""

    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    temperature: float = 0.0
    error_rate: float = 0.0
    response_time: float = 0.0
    availability: float = 100.0


@dataclass
class Component:
    """Represents a system component with health tracking."""

    component_id: str
    component_type: ComponentType
    health_status: HealthStatus = HealthStatus.HEALTHY
    health_metrics: HealthMetric = field(default_factory=HealthMetric)
    fault_history: list[str] = field(default_factory=list)
    restart_count: int = 0
    last_health_check: float = field(default_factory=time.time)
    is_critical: bool = False


@dataclass
class RecoveryAction:
    """Represents a recovery action taken."""

    action_id: str
    fault_id: str
    strategy: RecoveryStrategy
    component_id: str
    status: str = "pending"
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    success: bool = False
    error_message: Optional[str] = None


@dataclass
class SystemSnapshot:
    """Snapshot of system state for rollback."""

    snapshot_id: str
    timestamp: float = field(default_factory=time.time)
    component_states: dict = field(default_factory=dict)
    active_faults: list[str] = field(default_factory=list)
    description: str = ""


class FaultToleranceManager:
    """Manages fault detection, tolerance, and recovery."""

    def __init__(
        self,
        enable_auto_recovery: bool = True,
        health_check_interval: float = 5.0,
    ):
        self.components: dict[str, Component] = {}
        self.faults: dict[str, Fault] = {}
        self.recovery_actions: dict[str, RecoveryAction] = {}
        self.snapshots: list[SystemSnapshot] = []
        self.enable_auto_recovery = enable_auto_recovery
        self.health_check_interval = health_check_interval
        self.fault_counter = 0
        self.action_counter = 0
        self.snapshot_counter = 0

    def register_component(
        self,
        component_id: str,
        component_type: ComponentType,
        is_critical: bool = False,
    ) -> Component:
        """Register a component for monitoring."""
        component = Component(
            component_id=component_id,
            component_type=component_type,
            is_critical=is_critical,
        )
        self.components[component_id] = component
        return component

    def unregister_component(self, component_id: str) -> bool:
        """Unregister a component."""
        if component_id in self.components:
            del self.components[component_id]
            return True
        return False

    def report_fault(
        self,
        fault_type: FaultType,
        severity: Severity,
        component_id: str,
        description: str = "",
    ) -> Optional[Fault]:
        """Report a new fault."""
        if component_id not in self.components:
            return None

        self.fault_counter += 1
        fault = Fault(
            fault_id=f"fault_{self.fault_counter}",
            fault_type=fault_type,
            severity=severity,
            component_id=component_id,
            component_type=self.components[component_id].component_type,
            description=description,
        )
        self.faults[fault.fault_id] = fault
        self.components[component_id].fault_history.append(fault.fault_id)

        if severity == Severity.CRITICAL:
            self.components[component_id].health_status = HealthStatus.CRITICAL
        elif severity in (Severity.HIGH, Severity.MEDIUM):
            self.components[component_id].health_status = HealthStatus.DEGRADED

        if self.enable_auto_recovery:
            self._trigger_recovery(fault)

        return fault

    def resolve_fault(self, fault_id: str) -> bool:
        """Mark a fault as resolved."""
        if fault_id not in self.faults:
            return False

        fault = self.faults[fault_id]
        fault.resolved = True
        fault.resolved_at = time.time()

        component = self.components.get(fault.component_id)
        if component:
            active_faults = [
                f
                for f in self.faults.values()
                if f.component_id == fault.component_id and not f.resolved
            ]
            if not active_faults:
                component.health_status = HealthStatus.HEALTHY

        return True

    def _trigger_recovery(self, fault: Fault) -> None:
        """Trigger recovery for a fault."""
        strategy = self._select_recovery_strategy(fault)
        self.execute_recovery(fault.fault_id, strategy)

    def _select_recovery_strategy(self, fault: Fault) -> RecoveryStrategy:
        """Select appropriate recovery strategy for fault."""
        if fault.severity == Severity.CRITICAL:
            if fault.fault_type in (
                FaultType.HARDWARE_FAILURE,
                FaultType.ACTUATOR_FAILURE,
            ):
                return RecoveryStrategy.ISOLATION
            return RecoveryStrategy.FAILOVER

        if fault.severity == Severity.HIGH:
            return RecoveryStrategy.RESTART

        if fault.severity == Severity.MEDIUM:
            return RecoveryStrategy.SELF_HEALING

        return RecoveryStrategy.GRACEFUL_DEGRADATION

    def execute_recovery(
        self,
        fault_id: str,
        strategy: RecoveryStrategy,
    ) -> Optional[RecoveryAction]:
        """Execute recovery action for a fault."""
        if fault_id not in self.faults:
            return None

        fault = self.faults[fault_id]
        self.action_counter += 1

        action = RecoveryAction(
            action_id=f"action_{self.action_counter}",
            fault_id=fault_id,
            strategy=strategy,
            component_id=fault.component_id,
        )

        component = self.components.get(fault.component_id)
        if component:
            component.health_status = HealthStatus.RECOVERING

        if strategy == RecoveryStrategy.RESTART:
            action.success = self._execute_restart(component)
        elif strategy == RecoveryStrategy.FAILOVER:
            action.success = self._execute_failover(component)
        elif strategy == RecoveryStrategy.ISOLATION:
            action.success = self._execute_isolation(component)
        elif strategy == RecoveryStrategy.SELF_HEALING:
            action.success = self._execute_self_healing(component)
        else:
            action.success = True

        action.completed_at = time.time()
        action.status = "completed"
        self.recovery_actions[action.action_id] = action

        if component and action.success:
            component.health_status = HealthStatus.HEALTHY
            if strategy == RecoveryStrategy.RESTART:
                component.restart_count += 1

        return action

    def _execute_restart(self, component: Optional[Component]) -> bool:
        """Execute restart recovery."""
        if component:
            time.sleep(0.01)
            return True
        return False

    def _execute_failover(self, component: Optional[Component]) -> bool:
        """Execute failover recovery."""
        if component:
            time.sleep(0.01)
            return True
        return False

    def _execute_isolation(self, component: Optional[Component]) -> bool:
        """Execute isolation recovery."""
        if component:
            component.health_status = HealthStatus.FAILED
            return True
        return False

    def _execute_self_healing(self, component: Optional[Component]) -> bool:
        """Execute self-healing recovery."""
        if component:
            time.sleep(0.01)
            return True
        return False

    def update_health_metrics(
        self,
        component_id: str,
        cpu_usage: float,
        memory_usage: float,
        temperature: float = 0.0,
        error_rate: float = 0.0,
        response_time: float = 0.0,
    ) -> bool:
        """Update health metrics for a component."""
        if component_id not in self.components:
            return False

        component = self.components[component_id]
        component.health_metrics.cpu_usage = cpu_usage
        component.health_metrics.memory_usage = memory_usage
        component.health_metrics.temperature = temperature
        component.health_metrics.error_rate = error_rate
        component.health_metrics.response_time = response_time
        component.last_health_check = time.time()

        self._evaluate_health(component)
        return True

    def _evaluate_health(self, component: Component) -> None:
        """Evaluate component health based on metrics."""
        metrics = component.health_metrics

        if metrics.error_rate > 0.5 or metrics.cpu_usage > 95:
            component.health_status = HealthStatus.CRITICAL
        elif metrics.error_rate > 0.2 or metrics.cpu_usage > 80:
            component.health_status = HealthStatus.DEGRADED
        elif component.health_status != HealthStatus.RECOVERING:
            component.health_status = HealthStatus.HEALTHY

    def create_snapshot(self, description: str = "") -> SystemSnapshot:
        """Create a system snapshot for rollback."""
        self.snapshot_counter += 1
        snapshot = SystemSnapshot(
            snapshot_id=f"snapshot_{self.snapshot_counter}",
            description=description,
        )

        for comp_id, comp in self.components.items():
            snapshot.component_states[comp_id] = {
                "health_status": comp.health_status.value,
                "health_metrics": {
                    "cpu_usage": comp.health_metrics.cpu_usage,
                    "memory_usage": comp.health_metrics.memory_usage,
                },
            }

        snapshot.active_faults = [
            f.fault_id for f in self.faults.values() if not f.resolved
        ]

        self.snapshots.append(snapshot)
        return snapshot

    def rollback_to_snapshot(self, snapshot_id: str) -> bool:
        """Rollback system to a previous snapshot."""
        snapshot = next(
            (s for s in self.snapshots if s.snapshot_id == snapshot_id), None
        )
        if not snapshot:
            return False

        for comp_id, state in snapshot.component_states.items():
            if comp_id in self.components:
                self.components[comp_id].health_status = HealthStatus(
                    state["health_status"]
                )

        for fault_id in snapshot.active_faults:
            if fault_id in self.faults:
                self.faults[fault_id].resolved = True
                self.faults[fault_id].resolved_at = time.time()

        return True

    def get_fault_summary(self) -> dict:
        """Get summary of all faults."""
        unresolved = [f for f in self.faults.values() if not f.resolved]
        critical = [f for f in unresolved if f.severity == Severity.CRITICAL]

        return {
            "total_faults": len(self.faults),
            "unresolved_faults": len(unresolved),
            "critical_faults": len(critical),
            "resolved_faults": len(self.faults) - len(unresolved),
            "by_severity": {
                "critical": len(
                    [f for f in unresolved if f.severity == Severity.CRITICAL]
                ),
                "high": len([f for f in unresolved if f.severity == Severity.HIGH]),
                "medium": len([f for f in unresolved if f.severity == Severity.MEDIUM]),
                "low": len([f for f in unresolved if f.severity == Severity.LOW]),
            },
        }

    def get_component_health(self, component_id: str) -> Optional[dict]:
        """Get health status of a component."""
        if component_id not in self.components:
            return None

        component = self.components[component_id]
        return {
            "component_id": component.component_id,
            "component_type": component.component_type.value,
            "health_status": component.health_status.value,
            "is_critical": component.is_critical,
            "health_metrics": {
                "cpu_usage": component.health_metrics.cpu_usage,
                "memory_usage": component.health_metrics.memory_usage,
                "temperature": component.health_metrics.temperature,
                "error_rate": component.health_metrics.error_rate,
            },
            "fault_history_count": len(component.fault_history),
            "restart_count": component.restart_count,
        }

    def get_recovery_stats(self) -> dict:
        """Get recovery action statistics."""
        total = len(self.recovery_actions)
        successful = sum(1 for a in self.recovery_actions.values() if a.success)
        failed = total - successful

        return {
            "total_recovery_actions": total,
            "successful_recoveries": successful,
            "failed_recoveries": failed,
            "success_rate": successful / total if total > 0 else 0,
            "by_strategy": {
                strategy.value: sum(
                    1 for a in self.recovery_actions.values() if a.strategy == strategy
                )
                for strategy in RecoveryStrategy
            },
        }

    def detect_cascade_failure(
        self,
        component_id: str,
    ) -> list[str]:
        """Detect potential cascade failures from a component failure."""
        if component_id not in self.components:
            return []

        component = self.components[component_id]
        if not component.is_critical:
            return []

        affected = []
        for comp_id, comp in self.components.items():
            if (
                comp_id != component_id
                and comp.component_type == component.component_type
            ):
                if comp.health_status in (HealthStatus.DEGRADED, HealthStatus.CRITICAL):
                    affected.append(comp_id)

        return affected


def create_fault_tolerance_manager(
    enable_auto_recovery: bool = True,
) -> FaultToleranceManager:
    """Factory function to create fault tolerance manager."""
    return FaultToleranceManager(enable_auto_recovery=enable_auto_recovery)


def build_with_drone_fleet(
    num_drones: int = 10,
    enable_auto_recovery: bool = True,
) -> FaultToleranceManager:
    """Build fault tolerance manager with drone fleet."""
    manager = FaultToleranceManager(enable_auto_recovery=enable_auto_recovery)

    for i in range(num_drones):
        manager.register_component(
            component_id=f"drone_{i}",
            component_type=ComponentType.DRONE,
            is_critical=False,
        )

    manager.register_component(
        component_id="main_controller",
        component_type=ComponentType.CONTROLLER,
        is_critical=True,
    )

    manager.register_component(
        component_id="comm_system",
        component_type=ComponentType.COMMUNICATION,
        is_critical=True,
    )

    return manager
