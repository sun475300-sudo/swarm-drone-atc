"""ODYSSEY Phase 438 — 분산 경로-벡터 장애 우회 수렴 단위 테스트.

외부 의존성 0(순수 결정적). Phase 432 메시 인접 위에서 노드 장애 전후를 비교한다.
핵심 불변식: (1) 장애 전후 경로 비교가 Phase 436 콜드스타트 수렴과 일치하고,
(2) Phase 435 가 백업 경로 존재를 보장하면 그 주 경로 내부 중계가 죽어도 우회로
살아남는다(교차 검증).
"""

from __future__ import annotations

import pytest

from simulation.federation_discovery import FederationDiscoveryService, Volume4D
from simulation.federation_mesh import FederationMesh
from simulation.federation_path_vector import PathVectorRouting
from simulation.federation_path_vector_failover import PathVectorFailover
from simulation.federation_resilient_routing import FederationResilientRouting


def _tile(x_min: float, x_max: float) -> Volume4D:
    """전 고도·전 시간 창을 덮고 x축으로만 구분되는 타일 볼륨."""
    return Volume4D(x_min, x_max, 0, 1000, 0, 120, 0, 600)


def _line_mesh(n: int) -> FederationMesh:
    """x축으로 맞닿은 n개 타일 직선 메시: T0-T1-...-T(n-1)."""
    svc = FederationDiscoveryService(cell_size_m=500.0)
    for i in range(n):
        svc.register(f"T{i}", _tile(i * 1000, (i + 1) * 1000))
    return FederationMesh(svc)


def _grid_mesh(rows: int, cols: int) -> FederationMesh:
    """rows×cols 격자 타일 메시 (king-move 인접 — 모서리 대각 포함)."""
    svc = FederationDiscoveryService(cell_size_m=500.0)
    for r in range(rows):
        for c in range(cols):
            svc.register(
                f"R{r}C{c}",
                Volume4D(c * 1000, (c + 1) * 1000, r * 1000, (r + 1) * 1000, 0, 120, 0, 600),
            )
    return FederationMesh(svc)


# --- 빈 장애 집합: 항등 -----------------------------------------------------


def test_empty_failure_keeps_all_paths():
    mesh = _line_mesh(4)
    fo = PathVectorFailover(mesh, set())
    base = PathVectorRouting(mesh)
    base.converge()
    for o in mesh.instances():
        assert fo.lost_routes(o) == ()
        assert fo.rerouted(o) == {}
        for d in mesh.instances():
            assert fo.surviving_path(o, d) == base.best_path(o, d)


def test_empty_failure_survivors_are_all_instances():
    mesh = _grid_mesh(2, 3)
    fo = PathVectorFailover(mesh, set())
    assert fo.survivors() == mesh.instances()
    assert fo.failed_instances() == ()


# --- 직선 메시 중간 노드 장애: 단절 ----------------------------------------


def test_line_middle_failure_partitions():
    # T0-T1-T2-T3-T4, T2 죽으면 {T0,T1} 와 {T3,T4} 단절.
    mesh = _line_mesh(5)
    fo = PathVectorFailover(mesh, {"T2"})
    assert fo.surviving_path("T0", "T3") == ()
    assert fo.surviving_path("T0", "T4") == ()
    assert "T3" in fo.lost_routes("T0")
    assert "T4" in fo.lost_routes("T0")
    # 같은 분파 내부는 유지.
    assert fo.surviving_path("T0", "T1") == ("T0", "T1")


def test_line_endpoint_failure_no_partition():
    # 끝점 T4 가 죽어도 나머지는 연결 유지(단절은 T4 행 목적지뿐).
    mesh = _line_mesh(5)
    fo = PathVectorFailover(mesh, {"T4"})
    assert fo.surviving_path("T0", "T3") == ("T0", "T1", "T2", "T3")
    assert fo.lost_routes("T0") == ("T4",)


def test_line_no_reroute_single_path_topology():
    # 직선은 단일 경로뿐이라 우회가 없다(끊기거나 그대로).
    mesh = _line_mesh(5)
    fo = PathVectorFailover(mesh, {"T2"})
    for o in fo.survivors():
        assert fo.rerouted(o) == {}


