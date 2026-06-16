"""ODYSSEY Phase 433 — 신뢰 가중 메시 라우팅 단위 테스트.

외부 의존성 0(순수 결정적). Phase 432 메시 + Phase 428 신뢰 위에서 동작한다.

토폴로지(다이아몬드, 대각 인접 없음)::

        B
      /   \\
    A       D
      \\   /
        C

  A·D 는 직접 인접하지 않고 B 또는 C 중계를 거쳐야 한다. B·C 는 y 간격으로
  서로 인접하지 않는다(평행 중계).
"""

from __future__ import annotations

import math

import pytest

from simulation.federation_discovery import FederationDiscoveryService, Volume4D
from simulation.federation_mesh import FederationMesh
from simulation.federation_trust import FederationTrustModel
from simulation.federation_trust_routing import TrustWeightedRouter


def _diamond_service() -> FederationDiscoveryService:
    """A-B, A-C, B-D, C-D 만 인접한 다이아몬드 디스커버리(A·D 비인접, B·C 비인접)."""
    svc = FederationDiscoveryService()
    # A·D 는 y[0,2000] 전체를 덮는 서·동 타일, B·C 는 y 로 분리된 중간 평행 타일.
    svc.register("A", Volume4D(0, 1000, 0, 2000, 0, 120, 0, 600))
    svc.register("B", Volume4D(1000, 2000, 0, 900, 0, 120, 0, 600))
    svc.register("C", Volume4D(1000, 2000, 1100, 2000, 0, 120, 0, 600))
    svc.register("D", Volume4D(2000, 3000, 0, 2000, 0, 120, 0, 600))
    return svc


def _diamond_mesh() -> FederationMesh:
    """다이아몬드 디스커버리 위에 구성한 메시."""
    return FederationMesh(_diamond_service())


def _build(
    observations: list[tuple[str, str, bool, int]] | None = None,
    **kwargs,
) -> TrustWeightedRouter:
    """다이아몬드 메시 + 지정 관찰을 누적한 신뢰 모델로 라우터를 만든다.

    observations: (observer, target, success, count) 리스트.
    """
    trust = FederationTrustModel()
    for observer, target, success, count in observations or []:
        for _ in range(count):
            trust.observe(observer, target, success, kind="handover")
    return TrustWeightedRouter(_diamond_mesh(), trust, **kwargs)


# --- 토폴로지 sanity (다이아몬드가 의도대로 구성됐는지) ----------------------


def test_diamond_topology_is_as_designed():
    mesh = _diamond_mesh()
    assert mesh.neighbors("A") == ("B", "C")
    assert mesh.neighbors("B") == ("A", "D")
    assert mesh.neighbors("C") == ("A", "D")
    assert mesh.neighbors("D") == ("B", "C")


# --- relay_trust ------------------------------------------------------------


def test_relay_trust_self_is_perfect():
    router = _build()
    assert router.relay_trust("A", "A") == 1.0


def test_relay_trust_unobserved_is_neutral_prior():
    router = _build()
    assert router.relay_trust("A", "B") == pytest.approx(0.5)


def test_relay_trust_rises_with_successes():
    router = _build([("A", "B", True, 6)])
    assert router.relay_trust("A", "B") == pytest.approx(7.0 / 8.0)


def test_relay_trust_falls_with_failures():
    router = _build([("A", "C", False, 6)])
    assert router.relay_trust("A", "C") == pytest.approx(1.0 / 8.0)


# --- route: 신뢰 가중 경로 선택 ---------------------------------------------


def test_route_self_returns_single_node():
    router = _build()
    assert router.route("A", "A") == ("A",)


def test_route_direct_neighbor():
    router = _build()
    assert router.route("A", "B") == ("A", "B")


def test_route_tie_broken_lexicographically_when_no_trust_signal():
    # 관찰 0 → 모든 중계 신뢰 0.5 동일 → 비용 동률 → 경로 사전식(B<C) 우선.
    router = _build()
    assert router.route("A", "D") == ("A", "B", "D")


def test_route_prefers_trusted_relay():
    # A 가 C 를 신뢰, B 를 불신 → 사전식 우선(B)을 뒤집고 C 경유 선택.
    router = _build([("A", "C", True, 6), ("A", "B", False, 6)])
    assert router.route("A", "D") == ("A", "C", "D")


def test_route_avoids_untrusted_relay():
    router = _build([("A", "B", False, 8)])
    # B 불신 → 신뢰 가중 비용이 C 경유보다 커져 C 선택.
    assert router.route("A", "D") == ("A", "C", "D")


def test_route_symmetric_topology_back():
    router = _build([("D", "B", True, 6)])
    assert router.route("D", "A") == ("D", "B", "A")


def test_route_unreachable_returns_empty():
    svc = _diamond_service()
    svc.register("ISO", Volume4D(9000, 9500, 9000, 9500, 0, 120, 0, 600))
    router = TrustWeightedRouter(FederationMesh(svc), FederationTrustModel())
    assert router.route("A", "ISO") == ()


def test_route_unregistered_raises_keyerror():
    router = _build()
    with pytest.raises(KeyError):
        router.route("A", "NOPE")
    with pytest.raises(KeyError):
        router.route("NOPE", "A")


def test_route_deterministic_repeat():
    router = _build([("A", "C", True, 6), ("A", "B", False, 6)])
    first = router.route("A", "D")
    assert all(router.route("A", "D") == first for _ in range(5))


