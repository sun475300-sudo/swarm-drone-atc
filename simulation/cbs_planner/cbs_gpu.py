"""
CBS 충돌 탐지 GPU 가속 — PyTorch 텐서 기반

detect_conflict의 O(N²×T) 이중 루프를 텐서 연산으로 일괄 처리.
"""

from __future__ import annotations

import numpy as np

try:
    import torch
    _TORCH = True
except ImportError:
    _TORCH = False

from .cbs import Conflict, GridNode


def _select_device() -> "torch.device":
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def gpu_detect_conflict(paths: dict[str, list[GridNode]]) -> Conflict | None:
    """
    GPU 가속 충돌 탐지.

    모든 드론 경로를 (N, T, 3) 텐서로 변환 후,
    모든 쌍의 노드 일치를 한 번에 비교.
    """
    if not _TORCH or not paths:
        return None

    drone_ids = list(paths.keys())
    n = len(drone_ids)
    if n < 2:
        return None

    max_t = max(len(p) for p in paths.values())
    device = _select_device()

    # (N, T, 3) 텐서 구성 — 경로 끝은 마지막 노드로 패딩
    path_tensor = torch.zeros((n, max_t, 3), dtype=torch.int32, device=device)
    for i, did in enumerate(drone_ids):
        p = paths[did]
        for t in range(max_t):
            node = p[min(t, len(p) - 1)]
            path_tensor[i, t, 0] = node.x
            path_tensor[i, t, 1] = node.y
            path_tensor[i, t, 2] = node.z

    # === 정점 충돌 탐지 ===
    # (N, N, T) — 모든 쌍, 모든 시간에서 노드 일치 여부
    # path_tensor[i, t] == path_tensor[j, t] → 3축 모두 같으면 충돌
    p_i = path_tensor.unsqueeze(1)  # (N, 1, T, 3)
    p_j = path_tensor.unsqueeze(0)  # (1, N, T, 3)
    vertex_match = (p_i == p_j).all(dim=3)  # (N, N, T)

    # 자기 자신 마스킹 + 상삼각만
    mask = torch.triu(torch.ones(n, n, dtype=torch.bool, device=device), diagonal=1)
    vertex_match = vertex_match & mask.unsqueeze(2)

    # 첫 번째 충돌 찾기
    if vertex_match.any():
        # flatten 후 argmin으로 가장 이른 충돌
        # 시간 우선으로 찾기: (T, N, N)으로 전치
        vm_t_first = vertex_match.permute(2, 0, 1)  # (T, N, N)
        for t in range(max_t):
            if vm_t_first[t].any():
                idx = vm_t_first[t].nonzero(as_tuple=False)[0]
                i, j = idx[0].item(), idx[1].item()
                node = paths[drone_ids[i]][min(t, len(paths[drone_ids[i]]) - 1)]
                return Conflict(drone_ids[i], drone_ids[j], node, t)

    # === 에지 충돌 (스왑) 탐지 ===
    if max_t > 1:
        # path_tensor[i, t] == path_tensor[j, t-1] AND path_tensor[j, t] == path_tensor[i, t-1]
        curr = path_tensor[:, 1:, :]   # (N, T-1, 3)
        prev = path_tensor[:, :-1, :]  # (N, T-1, 3)

        curr_i = curr.unsqueeze(1)     # (N, 1, T-1, 3)
        prev_j = prev.unsqueeze(0)     # (1, N, T-1, 3)
        curr_j = curr.unsqueeze(0)     # (1, N, T-1, 3)
        prev_i = prev.unsqueeze(1)     # (N, 1, T-1, 3)

        swap_match = (curr_i == prev_j).all(dim=3) & (curr_j == prev_i).all(dim=3)  # (N, N, T-1)
        swap_match = swap_match & mask.unsqueeze(2)

        if swap_match.any():
            sm_t = swap_match.permute(2, 0, 1)
            for t in range(max_t - 1):
                if sm_t[t].any():
                    idx = sm_t[t].nonzero(as_tuple=False)[0]
                    i, j = idx[0].item(), idx[1].item()
                    actual_t = t + 1
                    node = paths[drone_ids[i]][min(actual_t, len(paths[drone_ids[i]]) - 1)]
                    return Conflict(drone_ids[i], drone_ids[j], node, actual_t)

    return None
