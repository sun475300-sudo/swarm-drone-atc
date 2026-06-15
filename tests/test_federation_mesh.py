"""ODYSSEY Phase 432 — 메시 연합 토폴로지 + 멀티홉 전파 단위 테스트.

외부 의존성 0(순수 결정적). Phase 421 디스커버리 위에서 동작한다.
"""

from __future__ import annotations

import pytest

from simulation.federation_discovery import FederationDiscoveryService, Volume4D
from simulation.federation_mesh import FederationMesh


def _tile(x_min: float, x_max: float) -> Volume4D:
    """전 고도·전 시간 창을 덮고 x축으로만 구분되는 타일 볼륨."""
    return Volume4D(x_min, x_max, 0, 1000, 0, 120, 0, 600)


def _line_service() -> FederationDiscoveryService:
    """x축으로 맞닿은 세 타일: WEST[0,1000)·MID[1000,2000)·EAST[2000,3000)."""
    svc = FederationDiscoveryService(cell_size_m=500.0)
    svc.register("WEST", _tile(0, 1000))
    svc.register("MID", _tile(1000, 2000))
    svc.register("EAST", _tile(2000, 3000))
    return svc


# --- 인접 그래프 구성 -------------------------------------------------------


def test_adjacent_tiles_are_neighbors():
    mesh = FederationMesh(_line_service())
    assert mesh.neighbors("WEST") == ("MID",)
    assert mesh.neighbors("MID") == ("EAST", "WEST")
    assert mesh.neighbors("EAST") == ("MID",)


def test_distant_tiles_are_not_neighbors():
    mesh = FederationMesh(_line_service())
    assert "EAST" not in mesh.neighbors("WEST")


def test_overlapping_volumes_are_neighbors():
    svc = FederationDiscoveryService()
    svc.register("A", Volume4D(0, 1200, 0, 1000, 0, 120, 0, 600))
    svc.register("B", Volume4D(1000, 2000, 0, 1000, 0, 120, 0, 600))
    mesh = FederationMesh(svc)
    assert mesh.neighbors("A") == ("B",)


def test_vertical_separation_breaks_adjacency():
    """수평으로 맞닿아도 고도(z)가 겹치지 않으면 이웃이 아니다."""
    svc = FederationDiscoveryService()
    svc.register("LOW", Volume4D(0, 1000, 0, 1000, 0, 60, 0, 600))
    svc.register("HIGH", Volume4D(1000, 2000, 0, 1000, 60, 120, 0, 600))
    mesh = FederationMesh(svc)
    assert mesh.neighbors("LOW") == ()
    assert mesh.neighbors("HIGH") == ()


def test_time_window_disjoint_breaks_adjacency():
    """수평으로 맞닿아도 시간 창이 겹치지 않으면 이웃이 아니다."""
    svc = FederationDiscoveryService()
    svc.register("MORNING", Volume4D(0, 1000, 0, 1000, 0, 120, 0, 300))
    svc.register("EVENING", Volume4D(1000, 2000, 0, 1000, 0, 120, 300, 600))
    mesh = FederationMesh(svc)
    assert mesh.neighbors("MORNING") == ()


def test_adjacency_is_symmetric_and_sorted():
    mesh = FederationMesh(_line_service())
    adj = mesh.adjacency()
    for node, nbrs in adj.items():
        assert list(nbrs) == sorted(nbrs)
        for nb in nbrs:
            assert node in adj[nb]


def test_tolerance_zero_excludes_touching_tiles():
    """허용오차 0이면 정확히 맞닿은(겹치지 않는) 타일은 이웃이 아니다."""
    mesh = FederationMesh(_line_service(), border_tolerance_m=0.0)
    assert mesh.neighbors("WEST") == ()
    assert mesh.neighbors("MID") == ()
    assert mesh.neighbors("EAST") == ()


def test_gap_exactly_tolerance_is_not_neighbor():
    """간격이 정확히 허용오차와 같으면 이웃이 아니다 (엄격 부등식 = gap < tol)."""
    svc = FederationDiscoveryService()
    svc.register("A", _tile(0, 1000))
    svc.register("B", _tile(2000, 3000))  # x 간격 = 1000
    mesh = FederationMesh(svc, border_tolerance_m=1000.0)
    assert mesh.neighbors("A") == ()
    # 간격(1000)보다 큰 허용오차면 이웃이 된다.
    near = FederationMesh(svc, border_tolerance_m=1000.001)
    assert near.neighbors("A") == ("B",)


def test_negative_tolerance_rejected():
    with pytest.raises(ValueError):
        FederationMesh(_line_service(), border_tolerance_m=-1.0)


# --- 연결성 / 연결 요소 -----------------------------------------------------


def test_line_mesh_is_connected():
    mesh = FederationMesh(_line_service())
    assert mesh.is_connected() is True
    assert mesh.components() == (("EAST", "MID", "WEST"),)


def test_isolated_instance_splits_components():
    svc = _line_service()
    svc.register("ISLAND", _tile(10000, 11000))
    mesh = FederationMesh(svc)
    assert mesh.is_connected() is False
    assert mesh.components() == (("EAST", "MID", "WEST"), ("ISLAND",))


