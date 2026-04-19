"""
Phase 406: Graph Neural Network for Drone Swarm Topology Learning
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import time


@dataclass
class GraphNode:
    node_id: str
    position: np.ndarray
    velocity: np.ndarray
    features: Dict[str, np.ndarray] = field(default_factory=dict)


@dataclass
class GraphEdge:
    source: str
    target: str
    edge_type: str = "communication"
    weight: float = 1.0


class GraphNeuralNetwork:
    def __init__(
        self,
        node_feature_dim: int = 32,
        hidden_dim: int = 64,
        num_layers: int = 3,
        message_passing_steps: int = 3,
    ):
        self.node_feature_dim = node_feature_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.message_passing_steps = message_passing_steps

        self.node_embeddings: Dict[str, np.ndarray] = {}
        self.edge_features: Dict[Tuple[str, str], np.ndarray] = {}

        self._initialize_parameters()

    def _initialize_parameters(self):
        np.random.seed(42)

        self.W_node = np.random.randn(self.hidden_dim, self.node_feature_dim) * 0.1
        self.W_message = np.random.randn(self.hidden_dim, self.hidden_dim * 2) * 0.1
        self.W_update = np.random.randn(self.hidden_dim, self.hidden_dim) * 0.1
        self.W_readout = np.random.randn(1, self.hidden_dim) * 0.1

    def add_node(self, node_id: str, position: np.ndarray, velocity: np.ndarray):
        features = np.concatenate([position, velocity])
        if len(features) < self.node_feature_dim:
            features = np.pad(features, (0, self.node_feature_dim - len(features)))
        else:
            features = features[: self.node_feature_dim]

        self.node_embeddings[node_id] = features

    def add_edge(self, source: str, target: str, edge_type: str = "communication"):
        if source not in self.node_embeddings or target not in self.node_embeddings:
            return

        self.edge_features[(source, target)] = np.random.randn(self.hidden_dim) * 0.1

    def build_graph_from_drones(
        self, drones: List[Dict], communication_range: float = 100.0
    ):
        self.node_embeddings.clear()
        self.edge_features.clear()

        for drone in drones:
            pos = np.array(drone.get("position", [0, 0, 0]))
            vel = np.array(drone.get("velocity", [0, 0, 0]))
            self.add_node(drone["id"], pos, vel)

        for i, drone1 in enumerate(drones):
            pos1 = np.array(drone1.get("position", [0, 0, 0]))
            for j, drone2 in enumerate(drones):
                if i >= j:
                    continue

                pos2 = np.array(drone2.get("position", [0, 0, 0]))
                distance = np.linalg.norm(pos1 - pos2)

                if distance < communication_range:
                    self.add_edge(drone1["id"], drone2["id"])

    def message_passing(self) -> Dict[str, np.ndarray]:
        node_states = {}

        for node_id, embedding in self.node_embeddings.items():
            node_states[node_id] = np.tanh(self.W_node @ embedding)

        for step in range(self.message_passing_steps):
            new_states = {}

            for node_id in node_states:
                messages = []

                for (source, target), edge_feat in self.edge_features.items():
                    if target == node_id and source in node_states:
                        combined = np.concatenate([node_states[source], edge_feat])
                        message = np.tanh(self.W_message @ combined)
                        messages.append(message)

                if messages:
                    aggregated = np.mean(messages, axis=0)
                    new_state = np.tanh(
                        self.W_update @ (node_states[node_id] + aggregated)
                    )
                else:
                    new_state = node_states[node_id]

                new_states[node_id] = new_state

            node_states = new_states

        return node_states

    def predict_collision_risk(
        self, drones: List[Dict]
    ) -> Dict[Tuple[str, str], float]:
        self.build_graph_from_drones(drones)

        node_states = self.message_passing()

        risks = {}

        for i, drone1 in enumerate(drones):
            for j, drone2 in enumerate(drones):
                if i >= j:
                    continue

                state1 = node_states.get(drone1["id"], np.zeros(self.hidden_dim))
                state2 = node_states.get(drone2["id"], np.zeros(self.hidden_dim))

                pos1 = np.array(drone1.get("position", [0, 0, 0]))
                pos2 = np.array(drone2.get("position", [0, 0, 0]))

                distance = np.linalg.norm(pos1 - pos2)
                rel_vel = np.array(drone1.get("velocity", [0, 0, 0])) - np.array(
                    drone2.get("velocity", [0, 0, 0])
                )
                closing_speed = np.linalg.norm(rel_vel)

                base_risk = 1.0 / (1.0 + distance / 10.0)

                similarity = np.dot(state1, state2) / (
                    np.linalg.norm(state1) * np.linalg.norm(state2) + 1e-6
                )
                behavior_risk = (1.0 - similarity) / 2.0

                total_risk = 0.6 * base_risk + 0.4 * behavior_risk

                risks[(drone1["id"], drone2["id"])] = min(total_risk, 1.0)

        return risks

    def predict_trajectory(
        self,
        drone_id: str,
        future_steps: int = 10,
    ) -> List[np.ndarray]:
        node_states = self.message_passing()

        current_state = node_states.get(drone_id, np.zeros(self.hidden_dim))

        trajectory = []
        state = current_state

        for _ in range(future_steps):
            transition = np.tanh(state * 0.9 + np.random.randn(self.hidden_dim) * 0.1)
            state = transition

            readout = self.W_readout @ state
            position_offset = np.tanh(readout) * 10.0

            trajectory.append(position_offset)

        return trajectory

    def get_swarm_embedding(self) -> np.ndarray:
        node_states = self.message_passing()

        if not node_states:
            return np.zeros(self.hidden_dim)

        swarm_embedding = np.mean(list(node_states.values()), axis=0)

        return swarm_embedding
