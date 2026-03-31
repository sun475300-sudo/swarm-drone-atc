"""
Phase 520: Swarm Diplomacy
다중 군집 간 협상, 자원 공유, 영공 분쟁 해결.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple


class DiplomacyAction(Enum):
    COOPERATE = "cooperate"
    DEFECT = "defect"
    NEGOTIATE = "negotiate"
    YIELD = "yield"
    ENFORCE = "enforce"


class TreatyType(Enum):
    AIRSPACE_SHARING = "airspace_sharing"
    RESOURCE_EXCHANGE = "resource_exchange"
    NON_AGGRESSION = "non_aggression"
    MUTUAL_AID = "mutual_aid"
    CORRIDOR_ACCESS = "corridor_access"


class SwarmRelation(Enum):
    ALLIED = "allied"
    NEUTRAL = "neutral"
    RIVAL = "rival"
    HOSTILE = "hostile"


@dataclass
class SwarmFaction:
    faction_id: str
    name: str
    n_drones: int
    territory: np.ndarray  # center position
    resources: float
    reputation: float = 0.5
    power: float = 0.5


@dataclass
class Treaty:
    treaty_id: str
    treaty_type: TreatyType
    parties: List[str]
    terms: Dict
    active: bool = True
    duration_s: float = 3600
    violations: int = 0


@dataclass
class DiplomaticEvent:
    event_id: str
    factions: List[str]
    action: DiplomacyAction
    outcome: str
    payoff: Dict[str, float]
    timestamp: float


class NashBargaining:
    """Nash bargaining solution for resource allocation."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)

    def solve(self, utilities_a: np.ndarray, utilities_b: np.ndarray,
              disagreement: Tuple[float, float] = (0, 0)) -> Tuple[int, float, float]:
        da, db = disagreement
        products = (utilities_a - da) * (utilities_b - db)
        products[products < 0] = 0
        best_idx = int(np.argmax(products))
        return best_idx, float(utilities_a[best_idx]), float(utilities_b[best_idx])


class ReputationSystem:
    """Track and update faction reputations."""

    def __init__(self):
        self.history: Dict[str, List[float]] = {}

    def update(self, faction_id: str, delta: float):
        if faction_id not in self.history:
            self.history[faction_id] = [0.5]
        current = self.history[faction_id][-1]
        new_rep = np.clip(current + delta, 0, 1)
        self.history[faction_id].append(round(float(new_rep), 4))

    def get(self, faction_id: str) -> float:
        if faction_id not in self.history:
            return 0.5
        return self.history[faction_id][-1]


class SwarmDiplomacy:
    """Multi-swarm diplomacy and negotiation system."""

    def __init__(self, n_factions: int = 5, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_factions = n_factions
        self.bargaining = NashBargaining(seed)
        self.reputation = ReputationSystem()
        self.factions: Dict[str, SwarmFaction] = {}
        self.treaties: List[Treaty] = []
        self.events: List[DiplomaticEvent] = []
        self.relations: Dict[Tuple[str, str], SwarmRelation] = {}
        self._event_counter = 0
        self._treaty_counter = 0

        names = ["Alpha", "Bravo", "Charlie", "Delta", "Echo",
                 "Foxtrot", "Golf", "Hotel", "India", "Juliet"]
        for i in range(n_factions):
            fid = f"faction_{i}"
            territory = self.rng.uniform(-1000, 1000, 3)
            territory[2] = 0
            self.factions[fid] = SwarmFaction(
                fid, names[i % len(names)],
                self.rng.integers(5, 50), territory,
                self.rng.uniform(50, 200),
                self.rng.uniform(0.3, 0.8),
                self.rng.uniform(0.2, 0.9))
            self.reputation.update(fid, 0)

        fids = list(self.factions.keys())
        for i in range(len(fids)):
            for j in range(i + 1, len(fids)):
                rel = self.rng.choice([SwarmRelation.NEUTRAL, SwarmRelation.ALLIED, SwarmRelation.RIVAL])
                self.relations[(fids[i], fids[j])] = rel

    def negotiate(self, faction_a: str, faction_b: str,
                  treaty_type: TreatyType = TreatyType.AIRSPACE_SHARING) -> DiplomaticEvent:
        self._event_counter += 1
        fa = self.factions.get(faction_a)
        fb = self.factions.get(faction_b)
        if not fa or not fb:
            return DiplomaticEvent(f"EVT-{self._event_counter:05d}",
                                  [faction_a, faction_b], DiplomacyAction.DEFECT,
                                  "invalid factions", {}, 0)

        n_options = 10
        ua = self.rng.uniform(0, fa.resources / 100, n_options)
        ub = self.rng.uniform(0, fb.resources / 100, n_options)
        idx, pay_a, pay_b = self.bargaining.solve(ua, ub)

        rep_a = self.reputation.get(faction_a)
        rep_b = self.reputation.get(faction_b)
        cooperate_prob = (rep_a + rep_b) / 2

        if self.rng.random() < cooperate_prob:
            action = DiplomacyAction.COOPERATE
            self._treaty_counter += 1
            treaty = Treaty(f"TRT-{self._treaty_counter:04d}", treaty_type,
                          [faction_a, faction_b],
                          {"share_a": round(pay_a, 3), "share_b": round(pay_b, 3)})
            self.treaties.append(treaty)
            self.reputation.update(faction_a, 0.05)
            self.reputation.update(faction_b, 0.05)
            outcome = f"Treaty {treaty.treaty_id} signed"
        else:
            action = DiplomacyAction.DEFECT
            self.reputation.update(faction_a, -0.03)
            self.reputation.update(faction_b, -0.03)
            outcome = "Negotiation failed"

        event = DiplomaticEvent(
            f"EVT-{self._event_counter:05d}", [faction_a, faction_b],
            action, outcome, {faction_a: round(pay_a, 3), faction_b: round(pay_b, 3)},
            float(self._event_counter))
        self.events.append(event)
        return event

    def resolve_dispute(self, faction_a: str, faction_b: str) -> Dict:
        fa = self.factions.get(faction_a)
        fb = self.factions.get(faction_b)
        if not fa or not fb:
            return {"resolved": False}

        power_ratio = fa.power / (fa.power + fb.power + 1e-8)
        if abs(power_ratio - 0.5) < 0.1:
            return {"resolved": True, "method": "negotiation",
                    "result": self.negotiate(faction_a, faction_b).outcome}
        elif power_ratio > 0.6:
            self.reputation.update(faction_a, -0.1)
            return {"resolved": True, "method": "enforcement",
                    "winner": faction_a}
        else:
            self.reputation.update(faction_b, -0.1)
            return {"resolved": True, "method": "enforcement",
                    "winner": faction_b}

    def run_round(self) -> Dict:
        fids = list(self.factions.keys())
        negotiations = 0
        for _ in range(min(3, len(fids))):
            a, b = self.rng.choice(fids, 2, replace=False)
            self.negotiate(a, b, self.rng.choice(list(TreatyType)))
            negotiations += 1
        return {
            "negotiations": negotiations,
            "active_treaties": sum(1 for t in self.treaties if t.active),
            "events": len(self.events),
        }

    def summary(self) -> Dict:
        return {
            "factions": len(self.factions),
            "treaties": len(self.treaties),
            "events": len(self.events),
            "avg_reputation": round(
                np.mean([self.reputation.get(f) for f in self.factions]), 4),
        }
