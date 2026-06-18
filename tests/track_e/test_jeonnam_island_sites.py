"""GENESIS Phase 342 — 전남 도서(신안·완도) 의료 배송 거점 DB 검증."""
from __future__ import annotations

from src.applications.jeonnam_island_sites import (
    BASE_HOSPITALS,
    ISLAND_SITES,
    delivery_request_for,
    nearest_base,
    route_eta_table,
)
from src.applications.medical_delivery import Urgency


def test_sites_cover_both_counties() -> None:
    """신안군·완도군 거점이 모두 포함된다."""
    counties = {s.county for s in ISLAND_SITES}
    assert counties == {"신안군", "완도군"}


def test_coordinates_within_jeonnam_bbox() -> None:
    """모든 거점이 전남 도서 권역 위경도 박스 안에 있다."""
    for s in ISLAND_SITES:
        assert 33.9 < s.lat < 35.0, s.name
        assert 125.0 < s.lon < 127.0, s.name


def test_wando_site_picks_wando_base() -> None:
    """완도군 도서는 완도대성병원이 더 가깝다."""
    wando = next(s for s in ISLAND_SITES if s.name == "청산도")
    base, dist = nearest_base(wando)
    assert base.name == "완도대성병원"
    assert dist > 0


def test_sinan_site_picks_mokpo_base() -> None:
    """신안군 흑산도는 목포한국병원이 더 가깝다."""
    heuksan = next(s for s in ISLAND_SITES if s.name == "흑산도")
    base, _ = nearest_base(heuksan)
    assert base.name == "목포한국병원"


def test_delivery_request_targets_site() -> None:
    """생성된 요청의 목적지가 거점 좌표와 일치한다."""
    site = ISLAND_SITES[0]
    req = delivery_request_for(site, "epi_pen", Urgency.LIFE_THREATENING, 1000.0)
    assert req.destination_lat == site.lat
    assert req.destination_lon == site.lon
    assert site.name in req.request_id


def test_route_table_covers_all_sites() -> None:
    """ETA 표가 모든 거점을 포함하고 거리·ETA가 양수다."""
    table = route_eta_table()
    assert set(table.keys()) == {s.name for s in ISLAND_SITES}
    for row in table.values():
        assert row["distance_km"] > 0
        assert row["eta_min"] > 5.0   # 이착륙 5분 마진 초과
        assert row["base"] in {b.name for b in BASE_HOSPITALS}


def test_remote_island_misses_strict_sla() -> None:
    """원거리 도서(홍도)는 생명위급 10분 SLA를 60km/h로는 충족 못 한다."""
    table = route_eta_table(urgency=Urgency.LIFE_THREATENING)
    assert table["홍도"]["meets_sla"] is False
