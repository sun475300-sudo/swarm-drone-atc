"""ML 기반 충돌 예측 모듈 — PyTorch MLP로 드론 쌍의 충돌 확률을 예측한다."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from simulation.apf_engine.apf import APFState

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------
INPUT_DIM = 12  # 2드론 x (pos 3 + vel 3)
HIDDEN_DIM = 64
COLLISION_DIST = 50.0  # m — 이 거리 이내면 충돌로 간주
SAFE_DIST_MIN = 200.0  # m — 안전 데이터 최소 거리
SAFE_DIST_MAX = 2000.0  # m — 안전 데이터 최대 거리
DEFAULT_LR = 1e-3
DEFAULT_EPOCHS = 30
DEFAULT_BATCH = 256


# ---------------------------------------------------------------------------
# 모델
# ---------------------------------------------------------------------------
class _CollisionMLP(nn.Module):
    """간단한 3-layer MLP: 12 → 64 → 32 → 1."""

    def __init__(self) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(INPUT_DIM, HIDDEN_DIM),
            nn.ReLU(),
            nn.Linear(HIDDEN_DIM, HIDDEN_DIM // 2),
            nn.ReLU(),
            nn.Linear(HIDDEN_DIM // 2, 1),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


# ---------------------------------------------------------------------------
# 예측기 클래스
# ---------------------------------------------------------------------------
class CollisionPredictor:
    """드론 쌍의 충돌 확률을 예측하는 래퍼 클래스."""

    def __init__(self) -> None:
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = _CollisionMLP().to(self.device)

    # -- 추론 ----------------------------------------------------------
    def predict(self, drone_a: APFState, drone_b: APFState) -> float:
        """두 드론 상태로부터 충돌 확률(0~1)을 반환한다."""
        features = np.concatenate([
            drone_a.position, drone_a.velocity,
            drone_b.position, drone_b.velocity,
        ]).astype(np.float32)
        tensor = torch.from_numpy(features).unsqueeze(0).to(self.device)
        self.model.eval()
        with torch.no_grad():
            prob = self.model(tensor).item()
        return prob

    # -- 학습 ----------------------------------------------------------
    def train(
        self,
        dataset: tuple[np.ndarray, np.ndarray],
        *,
        epochs: int = DEFAULT_EPOCHS,
        lr: float = DEFAULT_LR,
        batch_size: int = DEFAULT_BATCH,
    ) -> list[float]:
        """(X, y) 데이터셋으로 모델을 학습한다. 에포크별 손실 리스트를 반환."""
        x_arr, y_arr = dataset
        x_t = torch.from_numpy(x_arr.astype(np.float32)).to(self.device)
        y_t = torch.from_numpy(y_arr.astype(np.float32)).to(self.device)
        loader = DataLoader(TensorDataset(x_t, y_t), batch_size=batch_size, shuffle=True)

        optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        criterion = nn.BCELoss()
        self.model.train()

        losses: list[float] = []
        for _ in range(epochs):
            epoch_loss = 0.0
            for xb, yb in loader:
                optimizer.zero_grad()
                pred = self.model(xb)
                loss = criterion(pred, yb)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item() * xb.size(0)
            losses.append(epoch_loss / len(x_t))
        return losses

    # -- 저장/로드 -----------------------------------------------------
    def save(self, path: str | Path) -> None:
        """모델 가중치를 파일로 저장한다."""
        torch.save(self.model.state_dict(), path)

    def load(self, path: str | Path) -> None:
        """저장된 가중치를 로드한다."""
        state = torch.load(path, map_location=self.device, weights_only=True)
        self.model.load_state_dict(state)


# ---------------------------------------------------------------------------
# 합성 데이터 생성
# ---------------------------------------------------------------------------
def generate_training_data(
    n_samples: int = 10_000,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """시뮬레이션 없이 합성 충돌/안전 데이터를 생성한다.

    Returns:
        (X, y) — X.shape=(n_samples, 12), y.shape=(n_samples,)
    """
    rng = np.random.default_rng(seed)
    n_collision = n_samples // 2
    n_safe = n_samples - n_collision

    def _random_states(n: int, dist_min: float, dist_max: float) -> np.ndarray:
        """드론 쌍 특징 벡터를 생성한다."""
        pos_a = rng.uniform(-1000, 1000, size=(n, 3))
        vel_a = rng.uniform(-15, 15, size=(n, 3))
        # 거리 범위 내에서 드론 B 위치 생성
        direction = rng.standard_normal((n, 3))
        direction /= np.linalg.norm(direction, axis=1, keepdims=True) + 1e-9
        dist = rng.uniform(dist_min, dist_max, size=(n, 1))
        pos_b = pos_a + direction * dist
        vel_b = rng.uniform(-15, 15, size=(n, 3))
        return np.hstack([pos_a, vel_a, pos_b, vel_b])

    x_collision = _random_states(n_collision, 0.0, COLLISION_DIST)
    x_safe = _random_states(n_safe, SAFE_DIST_MIN, SAFE_DIST_MAX)

    x = np.vstack([x_collision, x_safe]).astype(np.float32)
    y = np.concatenate([
        np.ones(n_collision, dtype=np.float32),
        np.zeros(n_safe, dtype=np.float32),
    ])

    # 셔플
    idx = rng.permutation(n_samples)
    return x[idx], y[idx]
