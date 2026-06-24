"""ODYSSEY Phase 436 — 분산 경로-벡터 라우팅 단위 테스트.

외부 의존성 0(순수 결정적). Phase 432 메시 인접 위에서 동작한다.
경로-벡터 수렴 결과가 Phase 432 중앙 BFS의 홉 거리와 일치함을 핵심 불변식으로 검증.
"""

from __future__ import annotations

import pytest

from simulation.federation_discovery import FederationDiscoveryService, Volume4D
from simulation.federation_mesh import FederationMesh
from simulation.federation_path_vector import PathVectorRouting


def _tile(x_min: float, x_max: float) -> Volume4D:
    """전 고도·전 시간 창을 덮고 x축으로만 구분되는 타일 볼륨."""
    return Volume4D(x_min, x_max, 0, 1000, 0, 120, 0, 600)


def _line_service(n: int) -> FederationDiscoveryService:
    """x축으로 맞닿은 n개 타일 직선 메시: T0[0,1000)·T1[1000,2000)·..."""
    svc = FederationDiscoveryService(cell_size_m=500.0)
    for i in range(n):
        svc.register(f"T{i}", _tile(i * 1000, (i + 1) * 1000))
    return svc


def _line_mesh(n: int) -> FederationMesh:
    return FederationMesh(_line_service(n))


def _grid_service(rows: int, cols: int) -> FederationDiscoveryService:
    """rows×cols 격자 타일 메시 (king-move 인접 — 모서리 대각 포함)."""
    svc = FederationDiscoveryService(cell_size_m=500.0)
    for r in range(rows):
        for c in range(cols):
            svc.register(
                f"R{r}C{c}",
                Volume4D(c * 1000, (c + 1) * 1000, r * 1000, (r + 1) * 1000, 0, 120, 0, 600),
            )
    return svc


# --- 기본 수렴 --------------------------------------------------------------


def test_single_node_converges_immediately():
    mesh = _line_mesh(1)
    pv = PathVectorRouting(mesh)
    assert pv.converge() == 0
    assert pv.is_converged
    assert pv.best_path("T0", "T0") == ("T0",)


def test_two_nodes_converge_in_one_round():
    mesh = _line_mesh(2)
    pv = PathVectorRouting(mesh)
    assert pv.converge() == 1
    assert pv.best_path("T0", "T1") == ("T0", "T1")
    assert pv.best_path("T1", "T0") == ("T1", "T0")


def test_self_route_is_zero_hop():
    pv = PathVectorRouting(_line_mesh(4))
    pv.converge()
    for node in pv.instances():
        assert pv.best_path(node, node) == (node,)
        assert pv.hop_count(node, node) == 0
        assert pv.next_hop(node, node) is None


def test_line_converges_in_diameter_rounds():
    """N개 직선 메시의 지름은 N-1 → N-1 라운드에 수렴."""
    for n in (2, 3, 5, 8):
        pv = PathVectorRouting(_line_mesh(n))
        assert pv.converge() == n - 1
        assert pv.rounds_to_converge == n - 1


def test_is_converged_false_before_converge_call():
    pv = PathVectorRouting(_line_mesh(3))
    assert not pv.is_converged
    assert pv.rounds_to_converge is None


# --- 경로 정확성 (중앙 BFS와의 일치) ----------------------------------------


def test_path_lengths_match_central_bfs_line():
    mesh = _line_mesh(6)
    pv = PathVectorRouting(mesh)
    pv.converge()
    nodes = mesh.instances()
    for src in nodes:
        for dst in nodes:
            central = mesh.shortest_path(src, dst)
            assert len(pv.best_path(src, dst)) == len(central)


def test_path_lengths_match_central_bfs_grid():
    mesh = FederationMesh(_grid_service(3, 3))
    pv = PathVectorRouting(mesh)
    pv.converge()
    nodes = mesh.instances()
    for src in nodes:
        for dst in nodes:
            assert len(pv.best_path(src, dst)) == len(mesh.shortest_path(src, dst))


def test_hop_count_matches_bfs_distance_line():
    mesh = _line_mesh(5)
    pv = PathVectorRouting(mesh)
    pv.converge()
    # 직선 메시에서 Ti→Tj 홉 수는 |i-j|.
    for i in range(5):
        for j in range(5):
            assert pv.hop_count(f"T{i}", f"T{j}") == abs(i - j)


# --- 경로 유효성 (인접·루프 없음·끝점) --------------------------------------


def test_all_paths_are_valid_adjacent_walks():
    mesh = FederationMesh(_grid_service(3, 3))
    adj = mesh.adjacency()
    pv = PathVectorRouting(mesh)
    pv.converge()
    for src in mesh.instances():
        for dst, path in pv.routes(src).items():
            assert path[0] == src
            assert path[-1] == dst
            # 연속 노드가 실제 이웃이어야 함.
            for a, b in zip(path, path[1:]):
                assert b in adj[a]


def test_paths_have_no_loops():
    mesh = FederationMesh(_grid_service(3, 4))
    pv = PathVectorRouting(mesh)
    pv.converge()
    for src in mesh.instances():
        for path in pv.routes(src).values():
            assert len(set(path)) == len(path)  # 중복 노드 없음(루프 방지)


# --- 결정성 -----------------------------------------------------------------


def test_convergence_is_deterministic():
    s1 = PathVectorRouting(FederationMesh(_grid_service(3, 3)))
    s2 = PathVectorRouting(FederationMesh(_grid_service(3, 3)))
    assert s1.converge() == s2.converge()
    for node in s1.instances():
        assert s1.routes(node) == s2.routes(node)


