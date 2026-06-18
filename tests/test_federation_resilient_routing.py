"""ODYSSEY Phase 435 — 메시 복원력 라우팅 단위 테스트.

외부 의존성 0(순수 결정적). Phase 432 `FederationMesh` 위에서 동작한다.
토폴로지는 Phase 432와 동일한 king-move 타일 인접으로 기하학적으로 구성한다
(맞닿은 면·모서리 = 이웃). 따라서 실제 메시 경로/인접과 통합 검증된다.
"""

from __future__ import annotations

import pytest

from simulation.federation_discovery import FederationDiscoveryService, Volume4D
from simulation.federation_mesh import FederationMesh
from simulation.federation_resilient_routing import FederationResilientRouting


def _cell(cx: int, cy: int) -> Volume4D:
    """격자 좌표 (cx, cy)의 1000 m 타일 (전 고도·전 시간)."""
    return Volume4D(cx * 1000, cx * 1000 + 1000, cy * 1000, cy * 1000 + 1000, 0, 120, 0, 600)


def _mesh(cells: dict[str, tuple[int, int]]) -> FederationMesh:
    svc = FederationDiscoveryService(cell_size_m=500.0)
    for name, (cx, cy) in cells.items():
        svc.register(name, _cell(cx, cy))
    return FederationMesh(svc)


def _line() -> FederationResilientRouting:
    """WEST-MID-EAST 일직선 (MID가 유일한 연결 고리)."""
    return FederationResilientRouting(_mesh({"WEST": (0, 0), "MID": (1, 0), "EAST": (2, 0)}))


def _tadpole() -> FederationResilientRouting:
    """삼각형 A-B-C + 꼬리 B-T.

    A=(0,0) B=(1,0) C=(0,1) 는 서로 king-move 인접한 3-사이클,
    T=(2,0) 은 B에만 붙는 꼬리. → B는 절단점, (B,T)는 브리지.
    """
    return FederationResilientRouting(
        _mesh({"A": (0, 0), "B": (1, 0), "C": (0, 1), "T": (2, 0)})
    )


def _grid2x2() -> FederationResilientRouting:
    """2x2 격자 — king-move로 네 타일이 완전 그래프(K4)."""
    return FederationResilientRouting(
        _mesh({"NW": (0, 1), "NE": (1, 1), "SW": (0, 0), "SE": (1, 0)})
    )


# --- 토폴로지 전제 검증 (메시 인접이 의도대로 구성됐는지) -------------------


def test_tadpole_topology_is_as_designed():
    mesh = _mesh({"A": (0, 0), "B": (1, 0), "C": (0, 1), "T": (2, 0)})
    assert mesh.neighbors("A") == ("B", "C")
    assert mesh.neighbors("B") == ("A", "C", "T")
    assert mesh.neighbors("C") == ("A", "B")
    assert mesh.neighbors("T") == ("B",)


def test_grid2x2_is_complete_graph():
    rr = _grid2x2()
    for node in rr.instances():
        assert len(_grid2x2_neighbors(node)) == 3


def _grid2x2_neighbors(node: str) -> tuple[str, ...]:
    mesh = _mesh({"NW": (0, 1), "NE": (1, 1), "SW": (0, 0), "SE": (1, 0)})
    return mesh.neighbors(node)


# --- 절단점 ----------------------------------------------------------------


def test_line_articulation_is_middle():
    assert _line().articulation_points() == ("MID",)


def test_tadpole_articulation_is_b():
    assert _tadpole().articulation_points() == ("B",)


def test_cycle_has_no_articulation_points():
    # 그리드 K4 / 삼각형은 사이클이라 단일 장애점이 없다.
    assert _grid2x2().articulation_points() == ()


def test_single_instance_has_no_articulation():
    rr = FederationResilientRouting(_mesh({"SOLO": (0, 0)}))
    assert rr.articulation_points() == ()


def test_empty_mesh_has_no_articulation():
    rr = FederationResilientRouting(_mesh({}))
    assert rr.articulation_points() == ()
    assert rr.bridges() == ()
    assert rr.instances() == ()


# --- 브리지 ----------------------------------------------------------------


def test_line_bridges_are_both_links():
    assert _line().bridges() == (("EAST", "MID"), ("MID", "WEST"))


def test_tadpole_bridge_is_the_tail():
    # 삼각형 간선은 브리지가 아니고, 꼬리 링크 (B,T)만 브리지.
    assert _tadpole().bridges() == (("B", "T"),)


def test_cycle_has_no_bridges():
    assert _grid2x2().bridges() == ()


def test_two_node_link_is_a_bridge():
    # 단일 링크 A-B: 유일한 간선이 브리지(루트-자식 브리지 경로 단독 검증).
    rr = FederationResilientRouting(_mesh({"A": (0, 0), "B": (1, 0)}))
    assert rr.bridges() == (("A", "B"),)
    assert rr.articulation_points() == ()


def test_bridges_are_sorted_pairs():
    for a, b in _tadpole().bridges():
        assert a <= b


# --- is_single_point_of_failure -------------------------------------------


def test_spof_true_for_articulation():
    assert _tadpole().is_single_point_of_failure("B") is True


def test_spof_false_for_leaf():
    assert _tadpole().is_single_point_of_failure("T") is False


