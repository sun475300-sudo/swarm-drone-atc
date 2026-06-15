"""GENESIS Phase 341 — 목포 해역 해도 기반 NFZ·회랑 배치 검증."""
from __future__ import annotations

from dataclasses import replace

from src.applications.mokpo_harbor import (
    MOKPO_BBOX_LAT,
    MOKPO_BBOX_LON,
    MOKPO_CORRIDORS,
    MOKPO_NFZS,
    WAYPOINTS,
    corridor_length_km,
    corridor_nfz_conflicts,
    harbor_summary,
    point_in_nfz,
)


def test_nfz_polygons_valid_and_within_bbox() -> None:
    """모든 NFZ는 3개 이상 꼭짓점을 갖고 목포 권역 박스 안에 있다."""
    assert len(MOKPO_NFZS) >= 3
    for nfz in MOKPO_NFZS:
        assert len(nfz.vertices) >= 3, nfz.name
        for lat, lon in nfz.vertices:
            assert MOKPO_BBOX_LAT[0] < lat < MOKPO_BBOX_LAT[1], nfz.name
            assert MOKPO_BBOX_LON[0] < lon < MOKPO_BBOX_LON[1], nfz.name


def test_waypoints_within_bbox() -> None:
    """모든 회랑 경유점이 목포 권역 박스 안에 있다."""
    for wp in WAYPOINTS:
        assert MOKPO_BBOX_LAT[0] < wp.lat < MOKPO_BBOX_LAT[1], wp.name
        assert MOKPO_BBOX_LON[0] < wp.lon < MOKPO_BBOX_LON[1], wp.name


def test_point_inside_port_nfz_detected() -> None:
    """본항 부두 중심 좌표는 '목포항 본항 부두' NFZ로 판정된다."""
    nfz = point_in_nfz(34.781, 126.386)
    assert nfz is not None
    assert nfz.name == "목포항 본항 부두"


def test_point_far_outside_returns_none() -> None:
    """서울 좌표는 어떤 목포 NFZ에도 속하지 않는다."""
    assert point_in_nfz(37.5665, 126.9780) is None


def test_corridor_lengths_positive() -> None:
    """모든 회랑의 누적 길이가 양수다."""
    for c in MOKPO_CORRIDORS:
        assert corridor_length_km(c) > 0.0, c.name


def test_designed_corridors_avoid_all_nfzs() -> None:
    """설계된 회랑 경유점은 어떤 NFZ도 통과하지 않는다(안전 배치)."""
    for c in MOKPO_CORRIDORS:
        assert corridor_nfz_conflicts(c) == [], c.name


def test_corridor_through_port_flags_conflict() -> None:
    """본항 부두를 지나도록 경유점을 옮기면 충돌 NFZ가 검출된다."""
    base = MOKPO_CORRIDORS[0]
    bad_wp = replace(base.waypoints[0], lat=34.781, lon=126.386)
    bad = replace(base, waypoints=(bad_wp,) + base.waypoints[1:])
    conflicts = corridor_nfz_conflicts(bad)
    assert any(n.name == "목포항 본항 부두" for n in conflicts)


def test_harbor_summary_shape() -> None:
    """요약은 NFZ·회랑 개수와 총 길이를 포함하며 설계 회랑 충돌은 0이다."""
    s = harbor_summary()
    assert s["nfz_count"] == len(MOKPO_NFZS)
    assert s["corridor_count"] == len(MOKPO_CORRIDORS)
    assert s["total_corridor_km"] > 0.0
    assert s["conflicting_corridors"] == 0
    assert "port" in s["nfz_kinds"]
