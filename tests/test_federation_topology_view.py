"""ODYSSEY Phase 439 — 신뢰 한정 도달성 통합 토폴로지 단위 테스트.

외부 의존성 0(순수 결정적). Phase 432 메시 + Phase 428 신뢰 위에서 동작한다.
다이아몬드 토폴로지(A-B, A-C, B-D, C-D)로 3+ 인스턴스 중계 신뢰를 검증한다.
"""

from __future__ import annotations

import pytest

from simulation.federation_discovery import FederationDiscoveryService, Volume4D
from simulation.federation_mesh import FederationMesh
from simulation.federation_topology_view import (
    CLASS_DIRECT,
    CLASS_RELAYED_RISKY,
    CLASS_RELAYED_TRUSTED,
    CLASS_SELF,
    CLASS_UNREACHABLE,
    REACHABILITY_CLASSES,
    FederationTopologyView,
)
from simulation.federation_trust import FederationTrustModel


def _diamond_service() -> FederationDiscoveryService:
    """A-B, A-C, B-D, C-D 만 인접한 다이아몬드(A·D 비인접, B·C 비인접)."""
    svc = FederationDiscoveryService()
    svc.register("A", Volume4D(0, 1000, 0, 2000, 0, 120, 0, 600))
    svc.register("B", Volume4D(1000, 2000, 0, 900, 0, 120, 0, 600))
    svc.register("C", Volume4D(1000, 2000, 1100, 2000, 0, 120, 0, 600))
    svc.register("D", Volume4D(2000, 3000, 0, 2000, 0, 120, 0, 600))
    return svc


def _diamond_mesh() -> FederationMesh:
    return FederationMesh(_diamond_service())


def _build(
    observations: list[tuple[str, str, bool, int]] | None = None,
    **kwargs,
) -> FederationTopologyView:
    """다이아몬드 메시 + 지정 관찰을 누적한 신뢰 모델로 뷰를 만든다.

    observations: (observer, target, success, count) 리스트.
    """
    trust = FederationTrustModel()
    for observer, target, success, count in observations or []:
        for _ in range(count):
            trust.observe(observer, target, success, kind="handover")
    return FederationTopologyView(_diamond_mesh(), trust, **kwargs)


# --- 토폴로지 sanity --------------------------------------------------------


def test_diamond_topology_is_as_designed():
    mesh = _diamond_mesh()
    assert mesh.neighbors("A") == ("B", "C")
    assert mesh.neighbors("D") == ("B", "C")
    assert "D" not in mesh.neighbors("A")


def test_instances_sorted():
    view = _build()
    assert view.instances() == ("A", "B", "C", "D")


# --- 분류: SELF / DIRECT / UNREACHABLE -------------------------------------


def test_self_is_classified_self():
    view = _build()
    assert view.reachability_class("A", "A") == CLASS_SELF


def test_direct_neighbor_is_direct_regardless_of_trust():
    # B 가 미검증이어도 직접 이웃이므로 중계 위험이 없다 → DIRECT.
    view = _build()
    assert view.reachability_class("A", "B") == CLASS_DIRECT
    assert view.reachability_class("A", "C") == CLASS_DIRECT


def test_unreachable_when_mesh_disconnected():
    svc = FederationDiscoveryService()
    svc.register("X", Volume4D(0, 1000, 0, 1000, 0, 120, 0, 600))
    svc.register("Y", Volume4D(5000, 6000, 0, 1000, 0, 120, 0, 600))
    view = FederationTopologyView(FederationMesh(svc), FederationTrustModel())
    assert view.reachability_class("X", "Y") == CLASS_UNREACHABLE


# --- 분류: RELAYED (3+ 인스턴스 중계 신뢰의 핵심) ---------------------------


def test_relayed_trusted_when_one_relay_trusted():
    # A 가 중계 B 를 적극 신뢰 → A→D 는 B 경유 완전-신뢰 경로 존재.
    view = _build([("A", "B", True, 5)])
    assert view.reachability_class("A", "D") == CLASS_RELAYED_TRUSTED
    assert view.trusted_path("A", "D") == ("A", "B", "D")


def test_relayed_risky_when_no_relay_observed():
    # 미검증 중계는 적극 신뢰가 아니므로 완전-신뢰 경로가 없다 → RISKY.
    view = _build()
    assert view.reachability_class("A", "D") == CLASS_RELAYED_RISKY
    assert view.trusted_path("A", "D") == ()


def test_relayed_risky_when_all_relays_observed_low_trust():
    view = _build([("A", "B", False, 5), ("A", "C", False, 5)])
    assert view.reachability_class("A", "D") == CLASS_RELAYED_RISKY


def test_unverified_relay_not_used_unlike_avoid_untrusted():
    # Phase 433 avoid_untrusted_route 는 미검증 중계를 통과시키지만(무죄 추정),
    # 본 모듈은 적극 신뢰만 통과시킨다 → 미검증이면 경로 없음(더 엄격).
    view = _build([("A", "B", True, 4)])  # 4건 < 게이트 5건 → 미검증
    assert view.trusted_path("A", "D") == ()
    assert view.reachability_class("A", "D") == CLASS_RELAYED_RISKY


# --- trusted_path 규약 ------------------------------------------------------


