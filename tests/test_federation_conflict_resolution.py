"""ODYSSEY Phase 424 — 연합 충돌 해소(인스턴스 간 우선순위 협상) 단위 테스트.

Phase 422 `intents_conflict` 위에서 충돌을 탐지하고, Phase 602 Vickrey 경매를
재사용해 어느 운영 의도가 경합 공역을 점유할지 결정한다. 외부 무작위성 없이
완전 결정적이며, 동률 우선순위는 intent_id 의 재현 가능한 해시로 분리한다.
"""

from __future__ import annotations

import pytest

from simulation.operational_intent import OperationalIntent, Volume4D
from simulation.federation_conflict_resolution import (
    CONTINGENT,
    ConflictResolution,
    FederationConflictResolver,
)


def _vol(t0: float = 0.0, t1: float = 60.0) -> Volume4D:
    """목포 해역 인근 작은 4D 볼륨 (시간 창만 가변)."""
    return Volume4D(
        outline=((34.79, 126.39), (34.81, 126.39), (34.81, 126.41), (34.79, 126.41)),
        altitude_lower_m=0.0,
        altitude_upper_m=120.0,
        time_start_s=t0,
        time_end_s=t1,
    )


def _intent(intent_id: str, priority: int, t0: float = 0.0, t1: float = 60.0) -> OperationalIntent:
    return OperationalIntent(
        intent_id=intent_id, state="ACCEPTED", priority=priority, volumes=(_vol(t0, t1),)
    )


def test_no_conflict_returns_none() -> None:
    # Arrange — 시간 창이 겹치지 않으면 충돌 없음
    a = _intent("A", priority=2, t0=0.0, t1=30.0)
    b = _intent("B", priority=2, t0=30.0, t1=60.0)
    resolver = FederationConflictResolver()

    # Act
    result = resolver.resolve_pair(a, b)

    # Assert
    assert result is None
    assert resolver.audit_log == ()


def test_higher_priority_wins() -> None:
    # Arrange — priority 1 이 priority 5 보다 우선(낮은 번호 = 높은 우선순위)
    high = _intent("HIGH", priority=1)
    low = _intent("LOW", priority=5)
    resolver = FederationConflictResolver()

    # Act
    result = resolver.resolve_pair(low, high)

    # Assert
    assert result is not None
    assert result.winner == "HIGH"
    assert result.loser == "LOW"


def test_clearing_price_is_second_highest_bid() -> None:
    # Arrange
    high = _intent("HIGH", priority=1)
    low = _intent("LOW", priority=5)
    resolver = FederationConflictResolver()

    bid_high = resolver.priority_bid(high)
    bid_low = resolver.priority_bid(low)

    # Act
    result = resolver.resolve_pair(high, low)

    # Assert — Vickrey 2위 가격제: 승자=최고입찰(high), 청산가=차순위(=패자 low 입찰)
    assert result.winning_bid > result.clearing_price
    assert result.winning_bid == pytest.approx(bid_high)
    assert result.clearing_price == pytest.approx(bid_low)


def test_equal_priority_is_deterministic_and_reproducible() -> None:
    # Arrange — 동률 우선순위, 두 개의 독립 resolver
    a = _intent("alpha", priority=3)
    b = _intent("bravo", priority=3)

    # Act — 입력 순서를 바꿔도 같은 승자
    r1 = FederationConflictResolver().resolve_pair(a, b)
    r2 = FederationConflictResolver().resolve_pair(b, a)

    # Assert
    assert r1.winner == r2.winner
    assert r1.loser == r2.loser


def test_ended_intent_does_not_conflict() -> None:
    # Arrange — 종료된 의도는 공역을 점유하지 않음
    ended = OperationalIntent("OLD", state="ENDED", priority=1, volumes=(_vol(),))
    live = _intent("NEW", priority=9)
    resolver = FederationConflictResolver()

    # Act
    result = resolver.resolve_pair(ended, live)

    # Assert
    assert result is None


def test_audit_log_is_immutable_and_records_resolution() -> None:
    # Arrange
    high = _intent("HIGH", priority=1)
    low = _intent("LOW", priority=5)
    resolver = FederationConflictResolver()

    # Act
    resolver.resolve_pair(high, low)
    log = resolver.audit_log

    # Assert — 튜플(불변)이며 한 건 기록, 외부 변형이 내부에 영향 없음
    assert isinstance(log, tuple)
    assert len(log) == 1
    assert isinstance(log[0], ConflictResolution)
    with pytest.raises(AttributeError):
        log[0].winner = "X"  # frozen dataclass


def test_resolve_all_returns_resolution_per_conflicting_pair() -> None:
    # Arrange — 세 의도가 같은 공역·시간에서 모두 충돌(3쌍)
    intents = [_intent("A", 1), _intent("B", 2), _intent("C", 3)]
    resolver = FederationConflictResolver()

    # Act
    resolutions = resolver.resolve_all(intents)

    # Assert — C(3,2) = 3 쌍, 모두 우선순위 1 의도(A)가 자신이 낀 쌍에서 승리
    assert len(resolutions) == 3
    a_wins = [r for r in resolutions if "A" in (r.intent_a, r.intent_b)]
    assert all(r.winner == "A" for r in a_wins)


def test_apply_resolutions_sets_loser_contingent_immutably() -> None:
    # Arrange
    high = _intent("HIGH", priority=1)
    low = _intent("LOW", priority=5)
    resolver = FederationConflictResolver()
    resolutions = resolver.resolve_all([high, low])

    # Act
    updated = resolver.apply_resolutions([high, low], resolutions)
    by_id = {oi.intent_id: oi for oi in updated}

    # Assert — 패자 CONTINGENT, 승자 불변, 원본 객체 미변형(불변성)
    assert by_id["LOW"].state == CONTINGENT
    assert by_id["HIGH"].state == "ACCEPTED"
    assert low.state == "ACCEPTED"  # 원본 보존


def test_priority_beyond_capacity_raises() -> None:
    # Arrange — max_priority 를 넘는 우선순위는 입찰가가 음수가 되므로 거부
    resolver = FederationConflictResolver(max_priority=5)
    over = _intent("OVER", priority=9)

    # Act / Assert
    with pytest.raises(ValueError):
        resolver.priority_bid(over)


def test_max_priority_below_two_rejected() -> None:
    # Arrange / Act / Assert — priority>=1 이므로 max_priority<2 면 사용 불가 resolver
    with pytest.raises(ValueError):
        FederationConflictResolver(max_priority=1)


def test_resolve_all_skips_already_contingent_intents() -> None:
    # Arrange — 단발 협상 후 결과를 재투입해도 양보 의도가 재경합하지 않음
    high = _intent("HIGH", priority=1)
    low = _intent("LOW", priority=5)
    resolver = FederationConflictResolver()
    first = resolver.resolve_all([high, low])
    settled = resolver.apply_resolutions([high, low], first)

    # Act — CONTINGENT 가 된 LOW 가 포함된 목록을 다시 협상
    second = resolver.resolve_all(list(settled))

    # Assert — 재경합 없음(빈 결과)
    assert second == []
