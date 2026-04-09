"""
다중 에이전트 협상
=================
경로 충돌 시 에이전트 간 양보/교환 프로토콜.

사용법:
    neg = AgentNegotiation()
    neg.register_agent("d1", priority=5, flexibility=0.8)
    result = neg.negotiate("d1", "d2", conflict_point=(100, 200, 50))
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentProfile:
    """에이전트 협상 프로필"""
    agent_id: str
    priority: int = 5  # 1(low) ~ 10(high)
    flexibility: float = 0.5  # 0(rigid) ~ 1(flexible)
    concessions_made: int = 0
    concessions_received: int = 0


@dataclass
class NegotiationResult:
    """협상 결과"""
    agent_a: str
    agent_b: str
    yielder: str  # who yields
    action: str  # YIELD_ALTITUDE, YIELD_TIME, YIELD_PATH, DEADLOCK
    cost_a: float = 0.0
    cost_b: float = 0.0
    rounds: int = 1


class AgentNegotiation:
    """에이전트 간 협상."""

    def __init__(self, max_rounds: int = 5) -> None:
        self._agents: dict[str, AgentProfile] = {}
        self._history: list[NegotiationResult] = []
        self.max_rounds = max_rounds

    def register_agent(
        self, agent_id: str, priority: int = 5, flexibility: float = 0.5,
    ) -> None:
        self._agents[agent_id] = AgentProfile(
            agent_id=agent_id, priority=priority, flexibility=flexibility,
        )

    def _willingness(self, agent: AgentProfile) -> float:
        """양보 의지 점수 (높을수록 양보 가능)"""
        base = agent.flexibility * (10 - agent.priority) / 10
        fatigue = min(0.3, agent.concessions_made * 0.05)
        return max(0, base - fatigue)

    def negotiate(
        self, agent_a: str, agent_b: str,
        conflict_point: tuple[float, ...] | None = None,
    ) -> NegotiationResult:
        pa = self._agents.get(agent_a)
        pb = self._agents.get(agent_b)

        if not pa or not pb:
            return NegotiationResult(agent_a, agent_b, "", "DEADLOCK")

        for rnd in range(1, self.max_rounds + 1):
            wa = self._willingness(pa)
            wb = self._willingness(pb)

            if wa > wb:
                yielder = agent_a
                pa.concessions_made += 1
                pb.concessions_received += 1
            elif wb > wa:
                yielder = agent_b
                pb.concessions_made += 1
                pa.concessions_received += 1
            else:
                # 우선순위로 결정
                if pa.priority < pb.priority:
                    yielder = agent_a
                    pa.concessions_made += 1
                elif pb.priority < pa.priority:
                    yielder = agent_b
                    pb.concessions_made += 1
                else:
                    continue  # 다음 라운드

            # 양보 행동 결정
            if conflict_point and len(conflict_point) >= 3:
                action = "YIELD_ALTITUDE" if conflict_point[2] > 60 else "YIELD_PATH"
            else:
                action = "YIELD_TIME"

            result = NegotiationResult(
                agent_a=agent_a, agent_b=agent_b,
                yielder=yielder, action=action, rounds=rnd,
            )
            self._history.append(result)
            return result

        result = NegotiationResult(agent_a, agent_b, "", "DEADLOCK", rounds=self.max_rounds)
        self._history.append(result)
        return result

    def deadlock_count(self) -> int:
        return sum(1 for r in self._history if r.action == "DEADLOCK")

    def agent_stats(self, agent_id: str) -> dict[str, Any]:
        a = self._agents.get(agent_id)
        if not a:
            return {}
        return {
            "priority": a.priority,
            "flexibility": a.flexibility,
            "concessions_made": a.concessions_made,
            "concessions_received": a.concessions_received,
        }

    def summary(self) -> dict[str, Any]:
        return {
            "agents": len(self._agents),
            "negotiations": len(self._history),
            "deadlocks": self.deadlock_count(),
            "success_rate": round(
                (1 - self.deadlock_count() / max(len(self._history), 1)) * 100, 1
            ),
        }
