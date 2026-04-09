"""Multi-Agent Coordination Framework for Phase 220-239.

Provides coordination between multiple ATC agents for distributed
airspace control, task distribution, and collaborative decision-making.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

import numpy as np


class AgentType(Enum):
    """Types of ATC agents."""

    AIRSPACE_CONTROLLER = "airspace_controller"
    CONFLICT_RESOLVER = "conflict_resolver"
    WEATHER_MONITOR = "weather_monitor"
    EMERGENCY_HANDLER = "emergency_handler"
    TRAFFIC_MANAGER = "traffic_manager"
    FORMATION_CONTROLLER = "formation_controller"


class AgentState(Enum):
    """Agent operational states."""

    IDLE = "idle"
    ACTIVE = "active"
    BUSY = "busy"
    OFFLINE = "offline"
    EMERGENCY = "emergency"


class TaskPriority(Enum):
    """Task priority levels."""

    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3
    EMERGENCY = 4


@dataclass
class Task:
    """Represents a task assigned to an agent."""

    task_id: str
    task_type: str
    priority: TaskPriority
    assigned_agent: Optional[str] = None
    status: str = "pending"
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    payload: dict = field(default_factory=dict)
    result: Optional[dict] = None
    error: Optional[str] = None


@dataclass
class AgentMetrics:
    """Performance metrics for an agent."""

    tasks_completed: int = 0
    tasks_failed: int = 0
    avg_response_time: float = 0.0
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    last_heartbeat: float = field(default_factory=time.time)


@dataclass
class Agent:
    """Represents an ATC agent in the coordination system."""

    agent_id: str
    agent_type: AgentType
    state: AgentState = AgentState.IDLE
    capabilities: list[str] = field(default_factory=list)
    load: float = 0.0
    max_load: float = 100.0
    region: Optional[str] = None
    metrics: AgentMetrics = field(default_factory=AgentMetrics)
    assigned_drones: list[str] = field(default_factory=list)
    tasks: list[Task] = field(default_factory=list)

    def can_accept_task(self, task: Task) -> bool:
        """Check if agent can accept a new task."""
        if self.state in (AgentState.OFFLINE, AgentState.EMERGENCY):
            return False
        if self.load >= self.max_load:
            return False
        return True

    def assign_task(self, task: Task) -> bool:
        """Assign a task to this agent."""
        if not self.can_accept_task(task):
            return False
        task.assigned_agent = self.agent_id
        task.status = "assigned"
        self.tasks.append(task)
        self.load += self._estimate_load(task)
        return True

    def _estimate_load(self, task: Task) -> float:
        """Estimate load increment for a task."""
        priority_weights = {
            TaskPriority.LOW: 5,
            TaskPriority.NORMAL: 10,
            TaskPriority.HIGH: 20,
            TaskPriority.CRITICAL: 35,
            TaskPriority.EMERGENCY: 50,
        }
        return priority_weights.get(task.priority, 10)

    def complete_task(self, task_id: str, result: dict) -> bool:
        """Mark a task as completed."""
        for task in self.tasks:
            if task.task_id == task_id:
                task.status = "completed"
                task.result = task.result or {}
                task.result.update(result)
                task.completed_at = time.time()
                self.load -= self._estimate_load(task)
                self.load = max(0, self.load)
                self.metrics.tasks_completed += 1
                return True
        return False


class MessageType(Enum):
    """Types of messages between agents."""

    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    HEARTBEAT = "heartbeat"
    STATE_UPDATE = "state_update"
    EMERGENCY_ALERT = "emergency_alert"
    COORDINATION = "coordination"
    HANDOVER = "handover"


@dataclass
class AgentMessage:
    """Message passed between agents."""

    message_id: str
    sender_id: str
    receiver_id: str
    message_type: MessageType
    timestamp: float = field(default_factory=time.time)
    payload: dict = field(default_factory=dict)
    correlation_id: Optional[str] = None


class CommunicationProtocol(Enum):
    """Communication protocols for agent coordination."""

    DIRECT = "direct"
    BROADCAST = "broadcast"
    MULTICAST = "multicast"
    HIERARCHICAL = "hierarchical"


class MultiAgentCoordinator:
    """Coordinates multiple ATC agents for distributed control."""

    def __init__(
        self,
        num_controllers: int = 3,
        protocol: CommunicationProtocol = CommunicationProtocol.DIRECT,
    ):
        self.agents: dict[str, Agent] = {}
        self.pending_tasks: list[Task] = []
        self.completed_tasks: list[Task] = []
        self.message_queue: list[AgentMessage] = []
        self.protocol = protocol
        self.coordination_lock = threading.Lock()
        self.task_counter = 0
        self.message_counter = 0

        self._initialize_agents(num_controllers)

    def _initialize_agents(self, num_controllers: int) -> None:
        """Initialize default set of agents."""
        for i in range(num_controllers):
            agent = Agent(
                agent_id=f"controller_{i}",
                agent_type=AgentType.AIRSPACE_CONTROLLER,
                capabilities=["conflict_resolution", "traffic_management"],
                region=f"zone_{i}",
            )
            self.agents[agent.agent_id] = agent

        emergency_handler = Agent(
            agent_id="emergency_handler",
            agent_type=AgentType.EMERGENCY_HANDLER,
            capabilities=["emergency_response", "disaster_recovery"],
            region="all",
        )
        self.agents[emergency_handler.agent_id] = emergency_handler

        weather_monitor = Agent(
            agent_id="weather_monitor",
            agent_type=AgentType.WEATHER_MONITOR,
            capabilities=["weather_monitoring", "risk_assessment"],
            region="all",
        )
        self.agents[weather_monitor.agent_id] = weather_monitor

    def register_agent(self, agent: Agent) -> None:
        """Register a new agent in the coordinator."""
        with self.coordination_lock:
            self.agents[agent.agent_id] = agent

    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent from the coordinator."""
        with self.coordination_lock:
            if agent_id in self.agents:
                self.agents[agent_id].state = AgentState.OFFLINE
                return True
            return False

    def create_task(
        self,
        task_type: str,
        priority: TaskPriority,
        payload: dict,
    ) -> Task:
        """Create a new task in the coordination system."""
        with self.coordination_lock:
            self.task_counter += 1
            task = Task(
                task_id=f"task_{self.task_counter}",
                task_type=task_type,
                priority=priority,
                payload=payload,
            )
            self.pending_tasks.append(task)
            return task

    def assign_task_to_agent(self, task_id: str, agent_id: str) -> bool:
        """Assign a pending task to a specific agent."""
        with self.coordination_lock:
            task = next((t for t in self.pending_tasks if t.task_id == task_id), None)
            if not task:
                return False

            agent = self.agents.get(agent_id)
            if not agent or not agent.can_accept_task(task):
                return False

            if agent.assign_task(task):
                self.pending_tasks.remove(task)
                self._send_message(
                    sender_id="coordinator",
                    receiver_id=agent_id,
                    message_type=MessageType.TASK_REQUEST,
                    payload={"task": task},
                )
                return True
            return False

    def auto_assign_tasks(self) -> int:
        """Automatically assign pending tasks to available agents."""
        assigned_count = 0
        with self.coordination_lock:
            for task in list(self.pending_tasks):
                best_agent = self._select_best_agent(task)
                if best_agent:
                    if best_agent.assign_task(task):
                        self.pending_tasks.remove(task)
                        assigned_count += 1
        return assigned_count

    def _select_best_agent(self, task: Task) -> Optional[Agent]:
        """Select the best available agent for a task."""
        available = [
            a
            for a in self.agents.values()
            if a.can_accept_task(task) and task.task_type in a.capabilities
        ]
        if not available:
            available = [a for a in self.agents.values() if a.can_accept_task(task)]

        if not available:
            return None

        return min(available, key=lambda a: a.load)

    def _send_message(
        self,
        sender_id: str,
        receiver_id: str,
        message_type: MessageType,
        payload: dict,
        correlation_id: Optional[str] = None,
    ) -> AgentMessage:
        """Send a message between agents."""
        with self.coordination_lock:
            self.message_counter += 1
            message = AgentMessage(
                message_id=f"msg_{self.message_counter}",
                sender_id=sender_id,
                receiver_id=receiver_id,
                message_type=message_type,
                payload=payload,
                correlation_id=correlation_id,
            )
            self.message_queue.append(message)
            return message

    def broadcast_message(
        self,
        sender_id: str,
        message_type: MessageType,
        payload: dict,
    ) -> list[AgentMessage]:
        """Broadcast a message to all agents."""
        messages = []
        for agent_id in self.agents:
            if agent_id != sender_id:
                msg = self._send_message(sender_id, agent_id, message_type, payload)
                messages.append(msg)
        return messages

    def handover_task(self, task_id: str, from_agent_id: str, to_agent_id: str) -> bool:
        """Handover a task from one agent to another."""
        with self.coordination_lock:
            from_agent = self.agents.get(from_agent_id)
            to_agent = self.agents.get(to_agent_id)

            if not from_agent or not to_agent:
                return False

            task = next((t for t in from_agent.tasks if t.task_id == task_id), None)
            if not task:
                return False

            from_agent.tasks.remove(task)
            from_agent.load -= from_agent._estimate_load(task)

            if not to_agent.can_accept_task(task):
                from_agent.tasks.append(task)
                from_agent.load += from_agent._estimate_load(task)
                return False

            if to_agent.assign_task(task):
                self._send_message(
                    from_agent_id,
                    to_agent_id,
                    MessageType.HANDOVER,
                    {"task": task},
                )
                return True

            return False

    def get_agent_status(self, agent_id: str) -> Optional[dict]:
        """Get current status of an agent."""
        agent = self.agents.get(agent_id)
        if not agent:
            return None
        return {
            "agent_id": agent.agent_id,
            "type": agent.agent_type.value,
            "state": agent.state.value,
            "load": agent.load,
            "max_load": agent.max_load,
            "region": agent.region,
            "tasks_count": len(agent.tasks),
            "metrics": {
                "completed": agent.metrics.tasks_completed,
                "failed": agent.metrics.tasks_failed,
                "avg_response": agent.metrics.avg_response_time,
            },
        }

    def get_coordination_summary(self) -> dict:
        """Get summary of the coordination system."""
        return {
            "total_agents": len(self.agents),
            "active_agents": sum(
                1 for a in self.agents.values() if a.state == AgentState.ACTIVE
            ),
            "pending_tasks": len(self.pending_tasks),
            "total_tasks": sum(len(a.tasks) for a in self.agents.values()),
            "completed_tasks": sum(
                a.metrics.tasks_completed for a in self.agents.values()
            ),
            "messages_in_queue": len(self.message_queue),
        }

    def simulate_task_execution(
        self, task_id: str, agent_id: str, duration: float
    ) -> bool:
        """Simulate task execution by an agent."""
        agent = self.agents.get(agent_id)
        if not agent:
            return False

        task = next((t for t in agent.tasks if t.task_id == task_id), None)
        if not task:
            return False

        task.started_at = time.time()
        time.sleep(duration)
        task.status = "completed"
        task.completed_at = time.time()
        agent.metrics.tasks_completed += 1
        agent.load = max(0, agent.load - agent._estimate_load(task))
        return True

    def handle_emergency(
        self,
        emergency_type: str,
        affected_agents: list[str],
        payload: dict,
    ) -> dict:
        """Handle emergency situation across agents."""
        emergency_task = self.create_task(
            task_type="emergency_response",
            priority=TaskPriority.EMERGENCY,
            payload=payload,
        )

        self.broadcast_message(
            sender_id="emergency_handler",
            message_type=MessageType.EMERGENCY_ALERT,
            payload={
                "emergency_type": emergency_type,
                "task_id": emergency_task.task_id,
                "affected_agents": affected_agents,
            },
        )

        for agent_id in affected_agents:
            agent = self.agents.get(agent_id)
            if agent:
                agent.state = AgentState.EMERGENCY

        emergency_agent = self.agents.get("emergency_handler")
        if emergency_agent:
            emergency_agent.assign_task(emergency_task)

        return {
            "emergency_id": emergency_task.task_id,
            "status": "handled",
            "affected_count": len(affected_agents),
        }

    def load_balance(self) -> dict:
        """Load balance tasks across agents."""
        with self.coordination_lock:
            overloaded = [a for a in self.agents.values() if a.load > a.max_load * 0.8]
            underutilized = [
                a for a in self.agents.values() if a.load < a.max_load * 0.4
            ]

            handoffs = 0
            for overload in overloaded:
                for task in list(overload.tasks):
                    if task.priority in (TaskPriority.LOW, TaskPriority.NORMAL):
                        for under in underutilized:
                            if under.can_accept_task(task):
                                if self.handover_task(
                                    task.task_id, overload.agent_id, under.agent_id
                                ):
                                    handoffs += 1
                                    break

            return {
                "overloaded_agents": len(overloaded),
                "underutilized_agents": len(underutilized),
                "handoffs_performed": handoffs,
            }


