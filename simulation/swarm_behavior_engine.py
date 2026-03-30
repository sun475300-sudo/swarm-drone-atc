"""Phase 294: Swarm Behavior Engine — 군집 행동 엔진.

Reynolds Boids 모델 확장, 분리/정렬/응집 + 장애물 회피,
사용자 정의 행동 규칙 및 행동 전환 FSM.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class BehaviorMode(Enum):
    FLOCK = "flock"
    SCATTER = "scatter"
    CONVERGE = "converge"
    PATROL = "patrol"
    EVADE = "evade"
    SEARCH = "search"
    FOLLOW_LEADER = "follow_leader"
    ORBIT = "orbit"


@dataclass
class BoidState:
    agent_id: str
    position: np.ndarray
    velocity: np.ndarray
    acceleration: np.ndarray = field(default_factory=lambda: np.zeros(3))
    max_speed: float = 15.0
    max_force: float = 5.0
    perception_radius: float = 50.0
    behavior: BehaviorMode = BehaviorMode.FLOCK


@dataclass
class BehaviorWeights:
    separation: float = 2.0
    alignment: float = 1.0
    cohesion: float = 1.0
    obstacle_avoidance: float = 3.0
    goal_seeking: float = 1.5
    leader_follow: float = 2.0


class ReynoldsBoids:
    """확장 Reynolds Boids 모델."""

    @staticmethod
    def separation(agent: BoidState, neighbors: List[BoidState], desired_dist: float = 15.0) -> np.ndarray:
        steer = np.zeros(3)
        count = 0
        for nb in neighbors:
            diff = agent.position - nb.position
            d = np.linalg.norm(diff)
            if 0 < d < desired_dist:
                steer += diff / (d * d)
                count += 1
        if count > 0:
            steer /= count
        return steer

    @staticmethod
    def alignment(agent: BoidState, neighbors: List[BoidState]) -> np.ndarray:
        if not neighbors:
            return np.zeros(3)
        avg_vel = np.mean([n.velocity for n in neighbors], axis=0)
        return avg_vel - agent.velocity

    @staticmethod
    def cohesion(agent: BoidState, neighbors: List[BoidState]) -> np.ndarray:
        if not neighbors:
            return np.zeros(3)
        center = np.mean([n.position for n in neighbors], axis=0)
        return center - agent.position

    @staticmethod
    def seek(agent: BoidState, target: np.ndarray) -> np.ndarray:
        desired = target - agent.position
        d = np.linalg.norm(desired)
        if d < 0.1:
            return np.zeros(3)
        desired = desired / d * agent.max_speed
        return desired - agent.velocity

    @staticmethod
    def evade(agent: BoidState, threat: np.ndarray) -> np.ndarray:
        away = agent.position - threat
        d = np.linalg.norm(away)
        if d < 0.1:
            return np.zeros(3)
        return away / d * agent.max_speed

    @staticmethod
    def orbit(agent: BoidState, center: np.ndarray, radius: float = 30.0) -> np.ndarray:
        to_center = center - agent.position
        dist = np.linalg.norm(to_center)
        if dist < 0.1:
            return np.zeros(3)
        # Tangent direction
        tangent = np.array([-to_center[1], to_center[0], 0])
        tangent = tangent / max(np.linalg.norm(tangent), 1e-6)
        # Radial correction
        radial = to_center / dist * (dist - radius) * 0.1
        return tangent * agent.max_speed * 0.5 + radial


class SwarmBehaviorEngine:
    """군집 행동 엔진.

    - Boids 3규칙 + 확장 행동
    - 행동 모드 전환 FSM
    - 사용자 정의 가중치 조정
    - 실시간 군집 분석
    """

    def __init__(self, weights: Optional[BehaviorWeights] = None, rng_seed: int = 42):
        self._rng = np.random.default_rng(rng_seed)
        self.weights = weights or BehaviorWeights()
        self._agents: Dict[str, BoidState] = {}
        self._boids = ReynoldsBoids()
        self._obstacles: List[np.ndarray] = []
        self._goal: Optional[np.ndarray] = None
        self._leader_id: Optional[str] = None
        self._step_count = 0

    def add_agent(self, agent: BoidState):
        self._agents[agent.agent_id] = agent

    def remove_agent(self, agent_id: str):
        self._agents.pop(agent_id, None)

    def add_obstacle(self, position: np.ndarray, radius: float = 10.0):
        self._obstacles.append(position)

    def set_goal(self, goal: np.ndarray):
        self._goal = goal

    def set_leader(self, leader_id: str):
        self._leader_id = leader_id

    def set_behavior(self, agent_id: str, mode: BehaviorMode):
        agent = self._agents.get(agent_id)
        if agent:
            agent.behavior = mode

    def set_all_behavior(self, mode: BehaviorMode):
        for agent in self._agents.values():
            agent.behavior = mode

    def _get_neighbors(self, agent: BoidState) -> List[BoidState]:
        neighbors = []
        for other in self._agents.values():
            if other.agent_id == agent.agent_id:
                continue
            if np.linalg.norm(other.position - agent.position) <= agent.perception_radius:
                neighbors.append(other)
        return neighbors

    def _compute_force(self, agent: BoidState) -> np.ndarray:
        neighbors = self._get_neighbors(agent)
        force = np.zeros(3)
        w = self.weights

        if agent.behavior == BehaviorMode.FLOCK:
            force += self._boids.separation(agent, neighbors) * w.separation
            force += self._boids.alignment(agent, neighbors) * w.alignment
            force += self._boids.cohesion(agent, neighbors) * w.cohesion
        elif agent.behavior == BehaviorMode.SCATTER:
            force += self._boids.separation(agent, neighbors) * w.separation * 5
        elif agent.behavior == BehaviorMode.CONVERGE:
            force += self._boids.cohesion(agent, neighbors) * w.cohesion * 3
        elif agent.behavior == BehaviorMode.EVADE:
            for obs in self._obstacles:
                force += self._boids.evade(agent, obs) * w.obstacle_avoidance
        elif agent.behavior == BehaviorMode.FOLLOW_LEADER:
            if self._leader_id and self._leader_id in self._agents:
                leader = self._agents[self._leader_id]
                force += self._boids.seek(agent, leader.position) * w.leader_follow
                force += self._boids.separation(agent, neighbors) * w.separation
        elif agent.behavior == BehaviorMode.ORBIT:
            if self._goal is not None:
                force += self._boids.orbit(agent, self._goal) * 2.0
        elif agent.behavior == BehaviorMode.SEARCH:
            noise = self._rng.normal(0, 2, 3)
            force += noise + self._boids.separation(agent, neighbors) * w.separation

        # Goal seeking (always active if goal set)
        if self._goal is not None and agent.behavior not in (BehaviorMode.EVADE, BehaviorMode.ORBIT):
            force += self._boids.seek(agent, self._goal) * w.goal_seeking

        # Obstacle avoidance
        for obs in self._obstacles:
            dist = np.linalg.norm(agent.position - obs)
            if dist < 30.0:
                force += self._boids.evade(agent, obs) * w.obstacle_avoidance

        # Clamp force
        mag = np.linalg.norm(force)
        if mag > agent.max_force:
            force = force / mag * agent.max_force
        return force

    def step(self, dt: float = 0.1) -> Dict[str, np.ndarray]:
        self._step_count += 1
        new_positions = {}
        for agent in self._agents.values():
            force = self._compute_force(agent)
            agent.acceleration = force
            agent.velocity += force * dt
            speed = np.linalg.norm(agent.velocity)
            if speed > agent.max_speed:
                agent.velocity = agent.velocity / speed * agent.max_speed
            agent.position += agent.velocity * dt
            new_positions[agent.agent_id] = agent.position.copy()
        return new_positions

    def get_swarm_center(self) -> np.ndarray:
        if not self._agents:
            return np.zeros(3)
        return np.mean([a.position for a in self._agents.values()], axis=0)

    def get_swarm_spread(self) -> float:
        if len(self._agents) < 2:
            return 0.0
        center = self.get_swarm_center()
        return float(np.mean([np.linalg.norm(a.position - center) for a in self._agents.values()]))

    def summary(self) -> dict:
        behaviors = {}
        for a in self._agents.values():
            behaviors[a.behavior.value] = behaviors.get(a.behavior.value, 0) + 1
        return {
            "total_agents": len(self._agents),
            "step_count": self._step_count,
            "swarm_center": self.get_swarm_center().tolist(),
            "swarm_spread": round(self.get_swarm_spread(), 2),
            "behaviors": behaviors,
            "obstacles": len(self._obstacles),
        }
