"""
Phase 474: Autonomous Negotiation Engine
다자간 협상 — 양보 전략, 효용 함수, 합의 도출.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple


class ConcessionStrategy(Enum):
    LINEAR = "linear"
    BOULWARE = "boulware"
    CONCEDER = "conceder"
    TOUGHGUY = "toughguy"
    RANDOM = "random"


@dataclass
class NegotiationIssue:
    name: str
    min_value: float
    max_value: float
    weight: float = 1.0


@dataclass
class Offer:
    agent_id: str
    values: Dict[str, float]
    utility: float
    round_num: int
    timestamp: float = 0.0


@dataclass
class NegotiationAgent:
    agent_id: str
    strategy: ConcessionStrategy
    reservation_utility: float = 0.3
    issues: Dict[str, Tuple[float, float]] = field(default_factory=dict)  # preferred range
    weights: Dict[str, float] = field(default_factory=dict)
    offers_made: List[Offer] = field(default_factory=list)
    offers_received: List[Offer] = field(default_factory=list)


class AutonomousNegotiation:
    """Multi-party negotiation engine for drone swarm resource allocation."""

    def __init__(self, seed: int = 42, max_rounds: int = 100, deadline: float = 1.0):
        self.rng = np.random.default_rng(seed)
        self.agents: Dict[str, NegotiationAgent] = {}
        self.issues: List[NegotiationIssue] = []
        self.max_rounds = max_rounds
        self.deadline = deadline
        self.current_round = 0
        self.agreements: List[Dict] = []
        self.history: List[Offer] = []

    def add_issue(self, name: str, min_val: float, max_val: float, weight: float = 1.0) -> None:
        self.issues.append(NegotiationIssue(name, min_val, max_val, weight))

    def add_agent(self, agent_id: str, strategy: ConcessionStrategy,
                  preferences: Optional[Dict[str, Tuple[float, float]]] = None,
                  reservation: float = 0.3) -> NegotiationAgent:
        prefs = preferences or {}
        weights = {issue.name: issue.weight + self.rng.standard_normal() * 0.1
                   for issue in self.issues}
        agent = NegotiationAgent(agent_id, strategy, reservation, prefs, weights)
        self.agents[agent_id] = agent
        return agent

    def _compute_utility(self, agent: NegotiationAgent, values: Dict[str, float]) -> float:
        utility = 0.0
        total_weight = sum(agent.weights.values()) or 1.0
        for issue in self.issues:
            v = values.get(issue.name, issue.min_value)
            normalized = (v - issue.min_value) / max(issue.max_value - issue.min_value, 1e-10)
            pref = agent.issues.get(issue.name)
            if pref:
                dist = abs(v - (pref[0] + pref[1]) / 2) / max(issue.max_value - issue.min_value, 1e-10)
                normalized = max(0, 1 - dist)
            utility += agent.weights.get(issue.name, 1.0) * normalized
        return utility / total_weight

    def _concession_factor(self, strategy: ConcessionStrategy, t: float) -> float:
        t = min(t, 1.0)
        if strategy == ConcessionStrategy.LINEAR:
            return t
        elif strategy == ConcessionStrategy.BOULWARE:
            return t ** 3
        elif strategy == ConcessionStrategy.CONCEDER:
            return 1 - (1 - t) ** 3
        elif strategy == ConcessionStrategy.TOUGHGUY:
            return t ** 5
        else:
            return self.rng.random() * t

    def _generate_offer(self, agent: NegotiationAgent) -> Offer:
        t = self.current_round / self.max_rounds
        cf = self._concession_factor(agent.strategy, t)

        values = {}
        for issue in self.issues:
            pref = agent.issues.get(issue.name)
            if pref:
                ideal = (pref[0] + pref[1]) / 2
            else:
                ideal = (issue.max_value + issue.min_value) / 2
            midpoint = (issue.max_value + issue.min_value) / 2
            value = ideal + cf * (midpoint - ideal)
            value += self.rng.standard_normal() * (issue.max_value - issue.min_value) * 0.02
            value = np.clip(value, issue.min_value, issue.max_value)
            values[issue.name] = float(value)

        utility = self._compute_utility(agent, values)
        return Offer(agent.agent_id, values, utility, self.current_round)

    def _evaluate_offer(self, agent: NegotiationAgent, offer: Offer) -> bool:
        utility = self._compute_utility(agent, offer.values)
        t = self.current_round / self.max_rounds
        threshold = agent.reservation_utility + (1 - agent.reservation_utility) * (1 - t)
        return utility >= threshold

    def negotiate_round(self) -> Optional[Dict]:
        self.current_round += 1
        agent_ids = list(self.agents.keys())
        offers = {}

        for aid in agent_ids:
            offer = self._generate_offer(self.agents[aid])
            offers[aid] = offer
            self.agents[aid].offers_made.append(offer)
            self.history.append(offer)

        for i, a_id in enumerate(agent_ids):
            for j, b_id in enumerate(agent_ids):
                if i >= j:
                    continue
                offer_a = offers[a_id]
                offer_b = offers[b_id]

                a_accepts = self._evaluate_offer(self.agents[a_id], offer_b)
                b_accepts = self._evaluate_offer(self.agents[b_id], offer_a)

                if a_accepts and b_accepts:
                    merged = {}
                    for issue in self.issues:
                        merged[issue.name] = (offer_a.values[issue.name] + offer_b.values[issue.name]) / 2
                    agreement = {
                        "parties": [a_id, b_id],
                        "values": merged,
                        "round": self.current_round,
                        "utility_a": self._compute_utility(self.agents[a_id], merged),
                        "utility_b": self._compute_utility(self.agents[b_id], merged),
                    }
                    self.agreements.append(agreement)
                    return agreement
        return None

    def run(self) -> Optional[Dict]:
        for _ in range(self.max_rounds):
            result = self.negotiate_round()
            if result:
                return result
        return None

    def summary(self) -> Dict:
        return {
            "agents": len(self.agents),
            "issues": len(self.issues),
            "rounds": self.current_round,
            "agreements": len(self.agreements),
            "total_offers": len(self.history),
        }
