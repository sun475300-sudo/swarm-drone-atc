"""Phase 661: Transformer 기반 궤적 예측 모델."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
import torch.nn as nn

STATE_DIM = 6  # x, y, z, vx, vy, vz
POS_DIM = 3    # x, y, z


@dataclass
class TrajectoryData:
    drone_id: str
    positions: List[np.ndarray] = field(default_factory=list)
    timestamps: List[float] = field(default_factory=list)


class PositionalEncoding(nn.Module):
    """Sinusoidal positional encoding for sequence positions."""

    def __init__(self, d_model: int, max_len: int = 500, dropout: float = 0.1) -> None:
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(
            torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model)
        )
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term[: d_model // 2])
        pe = pe.unsqueeze(0)  # (1, max_len, d_model)
        self.register_buffer("pe", pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.pe[:, : x.size(1)]
        return self.dropout(x)


class TrajectoryTransformer(nn.Module):
    """Encoder-only Transformer for drone trajectory prediction."""

    def __init__(
        self,
        input_dim: int = STATE_DIM,
        d_model: int = 64,
        nhead: int = 4,
        num_layers: int = 2,
        pred_horizon: int = 10,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        self.d_model = d_model
        self.pred_horizon = pred_horizon

        self.input_proj = nn.Linear(input_dim, d_model)
        self.pos_encoder = PositionalEncoding(d_model, dropout=dropout)

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead, dim_feedforward=d_model * 4,
            dropout=dropout, batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.pred_head = nn.Linear(d_model, pred_horizon * POS_DIM)

    def forward(self, src: torch.Tensor) -> torch.Tensor:
        """Forward pass.

        Args:
            src: (batch, seq_len, input_dim)

        Returns:
            (batch, pred_horizon, 3) predicted future positions
        """
        x = self.input_proj(src)
        x = self.pos_encoder(x)
        x = self.transformer(x)
        x = x[:, -1, :]  # last token
        x = self.pred_head(x)
        return x.view(-1, self.pred_horizon, POS_DIM)


class TrajectoryPredictor:
    """High-level wrapper for trajectory prediction."""

    def __init__(
        self,
        d_model: int = 64,
        nhead: int = 4,
        num_layers: int = 2,
        pred_horizon: int = 10,
        lr: float = 1e-3,
        seed: int = 42,
    ) -> None:
        self.rng = np.random.default_rng(seed)
        self.pred_horizon = pred_horizon
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.model = TrajectoryTransformer(
            d_model=d_model, nhead=nhead, num_layers=num_layers,
            pred_horizon=pred_horizon,
        ).to(self.device)

        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=lr)
        self.loss_fn = nn.MSELoss()

        self.trajectories: Dict[str, TrajectoryData] = {}
        self.train_losses: List[float] = []
        self.train_steps = 0

    def add_trajectory(self, drone_id: str, positions: np.ndarray) -> None:
        """Store observed trajectory data.

        Args:
            drone_id: drone identifier
            positions: (T, 3) array of positions
        """
        if drone_id not in self.trajectories:
            self.trajectories[drone_id] = TrajectoryData(drone_id=drone_id)
        self.trajectories[drone_id].positions.append(positions.copy())

    def train_step(
        self, batch_states: np.ndarray, batch_targets: np.ndarray
    ) -> float:
        """Single training step.

        Args:
            batch_states: (batch, seq_len, 6)
            batch_targets: (batch, pred_horizon, 3)

        Returns:
            loss value
        """
        self.model.train()
        states = torch.from_numpy(batch_states).float().to(self.device)
        targets = torch.from_numpy(batch_targets).float().to(self.device)

        self.optimizer.zero_grad()
        preds = self.model(states)
        loss = self.loss_fn(preds, targets)
        loss.backward()
        self.optimizer.step()

        loss_val = loss.item()
        self.train_losses.append(loss_val)
        self.train_steps += 1
        return loss_val

    def predict(self, states_sequence: np.ndarray) -> np.ndarray:
        """Predict future positions from state sequence.

        Args:
            states_sequence: (seq_len, 6) or (batch, seq_len, 6)

        Returns:
            (pred_horizon, 3) or (batch, pred_horizon, 3)
        """
        self.model.eval()
        if states_sequence.ndim == 2:
            states_sequence = states_sequence[np.newaxis]
            squeeze = True
        else:
            squeeze = False

        x = torch.from_numpy(states_sequence).float().to(self.device)
        with torch.no_grad():
            preds = self.model(x)

        result = preds.cpu().numpy()
        return result[0] if squeeze else result

    def get_prediction_accuracy(self) -> Dict[str, float]:
        """Return training metrics."""
        if not self.train_losses:
            return {"mean_loss": 0.0, "min_loss": 0.0, "latest_loss": 0.0, "steps": 0}
        return {
            "mean_loss": float(np.mean(self.train_losses)),
            "min_loss": float(np.min(self.train_losses)),
            "latest_loss": self.train_losses[-1],
            "steps": self.train_steps,
        }

    def get_trajectory_count(self) -> int:
        return len(self.trajectories)