def test_trusted_path_self_returns_single_node():
    assert _build().trusted_path("A", "A") == ("A",)


def test_trusted_path_direct_neighbor_length_two():
    # 직접 이웃은 중계가 없어 신뢰 무관하게 신뢰 경로다.
    assert _build().trusted_path("A", "B") == ("A", "B")


def test_trusted_path_tie_broken_lexicographically():
    # B·C 둘 다 신뢰 → 정렬 이웃 우선으로 B 경유.
    view = _build([("A", "B", True, 5), ("A", "C", True, 5)])
    assert view.trusted_path("A", "D") == ("A", "B", "D")


def test_trusted_path_picks_only_trusted_relay():
    # B 불신·C 신뢰 → C 경유.
    view = _build([("A", "B", False, 5), ("A", "C", True, 5)])
    assert view.trusted_path("A", "D") == ("A", "C", "D")


def test_trusted_path_allows_untrusted_destination():
    # 목적지 D 자체가 저신뢰여도 종단점이라 허용. 중계 C 는 신뢰.
    view = _build([("A", "C", True, 5), ("A", "D", False, 5)])
    assert view.trusted_path("A", "D") == ("A", "C", "D")


def test_trusted_path_uses_origin_own_beliefs_only():
    # B→C 신뢰는 A 의 경로 판정에 영향 없음(방향성·origin 관점).
    view = _build([("B", "C", True, 9)])
    assert view.trusted_path("A", "D") == ()


# --- 집계 도달 집합 ---------------------------------------------------------


def test_classify_excludes_origin_and_covers_others():
    view = _build([("A", "B", True, 5)])
    labels = view.classify("A")
    assert set(labels) == {"B", "C", "D"}
    assert labels == {"B": CLASS_DIRECT, "C": CLASS_DIRECT, "D": CLASS_RELAYED_TRUSTED}


def test_trusted_reach_includes_direct_and_trusted_relay():
    view = _build([("A", "B", True, 5)])
    assert view.trusted_reach("A") == ("B", "C", "D")


def test_trusted_reach_excludes_risky_destination():
    view = _build()  # 중계 미검증 → D 위험
    assert view.trusted_reach("A") == ("B", "C")


def test_risky_reach_lists_only_risky():
    view = _build()
    assert view.risky_reach("A") == ("D",)


def test_aggregates_consistent_with_classify():
    # trusted_reach·risky_reach 는 classify 와 동일 분류여야 한다(단일 분류 경로).
    view = _build([("A", "B", True, 5)])
    labels = view.classify("A")
    expected_trusted = tuple(
        sorted(d for d, l in labels.items() if l in (CLASS_DIRECT, CLASS_RELAYED_TRUSTED))
    )
    expected_risky = tuple(sorted(d for d, l in labels.items() if l == CLASS_RELAYED_RISKY))
    assert view.trusted_reach("A") == expected_trusted
    assert view.risky_reach("A") == expected_risky


# --- summary ----------------------------------------------------------------


def test_summary_has_all_class_keys():
    counts = _build().summary()
    assert set(counts) == set(REACHABILITY_CLASSES)


def test_summary_counts_ordered_pairs():
    # 4 인스턴스 → 4*3 = 12 순서쌍. SELF 는 제외되므로 합 = 12.
    counts = _build([("A", "B", True, 5)]).summary()
    assert sum(counts.values()) == 12
    # DIRECT 간선: A-B,A-C,B-A,B-D,C-A,C-D,D-B,D-C = 8 (양방향).
    assert counts[CLASS_DIRECT] == 8
    # A→D 는 B 신뢰 경유 → TRUSTED. 나머지 비인접쌍(D→A, B→C, C→B)은 RISKY.
    assert counts[CLASS_RELAYED_TRUSTED] == 1
    assert counts[CLASS_RELAYED_RISKY] == 3
    assert counts[CLASS_UNREACHABLE] == 0


# --- 입력 검증·결정성 -------------------------------------------------------


def test_unregistered_raises_keyerror():
    view = _build()
    with pytest.raises(KeyError):
        view.reachability_class("A", "Z")
    with pytest.raises(KeyError):
        view.trusted_path("Z", "A")
    with pytest.raises(KeyError):
        view.classify("Z")


def test_invalid_threshold_raises():
    with pytest.raises(ValueError):
        FederationTopologyView(_diamond_mesh(), FederationTrustModel(), trust_threshold=0.0)
    with pytest.raises(ValueError):
        FederationTopologyView(_diamond_mesh(), FederationTrustModel(), trust_threshold=1.0)


def test_invalid_min_observations_raises():
    with pytest.raises(ValueError):
        FederationTopologyView(
            _diamond_mesh(), FederationTrustModel(), min_observations=-1
        )


def test_min_observations_gate_configurable():
    # min_observations=4 로 낮추면 4건 관찰도 적극 신뢰로 인정.
    view = _build([("A", "B", True, 4)], min_observations=4)
    assert view.trusted_path("A", "D") == ("A", "B", "D")


def test_deterministic_repeat():
    view = _build([("A", "B", True, 5), ("A", "C", True, 5)])
    first = (view.trusted_path("A", "D"), view.classify("A"), view.summary())
    second = (view.trusted_path("A", "D"), view.classify("A"), view.summary())
    assert first == second
