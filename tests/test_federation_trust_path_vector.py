"""ODYSSEY Phase 437 — 신뢰 인지 분산 경로-벡터 라우팅 단위 테스트.

외부 의존성 0(순수 결정적). Phase 432 메시 인접 + Phase 428 신뢰 위에서 동작한다.
핵심 불변식:
  * 신뢰 관찰이 없으면(균일 0.5) 결과가 Phase 436 홉-최단 경로-벡터와 *정확히* 일치.
  * 각 노드는 자신이 더 신뢰하는 *다음 홉* 이웃을 1순위로 선호(BGP LOCAL_PREF) —
    홉이 늘거나 사전식으로 불리해도 신뢰가 높으면 그 경로를 택한다.
  * 신뢰는 재배열만 할 뿐 어떤 후보도 제거하지 않으므로 도달성은 메시와 동일.
"""

from __future__ import annotations

import pytest

from simulation.federation_discovery import FederationDiscoveryService, Volume4D
from simulation.federation_mesh import FederationMesh
from simulation.federation_path_vector import PathVectorRouting
from simulation.federation_trust import FederationTrustModel
from simulation.federation_trust_path_vector import TrustPathVectorRouting


# --- 토폴로지 픽스처 --------------------------------------------------------


def _tile(x_min: float, x_max: float) -> Volume4D:
    """전 고도·전 시간 창을 덮고 x축으로만 구분되는 타일 볼륨."""
    return Volume4D(x_min, x_max, 0, 1000, 0, 120, 0, 600)


def _line_service(n: int) -> FederationDiscoveryService:
    """x축으로 맞닿은 n개 타일 직선 메시."""
    svc = FederationDiscoveryService(cell_size_m=500.0)
    for i in range(n):
        svc.register(f"T{i}", _tile(i * 1000, (i + 1) * 1000))
    return svc


def _line_mesh(n: int) -> FederationMesh:
    return FederationMesh(_line_service(n))


def _cell(col: int, row: int) -> Volume4D:
    """(col,row) 격자 타일 — 전 고도·전 시간(king-move 인접)."""
    return Volume4D(
        col * 1000, (col + 1) * 1000, row * 1000, (row + 1) * 1000, 0, 120, 0, 600
    )


def _diamond_mesh() -> FederationMesh:
    """등-홉 다이아몬드: S~A, S~Z, A~D, Z~D (S↛D, A↛Z).

    S→D 로 가는 2-홉 경로가 둘(via A·via Z) 존재한다. 이름은 불신 노드 A가
    사전식으로 *작아* 신뢰가 없으면 A가 먼저 뽑히도록 의도(신뢰 우선 검증용).
    """
    svc = FederationDiscoveryService(cell_size_m=500.0)
    svc.register("S", _cell(0, 1))
    svc.register("A", _cell(1, 2))
    svc.register("Z", _cell(1, 0))
    svc.register("D", _cell(2, 1))
    return FederationMesh(svc)


def _no_trust() -> FederationTrustModel:
    return FederationTrustModel()


def _observe(model: FederationTrustModel, observer: str, target: str, *, ok: int, bad: int) -> None:
    for _ in range(ok):
        model.observe(observer, target, True)
    for _ in range(bad):
        model.observe(observer, target, False)


# --- 기본 수렴 --------------------------------------------------------------


def test_single_node_converges_immediately():
    pv = TrustPathVectorRouting(_line_mesh(1), _no_trust())
    assert pv.converge() == 0
    assert pv.is_converged
    assert pv.best_path("T0", "T0") == ("T0",)


def test_two_nodes_converge_in_one_round():
    pv = TrustPathVectorRouting(_line_mesh(2), _no_trust())
    assert pv.converge() == 1
    assert pv.best_path("T0", "T1") == ("T0", "T1")
    assert pv.best_path("T1", "T0") == ("T1", "T0")


def test_self_route_is_zero_hop():
    pv = TrustPathVectorRouting(_line_mesh(4), _no_trust())
    pv.converge()
    for node in pv.instances():
        assert pv.best_path(node, node) == (node,)
        assert pv.hop_count(node, node) == 0
        assert pv.next_hop(node, node) is None


def test_rounds_none_before_converge_then_cached():
    pv = TrustPathVectorRouting(_line_mesh(3), _no_trust())
    assert pv.rounds_to_converge is None
    first = pv.converge()
    assert pv.rounds_to_converge == first
    assert pv.converge() == first  # 재호출은 캐시 반환


# --- 핵심 불변식: 무관찰 → Phase 436 과 정확히 동일 -------------------------


@pytest.mark.parametrize("n", [1, 2, 3, 5, 8])
def test_uniform_trust_matches_phase436_line(n):
    mesh = _line_mesh(n)
    tpv = TrustPathVectorRouting(mesh, _no_trust())
    pv = PathVectorRouting(mesh)
    tpv.converge()
    pv.converge()
    for origin in tpv.instances():
        assert tpv.routes(origin) == pv.routes(origin)


def test_uniform_trust_matches_phase436_diamond():
    mesh = _diamond_mesh()
    tpv = TrustPathVectorRouting(mesh, _no_trust())
    pv = PathVectorRouting(mesh)
    tpv.converge()
    pv.converge()
    for origin in tpv.instances():
        assert tpv.routes(origin) == pv.routes(origin)
    # 무신뢰면 사전식으로 A 가 먼저 — S→D 는 (S, A, D).
    assert tpv.best_path("S", "D") == ("S", "A", "D")


