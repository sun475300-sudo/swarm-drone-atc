"""Tests for Multi-Agent Coordination Framework (Phase 220-239).

Tests cover agent registration, task assignment, message passing,
load balancing, emergency handling, and coordination protocols.
"""

import pytest
import time
from simulation.multi_agent_coordination import (
    Agent,
    AgentType,
    AgentState,
    AgentMetrics,
    Task,
    TaskPriority,
    MessageType,
    AgentMessage,
    CommunicationProtocol,
    MultiAgentCoordinator,
    create_coordinator,
    build_with_extended_agents,
)


class TestAgentBasics:
    """Test basic agent functionality."""

    def test_create_agent(self):
        """Test agent creation."""
        agent = Agent(
            agent_id="test_agent",
            agent_type=AgentType.AIRSPACE_CONTROLLER,
            capabilities=["conflict_resolution"],
        )
        assert agent.agent_id == "test_agent"
        assert agent.agent_type == AgentType.AIRSPACE_CONTROLLER
        assert agent.state == AgentState.IDLE
        assert agent.load == 0.0

    def test_agent_default_metrics(self):
        """Test agent default metrics."""
        agent = Agent(
            agent_id="test_agent",
            agent_type=AgentType.AIRSPACE_CONTROLLER,
        )
        assert agent.metrics.tasks_completed == 0
        assert agent.metrics.tasks_failed == 0
        assert agent.metrics.avg_response_time == 0.0

    def test_agent_can_accept_task_idle(self):
        """Test agent can accept task when idle."""
        agent = Agent(
            agent_id="test_agent",
            agent_type=AgentType.AIRSPACE_CONTROLLER,
            max_load=100.0,
        )
        task = Task(
            task_id="task_1",
            task_type="test_task",
            priority=TaskPriority.NORMAL,
        )
        assert agent.can_accept_task(task) is True

    def test_agent_cannot_accept_task_offline(self):
        """Test agent cannot accept task when offline."""
        agent = Agent(
            agent_id="test_agent",
            agent_type=AgentType.AIRSPACE_CONTROLLER,
            state=AgentState.OFFLINE,
        )
        task = Task(
            task_id="task_1",
            task_type="test_task",
            priority=TaskPriority.NORMAL,
        )
        assert agent.can_accept_task(task) is False

    def test_agent_cannot_accept_task_at_max_load(self):
        """Test agent cannot accept task at max load."""
        agent = Agent(
            agent_id="test_agent",
            agent_type=AgentType.AIRSPACE_CONTROLLER,
            max_load=100.0,
            load=100.0,
        )
        task = Task(
            task_id="task_1",
            task_type="test_task",
            priority=TaskPriority.NORMAL,
        )
        assert agent.can_accept_task(task) is False

    def test_agent_assign_task(self):
        """Test task assignment to agent."""
        agent = Agent(
            agent_id="test_agent",
            agent_type=AgentType.AIRSPACE_CONTROLLER,
            max_load=100.0,
        )
        task = Task(
            task_id="task_1",
            task_type="test_task",
            priority=TaskPriority.NORMAL,
        )
        assert agent.assign_task(task) is True
        assert task.assigned_agent == "test_agent"
        assert task.status == "assigned"
        assert agent.load > 0

    def test_agent_complete_task(self):
        """Test task completion."""
        agent = Agent(
            agent_id="test_agent",
            agent_type=AgentType.AIRSPACE_CONTROLLER,
            max_load=100.0,
        )
        task = Task(
            task_id="task_1",
            task_type="test_task",
            priority=TaskPriority.NORMAL,
        )
        agent.assign_task(task)
        result = {"status": "success", "output": "done"}
        assert agent.complete_task("task_1", result) is True
        assert task.status == "completed"
        assert task.result is not None


class TestCoordinatorBasics:
    """Test coordinator basic functionality."""

    def test_create_coordinator(self):
        """Test coordinator creation."""
        coordinator = create_coordinator(num_controllers=2)
        assert coordinator is not None
        assert len(coordinator.agents) >= 4

    def test_coordinator_initializes_agents(self):
        """Test coordinator initializes agents."""
        coordinator = create_coordinator(num_controllers=3)
        assert len(coordinator.agents) >= 5
        assert "controller_0" in coordinator.agents
        assert "controller_1" in coordinator.agents
        assert "controller_2" in coordinator.agents
        assert "emergency_handler" in coordinator.agents
        assert "weather_monitor" in coordinator.agents

    def test_register_agent(self):
        """Test agent registration."""
        coordinator = create_coordinator(num_controllers=1)
        new_agent = Agent(
            agent_id="new_controller",
            agent_type=AgentType.AIRSPACE_CONTROLLER,
            capabilities=["test"],
        )
        coordinator.register_agent(new_agent)
        assert "new_controller" in coordinator.agents

    def test_unregister_agent(self):
        """Test agent unregistration."""
        coordinator = create_coordinator(num_controllers=1)
        assert coordinator.unregister_agent("controller_0") is True
        assert coordinator.agents["controller_0"].state == AgentState.OFFLINE


