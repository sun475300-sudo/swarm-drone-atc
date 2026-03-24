"""지리/좌표 수학 유틸리티 (하버사인, NED 변환 등)"""
from __future__ import annotations
import numpy as np

EARTH_RADIUS_M = 6_371_000.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """두 WGS84 좌표 간 지구 표면 거리 (m)"""
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlam = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlam / 2) ** 2
    return 2 * EARTH_RADIUS_M * np.arcsin(np.sqrt(a))


def lla_to_ned(
    lat: float, lon: float, alt: float,
    ref_lat: float, ref_lon: float, ref_alt: float,
) -> np.ndarray:
    """WGS84 LLA → NED (북-동-하) 좌표 (m)"""
    dlat = np.radians(lat - ref_lat)
    dlon = np.radians(lon - ref_lon)
    north = dlat * EARTH_RADIUS_M
    east = dlon * EARTH_RADIUS_M * np.cos(np.radians(ref_lat))
    down = -(alt - ref_alt)
    return np.array([north, east, down])


def ned_to_lla(
    ned: np.ndarray,
    ref_lat: float, ref_lon: float, ref_alt: float,
) -> tuple[float, float, float]:
    """NED → WGS84 LLA"""
    lat = ref_lat + np.degrees(ned[0] / EARTH_RADIUS_M)
    lon = ref_lon + np.degrees(ned[1] / (EARTH_RADIUS_M * np.cos(np.radians(ref_lat))))
    alt = ref_alt - ned[2]
    return lat, lon, alt


def bearing(pos_from: np.ndarray, pos_to: np.ndarray) -> float:
    """2D NED 좌표 기반 방위각 (도, 0=북)"""
    dx = pos_to[1] - pos_from[1]  # East
    dy = pos_to[0] - pos_from[0]  # North
    return float(np.degrees(np.arctan2(dx, dy)) % 360)


def distance_3d(a: np.ndarray, b: np.ndarray) -> float:
    """3D 유클리드 거리 (m)"""
    return float(np.linalg.norm(a - b))


def closest_approach(
    pos_a: np.ndarray, vel_a: np.ndarray,
    pos_b: np.ndarray, vel_b: np.ndarray,
    dt: float = 0.1,
    lookahead_s: float = 90.0,
) -> tuple[float, float]:
    """
    최근접 점 거리 및 발생 시각 예측

    Returns:
        (min_distance_m, time_to_cpa_s)
    """
    rel_pos = pos_a - pos_b
    rel_vel = vel_a - vel_b

    rel_speed_sq = np.dot(rel_vel, rel_vel)
    if rel_speed_sq < 1e-10:
        return float(np.linalg.norm(rel_pos)), 0.0

    t_cpa = -np.dot(rel_pos, rel_vel) / rel_speed_sq
    t_cpa = np.clip(t_cpa, 0.0, lookahead_s)

    cpa_pos = rel_pos + rel_vel * t_cpa
    return float(np.linalg.norm(cpa_pos)), float(t_cpa)