# --- 격자 메시 노드 장애: 우회 ---------------------------------------------


def test_grid_failure_reroutes_not_lost():
    # 2x3 격자에서 R0C0→R0C2 주 경로는 (R0C0,R0C1,R0C2). R0C1 이 죽으면 우회 존재.
    mesh = _grid_mesh(2, 3)
    base = PathVectorRouting(mesh)
    base.converge()
    primary = base.best_path("R0C0", "R0C2")
    assert primary == ("R0C0", "R0C1", "R0C2")

    fo = PathVectorFailover(mesh, {"R0C1"})
    after = fo.surviving_path("R0C0", "R0C2")
    assert after  # 여전히 도달
    assert after != primary  # 경로가 바뀜
    assert "R0C1" not in after
    assert "R0C2" not in fo.lost_routes("R0C0")
    assert fo.rerouted("R0C0")["R0C2"] == (primary, after)


def test_is_reroutable_true_when_backup_exists():
    mesh = _grid_mesh(2, 3)
    fo = PathVectorFailover(mesh, {"R0C1"})
    assert fo.is_reroutable("R0C0", "R0C2") is True


def test_is_reroutable_false_when_partitioned():
    mesh = _line_mesh(5)
    fo = PathVectorFailover(mesh, {"T2"})
    assert fo.is_reroutable("T0", "T4") is False


def test_is_reroutable_false_for_dead_endpoint():
    mesh = _grid_mesh(2, 3)
    fo = PathVectorFailover(mesh, {"R0C2"})
    assert fo.is_reroutable("R0C0", "R0C2") is False


def test_is_reroutable_false_for_self_path():
    # 자기 경로는 의미 있는 라우팅 대상이 아니므로 False (rerouted 가 자기 경로
    # 제외하는 것과 일관).
    mesh = _line_mesh(4)
    fo = PathVectorFailover(mesh, {"T1"})
    assert fo.is_reroutable("T0", "T0") is False


def test_surviving_path_to_dead_destination_is_empty():
    # 살아있는 origin → 죽은 dst 는 partition 과 무관하게 빈 튜플.
    mesh = _grid_mesh(2, 3)
    fo = PathVectorFailover(mesh, {"R0C1"})
    assert fo.surviving_path("R0C0", "R0C1") == ()


# --- 죽은 origin -----------------------------------------------------------


def test_failed_origin_loses_all_routes():
    mesh = _line_mesh(4)
    base = PathVectorRouting(mesh)
    base.converge()
    fo = PathVectorFailover(mesh, {"T1"})
    lost = fo.lost_routes("T1")
    # T1 이 닿던 모든 목적지(자기 제외)가 단절.
    expected = tuple(sorted(d for d in base.routes("T1") if d != "T1"))
    assert lost == expected
    assert fo.rerouted("T1") == {}
    assert fo.surviving_path("T1", "T0") == ()


def test_dead_origin_not_in_survivors():
    mesh = _line_mesh(4)
    fo = PathVectorFailover(mesh, {"T1"})
    assert "T1" not in fo.survivors()
    assert fo.survivors() == ("T0", "T2", "T3")


# --- Phase 435 교차 검증 ----------------------------------------------------


def test_cross_validate_backup_path_implies_reroutable():
    # Phase 435 가 내부 분리 백업 경로 존재를 보장하면, 주 경로 내부 중계가
    # 모두 죽어도 Phase 438 은 우회로 살아남아야 한다.
    mesh = _grid_mesh(2, 3)
    resilient = FederationResilientRouting(mesh)
    primary = mesh.shortest_path("R0C0", "R0C2")
    interior = set(primary[1:-1])
    assert resilient.has_backup_path("R0C0", "R0C2")

    fo = PathVectorFailover(mesh, interior)
    assert fo.is_reroutable("R0C0", "R0C2") is True
    # 우회로의 *존재*와 죽은 노드 미사용을 불변식으로 검증한다. 경로 *동일성*은
    # Phase 435 BFS 와 Phase 436 path-vector 의 동률 분리 방식이 달라 더 조밀한
    # 토폴로지에서 깨질 수 있으므로 단언하지 않는다(거짓 실패 방지).
    surviving = fo.surviving_path("R0C0", "R0C2")
    assert surviving
    assert not (set(surviving) & interior)
    assert len(surviving) == len(resilient.backup_path("R0C0", "R0C2"))