class TestTaskManagement:
    """Test task creation and assignment."""

    def test_create_task(self):
        """Test task creation."""
        coordinator = create_coordinator()
        task = coordinator.create_task(
            task_type="conflict_resolution",
            priority=TaskPriority.HIGH,
            payload={"drone_id": "drone_1"},
        )
        assert task.task_id is not None
        assert task.task_type == "conflict_resolution"
        assert task.priority == TaskPriority.HIGH
        assert task.status == "pending"
        assert len(coordinator.pending_tasks) == 1

    def test_assign_task_to_agent(self):
        """Test task assignment to specific agent."""
        coordinator = create_coordinator(num_controllers=1)
        task = coordinator.create_task(
            task_type="conflict_resolution",
            priority=TaskPriority.NORMAL,
            payload={},
        )
        assert coordinator.assign_task_to_agent(task.task_id, "controller_0") is True
        assert len(coordinator.pending_tasks) == 0
        assert len(coordinator.agents["controller_0"].tasks) == 1

    def test_auto_assign_tasks(self):
        """Test automatic task assignment."""
        coordinator = create_coordinator(num_controllers=2)
        coordinator.create_task("conflict_resolution", TaskPriority.NORMAL, {})
        coordinator.create_task("traffic_management", TaskPriority.HIGH, {})
        coordinator.create_task("weather_monitoring", TaskPriority.LOW, {})
        assigned = coordinator.auto_assign_tasks()
        assert assigned >= 2

    def test_task_priority_ordering(self):
        """Test task priority affects assignment."""
        coordinator = create_coordinator(num_controllers=1)
        coordinator.agents["controller_0"].capabilities = ["test_task"]
        coordinator.create_task("test_task", TaskPriority.LOW, {})
        coordinator.create_task("test_task", TaskPriority.CRITICAL, {})
        coordinator.auto_assign_tasks()
        critical_task = next(
            t
            for t in coordinator.agents["controller_0"].tasks
            if t.priority == TaskPriority.CRITICAL
        )
        assert critical_task is not None


class TestMessagePassing:
    """Test inter-agent messaging."""

    def test_send_message(self):
        """Test sending a message."""
        coordinator = create_coordinator(num_controllers=1)
        msg = coordinator._send_message(
            sender_id="controller_0",
            receiver_id="emergency_handler",
            message_type=MessageType.TASK_REQUEST,
            payload={"data": "test"},
        )
        assert msg.message_id is not None
        assert msg.sender_id == "controller_0"
        assert msg.receiver_id == "emergency_handler"
        assert len(coordinator.message_queue) == 1

    def test_broadcast_message(self):
        """Test broadcasting messages."""
        coordinator = create_coordinator(num_controllers=2)
        messages = coordinator.broadcast_message(
            sender_id="emergency_handler",
            message_type=MessageType.EMERGENCY_ALERT,
            payload={"alert": "test"},
        )
        assert len(messages) >= 2

    def test_message_types(self):
        """Test various message types."""
        coordinator = create_coordinator(num_controllers=1)
        for msg_type in MessageType:
            msg = coordinator._send_message(
                sender_id="controller_0",
                receiver_id="emergency_handler",
                message_type=msg_type,
                payload={},
            )
            assert msg.message_type == msg_type


class TestCoordinationProtocols:
    """Test coordination protocols."""

    def test_direct_protocol(self):
        """Test direct communication protocol."""
        coordinator = MultiAgentCoordinator(
            num_controllers=2,
            protocol=CommunicationProtocol.DIRECT,
        )
        assert coordinator.protocol == CommunicationProtocol.DIRECT

    def test_hierarchical_protocol(self):
        """Test hierarchical communication protocol."""
        coordinator = MultiAgentCoordinator(
            num_controllers=2,
            protocol=CommunicationProtocol.HIERARCHICAL,
        )
        assert coordinator.protocol == CommunicationProtocol.HIERARCHICAL

    def test_build_extended_agents(self):
        """Test building coordinator with extended agents."""
        coordinator = build_with_extended_agents(
            num_controllers=2,
            num_conflict_resolvers=1,
            num_formation_controllers=1,
        )
        assert len(coordinator.agents) >= 6
        assert "conflict_resolver_0" in coordinator.agents
        assert "formation_controller_0" in coordinator.agents


