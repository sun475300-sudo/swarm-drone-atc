"""좌표계 변환 유틸리티"""
from __future__ import annotations
import numpy as np


def ned_to_xyz(ned: np.ndarray) -> np.ndarray:
    """NED → 시각화용 XYZ (X=East, Y=North, Z=Up)"""
    return np.array([ned[1], ned[0], -ned[2]])


def xyz_to_ned(xyz: np.ndarray) -> np.ndarray:
    """XYZ → NED"""
    return np.array([xyz[1], xyz[0], -xyz[2]])


def grid_to_ned(grid_x: float, grid_y: float, alt_m: float, grid_size_m: float = 10.0) -> np.ndarray:
    """격자 좌표 → NED 미터"""
    return np.array([grid_y * grid_size_m, grid_x * grid_size_m, -alt_m])


def ned_to_grid(ned: np.ndarray, grid_size_m: float = 10.0) -> tuple[int, int]:
    """NED → 격자 인덱스"""
    gx = int(ned[1] / grid_size_m)
    gy = int(ned[0] / grid_size_m)
    return gx, gy
