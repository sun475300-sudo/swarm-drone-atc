"""
Voronoi 공역 분할 GPU 가속 유틸리티

드론-셀 할당 및 침입 탐지를 텐서 연산으로 배치 처리.
"""

from __future__ import annotations

import numpy as np

try:
    import torch
    _TORCH = True
except ImportError:
    _TORCH = False


def _select_device() -> "torch.device":
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def gpu_nearest_cell_assignment(
    drone_positions: dict[str, np.ndarray],
    cell_centers: dict[str, np.ndarray],
) -> dict[str, str]:
    """
    GPU 가속 최근접 셀 할당.

    모든 드론과 모든 셀 중심 간 거리를 한 번에 계산하여
    각 드론에 가장 가까운 셀을 할당.

    Returns:
        {drone_id: nearest_cell_id}
    """
    if not _TORCH or not drone_positions or not cell_centers:
        return {}

    device = _select_device()
    dtype = torch.float32

    drone_ids = list(drone_positions.keys())
    cell_ids = list(cell_centers.keys())

    pos = torch.as_tensor(
        np.array([drone_positions[d][:2] for d in drone_ids]),
        dtype=dtype, device=device
    )  # (N, 2)
    centers = torch.as_tensor(
        np.array([cell_centers[c][:2] for c in cell_ids]),
        dtype=dtype, device=device
    )  # (M, 2)

    # (N, M) 거리 행렬
    dists = torch.cdist(pos, centers)  # (N, M)
    nearest_idx = dists.argmin(dim=1)  # (N,)

    return {drone_ids[i]: cell_ids[nearest_idx[i].item()] for i in range(len(drone_ids))}


def gpu_detect_intrusions(
    drone_positions: dict[str, np.ndarray],
    cell_centers: dict[str, np.ndarray],
    cell_owners: dict[str, str],
    threshold_m: float = 100.0,
) -> list[dict]:
    """
    GPU 가속 공역 침입 탐지.

    각 드론이 자기 셀이 아닌 다른 셀 중심에 threshold 이내로 접근하면 침입으로 판단.

    Returns:
        [{drone_id, intruded_cell, distance_m}, ...]
    """
    if not _TORCH or not drone_positions or not cell_centers:
        return []

    device = _select_device()
    dtype = torch.float32

    drone_ids = list(drone_positions.keys())
    cell_ids = list(cell_centers.keys())

    pos = torch.as_tensor(
        np.array([drone_positions[d][:2] for d in drone_ids]),
        dtype=dtype, device=device
    )
    centers = torch.as_tensor(
        np.array([cell_centers[c][:2] for c in cell_ids]),
        dtype=dtype, device=device
    )

    dists = torch.cdist(pos, centers)  # (N, M)

    intrusions = []
    close_pairs = (dists < threshold_m).nonzero(as_tuple=False)

    for pair in close_pairs:
        di, ci = pair[0].item(), pair[1].item()
        did = drone_ids[di]
        cid = cell_ids[ci]
        # 자기 셀이면 무시
        if cell_owners.get(did) == cid:
            continue
        intrusions.append({
            "drone_id": did,
            "intruded_cell": cid,
            "distance_m": dists[di, ci].item(),
        })

    return intrusions