def test_spof_unknown_raises():
    with pytest.raises(KeyError):
        _tadpole().is_single_point_of_failure("ZZZ")


# --- 백업 경로 -------------------------------------------------------------


def test_line_has_no_backup_path():
    # WEST-MID-EAST: MID가 죽으면 우회 불가 → 백업 없음.
    rr = _line()
    assert rr.backup_path("WEST", "EAST") == ()
    assert rr.has_backup_path("WEST", "EAST") is False


def test_cycle_has_backup_path():
    # K4: 어떤 쌍이든 내부 노드·간선 분리 백업 존재.
    rr = _grid2x2()
    backup = rr.backup_path("NW", "SE")
    assert backup and backup[0] == "NW" and backup[-1] == "SE"
    assert rr.has_backup_path("NW", "SE") is True


def test_backup_path_shares_no_interior_node():
    rr = _grid2x2()
    primary = _grid2x2_mesh().shortest_path("NW", "SE")
    backup = rr.backup_path("NW", "SE")
    primary_interior = set(primary[1:-1])
    backup_interior = set(backup[1:-1])
    assert primary_interior.isdisjoint(backup_interior)


def test_backup_path_shares_no_edge_with_primary():
    # 백업 경로는 주 경로와 간선도 공유하지 않는다(엔드포인트만 공유).
    rr = _grid2x2()
    primary = _grid2x2_mesh().shortest_path("NW", "SE")
    backup = rr.backup_path("NW", "SE")
    primary_edges = {frozenset((primary[i], primary[i + 1])) for i in range(len(primary) - 1)}
    backup_edges = {frozenset((backup[i], backup[i + 1])) for i in range(len(backup) - 1)}
    assert primary_edges.isdisjoint(backup_edges)


def _grid2x2_mesh() -> FederationMesh:
    return _mesh({"NW": (0, 1), "NE": (1, 1), "SW": (0, 0), "SE": (1, 0)})


def test_tadpole_backup_for_triangle_edge():
    # A-C는 직접 간선이지만 삼각형이라 A-B-C 우회 존재.
    rr = _tadpole()
    backup = rr.backup_path("A", "C")
    assert backup[0] == "A" and backup[-1] == "C"
    assert "B" in backup  # 직접 간선 A-C를 우회


def test_backup_none_when_tail_needs_articulation():
    # A→T 는 반드시 B를 거쳐야 함 → 백업 불가.
    assert _tadpole().backup_path("A", "T") == ()


def test_backup_path_same_src_dst_is_empty():
    assert _line().backup_path("MID", "MID") == ()


def test_backup_path_unknown_raises():
    with pytest.raises(KeyError):
        _line().backup_path("WEST", "ZZZ")


# --- 생존 도달성 -----------------------------------------------------------


def test_surviving_reach_no_failure():
    reach = _line().surviving_reach("WEST", frozenset())
    assert reach == {"WEST": 0, "MID": 1, "EAST": 2}


def test_surviving_reach_with_articulation_failed():
    # MID 장애 → WEST는 자기 자신만 도달.
    reach = _line().surviving_reach("WEST", {"MID"})
    assert reach == {"WEST": 0}


def test_surviving_reach_tadpole_loses_tail():
    # B 장애 → A는 C까지만, 꼬리 T는 단절.
    reach = _tadpole().surviving_reach("A", {"B"})
    assert reach == {"A": 0, "C": 1}


def test_surviving_reach_origin_failed_is_empty():
    assert _line().surviving_reach("MID", {"MID"}) == {}


def test_surviving_reach_unknown_origin_raises():
    with pytest.raises(KeyError):
        _line().surviving_reach("ZZZ", set())


# --- 요약 / 결정성 ---------------------------------------------------------


def test_summary_counts():
    assert _tadpole().summary() == {
        "instances": 4,
        "articulation_points": 1,
        "bridges": 1,
    }


def test_deterministic_repeat():
    rr = _tadpole()
    first = (rr.articulation_points(), rr.bridges(), rr.backup_path("A", "C"))
    second = (rr.articulation_points(), rr.bridges(), rr.backup_path("A", "C"))
    assert first == second


def test_analyzer_independent_of_later_mesh_changes():
    svc = FederationDiscoveryService(cell_size_m=500.0)
    svc.register("WEST", _cell(0, 0))
    svc.register("MID", _cell(1, 0))
    svc.register("EAST", _cell(2, 0))
    mesh = FederationMesh(svc)
    rr = FederationResilientRouting(mesh)
    # 스냅샷 이후 디스커버리·메시가 바뀌어도 분석기는 생성 시점 그래프를 유지.
    # MID에 직접 붙는 ALT를 추가해 메시 주 경로를 WEST-ALT-EAST로 바꿔도,
    # 분석기는 스냅샷(WEST-MID-EAST)에서만 판정해야 한다.
    svc.register("ALT", _cell(1, 1))  # MID 위 타일 — WEST·MID·EAST와 king-move 인접
    mesh.rebuild()
    assert rr.articulation_points() == ("MID",)
    assert rr.instances() == ("EAST", "MID", "WEST")
    # backup_path는 메시 live 경로가 아니라 스냅샷에서 산정 → 일직선엔 백업 없음.
    assert rr.backup_path("WEST", "EAST") == ()