def test_empty_and_single_are_trivially_connected():
    empty = FederationMesh(FederationDiscoveryService())
    assert empty.is_connected() is True
    assert empty.components() == ()
    svc = FederationDiscoveryService()
    svc.register("SOLO", _tile(0, 1000))
    single = FederationMesh(svc)
    assert single.is_connected() is True


# --- 최단 경로 -------------------------------------------------------------


def test_shortest_path_multi_hop():
    mesh = FederationMesh(_line_service())
    assert mesh.shortest_path("WEST", "EAST") == ("WEST", "MID", "EAST")


def test_shortest_path_same_node():
    mesh = FederationMesh(_line_service())
    assert mesh.shortest_path("MID", "MID") == ("MID",)


def _diamond_service() -> FederationDiscoveryService:
    """다이아몬드 토폴로지: A-B·A-C·B-D·C-D, A·D 는 비인접 (A→D 동률 2경로).

    좌(A)·중상(B)·중하(C)·우(D) 배치. A·D 는 x 간격 1000 으로 비인접이라
    A→D 최단 경로는 반드시 B 또는 C 를 경유한다(동률 2경로).
    """
    svc = FederationDiscoveryService()
    svc.register("A", Volume4D(0, 1000, 0, 2000, 0, 120, 0, 600))  # 좌측 기둥
    svc.register("B", Volume4D(1000, 2000, 1000, 2000, 0, 120, 0, 600))  # 중상
    svc.register("C", Volume4D(1000, 2000, 0, 1000, 0, 120, 0, 600))  # 중하
    svc.register("D", Volume4D(2000, 3000, 0, 2000, 0, 120, 0, 600))  # 우측 기둥
    return svc


def test_shortest_path_tie_break_prefers_sorted_neighbor():
    """동률 경로(A→B→D vs A→C→D)는 정렬 이웃(B<C)을 우선한다."""
    mesh = FederationMesh(_diamond_service())
    assert mesh.neighbors("A") == ("B", "C")
    assert mesh.shortest_path("A", "D") == ("A", "B", "D")


def test_relay_table_diamond_first_hop_deterministic():
    """다이아몬드에서 D 로의 다음 홉은 결정적으로 B (정렬 이웃 우선)."""
    mesh = FederationMesh(_diamond_service())
    assert mesh.relay_table("A")["D"] == "B"


def test_shortest_path_unreachable_returns_empty():
    svc = _line_service()
    svc.register("ISLAND", _tile(10000, 11000))
    mesh = FederationMesh(svc)
    assert mesh.shortest_path("WEST", "ISLAND") == ()


def test_shortest_path_unknown_node_raises():
    mesh = FederationMesh(_line_service())
    with pytest.raises(KeyError):
        mesh.shortest_path("WEST", "GHOST")


# --- 멀티홉 전파 (Phase 425 일반화) ----------------------------------------


def test_propagate_hop_counts():
    mesh = FederationMesh(_line_service())
    assert mesh.propagate("WEST") == {"WEST": 0, "MID": 1, "EAST": 2}


def test_propagate_ttl_limits_reach():
    mesh = FederationMesh(_line_service())
    assert mesh.propagate("WEST", ttl=1) == {"WEST": 0, "MID": 1}


def test_propagate_ttl_zero_only_origin():
    mesh = FederationMesh(_line_service())
    assert mesh.propagate("WEST", ttl=0) == {"WEST": 0}


def test_propagate_negative_ttl_rejected():
    mesh = FederationMesh(_line_service())
    with pytest.raises(ValueError):
        mesh.propagate("WEST", ttl=-1)


# --- 중계 포워딩 테이블 -----------------------------------------------------


def test_relay_table_next_hops():
    mesh = FederationMesh(_line_service())
    # WEST 에서 EAST 로 가려면 첫 홉은 MID, MID 도 직접 이웃이므로 MID.
    assert mesh.relay_table("WEST") == {"MID": "MID", "EAST": "MID"}


def test_relay_table_branches_from_center():
    mesh = FederationMesh(_line_service())
    assert mesh.relay_table("MID") == {"EAST": "EAST", "WEST": "WEST"}


def test_relay_table_ttl_limits():
    mesh = FederationMesh(_line_service())
    assert mesh.relay_table("WEST", ttl=1) == {"MID": "MID"}


def test_relay_table_ttl_zero_is_empty():
    """ttl=0 이면 origin 제외 후 도달 목적지가 없어 빈 테이블."""
    mesh = FederationMesh(_line_service())
    assert mesh.relay_table("WEST", ttl=0) == {}


def test_relay_table_negative_ttl_rejected():
    mesh = FederationMesh(_line_service())
    with pytest.raises(ValueError):
        mesh.relay_table("WEST", ttl=-1)


# --- 결정성 / 재구성 / 요약 ------------------------------------------------


def test_rebuild_reflects_new_registration():
    svc = FederationDiscoveryService()
    svc.register("A", _tile(0, 1000))
    mesh = FederationMesh(svc)
    assert mesh.neighbors("A") == ()
    svc.register("B", _tile(1000, 2000))
    mesh.rebuild()
    assert mesh.neighbors("A") == ("B",)


def test_summary_counts():
    mesh = FederationMesh(_line_service())
    assert mesh.summary() == {"instances": 3, "edges": 2, "components": 1}


def test_deterministic_across_construction():
    a = FederationMesh(_line_service()).adjacency()
    b = FederationMesh(_line_service()).adjacency()
    assert a == b
