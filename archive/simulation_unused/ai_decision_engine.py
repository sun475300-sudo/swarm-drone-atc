"""
Phase 471: AI-Powered Autonomous Decision Engine
AI-driven autonomous decision making for drone swarm operations.
"""

import numpy as np
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Optional, Tuple, Any, Callable
from collections import defaultdict


class DecisionType(Enum):
    """Decision types."""

    ROUTE_PLANNING = auto()
    COLLISION_AVOIDANCE = auto()
    TASK_ALLOCATION = auto()
    EMERGENCY_RESPONSE = auto()
    ENERGY_MANAGEMENT = auto()
    FORMATION_CONTROL = auto()
    THREAT_ASSESSMENT = auto()


class DecisionPriority(Enum):
    """Decision priority levels."""

    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


class ConfidenceLevel(Enum):
    """AI confidence levels."""

    VERY_HIGH = auto()
    HIGH = auto()
    MEDIUM = auto()
    LOW = auto()
    UNCERTAIN = auto()


@dataclass
class DecisionContext:
    """Decision context."""

    decision_type: DecisionType
    drone_id: str
    position: np.ndarray
    velocity: np.ndarray
    battery: float
    threats: List[Dict[str, Any]]
    neighbors: List[str]
    environment: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)


@dataclass
class Decision:
    """AI decision output."""

    decision_id: str
    decision_type: DecisionType
    priority: DecisionPriority
    action: str
    parameters: Dict[str, Any]
    confidence: ConfidenceLevel
    reasoning: List[str]
    expected_outcome: Dict[str, float]
    timestamp: float = field(default_factory=time.time)


@dataclass
class DecisionRule:
    """Decision rule."""

    rule_id: str
    condition: Callable[[DecisionContext], bool]
    action: str
    priority: DecisionPriority
    confidence: float = 0.9


@dataclass
class DecisionHistory:
    """Decision history record."""

    decision: Decision
    outcome: Dict[str, Any]
    success: bool
    feedback: float = 0.0


