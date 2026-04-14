"""
멀티 GPU APF 연산 — DataParallel 기반 2000기+ 드론 처리

단일 GPU의 VRAM/연산 한계를 넘어 다중 GPU에 드론을 분할 배치.
GPU 1개면 자동으로 단일 GPU 모드로 폴백.
"""

from __future__ import annotations

import numpy as np

try:
    import torch
    import torch.nn as nn
    _TORCH = True
except ImportError:
    _TORCH = False

from .apf import APFState, APF_PARAMS


class _APFBatchModule(nn.Module):
    """DataParallel 호환 APF 배치 연산 모듈."""

    def __init__(self, k_att: float, k_rep: float, d0: float, max_force: float):
        super().__init__()
        self.k_att = k_att
        self.k_rep = k_rep
        self.d0 = d0
        self.max_force = max_force

    def forward(self, positions: torch.Tensor, goals: torch.Tensor,
                all_positions: torch.Tensor) -> torch.Tensor:
        """
        Args:
            positions: (batch, 3) — 이 배치의 드론 위치
            goals: (batch, 3) — 이 배치의 목표
            all_positions: (N, 3) — 전체 드론 위치 (척력 계산용)
        Returns:
            forces: (batch, 3)
        """
        batch = positions.shape[0]
        F = torch.zeros_like(positions)

        # 인력
        goal_diff = goals - positions
        goal_dist = torch.linalg.norm(goal_diff, dim=1, keepdim=True).clamp(min=0.1)
        F += self.k_att * goal_diff / goal_dist

        # 척력 (전체 드론 대비)
        diff = positions.unsqueeze(1) - all_positions.unsqueeze(0)  # (batch, N, 3)
        dist = torch.linalg.norm(diff, dim=2).clamp(min=1e-6)       # (batch, N)

        in_range = (dist < self.d0) & (dist > 0.5)
        if in_range.any():
            n_hat = diff / dist.unsqueeze(2)
            mag = self.k_rep * (1.0 / dist - 1.0 / self.d0) / dist ** 2
            mag = mag * in_range.float()
            F += (mag.unsqueeze(2) * n_hat).sum(dim=1)

        # 클리핑
        f_mag = torch.linalg.norm(F, dim=1, keepdim=True)
        clip = f_mag > self.max_force
        F[clip.squeeze()] = F[clip.squeeze()] / f_mag[clip] * self.max_force

        return F


def get_gpu_count() -> int:
    """사용 가능한 GPU 수."""
    if not _TORCH:
        return 0
    return torch.cuda.device_count()


def multi_gpu_batch_compute(
    states: list[APFState],
    goals: dict[str, np.ndarray],
    params: dict | None = None,
) -> dict[str, np.ndarray]:
    """
    멀티 GPU APF 배치 연산.

    GPU 2개 이상이면 DataParallel, 1개면 단일 GPU, 0개면 CPU.
    """
    if not _TORCH or len(states) == 0:
        return {}

    p = params or APF_PARAMS
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    ids = [s.drone_id for s in states]
    n = len(states)

    pos_np = np.array([s.position for s in states])
    positions = torch.as_tensor(pos_np, dtype=torch.float32, device=device)

    goal_np = np.array([goals.get(s.drone_id, s.position) for s in states])
    goal_tensor = torch.as_tensor(goal_np, dtype=torch.float32, device=device)

    module = _APFBatchModule(
        k_att=p["k_att"], k_rep=p["k_rep_drone"],
        d0=p["d0_drone"], max_force=p["max_force"],
    ).to(device)

    # 멀티 GPU (2개 이상)
    n_gpus = torch.cuda.device_count()
    if n_gpus > 1:
        module = nn.DataParallel(module)

    with torch.no_grad():
        forces = module(positions, goal_tensor, positions)

    forces_np = forces.cpu().numpy()
    return {ids[i]: forces_np[i] for i in range(n)}
