"""Phase 320: Federated Learning v2 — 연합 학습 v2.

FedAvg + 차등 프라이버시, 모델 집계,
비균일 데이터 분포, 통신 효율 최적화.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class AggregationMethod(Enum):
    FEDAVG = "fedavg"
    FEDPROX = "fedprox"
    SCAFFOLD = "scaffold"


class ClientStatus(Enum):
    IDLE = "idle"
    TRAINING = "training"
    UPLOADING = "uploading"
    READY = "ready"


@dataclass
class FLClient:
    client_id: str
    data_size: int = 100
    model_weights: Optional[np.ndarray] = None
    local_loss: float = float("inf")
    status: ClientStatus = ClientStatus.IDLE
    rounds_participated: int = 0
    privacy_budget: float = 1.0  # epsilon for DP


@dataclass
class FLRound:
    round_id: int
    participants: List[str]
    global_loss: float = 0.0
    avg_local_loss: float = 0.0
    model_divergence: float = 0.0
    duration_sec: float = 0.0
    privacy_spent: float = 0.0


@dataclass
class GlobalModel:
    weights: np.ndarray
    version: int = 0
    total_rounds: int = 0
    best_loss: float = float("inf")


class FederatedLearningV2:
    """연합 학습 v2 엔진.

    - FedAvg/FedProx 모델 집계
    - 차등 프라이버시 (가우시안 노이즈)
    - 클라이언트 선택 전략
    - 모델 압축 및 전송
    - 수렴 추적
    """

    def __init__(self, model_dim: int = 50, lr: float = 0.01,
                 method: AggregationMethod = AggregationMethod.FEDAVG,
                 dp_epsilon: float = 1.0, dp_delta: float = 1e-5,
                 rng_seed: int = 42):
        self._rng = np.random.default_rng(rng_seed)
        self._model_dim = model_dim
        self._lr = lr
        self._method = method
        self._dp_epsilon = dp_epsilon
        self._dp_delta = dp_delta

        # Initialize global model
        self._global = GlobalModel(
            weights=self._rng.normal(0, 0.1, model_dim)
        )
        self._clients: Dict[str, FLClient] = {}
        self._rounds: List[FLRound] = []
        self._convergence_history: List[float] = []

    def register_client(self, client_id: str, data_size: int = 100) -> FLClient:
        client = FLClient(
            client_id=client_id, data_size=data_size,
            model_weights=self._global.weights.copy(),
        )
        self._clients[client_id] = client
        return client

    def select_clients(self, fraction: float = 0.5) -> List[str]:
        """Random client selection weighted by data size."""
        all_ids = list(self._clients.keys())
        n_select = max(1, int(len(all_ids) * fraction))
        weights = np.array([self._clients[cid].data_size for cid in all_ids], dtype=float)
        weights /= weights.sum()
        selected = self._rng.choice(all_ids, size=n_select, replace=False, p=weights)
        return selected.tolist()

    def local_train(self, client_id: str, n_epochs: int = 5) -> float:
        """Simulate local training on client."""
        client = self._clients.get(client_id)
        if not client:
            return float("inf")

        client.status = ClientStatus.TRAINING
        client.model_weights = self._global.weights.copy()

        # Simulate SGD with synthetic loss landscape
        w = client.model_weights.copy()
        target = self._rng.normal(0, 1, self._model_dim) * 0.1  # synthetic target

        for _ in range(n_epochs):
            grad = (w - target) + self._rng.normal(0, 0.01, self._model_dim)
            w -= self._lr * grad

        client.model_weights = w
        client.local_loss = float(np.mean((w - target) ** 2))
        client.status = ClientStatus.READY
        client.rounds_participated += 1
        return client.local_loss

    def aggregate(self, participant_ids: List[str]) -> float:
        """Aggregate model updates from participants."""
        if not participant_ids:
            return float("inf")

        total_data = sum(self._clients[cid].data_size for cid in participant_ids)
        weighted_sum = np.zeros(self._model_dim)
        total_loss = 0.0

        for cid in participant_ids:
            client = self._clients[cid]
            if client.model_weights is None:
                continue
            weight = client.data_size / total_data

            # Apply differential privacy noise
            if self._dp_epsilon < float("inf"):
                sensitivity = 2.0 * self._lr
                sigma = sensitivity * np.sqrt(2 * np.log(1.25 / self._dp_delta)) / self._dp_epsilon
                noise = self._rng.normal(0, sigma, self._model_dim)
                update = client.model_weights + noise
            else:
                update = client.model_weights

            if self._method == AggregationMethod.FEDAVG:
                weighted_sum += weight * update
            elif self._method == AggregationMethod.FEDPROX:
                proximal = update + 0.01 * (self._global.weights - update)
                weighted_sum += weight * proximal
            else:
                weighted_sum += weight * update

            total_loss += weight * client.local_loss

        self._global.weights = weighted_sum
        self._global.version += 1
        self._global.total_rounds += 1
        if total_loss < self._global.best_loss:
            self._global.best_loss = total_loss

        # Distribute updated model
        for cid in self._clients:
            self._clients[cid].model_weights = self._global.weights.copy()
            self._clients[cid].status = ClientStatus.IDLE

        # Compute divergence
        divergences = []
        for cid in participant_ids:
            c = self._clients[cid]
            div = np.linalg.norm(c.model_weights - self._global.weights)
            divergences.append(div)

        fl_round = FLRound(
            round_id=self._global.total_rounds,
            participants=participant_ids,
            global_loss=total_loss,
            avg_local_loss=np.mean([self._clients[cid].local_loss for cid in participant_ids]),
            model_divergence=np.mean(divergences) if divergences else 0.0,
        )
        self._rounds.append(fl_round)
        self._convergence_history.append(total_loss)

        return total_loss

    def run_round(self, fraction: float = 0.5, n_epochs: int = 5) -> FLRound:
        """Execute a complete FL round: select → train → aggregate."""
        selected = self.select_clients(fraction)
        for cid in selected:
            self.local_train(cid, n_epochs)
        self.aggregate(selected)
        return self._rounds[-1]

    def get_convergence(self) -> List[float]:
        return self._convergence_history.copy()

    def get_global_model(self) -> GlobalModel:
        return self._global

    def summary(self) -> dict:
        return {
            "total_clients": len(self._clients),
            "total_rounds": self._global.total_rounds,
            "model_version": self._global.version,
            "best_loss": round(self._global.best_loss, 6),
            "method": self._method.value,
            "dp_epsilon": self._dp_epsilon,
            "convergence_points": len(self._convergence_history),
        }
