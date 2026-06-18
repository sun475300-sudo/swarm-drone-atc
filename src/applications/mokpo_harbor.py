"""GENESIS Phase 341: 목포 해역 실 좌표계 임포트 — 해도 기반 NFZ·회랑 배치.

P747 `docs/track_f/p747_marine.md`(해수부 항만 시범)·Phase 342
`jeonnam_island_sites.py`(신안·완도 의료 배송)의 실증 거점에 **목포항 해역의
비행금지구역(NFZ)·항로 회랑(corridor)** 좌표를 입혀, 실증 배치 시 충돌 없는
운항 회랑을 산출한다.

좌표 정확도 안내(maturity honesty):
    아래 좌표는 공개 지도 기준 **항만 지형 근사값**이며 실측(해도·RTK 측량)
    값이 아니다. 실증 배치 전 국립해양조사원 해도·정밀 측량으로 갱신해야 한다.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.applications.medical_delivery import haversine_km

# 목포항 권역 위경도 박스 (근사) — 좌표 검증용 경계
MOKPO_BBOX_LAT = (34.70, 34.82)
MOKPO_BBOX_LON = (126.30, 126.42)


@dataclass(frozen=True)
class HarborNFZ:
    """해도 기반 비행금지구역 (근사 폴리곤)."""

    name: str
    kind: str  # port / bridge / terrain / anchorage
    vertices: tuple[tuple[float, float], ...]  # (lat, lon) 시계/반시계 무관


@dataclass(frozen=True)
class Waypoint:
    """회랑 경유점 (근사 좌표)."""

    name: str
    lat: float
    lon: float


@dataclass(frozen=True)
class Corridor:
    """항로 회랑 — 순서 있는 경유점 + 폭(m)."""

    name: str
    waypoints: tuple[Waypoint, ...]
    width_m: float


# 해도 기반 NFZ — 항만 부두·대교·지형·정박지 (공개 지도 기준 근사)
MOKPO_NFZS: tuple[HarborNFZ, ...] = (
    HarborNFZ(
        "목포항 본항 부두", "port",
        ((34.776, 126.380), (34.776, 126.392),
         (34.786, 126.392), (34.786, 126.380)),
    ),
    HarborNFZ(
        "목포대교", "bridge",
        ((34.775, 126.340), (34.775, 126.360),
         (34.790, 126.360), (34.790, 126.340)),
    ),
    HarborNFZ(
        "유달산·삼학도 지형", "terrain",
        ((34.782, 126.372), (34.782, 126.384),
         (34.792, 126.384), (34.792, 126.372)),
    ),
    HarborNFZ(
        "남항 정박지", "anchorage",
        ((34.752, 126.366), (34.752, 126.378),
         (34.762, 126.378), (34.762, 126.366)),
    ),
)

# 회랑 경유점 — 항만 진입·도서 연계·의료 배송 거점
WAYPOINTS: tuple[Waypoint, ...] = (
    Waypoint("북항 진입점", 34.802, 126.358),
    Waypoint("고하도 관문", 34.768, 126.330),
    Waypoint("남측 진입점", 34.745, 126.388),
    Waypoint("신안 방면 관문", 34.760, 126.305),
    Waypoint("목포한국병원 헬리포트", 34.7936, 126.3886),
)


def _wp(name: str) -> Waypoint:
    return next(w for w in WAYPOINTS if w.name == name)


# 실증 운항 회랑 — NFZ를 우회하도록 배치
MOKPO_CORRIDORS: tuple[Corridor, ...] = (
    Corridor("항만 남측 진입 회랑",
             (_wp("남측 진입점"), _wp("북항 진입점")), 200.0),
    Corridor("신안 도서 연계 회랑",
             (_wp("북항 진입점"), _wp("고하도 관문"), _wp("신안 방면 관문")), 250.0),
    Corridor("의료 배송 출발 회랑",
             (_wp("목포한국병원 헬리포트"), _wp("신안 방면 관문")), 150.0),
)


def _point_in_polygon(lat: float, lon: float,
                      vertices: tuple[tuple[float, float], ...]) -> bool:
    """레이 캐스팅 — (lat, lon) 폴리곤 내부 판정."""
    inside = False
    n = len(vertices)
    j = n - 1
    for i in range(n):
        yi, xi = vertices[i]
        yj, xj = vertices[j]
        if ((yi > lat) != (yj > lat)) and (
            lon < (xj - xi) * (lat - yi) / (yj - yi) + xi
        ):
            inside = not inside
        j = i
    return inside


def point_in_nfz(lat: float, lon: float) -> HarborNFZ | None:
    """좌표가 포함된 첫 NFZ를 반환(없으면 None)."""
    for nfz in MOKPO_NFZS:
        if _point_in_polygon(lat, lon, nfz.vertices):
            return nfz
    return None


def corridor_length_km(corridor: Corridor) -> float:
    """회랑 경유점 누적 거리(km)."""
    total = 0.0
    pts = corridor.waypoints
    for a, b in zip(pts, pts[1:]):
        total += haversine_km(a.lat, a.lon, b.lat, b.lon)
    return total


def corridor_nfz_conflicts(corridor: Corridor) -> list[HarborNFZ]:
    """회랑 경유점이 통과하는 NFZ 목록(비면 충돌 없음)."""
    conflicts: list[HarborNFZ] = []
    for wp in corridor.waypoints:
        nfz = point_in_nfz(wp.lat, wp.lon)
        if nfz is not None and nfz not in conflicts:
            conflicts.append(nfz)
    return conflicts


def harbor_summary() -> dict[str, object]:
    """NFZ·회랑 요약(개수·종류·총 회랑 길이·충돌 회랑 수)."""
    total_km = sum(corridor_length_km(c) for c in MOKPO_CORRIDORS)
    conflicting = sum(1 for c in MOKPO_CORRIDORS if corridor_nfz_conflicts(c))
    return {
        "nfz_count": len(MOKPO_NFZS),
        "nfz_kinds": sorted({n.kind for n in MOKPO_NFZS}),
        "corridor_count": len(MOKPO_CORRIDORS),
        "total_corridor_km": round(total_km, 2),
        "conflicting_corridors": conflicting,
    }
