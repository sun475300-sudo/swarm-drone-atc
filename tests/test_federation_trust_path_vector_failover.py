"""ODYSSEY Phase 440 — 신뢰 인지 분산 경로-벡터 장애 우회 수렴 단위 테스트.

외부 의존성 0(순수 결정적). Phase 432 메시 인접 + Phase 428 신뢰 위에서 노드 장애
전후의 *신뢰 가중* 경로를 비교한다. 핵심 불변식:
  (1) 빈 장애 집합 → Phase 437 고정 메시 결과와 항등.
  (2) 신뢰 관찰이 없으면(균일 0.5) Phase 438(홉만) 장애 분석과 *정확히* 동일 —
      연합 라우팅 2×2 격자의 두 칸이 그 모서리에서 만난다.
  (3) 도달성(단절·우회 가능 여부)은 신뢰와 무관 = Phase 438 과 동일.
  (4) 신뢰는 장애 후 *어느 우회로를 고르는가* 만 바꾼다.
"""

from __future__ import annotations

import pytest

from simulation.federation_discovery import FederationDiscoveryService, Volume4D
from simulation.federation_mesh import FederationMesh
from simulation.federation_path_vector_failover import PathVectorFailover
from simulation.federation_resilient_routing import FederationResilientRouting
from simulation.federation_trust import FederationTrustModel
from simulation.federation_trust_path_vector import TrustPathVectorRouting
from simulation.federation_trust_path_vector_failover import TrustPathVectorFailover

# --- 토폴로지 픽스처 (기하 메시) -------------------------------------------


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


# --- 고정 인접 메시 스텁 (임의 토폴로지) -----------------------------------


class _FixedMesh:
    """``adjacency()`` 만 노출하는 메시 스텁. 라우터·페일오버 모두 이것만 호출한다.

    기하 메시로는 만들기 까다로운 임의 토폴로지(신뢰 동률 우회 분기 등)를 직접
    구성하기 위한 테스트 더블이다.
    """

    def __init__(self, edges: list[tuple[str, str]], nodes: list[str] | None = None) -> None:
        adj: dict[str, set[str]] = {}
        for n in nodes or []:
            adj.setdefault(n, set())
        for a, b in edges:
            adj.setdefault(a, set()).add(b)
            adj.setdefault(b, set()).add(a)
        self._adj = {n: tuple(sorted(nb)) for n, nb in adj.items()}

    def adjacency(self) -> dict[str, tuple[str, ...]]:
        return {n: tuple(nb) for n, nb in self._adj.items()}


def _kite_mesh() -> _FixedMesh:
    """S→D 주 경로(S-P-D, 2홉) + 장애 후 두 등홉 우회(S-A-M-D, S-Z-M-D, 3홉).

    P 가 죽으면 S→D 는 A 경유·Z 경유 두 3홉 경로만 남고, 둘은 홉이 같아 S 의
    *다음 홉* 신뢰(A vs Z)가 우회 선택을 가른다. 이름순으로 A<Z 라 무신뢰면 A 가
    선택된다(신뢰가 Z 를 끌어올리는지 검증).
    """
    return _FixedMesh(
        [("S", "P"), ("P", "D"), ("S", "A"), ("A", "M"), ("M", "D"), ("S", "Z"), ("Z", "M")]
    )


def _no_trust() -> FederationTrustModel:
    return FederationTrustModel()


def _observe(model: FederationTrustModel, observer: str, target: str, *, ok: int, bad: int) -> None:
    for _ in range(ok):
        model.observe(observer, target, True)
    for _ in range(bad):
        model.observe(observer, target, False)


# --- 빈 장애 집합: Phase 437 과 항등 ----------------------------------------


def test_empty_failure_identity_with_phase437():
    mesh = _grid_mesh(2, 3)
    trust = _no_trust()
    fo = TrustPathVectorFailover(mesh, trust, set())
    base = TrustPathVectorRouting(mesh, trust)
    base.converge()
    for o in mesh.instances():
        assert fo.lost_routes(o) == ()
        assert fo.rerouted(o) == {}
        for d in mesh.instances():
            assert fo.surviving_path(o, d) == base.best_path(o, d)


