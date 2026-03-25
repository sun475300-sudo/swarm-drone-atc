"""
Voronoi Tessellation 기반 동적 공역 분할
드론 수와 위치에 따라 공역을 자동으로 균등 분할

사용 목적:
  - 각 드론에 책임 공역 할당 (분산 제어)
  - 충돌 확률 낮은 구역별 분리 비행
  - 드론 추가/제거 시 실시간 재분할
"""
from __future__ import annotations
import numpy as np
from scipy.spatial import Voronoi, ConvexHull
from dataclasses import dataclass
from typing import Optional


@dataclass
class AirspaceCell:
    """Voronoi 셀 = 드론 1기의 책임 공역"""
    drone_id: str
    center: np.ndarray          # 셀 중심 (= 드론 위치)
    vertices: list[np.ndarray]  # 셀 꼭짓점 (2D 평면 기준)
    area_km2: float
    altitude_band: tuple[float, float]  # (min_alt, max_alt) m


def compute_voronoi_partition(
    drone_positions: dict[str, np.ndarray],
    bounds_m: dict,             # {"x": [-5000, 5000], "y": [-5000, 5000]}
    altitude_bands: Optional[dict[str, tuple[float, float]]] = None,
) -> dict[str, AirspaceCell]:
    """
    2D Voronoi 분할 계산 (고도는 별도 레이어로 처리)

    Args:
        drone_positions: {drone_id: [x, y, z]} (미터)
        bounds_m:        공역 경계 (미터)
        altitude_bands:  {drone_id: (min_alt, max_alt)} - 없으면 균등 분배

    Returns:
        {drone_id: AirspaceCell}
    """
    if not drone_positions:
        return {}
    if len(drone_positions) < 2:
        # 드론이 1기면 전체 공역 할당
        only_id = list(drone_positions.keys())[0]
        area = ((bounds_m["x"][1] - bounds_m["x"][0]) *
                (bounds_m["y"][1] - bounds_m["y"][0])) / 1e6
        return {
            only_id: AirspaceCell(
                drone_id=only_id,
                center=drone_positions[only_id],
                vertices=[],
                area_km2=area,
                altitude_band=(30.0, 120.0)
            )
        }

    drone_ids = list(drone_positions.keys())
    points_2d = np.array([drone_positions[d][:2] for d in drone_ids])

    # 경계 미러링: Voronoi가 유한 셀을 생성하도록
    margin = max(
        bounds_m["x"][1] - bounds_m["x"][0],
        bounds_m["y"][1] - bounds_m["y"][0]
    ) * 2.0
    mirror_offsets = [
        [0, 0], [margin, 0], [-margin, 0],
        [0, margin], [0, -margin],
        [margin, margin], [-margin, -margin],
        [margin, -margin], [-margin, margin],
    ]
    mirrored = np.vstack([points_2d + off for off in mirror_offsets])

    try:
        vor = Voronoi(mirrored)
    except Exception:
        # 점이 collinear인 경우 균등 분할 폴백
        return _uniform_fallback(drone_ids, drone_positions, bounds_m)

    # 고도 밴드 계산
    if altitude_bands is None:
        altitude_bands = _compute_altitude_bands(drone_ids)

    cells = {}
    n = len(drone_ids)

    for i, did in enumerate(drone_ids):
        region_idx = vor.point_region[i]
        region = vor.regions[region_idx]

        # 무한 꼭짓점(-1) 제거 후 클리핑
        if -1 in region or not region:
            vertices = []
        else:
            raw_verts = vor.vertices[region]
            # 경계 내로 클리핑
            clipped = _clip_polygon_to_bounds(raw_verts, bounds_m)
            vertices = [v.tolist() for v in clipped]

        # 면적 계산 (km²)
        area = 0.0
        if len(vertices) >= 3:
            try:
                verts_arr = np.array(vertices)
                hull = ConvexHull(verts_arr)
                area = hull.volume / 1e6  # m² → km²
            except Exception:
                area = 0.0

        cells[did] = AirspaceCell(
            drone_id=did,
            center=drone_positions[did],
            vertices=vertices,
            area_km2=area,
            altitude_band=altitude_bands.get(did, (30.0, 120.0))
        )

    return cells


