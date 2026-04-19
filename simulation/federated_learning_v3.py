"""
Phase 405: Federated Learning v3 with Differential Privacy
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import time
import hashlib


class AggregationMethod(Enum):
    FEDAVG = "fedavg"
    FEDPROX = "fedprox"
    FEDNOVA = "fednova"
    SCAFFOLD = "scaffold"


@dataclass
class ModelUpdate:
    drone_id: str
    round_number: int
    parameters: Dict[str, np.ndarray]
    num_samples: int
    timestamp: float
    loss: float
    accuracy: float


@dataclass
class AggregatedModel:
    round_number: int
    parameters: Dict[str, np.ndarray]
    timestamp: float
    participating_drones: List[str]
    avg_loss: float
    avg_accuracy: float


class FederatedLearningV3:
    def __init__(
        self,
        model_shape: Dict[str, Tuple[int, ...]],
        aggregation_method: AggregationMethod = AggregationMethod.FEDAVG,
        differential_privacy: bool = True,
        noise_multiplier: float = 1.0,
        max_grad_norm: float = 1.0,
        min_clients_per_round: int = 3,
    ):
        self.model_shape = model_shape
        self.aggregation_method = aggregation_method
        self.differential_privacy = differential_privacy
        self.noise_multiplier = noise_multiplier
        self.max_grad_norm = max_grad_norm
        self.min_clients_per_round = min_clients_per_round

        self.global_model = self._initialize_model()
        self.client_models: Dict[str, Dict[str, np.ndarray]] = {}
        self.update_history: List[ModelUpdate] = []

        self.current_round = 0
        self.noise_budget = 10.0

        self.training_stats = {
            "rounds": 0,
            "total_samples": 0,
            "avg_loss_per_round": [],
        }

    def _initialize_model(self) -> Dict[str, np.ndarray]:
        model = {}
        for name, shape in self.model_shape.items():
            model[name] = np.zeros(shape)
        return model

    def register_client(self, drone_id: str):
        self.client_models[drone_id] = self._initialize_model()

    def get_client_model(self, drone_id: str) -> Dict[str, np.ndarray]:
        if drone_id not in self.client_models:
            self.register_client(drone_id)
        return self.client_models[drone_id]

    def submit_update(self, update: ModelUpdate) -> bool:
        if update.round_number != self.current_round:
            return False

        self.update_history.append(update)
        return True

    def get_pending_updates_count(self) -> int:
        return len(
            [u for u in self.update_history if u.round_number == self.current_round]
        )

    def should_aggregate(self) -> bool:
        return self.get_pending_updates_count() >= self.min_clients_per_round

    def aggregate(self) -> Optional[AggregatedModel]:
        if not self.should_aggregate():
            return None

        round_updates = [
            u for u in self.update_history if u.round_number == self.current_round
        ]

        if len(round_updates) < self.min_clients_per_round:
            return None

        if self.aggregation_method == AggregationMethod.FEDAVG:
            aggregated = self._fedavg(round_updates)
        elif self.aggregation_method == AggregationMethod.FEDPROX:
            aggregated = self._fedprox(round_updates)
        elif self.aggregation_method == AggregationMethod.FEDNOVA:
            aggregated = self._fednova(round_updates)
        else:
            aggregated = self._fedavg(round_updates)

        self.global_model = aggregated.parameters

        self.current_round += 1

        return aggregated

    def _fedavg(self, updates: List[ModelUpdate]) -> AggregatedModel:
        total_samples = sum(u.num_samples for u in updates)

        aggregated_params = {}
        for param_name in self.global_model.keys():
            weighted_sum = np.zeros_like(self.global_model[param_name])

            for update in updates:
                weight = update.num_samples / total_samples
                weighted_sum += update.parameters[param_name] * weight

            if self.differential_privacy:
                weighted_sum = self._add_noise(weighted_sum)

            aggregated_params[param_name] = weighted_sum

        avg_loss = np.mean([u.loss for u in updates])
        avg_accuracy = np.mean([u.accuracy for u in updates])

        return AggregatedModel(
            round_number=self.current_round,
            parameters=aggregated_params,
            timestamp=time.time(),
            participating_drones=[u.drone_id for u in updates],
            avg_loss=avg_loss,
            avg_accuracy=avg_accuracy,
        )

    def _fedprox(self, updates: List[ModelUpdate]) -> AggregatedModel:
        mu = 0.01

        total_samples = sum(u.num_samples for u in updates)

        aggregated_params = {}
        for param_name in self.global_model.keys():
            weighted_sum = np.zeros_like(self.global_model[param_name])

            for update in updates:
                weight = update.num_samples / total_samples

                proximal_term = (
                    self.global_model[param_name] - update.parameters[param_name]
                )
                adjusted_update = update.parameters[param_name] - mu * proximal_term

                weighted_sum += adjusted_update * weight

            if self.differential_privacy:
                weighted_sum = self._add_noise(weighted_sum)

            aggregated_params[param_name] = weighted_sum

        avg_loss = np.mean([u.loss for u in updates])
        avg_accuracy = np.mean([u.accuracy for u in updates])

        return AggregatedModel(
            round_number=self.current_round,
            parameters=aggregated_params,
            timestamp=time.time(),
            participating_drones=[u.drone_id for u in updates],
            avg_loss=avg_loss,
            avg_accuracy=avg_accuracy,
        )

    def _fednova(self, updates: List[ModelUpdate]) -> AggregatedModel:
        total_samples = sum(u.num_samples for u in updates)

        local_steps = [u.num_samples for u in updates]
        rho = sum(local_steps) / max(local_steps)

        aggregated_params = {}
        for param_name in self.global_model.keys():
            weighted_sum = np.zeros_like(self.global_model[param_name])

            for i, update in enumerate(updates):
                weight = local_steps[i] / sum(local_steps)

                normalized_update = update.parameters[param_name] / rho
                weighted_sum += normalized_update * weight

            if self.differential_privacy:
                weighted_sum = self._add_noise(weighted_sum)

            aggregated_params[param_name] = weighted_sum

        avg_loss = np.mean([u.loss for u in updates])
        avg_accuracy = np.mean([u.accuracy for u in updates])

        return AggregatedModel(
            round_number=self.current_round,
            parameters=aggregated_params,
            timestamp=time.time(),
            participating_drones=[u.drone_id for u in updates],
            avg_loss=avg_loss,
            avg_accuracy=avg_accuracy,
        )

    def _add_noise(self, params: np.ndarray) -> np.ndarray:
        noise_scale = self.noise_multiplier * self.max_grad_norm

        noise = np.random.normal(0, noise_scale, params.shape)

        param_norm = np.linalg.norm(params)
        if param_norm > self.max_grad_norm:
            params = params * (self.max_grad_norm / param_norm)

        return params + noise

    def get_global_model(self) -> Dict[str, np.ndarray]:
        return self.global_model.copy()

    def simulate_local_training(
        self,
        drone_id: str,
        local_epochs: int = 5,
    ) -> ModelUpdate:
        client_model = self.get_client_model(drone_id)

        simulated_loss = np.random.uniform(0.1, 0.5)
        simulated_accuracy = np.random.uniform(0.7, 0.95)

        trained_params = {}
        for param_name, param in client_model.items():
            grad = np.random.randn(*param.shape) * 0.01
            trained_params[param_name] = param - grad * local_epochs

        self.client_models[drone_id] = trained_params

        update = ModelUpdate(
            drone_id=drone_id,
            round_number=self.current_round,
            parameters=trained_params,
            num_samples=100,
            timestamp=time.time(),
            loss=simulated_loss,
            accuracy=simulated_accuracy,
        )

        return update

    def get_stats(self) -> Dict[str, Any]:
        return {
            "current_round": self.current_round,
            "total_clients": len(self.client_models),
            "pending_updates": self.get_pending_updates_count(),
            "aggregation_method": self.aggregation_method.value,
            "differential_privacy_enabled": self.differential_privacy,
            "noise_budget": self.noise_budget,
        }
