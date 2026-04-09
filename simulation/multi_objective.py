"""
다중 목표 최적화
================
파레토 프론트 + 에너지/시간/안전 트레이드오프.

사용법:
    moo = MultiObjectiveOptimizer()
    moo.add_solution("path_A", energy=80, time=120, safety=0.95)
    pareto = moo.pareto_front()
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class Solution:
    """후보 솔루션"""
    solution_id: str
    objectives: dict[str, float]  # name → value (lower is better)
    metadata: dict[str, Any] = field(default_factory=dict)


class MultiObjectiveOptimizer:
    """다중 목표 최적화."""

    def __init__(self, objective_names: list[str] | None = None) -> None:
        self._objectives = objective_names or ["energy", "time", "risk"]
        self._solutions: list[Solution] = []

    def add_solution(
        self,
        solution_id: str,
        metadata: dict[str, Any] | None = None,
        **objectives: float,
    ) -> Solution:
        sol = Solution(
            solution_id=solution_id,
            objectives=objectives,
            metadata=metadata or {},
        )
        self._solutions.append(sol)
        return sol

    def dominates(self, a: Solution, b: Solution) -> bool:
        """a가 b를 지배하는가 (모든 목표에서 같거나 낫고, 하나 이상에서 나음)"""
        keys = set(a.objectives) & set(b.objectives)
        if not keys:
            return False
        at_least_one_better = False
        for k in keys:
            if a.objectives[k] > b.objectives[k]:
                return False
            if a.objectives[k] < b.objectives[k]:
                at_least_one_better = True
        return at_least_one_better

    def pareto_front(self) -> list[Solution]:
        """비지배 솔루션 집합"""
        front = []
        for sol in self._solutions:
            dominated = False
            for other in self._solutions:
                if other.solution_id != sol.solution_id and self.dominates(other, sol):
                    dominated = True
                    break
            if not dominated:
                front.append(sol)
        return front

    def weighted_score(
        self, solution: Solution, weights: dict[str, float] | None = None,
    ) -> float:
        """가중 합산 점수 (lower is better)"""
        w = weights or {k: 1.0 for k in self._objectives}
        score = 0.0
        for k, v in solution.objectives.items():
            score += v * w.get(k, 1.0)
        return score

    def best_compromise(
        self, weights: dict[str, float] | None = None,
    ) -> Solution | None:
        """가중치 기반 최적 절충안"""
        front = self.pareto_front()
        if not front:
            return None
        return min(front, key=lambda s: self.weighted_score(s, weights))

    def normalize(self) -> list[dict[str, float]]:
        """목표값 0-1 정규화"""
        if not self._solutions:
            return []

        keys = list(self._solutions[0].objectives.keys())
        mins = {k: min(s.objectives.get(k, 0) for s in self._solutions) for k in keys}
        maxs = {k: max(s.objectives.get(k, 0) for s in self._solutions) for k in keys}

        result = []
        for sol in self._solutions:
            norm = {}
            for k in keys:
                rng = maxs[k] - mins[k]
                norm[k] = (sol.objectives.get(k, 0) - mins[k]) / rng if rng > 0 else 0
            result.append(norm)
        return result

    def hypervolume_indicator(self, ref_point: dict[str, float] | None = None) -> float:
        """2D 하이퍼볼륨 근사 (2개 목표)"""
        front = self.pareto_front()
        if not front or len(list(front[0].objectives)) < 2:
            return 0.0

        keys = list(front[0].objectives.keys())[:2]
        ref = ref_point or {k: max(s.objectives.get(k, 0) for s in self._solutions) * 1.1 for k in keys}

        points = sorted(front, key=lambda s: s.objectives.get(keys[0], 0))
        area = 0.0
        prev_y = ref[keys[1]]
        for p in points:
            x = ref[keys[0]] - p.objectives.get(keys[0], 0)
            y = prev_y - p.objectives.get(keys[1], 0)
            if x > 0 and y > 0:
                area += x * y
            prev_y = p.objectives.get(keys[1], 0)
        return area

    def summary(self) -> dict[str, Any]:
        front = self.pareto_front()
        return {
            "total_solutions": len(self._solutions),
            "pareto_size": len(front),
            "objectives": self._objectives,
        }
