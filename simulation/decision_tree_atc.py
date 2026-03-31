"""
의사결정 트리 관제
=================
IF-THEN 규칙 기반 빠른 관제 결정 + 규칙 학습.

사용법:
    dt = DecisionTreeATC()
    dt.add_rule("collision_imminent", lambda ctx: ctx["cpa_dist"] < 20, action="EVADE")
    decision = dt.decide({"cpa_dist": 15, "battery": 80})
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Rule:
    """규칙"""
    name: str
    condition: Callable[[dict[str, Any]], bool]
    action: str
    priority: int = 5  # 1(low) ~ 10(high)
    hit_count: int = 0
    miss_count: int = 0


@dataclass
class Decision:
    """결정 결과"""
    rule_name: str
    action: str
    priority: int
    context_snapshot: dict[str, Any]


class DecisionTreeATC:
    """규칙 기반 관제."""

    def __init__(self) -> None:
        self._rules: list[Rule] = []
        self._decisions: list[Decision] = []
        self._default_action = "MONITOR"

    def add_rule(
        self, name: str, condition: Callable[[dict[str, Any]], bool],
        action: str = "MONITOR", priority: int = 5,
    ) -> None:
        self._rules.append(Rule(
            name=name, condition=condition,
            action=action, priority=priority,
        ))
        self._rules.sort(key=lambda r: -r.priority)

    def remove_rule(self, name: str) -> bool:
        before = len(self._rules)
        self._rules = [r for r in self._rules if r.name != name]
        return len(self._rules) < before

    def decide(self, context: dict[str, Any]) -> Decision:
        """우선순위 순서로 규칙 평가"""
        for rule in self._rules:
            try:
                if rule.condition(context):
                    rule.hit_count += 1
                    decision = Decision(
                        rule_name=rule.name,
                        action=rule.action,
                        priority=rule.priority,
                        context_snapshot=dict(context),
                    )
                    self._decisions.append(decision)
                    return decision
                else:
                    rule.miss_count += 1
            except (KeyError, ValueError, TypeError):
                rule.miss_count += 1

        decision = Decision(
            rule_name="default", action=self._default_action,
            priority=0, context_snapshot=dict(context),
        )
        self._decisions.append(decision)
        return decision

    def batch_decide(self, contexts: list[dict[str, Any]]) -> list[Decision]:
        return [self.decide(ctx) for ctx in contexts]

    def rule_stats(self) -> list[dict[str, Any]]:
        return [
            {
                "name": r.name, "action": r.action, "priority": r.priority,
                "hits": r.hit_count, "misses": r.miss_count,
                "hit_rate": round(r.hit_count / max(r.hit_count + r.miss_count, 1) * 100, 1),
            }
            for r in self._rules
        ]

    def most_used_rules(self, n: int = 5) -> list[str]:
        sorted_rules = sorted(self._rules, key=lambda r: -r.hit_count)
        return [r.name for r in sorted_rules[:n]]

    def recent_decisions(self, n: int = 20) -> list[Decision]:
        return self._decisions[-n:]

    def summary(self) -> dict[str, Any]:
        return {
            "rules": len(self._rules),
            "decisions": len(self._decisions),
            "actions_used": len(set(d.action for d in self._decisions)),
        }
