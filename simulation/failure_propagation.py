"""
장애 전파 분석
==============
고장 파급 그래프 + 영향 범위 + 격리 전략.

사용법:
    fp = FailurePropagation()
    fp.add_dependency("d1", "d2")  # d1 → d2 의존
    affected = fp.propagate("d1")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PropagationResult:
    """전파 분석 결과"""
    origin: str
    affected_nodes: list[str]
    depth: int
    isolation_candidates: list[str]
    impact_score: float  # 0~1


class FailurePropagation:
    """고장 파급 그래프 분석."""

    def __init__(self) -> None:
        self._deps: dict[str, set[str]] = {}  # node → set of nodes that depend on it
        self._nodes: set[str] = set()
        self._failures: list[dict[str, Any]] = []

    def add_node(self, node_id: str) -> None:
        self._nodes.add(node_id)

    def add_dependency(self, source: str, target: str) -> None:
        """target이 source에 의존 (source 고장 → target 영향)"""
        self._nodes.add(source)
        self._nodes.add(target)
        if source not in self._deps:
            self._deps[source] = set()
        self._deps[source].add(target)

    def propagate(self, failed_node: str) -> PropagationResult:
        """고장 전파 시뮬레이션"""
        affected: list[str] = []
        visited: set[str] = set()
        queue = [(failed_node, 0)]
        max_depth = 0

        while queue:
            node, depth = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            if node != failed_node:
                affected.append(node)
            max_depth = max(max_depth, depth)

            for dependent in self._deps.get(node, set()):
                if dependent not in visited:
                    queue.append((dependent, depth + 1))

        # 격리 후보: 첫 번째 레벨의 의존 노드
        isolation = list(self._deps.get(failed_node, set()))

        impact = len(affected) / max(len(self._nodes) - 1, 1)

        result = PropagationResult(
            origin=failed_node,
            affected_nodes=affected,
            depth=max_depth,
            isolation_candidates=isolation,
            impact_score=min(1.0, impact),
        )

        self._failures.append({
            "origin": failed_node,
            "affected_count": len(affected),
            "depth": max_depth,
        })

        return result

    def reverse_dependencies(self, node_id: str) -> list[str]:
        """이 노드가 의존하는 노드들"""
        deps = []
        for src, targets in self._deps.items():
            if node_id in targets:
                deps.append(src)
        return deps

    def single_points_of_failure(self) -> list[str]:
        """단일 장애점 (영향 범위 > 50%)"""
        spofs = []
        threshold = len(self._nodes) * 0.3
        for node in self._nodes:
            result = self.propagate(node)
            if len(result.affected_nodes) > threshold:
                spofs.append(node)
        self._failures.clear()  # 분석용이므로 이력 정리
        return spofs

    def resilience_score(self) -> float:
        """네트워크 복원력 점수 (0~1, 높을수록 강건)"""
        if not self._nodes:
            return 1.0
        total_impact = 0.0
        for node in self._nodes:
            result = self.propagate(node)
            total_impact += result.impact_score
        self._failures.clear()
        avg_impact = total_impact / len(self._nodes)
        return max(0, 1.0 - avg_impact)

    def summary(self) -> dict[str, Any]:
        total_edges = sum(len(v) for v in self._deps.values())
        return {
            "nodes": len(self._nodes),
            "edges": total_edges,
            "failures_analyzed": len(self._failures),
            "spofs": len(self.single_points_of_failure()),
        }