def test_tie_break_prefers_lexicographically_smaller_path():
    """다이아몬드 메시 T0-{A,B}-T3에서 동률 경로는 사전식 작은 쪽(A 경유)."""
    svc = FederationDiscoveryService(cell_size_m=500.0)
    # 가운데가 빈 다이아몬드: START 위/아래로 두 갈래, END에서 합류.
    svc.register("START", Volume4D(0, 1000, 1000, 2000, 0, 120, 0, 600))
    svc.register("PATH_A", Volume4D(1000, 2000, 2000, 3000, 0, 120, 0, 600))
    svc.register("PATH_B", Volume4D(1000, 2000, 0, 1000, 0, 120, 0, 600))
    svc.register("END", Volume4D(2000, 3000, 1000, 2000, 0, 120, 0, 600))
    mesh = FederationMesh(svc)
    # START는 A·B 둘 다와 인접, END도 A·B 둘 다와 인접해야 동률 성립.
    assert set(mesh.neighbors("START")) >= {"PATH_A", "PATH_B"}
    assert set(mesh.neighbors("END")) >= {"PATH_A", "PATH_B"}
    pv = PathVectorRouting(mesh)
    pv.converge()
    path = pv.best_path("START", "END")
    assert len(path) == 3
    assert path == ("START", "PATH_A", "END")  # 사전식 PATH_A < PATH_B


# --- 분단 메시 --------------------------------------------------------------


def _disconnected_service() -> FederationDiscoveryService:
    """두 갈래로 분리된 메시: {A,B} 와 멀리 떨어진 {C,D}."""
    svc = FederationDiscoveryService(cell_size_m=500.0)
    svc.register("A", _tile(0, 1000))
    svc.register("B", _tile(1000, 2000))
    svc.register("C", _tile(10000, 11000))
    svc.register("D", _tile(11000, 12000))
    return svc


def test_unreachable_destination_has_empty_path():
    mesh = FederationMesh(_disconnected_service())
    assert not mesh.is_connected()
    pv = PathVectorRouting(mesh)
    pv.converge()
    assert pv.best_path("A", "C") == ()
    assert pv.hop_count("A", "C") == -1
    assert pv.next_hop("A", "C") is None


def test_routes_within_partition_still_resolve():
    pv = PathVectorRouting(FederationMesh(_disconnected_service()))
    pv.converge()
    assert pv.best_path("A", "B") == ("A", "B")
    assert pv.best_path("C", "D") == ("C", "D")
    # 분단 너머 목적지는 테이블에 없음.
    assert "C" not in pv.routes("A")
    assert "D" not in pv.routes("A")


# --- 포워딩 테이블 / next_hop -----------------------------------------------


def test_next_hop_points_toward_destination_line():
    pv = PathVectorRouting(_line_mesh(5))
    pv.converge()
    # T0에서 임의 목적지로의 첫 홉은 항상 T1.
    for j in range(1, 5):
        assert pv.next_hop("T0", f"T{j}") == "T1"


def test_forwarding_table_excludes_self():
    pv = PathVectorRouting(_line_mesh(4))
    pv.converge()
    table = pv.forwarding_table("T0")
    assert "T0" not in table
    assert table["T1"] == "T1"
    assert table["T3"] == "T1"  # 직선이라 모든 원거리 목적지 첫 홉 = T1


def test_forwarding_table_matches_next_hop():
    pv = PathVectorRouting(FederationMesh(_grid_service(2, 3)))
    pv.converge()
    for origin in pv.instances():
        table = pv.forwarding_table(origin)
        for dst in pv.instances():
            if dst == origin or pv.best_path(origin, dst) == ():
                assert dst not in table
            else:
                assert table[dst] == pv.next_hop(origin, dst)


# --- 자동 수렴 / 입력 검증 --------------------------------------------------


def test_queries_auto_converge():
    """converge() 명시 호출 없이 조회해도 자동 수렴한다."""
    pv = PathVectorRouting(_line_mesh(3))
    assert pv.best_path("T0", "T2") == ("T0", "T1", "T2")
    assert pv.is_converged


def test_unknown_origin_raises_keyerror():
    pv = PathVectorRouting(_line_mesh(3))
    pv.converge()
    with pytest.raises(KeyError):
        pv.best_path("NOPE", "T0")
    with pytest.raises(KeyError):
        pv.routes("NOPE")
    with pytest.raises(KeyError):
        pv.forwarding_table("NOPE")


def test_unknown_destination_raises_keyerror():
    pv = PathVectorRouting(_line_mesh(3))
    pv.converge()
    with pytest.raises(KeyError):
        pv.best_path("T0", "NOPE")


def test_empty_mesh_converges_immediately():
    svc = FederationDiscoveryService(cell_size_m=500.0)
    pv = PathVectorRouting(FederationMesh(svc))
    assert pv.converge() == 0
    assert pv.is_converged
    assert pv.instances() == ()


def test_converge_is_idempotent():
    """이미 수렴한 뒤 재호출해도 라운드 수·테이블이 동일하다(self._adj 불변)."""
    pv = PathVectorRouting(_line_mesh(4))
    r1 = pv.converge()
    t1 = {n: pv.routes(n) for n in pv.instances()}
    r2 = pv.converge()
    t2 = {n: pv.routes(n) for n in pv.instances()}
    assert r1 == r2
    assert t1 == t2


# --- 격자 대각 인접 (king-move) 검증 ----------------------------------------


def test_grid_diagonal_is_single_hop():
    """king-move 인접이므로 대각 타일도 1홉."""
    mesh = FederationMesh(_grid_service(2, 2))
    pv = PathVectorRouting(mesh)
    pv.converge()
    # R0C0 와 R1C1 은 대각 → 1홉.
    assert pv.hop_count("R0C0", "R1C1") == 1