def test_empty_failure_survivors_are_all_instances():
    mesh = _grid_mesh(2, 3)
    fo = TrustPathVectorFailover(mesh, _no_trust(), set())
    assert fo.survivors() == mesh.instances()
    assert fo.failed_instances() == ()


# --- 핵심 모서리: 무신뢰 → Phase 438(홉만)과 정확히 동일 -------------------


@pytest.mark.parametrize("failed", [set(), {"R0C1"}, {"R0C2"}, {"R0C1", "R1C1"}])
def test_uniform_trust_matches_phase438_grid(failed):
    mesh = _grid_mesh(2, 3)
    tfo = TrustPathVectorFailover(mesh, _no_trust(), failed)
    hop = PathVectorFailover(mesh, failed)
    assert tfo.survivors() == hop.survivors()
    assert tfo.failed_instances() == hop.failed_instances()
    # 도달성·우회 카운트는 두 엔진이 동일해야 한다. reconvergence_rounds 는 서로 다른
    # 수렴 엔진(436 vs 437)의 라운드 카운터라 보장된 불변식이 아니므로 제외한다.
    ts, hs = tfo.summary(), hop.summary()
    for field in ("survivors", "failed", "lost_pairs", "rerouted_pairs"):
        assert ts[field] == hs[field]
    for o in mesh.instances():
        assert tfo.lost_routes(o) == hop.lost_routes(o)
        assert tfo.rerouted(o) == hop.rerouted(o)
        for d in mesh.instances():
            assert tfo.surviving_path(o, d) == hop.surviving_path(o, d)
            assert tfo.is_reroutable(o, d) == hop.is_reroutable(o, d)


@pytest.mark.parametrize("n", [4, 6, 8])  # T2 가 항상 내부 노드 → 분단 발생
def test_uniform_trust_matches_phase438_line(n):
    mesh = _line_mesh(n)
    failed = {"T2"}
    tfo = TrustPathVectorFailover(mesh, _no_trust(), failed)
    hop = PathVectorFailover(mesh, failed)
    for o in mesh.instances():
        assert tfo.lost_routes(o) == hop.lost_routes(o)
        for d in mesh.instances():
            assert tfo.surviving_path(o, d) == hop.surviving_path(o, d)


# --- 신뢰가 장애 후 우회를 가른다 (핵심 가치) ------------------------------


def test_trust_steers_reroute_after_primary_failure():
    # P(주 경로 중계)가 죽으면 S→D 는 A 경유·Z 경유 두 등홉 우회만 남는다.
    mesh = _kite_mesh()

    # 무신뢰: 사전식으로 A 가 먼저 → (S, A, M, D).
    plain = TrustPathVectorFailover(mesh, _no_trust(), {"P"})
    assert plain.surviving_path("S", "D") == ("S", "A", "M", "D")

    # S 가 A 를 불신, Z 를 신뢰 → 우회가 Z 경유로 이동.
    trust = _no_trust()
    _observe(trust, "S", "A", ok=0, bad=8)
    _observe(trust, "S", "Z", ok=8, bad=0)
    steered = TrustPathVectorFailover(mesh, trust, {"P"})
    assert steered.surviving_path("S", "D") == ("S", "Z", "M", "D")

    # 도달성·단절 여부는 신뢰와 무관하게 동일(신뢰는 경로만 바꾼다).
    assert plain.is_reroutable("S", "D") is True
    assert steered.is_reroutable("S", "D") is True
    assert plain.lost_routes("S") == steered.lost_routes("S")


def test_trust_steering_appears_in_rerouted():
    # P 를 가장 신뢰(주 경로 S-P-D 유지), Z 는 중간, A 는 불신. P 사망 후 신뢰가
    # 고른 Z 우회((S,Z,M,D))가 rerouted 에 (장애 전, 장애 후) 쌍으로 잡힌다.
    mesh = _kite_mesh()
    trust = _no_trust()
    _observe(trust, "S", "P", ok=8, bad=0)  # 최고 신뢰 → 주 경로 다음 홉
    _observe(trust, "S", "Z", ok=4, bad=4)  # 중간 신뢰 → 우회 1순위
    _observe(trust, "S", "A", ok=0, bad=8)  # 불신 → 우회 후순위
    fo = TrustPathVectorFailover(mesh, trust, {"P"})
    changed = fo.rerouted("S")
    assert "D" in changed
    before, after = changed["D"]
    assert before == ("S", "P", "D")
    assert after == ("S", "Z", "M", "D")