# --- route_cost -------------------------------------------------------------


def test_route_cost_self_is_zero():
    router = _build()
    assert router.route_cost("A", "A") == 0.0


def test_route_cost_unreachable_is_inf():
    svc = _diamond_service()
    svc.register("ISO", Volume4D(9000, 9500, 9000, 9500, 0, 120, 0, 600))
    router = TrustWeightedRouter(FederationMesh(svc), FederationTrustModel())
    assert router.route_cost("A", "ISO") == math.inf


def test_route_cost_trusted_relay_cheaper_than_neutral():
    # A→B 완전 신뢰(6승) → 간선 비용 hop_cost(1.0) 으로 환원.
    router = _build([("A", "B", True, 100)])
    # A→B 거의 1.0, B→D 미관찰 0.5 → 1.5. 총 ≈ 2.5.
    cost = router.route_cost("A", "B")
    assert cost == pytest.approx(1.0 + 1.0 * (1.0 - 101.0 / 102.0))


def test_route_cost_reflects_full_path():
    router = _build()
    # 미관찰: 각 간선 = 1.0 + 1.0*0.5 = 1.5, 2홉 → 3.0.
    assert router.route_cost("A", "D") == pytest.approx(3.0)


def test_zero_untrust_weight_reduces_to_hop_count():
    router = _build([("A", "B", False, 8)], untrust_weight=0.0)
    # 신뢰 페널티 제거 → 순수 홉 수, 동률 사전식 → B 경유, 비용 = 2*hop_cost.
    assert router.route("A", "D") == ("A", "B", "D")
    assert router.route_cost("A", "D") == pytest.approx(2.0)


# --- avoid_untrusted_route --------------------------------------------------


def test_avoid_self():
    router = _build()
    assert router.avoid_untrusted_route("A", "A") == ("A",)


def test_avoid_picks_trusted_path_when_relay_untrusted():
    router = _build([("A", "B", False, 8)])  # B 불신
    assert router.avoid_untrusted_route("A", "D") == ("A", "C", "D")


def test_avoid_returns_empty_when_all_relays_untrusted():
    router = _build([("A", "B", False, 8), ("A", "C", False, 8)])
    assert router.avoid_untrusted_route("A", "D") == ()


def test_avoid_allows_untrusted_destination():
    # D 자체가 불신이어도 종단점이므로 경로 허용(중계 B·C 는 미관찰=허용).
    router = _build([("A", "D", False, 8)])
    path = router.avoid_untrusted_route("A", "D")
    assert path in (("A", "B", "D"), ("A", "C", "D"))
    assert path[-1] == "D"


def test_avoid_ignores_unobserved_relays():
    # 미관찰 중계는 불신으로 단정하지 않음 → 최단 경로 그대로(사전식 B).
    router = _build()
    assert router.avoid_untrusted_route("A", "D") == ("A", "B", "D")


def test_avoid_unregistered_raises_keyerror():
    router = _build()
    with pytest.raises(KeyError):
        router.avoid_untrusted_route("A", "NOPE")


def test_avoid_min_observations_gate():
    # 실패 4건(<5) → 증거 부족 → 불신 단정 안 함 → B 경유 허용.
    router = _build([("A", "B", False, 4)])
    assert router.avoid_untrusted_route("A", "D") == ("A", "B", "D")


# --- forwarding_table -------------------------------------------------------


def test_forwarding_table_maps_each_destination_to_first_hop():
    router = _build()
    table = router.forwarding_table("A")
    assert table["B"] == "B"
    assert table["C"] == "C"
    assert table["D"] == "B"  # 동률 → 사전식 B 우선
    assert "A" not in table


def test_forwarding_table_respects_trust():
    router = _build([("A", "B", False, 8)])  # B 불신 → D 는 C 경유
    table = router.forwarding_table("A")
    assert table["D"] == "C"


def test_forwarding_table_excludes_unreachable():
    svc = _diamond_service()
    svc.register("ISO", Volume4D(9000, 9500, 9000, 9500, 0, 120, 0, 600))
    router = TrustWeightedRouter(FederationMesh(svc), FederationTrustModel())
    assert "ISO" not in router.forwarding_table("A")


def test_forwarding_table_unregistered_raises_keyerror():
    router = _build()
    with pytest.raises(KeyError):
        router.forwarding_table("NOPE")


# --- 생성자 검증 ------------------------------------------------------------


def test_constructor_rejects_nonpositive_hop_cost():
    with pytest.raises(ValueError):
        TrustWeightedRouter(_diamond_mesh(), FederationTrustModel(), hop_cost=0.0)


def test_constructor_rejects_negative_untrust_weight():
    with pytest.raises(ValueError):
        TrustWeightedRouter(_diamond_mesh(), FederationTrustModel(), untrust_weight=-1.0)


def test_constructor_rejects_negative_min_observations():
    with pytest.raises(ValueError):
        TrustWeightedRouter(_diamond_mesh(), FederationTrustModel(), min_observations=-1)


@pytest.mark.parametrize("bad", [0.0, 1.0, -0.1, 1.5])
def test_constructor_rejects_out_of_range_trust_threshold(bad):
    with pytest.raises(ValueError):
        TrustWeightedRouter(_diamond_mesh(), FederationTrustModel(), trust_threshold=bad)