class AIDecisionEngine:
    """AI-powered autonomous decision engine."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.rules: Dict[str, DecisionRule] = {}
        self.decision_history: List[DecisionHistory] = []
        self.active_decisions: Dict[str, Decision] = {}
        self.decision_count = 0
        self._init_default_rules()

    def _init_default_rules(self) -> None:
        self.add_rule(
            "critical_battery",
            lambda ctx: ctx.battery < 20,
            "emergency_rtl",
            DecisionPriority.CRITICAL,
            0.95,
        )
        self.add_rule(
            "collision_imminent",
            lambda ctx: any(t.get("distance", 999) < 10 for t in ctx.threats),
            "emergency_avoid",
            DecisionPriority.CRITICAL,
            0.99,
        )
        self.add_rule(
            "low_battery",
            lambda ctx: ctx.battery < 40,
            "return_to_base",
            DecisionPriority.HIGH,
            0.85,
        )
        self.add_rule(
            "threat_detected",
            lambda ctx: len(ctx.threats) > 0,
            "assess_threat",
            DecisionPriority.HIGH,
            0.80,
        )
        self.add_rule(
            "optimal_cruise",
            lambda ctx: ctx.battery > 60 and len(ctx.threats) == 0,
            "continue_mission",
            DecisionPriority.LOW,
            0.90,
        )

    def add_rule(
        self,
        rule_id: str,
        condition: Callable[[DecisionContext], bool],
        action: str,
        priority: DecisionPriority,
        confidence: float = 0.9,
    ) -> None:
        self.rules[rule_id] = DecisionRule(
            rule_id, condition, action, priority, confidence
        )

    def evaluate_context(self, context: DecisionContext) -> List[Decision]:
        decisions = []
        for rule_id, rule in self.rules.items():
            if rule.condition(context):
                self.decision_count += 1
                decision = Decision(
                    decision_id=f"dec_{self.decision_count}",
                    decision_type=self._infer_decision_type(rule.action),
                    priority=rule.priority,
                    action=rule.action,
                    parameters=self._generate_parameters(context, rule.action),
                    confidence=self._map_confidence(rule.confidence),
                    reasoning=[
                        f"Rule '{rule_id}' triggered",
                        f"Battery: {context.battery}%",
                        f"Threats: {len(context.threats)}",
                    ],
                    expected_outcome=self._predict_outcome(context, rule.action),
                )
                decisions.append(decision)
        decisions.sort(key=lambda d: d.priority.value)
        return decisions

    def _infer_decision_type(self, action: str) -> DecisionType:
        mapping = {
            "emergency_rtl": DecisionType.ENERGY_MANAGEMENT,
            "emergency_avoid": DecisionType.COLLISION_AVOIDANCE,
            "return_to_base": DecisionType.ENERGY_MANAGEMENT,
            "assess_threat": DecisionType.THREAT_ASSESSMENT,
            "continue_mission": DecisionType.ROUTE_PLANNING,
            "change_formation": DecisionType.FORMATION_CONTROL,
            "reallocate_tasks": DecisionType.TASK_ALLOCATION,
        }
        return mapping.get(action, DecisionType.ROUTE_PLANNING)

    def _generate_parameters(
        self, context: DecisionContext, action: str
    ) -> Dict[str, Any]:
        params = {"drone_id": context.drone_id}
        if action == "emergency_rtl":
            params["target"] = [0, 0, 0]
            params["speed"] = "max"
        elif action == "emergency_avoid":
            avoid_dir = np.zeros(3)
            for threat in context.threats:
                tpos = np.array(threat.get("position", [0, 0, 0]))
                diff = context.position - tpos
                dist = np.linalg.norm(diff)
                if dist > 0:
                    avoid_dir += diff / dist
            if np.linalg.norm(avoid_dir) > 0:
                avoid_dir /= np.linalg.norm(avoid_dir)
            params["direction"] = avoid_dir.tolist()
            params["distance"] = 50
        elif action == "return_to_base":
            params["target"] = [0, 0, 0]
            params["speed"] = "cruise"
        elif action == "assess_threat":
            params["threats"] = context.threats
            params["scan_radius"] = 100
        elif action == "continue_mission":
            params["maintain_course"] = True
        return params

    def _predict_outcome(
        self, context: DecisionContext, action: str
    ) -> Dict[str, float]:
        outcome = {"success_probability": 0.9, "energy_cost": 5.0, "time_cost": 10.0}
        if action == "emergency_rtl":
            outcome["success_probability"] = 0.95
            outcome["energy_cost"] = context.battery * 0.3
        elif action == "emergency_avoid":
            outcome["success_probability"] = 0.99
            outcome["energy_cost"] = 2.0
        elif action == "assess_threat":
            outcome["success_probability"] = 0.85
            outcome["energy_cost"] = 1.0
        return outcome

    def _map_confidence(self, confidence: float) -> ConfidenceLevel:
        if confidence > 0.95:
            return ConfidenceLevel.VERY_HIGH
        elif confidence > 0.85:
            return ConfidenceLevel.HIGH
        elif confidence > 0.70:
            return ConfidenceLevel.MEDIUM
        elif confidence > 0.50:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.UNCERTAIN

    def execute_decision(self, decision: Decision) -> bool:
        self.active_decisions[decision.decision_id] = decision
        return True

    def record_outcome(
        self,
        decision_id: str,
        outcome: Dict[str, Any],
        success: bool,
        feedback: float = 0.0,
    ) -> None:
        if decision_id in self.active_decisions:
            history = DecisionHistory(
                self.active_decisions[decision_id], outcome, success, feedback
            )
            self.decision_history.append(history)
            del self.active_decisions[decision_id]

    def get_decision_stats(self) -> Dict[str, Any]:
        successful = sum(1 for h in self.decision_history if h.success)
        total = len(self.decision_history)
        return {
            "total_decisions": self.decision_count,
            "active_decisions": len(self.active_decisions),
            "completed_decisions": total,
            "success_rate": successful / total if total > 0 else 0,
            "avg_feedback": np.mean([h.feedback for h in self.decision_history])
            if self.decision_history
            else 0,
            "rules": len(self.rules),
        }


class SwarmDecisionCoordinator:
    """Coordinates decisions across drone swarm."""

    def __init__(self, n_drones: int, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.engine = AIDecisionEngine(seed)
        self.drone_contexts: Dict[str, DecisionContext] = {}
        self.drone_positions: Dict[str, np.ndarray] = {}
        self._init_swarm(n_drones)

    def _init_swarm(self, n: int) -> None:
        for i in range(n):
            pos = self.rng.uniform(-100, 100, size=3)
            vel = self.rng.uniform(-5, 5, size=3)
            ctx = DecisionContext(
                DecisionType.ROUTE_PLANNING,
                f"drone_{i}",
                pos,
                vel,
                battery=100.0,
                threats=[],
                neighbors=[],
                environment={"weather": "clear", "wind_speed": 5},
            )
            self.drone_contexts[f"drone_{i}"] = ctx
            self.drone_positions[f"drone_{i}"] = pos

    def update_context(self, drone_id: str, **kwargs) -> None:
        if drone_id in self.drone_contexts:
            ctx = self.drone_contexts[drone_id]
            for key, value in kwargs.items():
                if hasattr(ctx, key):
                    setattr(ctx, key, value)

    def evaluate_all(self) -> Dict[str, List[Decision]]:
        results = {}
        for drone_id, ctx in self.drone_contexts.items():
            decisions = self.engine.evaluate_context(ctx)
            if decisions:
                results[drone_id] = decisions
                self.engine.execute_decision(decisions[0])
        return results

    def handle_emergency(
        self, drone_id: str, emergency_type: str, severity: str = "high"
    ) -> Optional[Decision]:
        if drone_id not in self.drone_contexts:
            return None
        ctx = self.drone_contexts[drone_id]
        ctx.threats.append(
            {
                "type": emergency_type,
                "severity": severity,
                "position": ctx.position.tolist(),
                "distance": 5,
            }
        )
        decisions = self.engine.evaluate_context(ctx)
        if decisions:
            emergency_decisions = [
                d for d in decisions if d.priority == DecisionPriority.CRITICAL
            ]
            if emergency_decisions:
                self.engine.execute_decision(emergency_decisions[0])
                return emergency_decisions[0]
        return None

    def get_swarm_decisions(self) -> Dict[str, Any]:
        return {
            "engine_stats": self.engine.get_decision_stats(),
            "active_drones": len(self.drone_contexts),
            "drones_with_threats": sum(
                1 for c in self.drone_contexts.values() if len(c.threats) > 0
            ),
            "low_battery_drones": sum(
                1 for c in self.drone_contexts.values() if c.battery < 40
            ),
        }


if __name__ == "__main__":
    coordinator = SwarmDecisionCoordinator(n_drones=10, seed=42)
    results = coordinator.evaluate_all()
    print(f"Decisions made: {len(results)}")
    for drone_id, decisions in list(results.items())[:3]:
        print(f"  {drone_id}: {decisions[0].action} ({decisions[0].confidence.name})")
    emergency = coordinator.handle_emergency("drone_0", "collision", "critical")
    if emergency:
        print(f"Emergency: {emergency.action} ({emergency.priority.name})")
    print(f"Stats: {coordinator.get_swarm_decisions()}")