def create_coordinator(
    num_controllers: int = 3,
    protocol: CommunicationProtocol = CommunicationProtocol.DIRECT,
) -> MultiAgentCoordinator:
    """Factory function to create a multi-agent coordinator."""
    return MultiAgentCoordinator(num_controllers=num_controllers, protocol=protocol)


def build_with_extended_agents(
    num_controllers: int = 3,
    num_conflict_resolvers: int = 2,
    num_formation_controllers: int = 2,
) -> MultiAgentCoordinator:
    """Build coordinator with extended agent configuration."""
    coordinator = MultiAgentCoordinator(
        num_controllers=num_controllers,
        protocol=CommunicationProtocol.HIERARCHICAL,
    )

    for i in range(num_conflict_resolvers):
        agent = Agent(
            agent_id=f"conflict_resolver_{i}",
            agent_type=AgentType.CONFLICT_RESOLVER,
            capabilities=["conflict_resolution", "path_planning"],
            region=f"zone_{i % num_controllers}",
        )
        coordinator.register_agent(agent)

    for i in range(num_formation_controllers):
        agent = Agent(
            agent_id=f"formation_controller_{i}",
            agent_type=AgentType.FORMATION_CONTROLLER,
            capabilities=["formation_management", "swarm_coordination"],
            region="all",
        )
        coordinator.register_agent(agent)

    return coordinator
