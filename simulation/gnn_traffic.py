"""
그래프 신경망 교통 예측
=====================
드론 간 관계 그래프 기반 교통 밀도/충돌 예측.

사용법:
    gnn = GNNTraffic(seed=42)
    gnn.update_graph(drones={"d1": (100,200,50), "d2": (150,210,55)})
    pred = gnn.predict_density(horizon=30)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import numpy as np


@dataclass
class GraphNode:
    drone_id: str
    position: tuple[float, float, float]
    velocity: tuple[float, float, float] = (0, 0, 0)
    features: list[float] = field(default_factory=list)


class GNNTraffic:
    def __init__(self, proximity_threshold: float = 100.0,
                 hidden_dim: int = 16, seed: int = 42) -> None:
        self._rng = np.random.default_rng(seed)
        self._threshold = proximity_threshold
        self._hidden_dim = hidden_dim
        self._nodes: dict[str, GraphNode] = {}
        self._adjacency: dict[str, list[str]] = {}
        self._predictions: int = 0

        # 간이 GNN 가중치 (message passing)
        self._w_msg = self._rng.normal(0, 0.1, (6, hidden_dim))
        self._w_update = self._rng.normal(0, 0.1, (hidden_dim * 2, hidden_dim))
        self._w_out = self._rng.normal(0, 0.1, (hidden_dim, 3))  # density, risk, congestion

    def update_graph(self, drones: dict[str, tuple[float, float, float]],
                     velocities: dict[str, tuple[float, float, float]] | None = None) -> None:
        velocities = velocities or {}
        self._nodes.clear()
        self._adjacency.clear()

        for did, pos in drones.items():
            vel = velocities.get(did, (0, 0, 0))
            features = list(pos) + list(vel)
            self._nodes[did] = GraphNode(drone_id=did, position=pos,
                                          velocity=vel, features=features)
            self._adjacency[did] = []

        # 인접 행렬 구축 (근접 기반)
        ids = list(self._nodes.keys())
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                d = np.sqrt(sum((a - b) ** 2 for a, b in
                    zip(self._nodes[ids[i]].position, self._nodes[ids[j]].position)))
                if d < self._threshold:
                    self._adjacency[ids[i]].append(ids[j])
                    self._adjacency[ids[j]].append(ids[i])

    def _message_pass(self) -> dict[str, np.ndarray]:
        """1-hop 메시지 패싱"""
        embeddings: dict[str, np.ndarray] = {}

        for did, node in self._nodes.items():
            x = np.array(node.features[:6])
            h_self = np.maximum(0, x @ self._w_msg)  # ReLU

            # 이웃 메시지 집계 (평균)
            neighbors = self._adjacency.get(did, [])
            if neighbors:
                msgs = []
                for nid in neighbors:
                    nx = np.array(self._nodes[nid].features[:6])
                    msgs.append(np.maximum(0, nx @ self._w_msg))
                h_neigh = np.mean(msgs, axis=0)
            else:
                h_neigh = np.zeros(self._hidden_dim)

            # 결합 + 업데이트
            combined = np.concatenate([h_self, h_neigh])
            h_new = np.maximum(0, combined @ self._w_update)
            embeddings[did] = h_new

        return embeddings

    def predict_density(self, horizon: float = 30.0) -> dict[str, Any]:
        """교통 밀도/위험도/혼잡도 예측"""
        if not self._nodes:
            return {"density": 0, "risk": 0, "congestion": 0}

        embeddings = self._message_pass()
        self._predictions += 1

        # 글로벌 readout (평균 풀링)
        all_h = np.array(list(embeddings.values()))
        global_h = np.mean(all_h, axis=0)
        output = global_h @ self._w_out
        output = 1 / (1 + np.exp(-output))  # sigmoid

        # 노드별 위험도
        node_risks = {}
        for did, h in embeddings.items():
            node_out = h @ self._w_out
            node_out = 1 / (1 + np.exp(-node_out))
            node_risks[did] = round(float(node_out[1]), 3)

        return {
            "density": round(float(output[0]), 3),
            "risk": round(float(output[1]), 3),
            "congestion": round(float(output[2]), 3),
            "node_risks": node_risks,
            "horizon_sec": horizon,
            "n_edges": sum(len(v) for v in self._adjacency.values()) // 2,
        }

    def hotspots(self, top_k: int = 5) -> list[dict]:
        """고위험 핫스팟 탐지"""
        pred = self.predict_density()
        node_risks = pred.get("node_risks", {})
        sorted_risks = sorted(node_risks.items(), key=lambda x: -x[1])
        return [{"drone_id": did, "risk": r, "position": self._nodes[did].position}
                for did, r in sorted_risks[:top_k] if did in self._nodes]

    def edge_count(self) -> int:
        return sum(len(v) for v in self._adjacency.values()) // 2

    def summary(self) -> dict[str, Any]:
        return {
            "nodes": len(self._nodes),
            "edges": self.edge_count(),
            "predictions": self._predictions,
            "threshold": self._threshold,
        }