def test_reachability_independent_of_trust():
    # 신뢰 관찰이 도달성(단절·우회가능) 판정을 바꾸지 않음을 격자에서 확인.
    mesh = _grid_mesh(2, 3)
    trust = _no_trust()
    _observe(trust, "R0C0", "R0C1", ok=0, bad=9)
    _observe(trust, "R0C0", "R1C0", ok=9, bad=0)
    biased = TrustPathVectorFailover(mesh, trust, {"R0C1"})
    plain = TrustPathVectorFailover(mesh, _no_trust(), {"R0C1"})
    for o in mesh.instances():
        assert biased.lost_routes(o) == plain.lost_routes(o)
        for d in mesh.instances():
            assert biased.is_reroutable(o, d) == plain.is_reroutable(o, d)


# --- 표준 페일오버 동작 (438 과 동일 계약) ----------------------------------


def test_line_middle_failure_partitions():
    mesh = _line_mesh(5)
    fo = TrustPathVectorFailover(mesh, _no_trust(), {"T2"})
    assert fo.surviving_path("T0", "T3") == ()
    assert fo.surviving_path("T0", "T4") == ()
    assert "T3" in fo.lost_routes("T0")
    assert "T4" in fo.lost_routes("T0")
    assert fo.surviving_path("T0", "T1") == ("T0", "T1")


def test_grid_failure_reroutes_not_lost():
    mesh = _grid_mesh(2, 3)
    fo = TrustPathVectorFailover(mesh, _no_trust(), {"R0C1"})
    after = fo.surviving_path("R0C0", "R0C2")
    assert after
    assert "R0C1" not in after
    assert "R0C2" not in fo.lost_routes("R0C0")
    assert fo.rerouted("R0C0")["R0C2"][1] == after


def test_surviving_path_to_dead_destination_is_empty():
    mesh = _grid_mesh(2, 3)
    fo = TrustPathVectorFailover(mesh, _no_trust(), {"R0C1"})
    assert fo.surviving_path("R0C0", "R0C1") == ()


def test_is_reroutable_false_for_self_and_dead():
    mesh = _grid_mesh(2, 3)
    fo = TrustPathVectorFailover(mesh, _no_trust(), {"R0C2"})
    assert fo.is_reroutable("R0C0", "R0C0") is False  # 자기 경로
    assert fo.is_reroutable("R0C0", "R0C2") is False  # 죽은 목적지


def test_failed_origin_loses_all_routes():
    mesh = _line_mesh(4)
    base = TrustPathVectorRouting(mesh, _no_trust())
    base.converge()
    fo = TrustPathVectorFailover(mesh, _no_trust(), {"T1"})
    expected = tuple(sorted(d for d in base.routes("T1") if d != "T1"))
    assert fo.lost_routes("T1") == expected
    assert fo.rerouted("T1") == {}
    assert fo.surviving_path("T1", "T0") == ()


def test_dead_origin_not_in_survivors():
    mesh = _line_mesh(4)
    fo = TrustPathVectorFailover(mesh, _no_trust(), {"T1"})
    assert "T1" not in fo.survivors()
    assert fo.survivors() == ("T0", "T2", "T3")


# --- 입력 검증 --------------------------------------------------------------


def test_unknown_failed_id_raises_keyerror():
    mesh = _line_mesh(3)
    with pytest.raises(KeyError):
        TrustPathVectorFailover(mesh, _no_trust(), {"NOPE"})


def test_negative_untrust_weight_rejected():
    mesh = _line_mesh(3)
    with pytest.raises(ValueError):
        TrustPathVectorFailover(mesh, _no_trust(), set(), untrust_weight=-1.0)


