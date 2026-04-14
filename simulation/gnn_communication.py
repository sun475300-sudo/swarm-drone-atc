"""GNN 기반 드론 통신 네트워크 — torch_geometric 없이 직접 구현한 Message Passing GNN."""

from __future__ import annotations

import numpy as np
import torch
import torch.nn as nn

# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------
NODE_FEAT_DIM = 6    # pos(3) + vel(3)
HIDDEN_DIM = 32      # GNN 임베딩 차원
DEFAULT_COMM_RANGE = 500.0  # 미터 — 기본 통신 범위


# ---------------------------------------------------------------------------
# 인접 행렬 생성
# ---------------------------------------------------------------------------
def build_adjacency(
    positions: np.ndarray,
    comm_range: float = DEFAULT_COMM_RANGE,
) -> np.ndarray:
    """거리 기반 인접 행렬을 생성한다.

    Args:
        positions: (N, 3) 드론 위치 배열
        comm_range: 통신 범위 (m)

    Returns:
        (N, N) 이진 인접 행렬 (자기 자신 제외)
    """
    # 쌍별 거리 계산
    diff = positions[:, np.newaxis, :] - positions[np.newaxis, :, :]
    dist = np.linalg.norm(diff, axis=-1)

    adj = (dist <= comm_range).astype(np.float32)
    np.fill_diagonal(adj, 0.0)
    return adj


# ---------------------------------------------------------------------------
# GNN 레이어
# ---------------------------------------------------------------------------
class _MessagePassingLayer(nn.Module):
    """단일 Message Passing 레이어 — mean aggregation + 선형 변환."""

    def __init__(self, in_dim: int, out_dim: int) -> None:
        super().__init__()
        # 자기 특성 변환
        self.linear_self = nn.Linear(in_dim, out_dim)
        # 이웃 집계 특성 변환
        self.linear_neigh = nn.Linear(in_dim, out_dim)

    def forward(self, x: torch.Tensor, adj: torch.Tensor) -> torch.Tensor:
        """Message passing 수행.

        Args:
            x: (N, in_dim) 노드 특성
            adj: (N, N) 인접 행렬

        Returns:
            (N, out_dim) 갱신된 노드 특성
        """
        # 이웃 수 계산 (0으로 나누기 방지)
        degree = adj.sum(dim=-1, keepdim=True).clamp(min=1.0)

        # Mean aggregation: 인접 행렬로 이웃 특성 합산 후 평균
        neigh_sum = torch.matmul(adj, x)  # (N, in_dim)
        neigh_mean = neigh_sum / degree

        # 자기 특성 + 이웃 특성 결합
        out = self.linear_self(x) + self.linear_neigh(neigh_mean)
        return torch.relu(out)


# ---------------------------------------------------------------------------
# 드론 그래프 네트워크
# ---------------------------------------------------------------------------
class DroneGraphNetwork(nn.Module):
    """2-layer GNN으로 드론 간 통신을 모델링한다.

    입력: 노드 특성 (pos+vel, 6차원) + 인접 행렬
    출력: 각 드론의 32차원 임베딩 및 충돌 위험도 (0~1)
    """

    def __init__(
        self,
        node_feat_dim: int = NODE_FEAT_DIM,
        hidden_dim: int = HIDDEN_DIM,
    ) -> None:
        super().__init__()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # 2-layer GNN
        self.layer1 = _MessagePassingLayer(node_feat_dim, hidden_dim)
        self.layer2 = _MessagePassingLayer(hidden_dim, hidden_dim)

        # 위험도 예측 헤드
        self.risk_head = nn.Sequential(
            nn.Linear(hidden_dim, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
            nn.Sigmoid(),
        )

        self.to(self.device)

    def forward(
        self,
        node_features: torch.Tensor,
        adj: torch.Tensor,
    ) -> torch.Tensor:
        """GNN 순전파 — 드론 임베딩을 계산한다.

        Args:
            node_features: (N, 6) 드론 특성 (pos + vel)
            adj: (N, N) 인접 행렬

        Returns:
            (N, hidden_dim) 드론 임베딩
        """
        h = self.layer1(node_features, adj)
        h = self.layer2(h, adj)
        return h

    def predict_risk(self, embeddings: torch.Tensor) -> torch.Tensor:
        """임베딩에서 각 드론의 충돌 위험도를 예측한다.

        Args:
            embeddings: (N, hidden_dim) GNN 출력 임베딩

        Returns:
            (N,) 각 드론의 충돌 위험도 (0~1)
        """
        return self.risk_head(embeddings).squeeze(-1)

    def compute_risk(
        self,
        positions: np.ndarray,
        velocities: np.ndarray,
        comm_range: float = DEFAULT_COMM_RANGE,
    ) -> np.ndarray:
        """위치/속도 배열에서 직접 충돌 위험도를 계산하는 편의 메서드.

        Args:
            positions: (N, 3) 위치 배열
            velocities: (N, 3) 속도 배열
            comm_range: 통신 범위 (m)

        Returns:
            (N,) 충돌 위험도 numpy 배열
        """
        # 인접 행렬 생성
        adj_np = build_adjacency(positions, comm_range)

        # 텐서 변환
        features = np.hstack([positions, velocities]).astype(np.float32)
        node_feat = torch.from_numpy(features).to(self.device)
        adj = torch.from_numpy(adj_np).to(self.device)

        # 추론
        self.eval()
        with torch.no_grad():
            embeddings = self.forward(node_feat, adj)
            risk = self.predict_risk(embeddings)

        return risk.cpu().numpy()