class TestTaskHandover:
    """Test task handover between agents."""

    def test_handover_task_success(self):
        """Test successful task handover."""
        coordinator = create_coordinator(num_controllers=2)
        task = coordinator.create_task("conflict_resolution", TaskPriority.NORMAL, {})
        coordinator.assign_task_to_agent(task.task_id, "controller_0")
        assert (
            coordinator.handover_task(task.task_id, "controller_0", "controller_1")
            is True
        )
        assert len(coordinator.agents["controller_0"].tasks) == 0
        assert len(coordinator.agents["controller_1"].tasks) == 1

    def test_handover_task_failure_invalid_agent(self):
        """Test task handover failure with invalid agent."""
        coordinator = create_coordinator(num_controllers=1)
        task = coordinator.create_task("conflict_resolution", TaskPriority.NORMAL, {})
        coordinator.assign_task_to_agent(task.task_id, "controller_0")
        assert (
            coordinator.handover_task(task.task_id, "controller_0", "nonexistent")
            is False
        )


class TestEmergencyHandling:
    """Test emergency handling."""

    def test_handle_emergency(self):
        """Test emergency handling."""
        coordinator = create_coordinator(num_controllers=2)
        result = coordinator.handle_emergency(
            emergency_type="system_failure",
            affected_agents=["controller_0", "controller_1"],
            payload={"severity": "critical"},
        )
        assert result["emergency_id"] is not None
        assert result["status"] == "handled"
        assert result["affected_count"] == 2

    def test_emergency_alerts_agents(self):
        """Test emergency alerts sent to agents."""
        coordinator = create_coordinator(num_controllers=2)
        coordinator.handle_emergency(
            emergency_type="test",
            affected_agents=["controller_0"],
            payload={},
        )
        emergency_msgs = [
            m
            for m in coordinator.message_queue
            if m.message_type == MessageType.EMERGENCY_ALERT
        ]
        assert len(emergency_msgs) > 0


class TestLoadBalancing:
    """Test load balancing functionality."""

    def test_load_balance(self):
        """Test load balancing."""
        coordinator = create_coordinator(num_controllers=2)
        coordinator.create_task("conflict_resolution", TaskPriority.LOW, {})
        coordinator.auto_assign_tasks()
        result = coordinator.load_balance()
        assert "overloaded_agents" in result
        assert "underutilized_agents" in result
        assert "handoffs_performed" in result


class TestAgentStatus:
    """Test agent status reporting."""

    def test_get_agent_status(self):
        """Test getting agent status."""
        coordinator = create_coordinator(num_controllers=1)
        status = coordinator.get_agent_status("controller_0")
        assert status is not None
        assert status["agent_id"] == "controller_0"
        assert "load" in status
        assert "metrics" in status

    def test_get_agent_status_invalid(self):
        """Test getting status of invalid agent."""
        coordinator = create_coordinator()
        assert coordinator.get_agent_status("nonexistent") is None


class TestCoordinationSummary:
    """Test coordination summary."""

    def test_get_coordination_summary(self):
        """Test getting coordination summary."""
        coordinator = create_coordinator(num_controllers=2)
        summary = coordinator.get_coordination_summary()
        assert summary["total_agents"] >= 4
        assert "pending_tasks" in summary
        assert "completed_tasks" in summary


class TestTaskExecution:
    """Test simulated task execution."""

    def test_simulate_task_execution(self):
        """Test task execution simulation."""
        coordinator = create_coordinator(num_controllers=1)
        task = coordinator.create_task("test", TaskPriority.NORMAL, {})
        coordinator.assign_task_to_agent(task.task_id, "controller_0")
        assert (
            coordinator.simulate_task_execution(task.task_id, "controller_0", 0.01)
            is True
        )
        assert coordinator.agents["controller_0"].metrics.tasks_completed == 1


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_assign_nonexistent_task(self):
        """Test assigning nonexistent task."""
        coordinator = create_coordinator(num_controllers=1)
        assert coordinator.assign_task_to_agent("nonexistent", "controller_0") is False

    def test_assign_to_invalid_agent(self):
        """Test assigning task to invalid agent."""
        coordinator = create_coordinator()
        task = coordinator.create_task("test", TaskPriority.NORMAL, {})
        assert coordinator.assign_task_to_agent(task.task_id, "nonexistent") is False

    def test_complete_nonexistent_task(self):
        """Test completing nonexistent task."""
        agent = Agent(agent_id="test", agent_type=AgentType.AIRSPACE_CONTROLLER)
        assert agent.complete_task("nonexistent", {}) is False
