"""
Phase 502: Collective Intelligence Engine
집단지성 강화: 정보 공유 네트워크, 합의 알고리즘, 분산 학습.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple, Set


class ConsensusAlgorithm(Enum):
    MAJORITY = "majority"
    WEIGHTED = "weighted"
    BYZANTINE = "byzantine"
    PAXOS_LIKE = "paxos_like"


class KnowledgeType(Enum):
    OBSTACLE = "obstacle"
    TARGET = "target"
    WEATHER = "weather"
    THREAT = "threat"
    RESOURCE = "resource"


@dataclass
class KnowledgeItem:
    item_id: str
    ktype: KnowledgeType
    position: np.ndarray
    confidence: float
    source_drone: int
    timestamp: float
    shared_count: int = 0


@dataclass
class SwarmBelief:
    items: Dict[str, KnowledgeItem] = field(default_factory=dict)
    consensus_count: int = 0
    conflict_count: int = 0


class InformationNetwork:
    def __init__(self, n_drones: int, comm_range: float = 100.0, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_drones = n_drones
        self.comm_range = comm_range
        self.positions = self.rng.uniform(-200, 200, (n_drones, 3))
        self.positions[:, 2] = self.rng.uniform(20, 80, n_drones)
        self.adjacency: Dict[int, Set[int]] = {i: set() for i in range(n_drones)}
        self._update_topology()

    def _update_topology(self):
        self.adjacency = {i: set() for i in range(self.n_drones)}
        for i in range(self.n_drones):
            for j in range(i + 1, self.n_drones):
                dist = np.linalg.norm(self.positions[i] - self.positions[j])
                if dist <= self.comm_range:
                    self.adjacency[i].add(j)
                    self.adjacency[j].add(i)

    def propagate(self, source: int, item: KnowledgeItem, max_hops: int = 3) -> List[int]:
        reached = {source}
        frontier = {source}
        for _ in range(max_hops):
            next_frontier = set()
            for node in frontier:
                for neighbor in self.adjacency.get(node, set()):
                    if neighbor not in reached:
                        reached.add(neighbor)
                        next_frontier.add(neighbor)
                        item.shared_count += 1
            frontier = next_frontier
            if not frontier:
                break
        return list(reached)

    def connectivity(self) -> float:
        if self.n_drones <= 1:
            return 1.0
        visited = set()
        queue = [0]
        visited.add(0)
        while queue:
            node = queue.pop(0)
            for neighbor in self.adjacency.get(node, set()):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        return len(visited) / self.n_drones


class ConsensusEngine:
    def __init__(self, n_drones: int, algorithm: ConsensusAlgorithm = ConsensusAlgorithm.WEIGHTED,
                 seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_drones = n_drones
        self.algorithm = algorithm
        self.trust_weights = np.ones(n_drones) / n_drones
        self.rounds = 0

    def vote(self, proposals: Dict[int, float]) -> Tuple[float, float]:
        self.rounds += 1
        if not proposals:
            return 0.0, 0.0
        values = list(proposals.values())
        if self.algorithm == ConsensusAlgorithm.WEIGHTED:
            total_w = sum(self.trust_weights[d] for d in proposals)
            result = sum(v * self.trust_weights[d] for d, v in proposals.items()) / max(total_w, 1e-8)
            devs = [abs(v - result) for v in values]
            agreement = 1.0 - np.mean(devs) / (abs(result) + 1e-8)
        elif self.algorithm == ConsensusAlgorithm.BYZANTINE:
            sv = sorted(values)
            trim = max(1, len(sv) // 3)
            trimmed = sv[trim:-trim] if len(sv) > 2 * trim else sv
            result = float(np.mean(trimmed))
            agreement = len(trimmed) / max(len(sv), 1)
        else:
            result = float(np.median(values))
            agreement = 1.0 - np.std(values) / (np.mean(np.abs(values)) + 1e-8)
        return round(result, 4), round(float(max(0, min(1, agreement))), 4)


class CollectiveIntelligence:
    def __init__(self, n_drones: int = 30, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_drones = n_drones
        self.network = InformationNetwork(n_drones, seed=seed)
        self.consensus = ConsensusEngine(n_drones, seed=seed)
        self.belief = SwarmBelief()
        self.time = 0.0
        self._item_counter = 0

    def discover(self, drone_id: int, ktype: KnowledgeType, position: np.ndarray) -> KnowledgeItem:
        self._item_counter += 1
        item = KnowledgeItem(f"K-{self._item_counter:05d}", ktype, position,
                            self.rng.uniform(0.5, 1.0), drone_id, self.time)
        self.belief.items[item.item_id] = item
        self.network.propagate(drone_id, item)
        return item

    def reach_consensus(self, topic: str) -> Dict:
        proposals = {i: self.rng.standard_normal() + hash(topic) % 10
                    for i in range(self.n_drones) if self.rng.random() > 0.2}
        result, agreement = self.consensus.vote(proposals)
        if agreement > 0.6:
            self.belief.consensus_count += 1
        else:
            self.belief.conflict_count += 1
        return {"topic": topic, "result": result, "agreement": agreement, "voters": len(proposals)}

    def step(self, dt: float = 0.1) -> Dict:
        self.time += dt
        self.network.positions += self.rng.standard_normal((self.n_drones, 3)) * 2
        self.network._update_topology()
        if self.rng.random() < 0.3:
            drone = self.rng.integers(0, self.n_drones)
            ktype = self.rng.choice(list(KnowledgeType))
            pos = self.network.positions[drone] + self.rng.standard_normal(3) * 10
            self.discover(drone, ktype, pos)
        return {"time": round(self.time, 2), "knowledge_items": len(self.belief.items),
                "connectivity": round(self.network.connectivity(), 4)}

    def run(self, duration: float = 10, dt: float = 0.1) -> List[Dict]:
        return [self.step(dt) for _ in range(int(duration / dt))]

    def summary(self) -> Dict:
        return {"drones": self.n_drones, "knowledge_items": len(self.belief.items),
                "consensus_count": self.belief.consensus_count,
                "conflict_count": self.belief.conflict_count,
                "connectivity": round(self.network.connectivity(), 4)}
