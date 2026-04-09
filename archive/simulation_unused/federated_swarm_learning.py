"""
Phase 472: Federated Swarm Learning
Distributed federated learning across drone swarm for collective intelligence.
"""

import numpy as np
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Optional, Tuple, Any, Callable
from collections import defaultdict


class AggregationMethod(Enum):
    """Federated aggregation methods."""

    FEDAVG = auto()
    FEDPROX = auto()
    FEDMA = auto()
    SCAFFOLD = auto()
    FEDBN = auto()


class PrivacyLevel(Enum):
    """Privacy protection levels."""

    NONE = auto()
    DIFFERENTIAL = auto()
    HOMOMORPHIC = auto()
    SECURE_AGG = auto()


@dataclass
class DroneModel:
    """Local model on a drone."""

    drone_id: str
    weights: np.ndarray
    bias: np.ndarray
    data_samples: int = 0
    local_epochs: int = 5
    loss: float = 0.0
    accuracy: float = 0.0
    training_time_ms: float = 0.0


@dataclass
class GlobalModel:
    """Global federated model."""

    weights: np.ndarray
    bias: np.ndarray
    round: int = 0
    participating_drones: List[str] = field(default_factory=list)
    convergence_history: List[float] = field(default_factory=list)
    aggregation_method: AggregationMethod = AggregationMethod.FEDAVG


@dataclass
class FederatedRound:
    """Federated learning round."""

    round_id: int
    selected_drones: List[str]
    local_updates: Dict[str, DroneModel]
    global_update: GlobalModel
    start_time: float = 0.0
    end_time: float = 0.0
    convergence_rate: float = 0.0


class FederatedSwarmLearning:
    """Federated learning engine for drone swarm."""

    def __init__(
        self,
        n_drones: int,
        model_dim: int = 64,
        aggregation: AggregationMethod = AggregationMethod.FEDAVG,
        privacy: PrivacyLevel = PrivacyLevel.DIFFERENTIAL,
        seed: int = 42,
    ):
        self.rng = np.random.default_rng(seed)
        self.n_drones = n_drones
        self.model_dim = model_dim
        self.aggregation = aggregation
        self.privacy = privacy
        self.drone_models: Dict[str, DroneModel] = {}
        self.global_model: Optional[GlobalModel] = None
        self.rounds: List[FederatedRound] = []
        self.current_round = 0
        self.privacy_budget = 1.0
        self._init_models()

    def _init_models(self) -> None:
        weights = self.rng.standard_normal(self.model_dim) * 0.01
        bias = np.zeros(1)
        self.global_model = GlobalModel(weights.copy(), bias.copy())
        for i in range(self.n_drones):
            drone = DroneModel(
                drone_id=f"drone_{i}",
                weights=weights.copy()
                + self.rng.standard_normal(self.model_dim) * 0.001,
                bias=bias.copy(),
                data_samples=self.rng.integers(100, 1000),
            )
            self.drone_models[drone.drone_id] = drone

    def _add_differential_privacy(
        self, gradient: np.ndarray, epsilon: float = 1.0
    ) -> np.ndarray:
        sensitivity = 1.0
        noise = self.rng.laplace(0, sensitivity / epsilon, gradient.shape)
        return gradient + noise

    def _local_train(
        self, drone: DroneModel, local_data: Optional[np.ndarray] = None
    ) -> DroneModel:
        start = time.time()
        for _ in range(drone.local_epochs):
            grad = self.rng.standard_normal(self.model_dim) * 0.01
            if self.privacy == PrivacyLevel.DIFFERENTIAL:
                grad = self._add_differential_privacy(grad, epsilon=self.privacy_budget)
            drone.weights -= 0.01 * grad
        drone.loss = float(self.rng.uniform(0.1, 0.5))
        drone.accuracy = float(self.rng.uniform(0.7, 0.95))
        drone.training_time_ms = (time.time() - start) * 1000
        return drone

    def _aggregate_fedavg(
        self, selected: List[DroneModel]
    ) -> Tuple[np.ndarray, np.ndarray]:
        total_samples = sum(d.data_samples for d in selected)
        if total_samples == 0:
            return self.global_model.weights.copy(), self.global_model.bias.copy()
        weights = np.zeros(self.model_dim)
        bias = np.zeros(1)
        for drone in selected:
            w = drone.data_samples / total_samples
            weights += w * drone.weights
            bias += w * drone.bias
        return weights, bias

    def _aggregate_fedprox(
        self, selected: List[DroneModel], mu: float = 0.01
    ) -> Tuple[np.ndarray, np.ndarray]:
        total_samples = sum(d.data_samples for d in selected)
        if total_samples == 0:
            return self.global_model.weights.copy(), self.global_model.bias.copy()
        weights = np.zeros(self.model_dim)
        bias = np.zeros(1)
        for drone in selected:
            w = drone.data_samples / total_samples
            prox_term = mu * (drone.weights - self.global_model.weights)
            weights += w * (drone.weights - prox_term)
            bias += w * drone.bias
        return weights, bias

    def select_drones(self, fraction: float = 0.5) -> List[str]:
        n_select = max(1, int(self.n_drones * fraction))
        selected = self.rng.choice(
            list(self.drone_models.keys()), n_select, replace=False
        )
        return list(selected)

    def run_round(self, selected_drones: Optional[List[str]] = None) -> FederatedRound:
        self.current_round += 1
        if selected_drones is None:
            selected_drones = self.select_drones()
        round_obj = FederatedRound(
            round_id=self.current_round,
            selected_drones=selected_drones,
            local_updates={},
            global_update=self.global_model,
            start_time=time.time(),
        )
        for drone_id in selected_drones:
            drone = self.drone_models[drone_id]
            updated = self._local_train(drone)
            round_obj.local_updates[drone_id] = updated
        selected_models = [self.drone_models[did] for did in selected_drones]
        if self.aggregation == AggregationMethod.FEDAVG:
            new_weights, new_bias = self._aggregate_fedavg(selected_models)
        elif self.aggregation == AggregationMethod.FEDPROX:
            new_weights, new_bias = self._aggregate_fedprox(selected_models)
        else:
            new_weights, new_bias = self._aggregate_fedavg(selected_models)
        self.global_model.weights = new_weights
        self.global_model.bias = new_bias
        self.global_model.round = self.current_round
        self.global_model.participating_drones = selected_drones
        avg_loss = np.mean([m.loss for m in selected_models])
        self.global_model.convergence_history.append(float(avg_loss))
        round_obj.global_update = self.global_model
        round_obj.end_time = time.time()
        round_obj.convergence_rate = float(avg_loss)
        self.rounds.append(round_obj)
        return round_obj

    def train(self, n_rounds: int = 10) -> GlobalModel:
        for _ in range(n_rounds):
            self.run_round()
        return self.global_model

    def get_convergence_stats(self) -> Dict[str, Any]:
        if not self.global_model.convergence_history:
            return {"rounds": 0}
        history = self.global_model.convergence_history
        return {
            "total_rounds": self.current_round,
            "final_loss": history[-1] if history else 0,
            "best_loss": min(history) if history else 0,
            "convergence_rate": (history[0] - history[-1]) / len(history)
            if len(history) > 1
            else 0,
            "aggregation": self.aggregation.name,
            "privacy": self.privacy.name,
        }


