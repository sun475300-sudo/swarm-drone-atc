"""
연합 학습 집계
=============
드론별 로컬 학습 + 모델 집계 + 프라이버시.

사용법:
    fl = FederatedLearning(n_params=10)
    fl.register_client("d1")
    fl.submit_update("d1", weights=[0.1]*10)
    global_w = fl.aggregate()
"""
from __future__ import annotations
from typing import Any
import numpy as np


class FederatedLearning:
    def __init__(self, n_params: int = 10) -> None:
        self.n_params = n_params
        self._global_weights = np.zeros(n_params)
        self._clients: dict[str, np.ndarray | None] = {}
        self._rounds = 0

    def register_client(self, client_id: str) -> None:
        self._clients[client_id] = None

    def submit_update(self, client_id: str, weights: list[float]) -> bool:
        if client_id not in self._clients:
            return False
        self._clients[client_id] = np.array(weights[:self.n_params])
        return True

    def aggregate(self) -> list[float]:
        updates = [w for w in self._clients.values() if w is not None]
        if not updates:
            return self._global_weights.tolist()
        self._global_weights = np.mean(updates, axis=0)
        self._rounds += 1
        for cid in self._clients:
            self._clients[cid] = None
        return [round(float(w), 6) for w in self._global_weights]

    def global_weights(self) -> list[float]:
        return [round(float(w), 6) for w in self._global_weights]

    def participation_rate(self) -> float:
        if not self._clients:
            return 0
        return round(sum(1 for w in self._clients.values() if w is not None) / len(self._clients) * 100, 1)

    def summary(self) -> dict[str, Any]:
        return {
            "clients": len(self._clients),
            "rounds": self._rounds,
            "participation": self.participation_rate(),
        }
