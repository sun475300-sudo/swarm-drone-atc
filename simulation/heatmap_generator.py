"""충돌 위험 히트맵 생성 모듈.

드론 밀도 기반 2D 히트맵을 GPU 가속으로 생성한다.
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

import numpy as np

try:
    import torch

    _HAS_TORCH = True
except ImportError:
    _HAS_TORCH = False


def generate_risk_heatmap(
    drone_states: Sequence[Dict[str, Any]],
    grid_size: int = 50,
    bounds: Tuple[float, float] = (-5000.0, 5000.0),
) -> Dict[str, Any]:
    """드론 밀도 기반 충돌 위험 히트맵을 생성한다.

    Args:
        drone_states: 드론 상태 목록. 각 항목은 ``{"position": (x, y, z)}`` 형태.
        grid_size: 그리드 한 변의 셀 수.
        bounds: 공역 X/Y 축 최소·최대 범위 ``(min, max)``.

    Returns:
        ``{"grid": np.ndarray, "bounds": {"min": float, "max": float}, "max_density": float}``
    """
    lo, hi = float(bounds[0]), float(bounds[1])

    # 드론 위치에서 XY 좌표 추출
    positions = _extract_xy(drone_states)

    if len(positions) == 0:
        empty_grid = np.zeros((grid_size, grid_size), dtype=np.float64)
        return {"grid": empty_grid, "bounds": {"min": lo, "max": hi}, "max_density": 0.0}

    grid = _compute_density(positions, grid_size, lo, hi)
    max_density = float(grid.max())

    return {"grid": grid, "bounds": {"min": lo, "max": hi}, "max_density": max_density}


def _extract_xy(drone_states: Sequence[Dict[str, Any]]) -> np.ndarray:
    """드론 상태에서 (x, y) 좌표 배열을 추출한다."""
    coords: List[Tuple[float, float]] = []
    for state in drone_states:
        pos = state.get("position")
        if pos is not None and len(pos) >= 2:
            coords.append((float(pos[0]), float(pos[1])))
    if not coords:
        return np.empty((0, 2), dtype=np.float64)
    return np.array(coords, dtype=np.float64)


def _compute_density(
    positions: np.ndarray, grid_size: int, lo: float, hi: float
) -> np.ndarray:
    """GPU(torch) 또는 CPU(numpy)로 2D 밀도 그리드를 계산한다."""
    if _HAS_TORCH:
        return _density_torch(positions, grid_size, lo, hi)
    return _density_numpy(positions, grid_size, lo, hi)


def _density_torch(
    positions: np.ndarray, grid_size: int, lo: float, hi: float
) -> np.ndarray:
    """torch.histogramdd 를 사용한 GPU 가속 밀도 계산."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tensor = torch.tensor(positions, dtype=torch.float64, device=device)
    edges = [torch.linspace(lo, hi, grid_size + 1, device=device, dtype=torch.float64)] * 2
    hist = torch.histogramdd(tensor, bins=edges).hist
    return hist.cpu().numpy()


def _density_numpy(
    positions: np.ndarray, grid_size: int, lo: float, hi: float
) -> np.ndarray:
    """numpy 기반 CPU 밀도 계산 (torch 미설치 시 폴백)."""
    edges = np.linspace(lo, hi, grid_size + 1)
    hist, _, _ = np.histogram2d(positions[:, 0], positions[:, 1], bins=[edges, edges])
    return hist