class SwarmKnowledgeDistillation:
    """Knowledge distillation across drone swarm."""

    def __init__(self, n_drones: int, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_drones = n_drones
        self.teacher_models: Dict[str, np.ndarray] = {}
        self.student_models: Dict[str, np.ndarray] = {}
        self._init_models()

    def _init_models(self) -> None:
        for i in range(self.n_drones):
            self.teacher_models[f"drone_{i}"] = self.rng.standard_normal(64) * 0.1
            self.student_models[f"drone_{i}"] = self.rng.standard_normal(64) * 0.01

    def distill(self, temperature: float = 2.0) -> Dict[str, float]:
        losses = {}
        for drone_id in self.teacher_models:
            teacher = self.teacher_models[drone_id]
            student = self.student_models[drone_id]
            soft_teacher = np.exp(teacher / temperature) / np.sum(
                np.exp(teacher / temperature)
            )
            soft_student = np.exp(student / temperature) / np.sum(
                np.exp(student / temperature)
            )
            loss = float(np.mean((soft_teacher - soft_student) ** 2))
            student -= 0.01 * (soft_student - soft_teacher)
            losses[drone_id] = loss
        return losses

    def aggregate_knowledge(self) -> np.ndarray:
        all_knowledge = list(self.teacher_models.values())
        return np.mean(all_knowledge, axis=0)


class SwarmCollaborativeFiltering:
    """Collaborative filtering for swarm decision making."""

    def __init__(self, n_drones: int, n_items: int = 10, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_drones = n_drones
        self.n_items = n_items
        self.ratings: Dict[str, np.ndarray] = {}
        self._init_ratings()

    def _init_ratings(self) -> None:
        for i in range(self.n_drones):
            self.ratings[f"drone_{i}"] = self.rng.uniform(0, 5, self.n_items)

    def predict(self, drone_id: str, item_idx: int) -> float:
        if drone_id not in self.ratings:
            return 3.0
        similar_drones = self._find_similar(drone_id)
        if not similar_drones:
            return float(self.ratings[drone_id][item_idx])
        predictions = [self.ratings[d][item_idx] for d in similar_drones]
        return float(np.mean(predictions))

    def _find_similar(self, drone_id: str, top_k: int = 3) -> List[str]:
        if drone_id not in self.ratings:
            return []
        target = self.ratings[drone_id]
        similarities = []
        for other_id, other_ratings in self.ratings.items():
            if other_id == drone_id:
                continue
            sim = np.dot(target, other_ratings) / (
                np.linalg.norm(target) * np.linalg.norm(other_ratings) + 1e-8
            )
            similarities.append((other_id, sim))
        similarities.sort(key=lambda x: x[1], reverse=True)
        return [d for d, _ in similarities[:top_k]]

    def get_recommendations(self, drone_id: str, n: int = 5) -> List[int]:
        if drone_id not in self.ratings:
            return list(range(n))
        target = self.ratings[drone_id]
        unrated = np.where(target < 2.0)[0]
        scores = [(idx, self.predict(drone_id, idx)) for idx in unrated]
        scores.sort(key=lambda x: x[1], reverse=True)
        return [idx for idx, _ in scores[:n]]


if __name__ == "__main__":
    fed = FederatedSwarmLearning(n_drones=10, model_dim=64, seed=42)
    model = fed.train(n_rounds=5)
    print(f"Final round: {model.round}")
    print(f"Convergence: {fed.get_convergence_stats()}")
    distill = SwarmKnowledgeDistillation(n_drones=10, seed=42)
    losses = distill.distill()
    print(f"Distillation losses: {list(losses.values())[:3]}")
    collab = SwarmCollaborativeFiltering(n_drones=10, seed=42)
    recs = collab.get_recommendations("drone_0")
    print(f"Recommendations for drone_0: {recs}")