def test_require_unregistered_origin_raises():
    mesh = _line_mesh(3)
    fo = TrustPathVectorFailover(mesh, _no_trust(), set())
    with pytest.raises(KeyError):
        fo.lost_routes("GHOST")
    with pytest.raises(KeyError):
        fo.surviving_path("GHOST", "T0")


# --- summary & 재수렴 라운드 ------------------------------------------------


def test_summary_fields_and_consistency():
    mesh = _grid_mesh(2, 3)
    fo = TrustPathVectorFailover(mesh, _no_trust(), {"R0C1"})
    s = fo.summary()
    assert set(s) == {"survivors", "failed", "lost_pairs", "rerouted_pairs", "reconvergence_rounds"}
    assert s["survivors"] == len(fo.survivors())
    assert s["failed"] == 1
    assert s["lost_pairs"] == sum(len(fo.lost_routes(o)) for o in mesh.instances())
    assert s["rerouted_pairs"] == sum(len(fo.rerouted(o)) for o in mesh.instances())
    assert s["reconvergence_rounds"] == fo.reconvergence_rounds


def test_reconvergence_rounds_nonnegative():
    mesh = _grid_mesh(2, 3)
    fo = TrustPathVectorFailover(mesh, _no_trust(), {"R0C1"})
    assert fo.reconvergence_rounds >= 0


def test_determinism_repeated_construction():
    mesh = _grid_mesh(2, 3)
    trust = _no_trust()
    _observe(trust, "R0C0", "R0C1", ok=3, bad=5)
    a = TrustPathVectorFailover(mesh, trust, {"R0C1"})
    b = TrustPathVectorFailover(mesh, trust, {"R0C1"})
    assert a.summary() == b.summary()
    for o in mesh.instances():
        assert a.rerouted(o) == b.rerouted(o)
        assert a.lost_routes(o) == b.lost_routes(o)


# --- Phase 435 교차 검증 ----------------------------------------------------


def test_cross_validate_backup_path_implies_reroutable():
    # Phase 435 가 내부 분리 백업 경로 존재를 보장하면, 주 경로 내부 중계가 모두
    # 죽어도 신뢰 인지 페일오버는 우회로 살아남아야 한다(도달성은 신뢰 무관).
    mesh = _grid_mesh(2, 3)
    resilient = FederationResilientRouting(mesh)
    primary = mesh.shortest_path("R0C0", "R0C2")
    interior = set(primary[1:-1])
    assert resilient.has_backup_path("R0C0", "R0C2")
    fo = TrustPathVectorFailover(mesh, _no_trust(), interior)
    assert fo.is_reroutable("R0C0", "R0C2") is True
    surviving = fo.surviving_path("R0C0", "R0C2")
    assert surviving
    assert not (set(surviving) & interior)


def test_cross_validate_articulation_failure_causes_loss():
    mesh = _line_mesh(5)
    resilient = FederationResilientRouting(mesh)
    assert "T2" in resilient.articulation_points()
    fo = TrustPathVectorFailover(mesh, _no_trust(), {"T2"})
    total_lost = sum(len(fo.lost_routes(o)) for o in fo.survivors())
    assert total_lost > 0


# --- 콜드스타트 등가성 (장애 후 = 살아남은 메시 콜드스타트) -----------------


def test_after_equals_coldstart_on_pruned_mesh():
    mesh = _kite_mesh()
    trust = _no_trust()
    _observe(trust, "S", "A", ok=0, bad=8)
    _observe(trust, "S", "Z", ok=8, bad=0)
    fo = TrustPathVectorFailover(mesh, trust, {"P"})

    # 콜드스타트: P 를 인접에서 제거한 동등 메시 위 신뢰 인지 라우터.
    full = mesh.adjacency()
    pruned = [
        (a, b)
        for a, nbrs in full.items()
        if a != "P"
        for b in nbrs
        if b != "P" and a < b
    ]
    survivors = [n for n in full if n != "P"]
    cold = TrustPathVectorRouting(_FixedMesh(pruned, survivors), trust)
    cold.converge()
    for o in cold.instances():
        for d in cold.instances():
            assert fo.surviving_path(o, d) == cold.best_path(o, d)