def test_zero_untrust_weight_ignores_trust():
    """untrust_weight=0 이면 신뢰 관찰이 있어도 Phase 436 과 동일(신뢰 무가중)."""
    mesh = _diamond_mesh()
    trust = _no_trust()
    _observe(trust, "S", "A", ok=0, bad=10)  # A 강한 불신
    tpv = TrustPathVectorRouting(mesh, trust, untrust_weight=0.0)
    pv = PathVectorRouting(mesh)
    tpv.converge()
    pv.converge()
    assert tpv.routes("S") == pv.routes("S")
    assert tpv.best_path("S", "D") == ("S", "A", "D")


# --- 신뢰 우선 선호 ---------------------------------------------------------


def test_distrust_reroutes_over_lexicographic_default():
    """S 가 A 를 불신하면, 사전식으로 더 큰 Z 를 거쳐 가도록 재라우팅된다."""
    mesh = _diamond_mesh()
    trust = _no_trust()
    _observe(trust, "S", "A", ok=0, bad=8)  # A 불신
    _observe(trust, "S", "Z", ok=8, bad=0)  # Z 신뢰
    tpv = TrustPathVectorRouting(mesh, trust)
    tpv.converge()
    assert tpv.best_path("S", "D") == ("S", "Z", "D")
    assert tpv.next_hop("S", "D") == "Z"
    # 도달성은 그대로 — 여전히 2홉.
    assert tpv.hop_count("S", "D") == 2


# --- 일반 불변식: 루프 없음·도달성·결정성 -----------------------------------


def test_paths_are_loop_free():
    mesh = _diamond_mesh()
    trust = _no_trust()
    _observe(trust, "S", "A", ok=0, bad=5)
    tpv = TrustPathVectorRouting(mesh, trust)
    tpv.converge()
    for origin in tpv.instances():
        for dst, path in tpv.routes(origin).items():
            assert len(path) == len(set(path)), f"{origin}->{dst} 경로에 루프"
            assert path[0] == origin and path[-1] == dst


def test_reachability_matches_mesh():
    """신뢰는 재배열만 — 도달 가능 집합은 Phase 436(=메시)과 동일."""
    mesh = _diamond_mesh()
    trust = _no_trust()
    _observe(trust, "S", "A", ok=0, bad=8)
    tpv = TrustPathVectorRouting(mesh, trust)
    pv = PathVectorRouting(mesh)
    tpv.converge()
    pv.converge()
    for origin in tpv.instances():
        assert set(tpv.routes(origin)) == set(pv.routes(origin))


def test_deterministic_across_builds():
    mesh = _diamond_mesh()
    trust = _no_trust()
    _observe(trust, "S", "A", ok=1, bad=6)
    _observe(trust, "Z", "D", ok=3, bad=0)
    a = TrustPathVectorRouting(mesh, trust)
    b = TrustPathVectorRouting(mesh, trust)
    a.converge()
    b.converge()
    assert a.rounds_to_converge == b.rounds_to_converge
    for origin in a.instances():
        assert a.routes(origin) == b.routes(origin)


def test_forwarding_table_matches_next_hops():
    mesh = _diamond_mesh()
    trust = _no_trust()
    _observe(trust, "S", "A", ok=0, bad=4)
    _observe(trust, "S", "Z", ok=4, bad=0)
    tpv = TrustPathVectorRouting(mesh, trust)
    tpv.converge()
    for origin in tpv.instances():
        table = tpv.forwarding_table(origin)
        assert origin not in table  # 자기 자신 제외
        for dst, nh in table.items():
            assert nh == tpv.next_hop(origin, dst)
            assert nh in mesh.neighbors(origin)


# --- 경계·검증 --------------------------------------------------------------


def test_negative_untrust_weight_rejected():
    with pytest.raises(ValueError):
        TrustPathVectorRouting(_line_mesh(2), _no_trust(), untrust_weight=-0.1)


def test_unknown_instance_raises_keyerror():
    tpv = TrustPathVectorRouting(_line_mesh(3), _no_trust())
    tpv.converge()
    with pytest.raises(KeyError):
        tpv.best_path("nope", "T0")
    with pytest.raises(KeyError):
        tpv.best_path("T0", "nope")
    with pytest.raises(KeyError):
        tpv.routes("nope")
    with pytest.raises(KeyError):
        tpv.forwarding_table("nope")


def test_disconnected_components_unreachable():
    """떨어진 두 타일 그룹은 서로 도달 불가(빈 경로)."""
    svc = FederationDiscoveryService(cell_size_m=500.0)
    svc.register("T0", _tile(0, 1000))
    svc.register("T1", _tile(1000, 2000))
    svc.register("F0", _tile(50000, 51000))  # 멀리 떨어진 고립 타일
    mesh = FederationMesh(svc)
    tpv = TrustPathVectorRouting(mesh, _no_trust())
    tpv.converge()
    assert tpv.best_path("T0", "F0") == ()
    assert tpv.hop_count("T0", "F0") == -1
    assert tpv.next_hop("T0", "F0") is None