def _compute_altitude_bands(
    drone_ids: list[str],
    min_alt: float = 30.0,
    max_alt: float = 120.0,
) -> dict[str, tuple[float, float]]:
    """드론 수에 따라 고도 밴드 균등 분배"""
    n = len(drone_ids)
    band_height = (max_alt - min_alt) / max(n, 1)
    bands = {}
    for i, did in enumerate(drone_ids):
        low = min_alt + i * band_height
        high = low + band_height
        bands[did] = (low, high)
    return bands


def _clip_polygon_to_bounds(
    polygon: np.ndarray,
    bounds: dict,
) -> np.ndarray:
    """Sutherland-Hodgman 알고리즘으로 폴리곤 클리핑"""
    xmin, xmax = bounds["x"]
    ymin, ymax = bounds["y"]
    clip_edges = [
        ("x_min", xmin), ("x_max", xmax),
        ("y_min", ymin), ("y_max", ymax),
    ]

    output = list(polygon)

    for edge_type, edge_val in clip_edges:
        if not output:
            break
        input_list = output
        output = []
        for i in range(len(input_list)):
            cur = input_list[i]
            prev = input_list[i - 1]

            if edge_type == "x_min":
                inside = lambda p: p[0] >= edge_val
            elif edge_type == "x_max":
                inside = lambda p: p[0] <= edge_val
            elif edge_type == "y_min":
                inside = lambda p: p[1] >= edge_val
            else:
                inside = lambda p: p[1] <= edge_val

            if inside(cur):
                if not inside(prev):
                    output.append(_intersect(prev, cur, edge_type, edge_val))
                output.append(cur)
            elif inside(prev):
                output.append(_intersect(prev, cur, edge_type, edge_val))

    return np.array(output) if output else polygon


def _intersect(p1: np.ndarray, p2: np.ndarray, edge_type: str, val: float) -> np.ndarray:
    """두 점과 클리핑 경계의 교점"""
    x1, y1 = p1[:2]
    x2, y2 = p2[:2]
    if edge_type in ("x_min", "x_max"):
        if x2 == x1:
            return np.array([val, y1])
        t = (val - x1) / (x2 - x1)
        return np.array([val, y1 + t * (y2 - y1)])
    else:
        if y2 == y1:
            return np.array([x1, val])
        t = (val - y1) / (y2 - y1)
        return np.array([x1 + t * (x2 - x1), val])


def _uniform_fallback(
    drone_ids: list[str],
    drone_positions: dict[str, np.ndarray],
    bounds: dict,
) -> dict[str, AirspaceCell]:
    """Voronoi 실패 시 균등 분할 폴백"""
    n = len(drone_ids)
    cols = int(np.ceil(np.sqrt(n)))
    rows = int(np.ceil(n / cols))
    xw = (bounds["x"][1] - bounds["x"][0]) / cols
    yw = (bounds["y"][1] - bounds["y"][0]) / rows
    area = xw * yw / 1e6

    cells = {}
    for i, did in enumerate(drone_ids):
        col = i % cols
        row = i // cols
        x0 = bounds["x"][0] + col * xw
        y0 = bounds["y"][0] + row * yw
        center = drone_positions[did]
        cells[did] = AirspaceCell(
            drone_id=did,
            center=center,
            vertices=[[x0, y0], [x0 + xw, y0], [x0 + xw, y0 + yw], [x0, y0 + yw]],
            area_km2=area,
            altitude_band=(30.0, 120.0)
        )
    return cells


def is_in_cell(position: np.ndarray, cell: AirspaceCell) -> bool:
    """드론이 자신의 공역 셀 내에 있는지 확인"""
    if not cell.vertices:
        return True
    # 고도 확인
    alt = position[2]
    if not (cell.altitude_band[0] <= alt <= cell.altitude_band[1]):
        return False
    # 2D 포인트-인-폴리곤
    try:
        from matplotlib.path import Path
        path = Path(np.array(cell.vertices))
        return bool(path.contains_point(position[:2]))
    except Exception:
        return True
