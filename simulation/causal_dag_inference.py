# Phase 564: Causal DAG Inference — Do-Calculus Engine
"""
인과 추론 엔진: DAG 기반 인과 모델,
do-calculus 개입 효과 추정, 반사실 분석.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class CausalNode:
    name: str
    parents: list[str] = field(default_factory=list)
    mechanism: str = "linear"  # linear, threshold, noise
    coefficient: float = 1.0
    noise_std: float = 0.1


class CausalDAG:
    """인과 방향 비순환 그래프."""

    def __init__(self, seed=42):
        self.rng = np.random.default_rng(seed)
        self.nodes: dict[str, CausalNode] = {}
        self.adjacency: dict[str, list[str]] = {}

    def add_node(self, node: CausalNode):
        self.nodes[node.name] = node
        if node.name not in self.adjacency:
            self.adjacency[node.name] = []
        for p in node.parents:
            if p not in self.adjacency:
                self.adjacency[p] = []
            self.adjacency[p].append(node.name)

    def topological_sort(self) -> list[str]:
        in_degree = {n: 0 for n in self.nodes}
        for n, node in self.nodes.items():
            for p in node.parents:
                in_degree[n] = in_degree.get(n, 0) + 1

        queue = [n for n, d in in_degree.items() if d == 0]
        order = []
        while queue:
            n = queue.pop(0)
            order.append(n)
            for child in self.adjacency.get(n, []):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)
        return order

    def sample(self, n_samples=100, interventions: dict = None) -> dict[str, np.ndarray]:
        interventions = interventions or {}
        order = self.topological_sort()
        data = {}

        for name in order:
            node = self.nodes[name]
            if name in interventions:
                data[name] = np.full(n_samples, interventions[name])
                continue

            noise = self.rng.normal(0, node.noise_std, n_samples)
            if not node.parents:
                data[name] = self.rng.normal(0, 1, n_samples) + noise
            else:
                val = np.zeros(n_samples)
                for p in node.parents:
                    val += node.coefficient * data[p]
                if node.mechanism == "threshold":
                    val = (val > 0).astype(float)
                data[name] = val + noise

        return data

    def do_effect(self, treatment: str, outcome: str, value=1.0, n=1000) -> float:
        """do(X=value)의 Y에 대한 평균 인과 효과."""
        data_do = self.sample(n, {treatment: value})
        data_base = self.sample(n, {treatment: 0.0})
        ate = float(np.mean(data_do[outcome]) - np.mean(data_base[outcome]))
        return ate


@dataclass
class InferenceResult:
    treatment: str
    outcome: str
    ate: float
    ci_lower: float
    ci_upper: float


class CausalDAGInference:
    """인과 DAG 추론 시뮬레이션."""

    def __init__(self, seed=42):
        self.rng = np.random.default_rng(seed)
        self.dag = CausalDAG(seed)
        self.results: list[InferenceResult] = []
        self._build_drone_dag()

    def _build_drone_dag(self):
        nodes = [
            CausalNode("wind", [], "linear", 1.0, 0.5),
            CausalNode("battery", [], "linear", 1.0, 0.3),
            CausalNode("altitude", ["wind", "battery"], "linear", 0.8, 0.2),
            CausalNode("speed", ["wind", "altitude"], "linear", 0.6, 0.15),
            CausalNode("conflict_risk", ["speed", "altitude"], "linear", 0.7, 0.1),
            CausalNode("resolution_time", ["conflict_risk", "wind"], "linear", 0.5, 0.2),
            CausalNode("mission_success", ["conflict_risk", "battery", "resolution_time"], "threshold", 0.3, 0.1),
        ]
        for n in nodes:
            self.dag.add_node(n)

    def estimate_effects(self):
        pairs = [
            ("wind", "conflict_risk"),
            ("battery", "mission_success"),
            ("altitude", "speed"),
            ("speed", "conflict_risk"),
            ("conflict_risk", "resolution_time"),
        ]
        for treatment, outcome in pairs:
            ate = self.dag.do_effect(treatment, outcome, 1.0, 2000)
            # 부트스트랩 CI
            ates = []
            for _ in range(50):
                a = self.dag.do_effect(treatment, outcome, 1.0, 500)
                ates.append(a)
            ci_lo = float(np.percentile(ates, 5))
            ci_hi = float(np.percentile(ates, 95))
            self.results.append(InferenceResult(treatment, outcome, round(ate, 4), round(ci_lo, 4), round(ci_hi, 4)))

    def run(self):
        self.estimate_effects()

    def summary(self):
        return {
            "dag_nodes": len(self.dag.nodes),
            "dag_edges": sum(len(n.parents) for n in self.dag.nodes.values()),
            "effects_estimated": len(self.results),
            "significant": sum(1 for r in self.results if abs(r.ate) > 0.1),
            "avg_ate": round(float(np.mean([abs(r.ate) for r in self.results])) if self.results else 0, 4),
        }


if __name__ == "__main__":
    cdi = CausalDAGInference(42)
    cdi.run()
    for k, v in cdi.summary().items():
        print(f"  {k}: {v}")
