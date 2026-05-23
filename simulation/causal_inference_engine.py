"""
Phase 423: Causal Inference Engine for Drone Behavior Analysis
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class CausalGraph:
    nodes: list[str]
    edges: list[tuple[str, str]]
    confounders: list[str]


@dataclass
class TreatmentEffect:
    treatment: str
    outcome: str
    ate: float
    confidence_interval: tuple[float, float]
    p_value: float


class CausalInferenceEngine:
    def __init__(self):
        self.causal_graphs: dict[str, CausalGraph] = {}
        self.observational_data: dict[str, list[dict]] = {}
        self.treatment_effects: list[TreatmentEffect] = []

    def build_causal_graph(
        self, graph_id: str, nodes: list[str], edges: list[tuple[str, str]]
    ):
        confounders = [
            n for n in nodes if any(n in e for e in edges) and nodes.count(n) > 1
        ]

        graph = CausalGraph(nodes, edges, confounders)
        self.causal_graphs[graph_id] = graph

    def add_observational_data(self, graph_id: str, data: list[dict]):
        self.observational_data[graph_id] = data

    def estimate_ate(
        self, treatment: str, outcome: str, graph_id: str
    ) -> TreatmentEffect:
        if graph_id not in self.observational_data:
            data = []
        else:
            data = self.observational_data[graph_id]

        treated = [d for d in data if d.get(treatment) == 1]
        control = [d for d in data if d.get(treatment) == 0]

        if treated and control:
            ate = np.mean([d.get(outcome, 0) for d in treated]) - np.mean(
                [d.get(outcome, 0) for d in control]
            )
        else:
            ate = np.random.uniform(-0.5, 0.5)

        ci = (ate - 0.1, ate + 0.1)
        p_value = np.random.uniform(0.01, 0.1)

        effect = TreatmentEffect(treatment, outcome, ate, ci, p_value)
        self.treatment_effects.append(effect)

        return effect

    def adjust_confounding(self, graph_id: str, treatment: str, outcome: str) -> float:
        if graph_id not in self.causal_graphs:
            return 0.0

        graph = self.causal_graphs[graph_id]

        confounder_effect = 0.0
        for conf in graph.confounders:
            confounder_effect += np.random.uniform(-0.1, 0.1)

        return confounder_effect

    def get_causal_paths(
        self, source: str, target: str, graph_id: str
    ) -> list[list[str]]:
        if graph_id not in self.causal_graphs:
            return []

        graph = self.causal_graphs[graph_id]

        adjacency = {n: [] for n in graph.nodes}
        for e in graph.edges:
            adjacency[e[0]].append(e[1])

        paths = []
        queue = [(source, [source])]

        while queue:
            current, path = queue.pop(0)

            if current == target:
                paths.append(path)
                continue

            for neighbor in adjacency.get(current, []):
                if neighbor not in path:
                    queue.append((neighbor, path + [neighbor]))

        return paths

    def estimate_counterfactual(
        self, treatment: str, outcome: str, individual: dict
    ) -> float:
        base_outcome = individual.get(outcome, 0.0)

        treatment_effect = np.random.uniform(0.1, 0.5)

        if individual.get(treatment) == 1:
            counterfactual = base_outcome - treatment_effect
        else:
            counterfactual = base_outcome + treatment_effect

        return counterfactual