def test_cross_validate_articulation_failure_causes_loss():
    # Phase 435 가 단일 장애점이라 지목한 노드가 죽으면 어떤 쌍은 반드시 단절.
    mesh = _line_mesh(5)
    resilient = FederationResilientRouting(mesh)
    aps = resilient.articulation_points()
    assert "T2" in aps
    fo = PathVectorFailover(mesh, {"T2"})
    total_lost = sum(len(fo.lost_routes(o)) for o in fo.survivors())
    assert total_lost > 0


# --- 콜드스타트 등가성 ------------------------------------------------------


def test_after_equals_coldstart_on_pruned_mesh():
    # 장애 후 경로-벡터는 살아남은 메시의 콜드스타트 수렴과 동일한 고정점이어야 한다.
    mesh = _grid_mesh(2, 3)
    fo = PathVectorFailover(mesh, {"R0C1"})
    pruned = _grid_mesh(2, 3)
    # 콜드스타트: R0C1 을 인접에서 제거한 동등 메시 위 라우터.
    adj = {n: tuple(x for x in nb if x != "R0C1") for n, nb in pruned.adjacency().items() if n != "R0C1"}

    class _M:
        def adjacency(self):
            return dict(adj)

    cold = PathVectorRouting(_M())
    cold.converge()
    for o in fo.survivors():
        for d in fo.survivors():
            assert fo.surviving_path(o, d) == cold.best_path(o, d)


# --- 재수렴 라운드 / 요약 ---------------------------------------------------


def test_reconvergence_rounds_nonnegative():
    mesh = _grid_mesh(2, 3)
    fo = PathVectorFailover(mesh, {"R0C1"})
    assert fo.reconvergence_rounds >= 0


def test_summary_fields():
    mesh = _line_mesh(5)
    fo = PathVectorFailover(mesh, {"T2"})
    s = fo.summary()
    assert s["failed"] == 1
    assert s["survivors"] == 4
    assert s["lost_pairs"] > 0
    assert s["rerouted_pairs"] == 0  # 직선이라 우회 없음
    assert "reconvergence_rounds" in s


# --- 결정성 -----------------------------------------------------------------


def test_deterministic_across_instances():
    mesh = _grid_mesh(3, 3)
    a = PathVectorFailover(mesh, {"R1C1"})
    b = PathVectorFailover(_grid_mesh(3, 3), {"R1C1"})
    assert a.summary() == b.summary()
    for o in a.survivors():
        assert a.lost_routes(o) == b.lost_routes(o)
        assert a.rerouted(o) == b.rerouted(o)


# --- 입력 검증 --------------------------------------------------------------


def test_unknown_failed_instance_raises():
    mesh = _line_mesh(3)
    with pytest.raises(KeyError):
        PathVectorFailover(mesh, {"NOPE"})


def test_unknown_origin_raises():
    mesh = _line_mesh(3)
    fo = PathVectorFailover(mesh, {"T1"})
    with pytest.raises(KeyError):
        fo.surviving_path("NOPE", "T0")
    with pytest.raises(KeyError):
        fo.lost_routes("NOPE")
    with pytest.raises(KeyError):
        fo.rerouted("NOPE")


def test_multiple_failures():
    # 두 노드 동시 장애: 5-직선에서 T1,T3 죽으면 T0·T2·T4 모두 고립.
    mesh = _line_mesh(5)
    fo = PathVectorFailover(mesh, {"T1", "T3"})
    assert fo.failed_instances() == ("T1", "T3")
    assert fo.surviving_path("T0", "T2") == ()
    assert fo.surviving_path("T2", "T4") == ()
    assert fo.is_reroutable("T0", "T2") is False
