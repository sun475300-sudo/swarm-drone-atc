"""
Phase 477: Swarm Consciousness
Collective consciousness and emergent intelligence for drone swarm.
"""

import numpy as np
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Optional, Tuple, Any, Callable
from collections import defaultdict


class ConsciousnessLevel(Enum):
    """Consciousness levels."""

    REACTIVE = auto()
    ADAPTIVE = auto()
    DELIBERATIVE = auto()
    SELF_AWARE = auto()
    COLLECTIVE = auto()


@dataclass
class SharedMemory:
    """Shared memory across swarm."""

    memory_id: str
    data: Dict[str, Any]
    access_count: int = 0
    last_updated: float = field(default_factory=time.time)
    priority: int = 0


@dataclass
class CollectiveBelief:
    """Collective belief state."""

    belief_id: str
    content: Dict[str, Any]
    confidence: float
    supporters: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


@dataclass
class EmergentGoal:
    """Emergent goal from collective behavior."""

    goal_id: str
    description: str
    priority: float
    contributors: List[str] = field(default_factory=list)
    progress: float = 0.0
    is_active: bool = True


class SwarmConsciousness:
    """Collective consciousness engine."""

    def __init__(self, n_drones: int, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_drones = n_drones
        self.level = ConsciousnessLevel.COLLECTIVE
        self.shared_memory: Dict[str, SharedMemory] = {}
        self.beliefs: Dict[str, CollectiveBelief] = {}
        self.goals: Dict[str, EmergentGoal] = {}
        self.decision_history: List[Dict[str, Any]] = []
        self.consensus_threshold = 0.7
        self._init_consciousness()

    def _init_consciousness(self) -> None:
        self.shared_memory["global_state"] = SharedMemory(
            "global_state", {"n_drones": self.n_drones, "status": "active"}
        )
        self.beliefs["safety"] = CollectiveBelief(
            "safety",
            {"min_separation": 10.0},
            0.9,
            [f"drone_{i}" for i in range(self.n_drones)],
        )

    def share_knowledge(
        self, drone_id: str, key: str, knowledge: Dict[str, Any]
    ) -> None:
        if key not in self.shared_memory:
            self.shared_memory[key] = SharedMemory(key, knowledge)
        else:
            self.shared_memory[key].data.update(knowledge)
            self.shared_memory[key].access_count += 1
            self.shared_memory[key].last_updated = time.time()

    def form_belief(
        self, belief_id: str, content: Dict[str, Any], supporters: List[str]
    ) -> CollectiveBelief:
        confidence = len(supporters) / self.n_drones
        belief = CollectiveBelief(belief_id, content, confidence, supporters)
        self.beliefs[belief_id] = belief
        return belief

    def reach_consensus(self, topic: str, proposals: Dict[str, Any]) -> Dict[str, Any]:
        vote_counts = defaultdict(int)
        for drone_id, proposal in proposals.items():
            vote_counts[str(proposal)] += 1
        total_votes = sum(vote_counts.values())
        for proposal, count in vote_counts.items():
            if count / total_votes >= self.consensus_threshold:
                return {"consensus": True, "decision": proposal, "votes": count}
        return {"consensus": False, "decision": None, "votes": 0}

    def form_emergent_goal(
        self, goal_id: str, description: str, contributors: List[str]
    ) -> EmergentGoal:
        goal = EmergentGoal(
            goal_id, description, len(contributors) / self.n_drones, contributors
        )
        self.goals[goal_id] = goal
        return goal

    def update_goal_progress(self, goal_id: str, progress: float) -> None:
        if goal_id in self.goals:
            self.goals[goal_id].progress = min(1.0, progress)

    def collective_decision(
        self, options: List[Dict[str, Any]], criteria: Callable[[Dict], float]
    ) -> Dict[str, Any]:
        scored = [(opt, criteria(opt)) for opt in options]
        scored.sort(key=lambda x: x[1], reverse=True)
        decision = scored[0][0] if scored else {}
        self.decision_history.append(
            {
                "decision": decision,
                "score": scored[0][1] if scored else 0,
                "timestamp": time.time(),
            }
        )
        return decision

    def get_consciousness_state(self) -> Dict[str, Any]:
        return {
            "level": self.level.name,
            "shared_memories": len(self.shared_memory),
            "beliefs": len(self.beliefs),
            "active_goals": sum(1 for g in self.goals.values() if g.is_active),
            "decisions_made": len(self.decision_history),
        }


if __name__ == "__main__":
    consciousness = SwarmConsciousness(n_drones=10, seed=42)
    consciousness.share_knowledge("drone_0", "weather", {"wind": 5, "rain": False})
    belief = consciousness.form_belief(
        "route_safety", {"safe_altitude": 50}, [f"drone_{i}" for i in range(5)]
    )
    goal = consciousness.form_emergent_goal(
        "explore", "Explore area", [f"drone_{i}" for i in range(8)]
    )
    print(f"State: {consciousness.get_consciousness_state()}")
