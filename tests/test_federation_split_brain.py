"""ODYSSEY Phase 430 — 분할 뇌 안전 강하 정책 단위 테스트."""

from __future__ import annotations

import pytest

from simulation.federation_split_brain import (
    DESCEND,
    HOLD,
    LAND,
    NOMINAL,
    PartitionSnapshot,
    SafeDescentPolicy,
)


def _fully_linked(*instances: str) -> PartitionSnapshot:
    """주어진 인스턴스를 모두 상호 연결한 스냅샷 (단일 과반 분파)."""
    pairs = {tuple(sorted((a, b))) for a in instances for b in instances if a < b}
    return PartitionSnapshot(instances=tuple(sorted(instances)), links=frozenset(pairs))


# --- PartitionSnapshot ------------------------------------------------------


def test_single_instance_is_its_own_majority():
    snap = PartitionSnapshot(instances=("A",), links=frozenset())
    assert snap.majority_component() == frozenset({"A"})
    assert snap.in_majority("A") is True


def test_fully_connected_three_is_one_majority():
    snap = _fully_linked("A", "B", "C")
    assert snap.majority_component() == frozenset({"A", "B", "C"})
    assert all(snap.in_majority(i) for i in ("A", "B", "C"))


def test_two_one_split_majority_is_the_pair():
    # A-B 연결, C 고립 → {A,B}가 과반(2*2 > 3).
    snap = PartitionSnapshot(instances=("A", "B", "C"), links=frozenset({("A", "B")}))
    assert snap.majority_component() == frozenset({"A", "B"})
    assert snap.in_majority("A") is True
    assert snap.in_majority("C") is False


def test_even_split_has_no_majority():
    # {A,B} vs {C,D} 균등 분할 → 어떤 분파도 과반 아님.
    snap = PartitionSnapshot(
        instances=("A", "B", "C", "D"),
        links=frozenset({("A", "B"), ("C", "D")}),
    )
    assert snap.majority_component() == frozenset()
    assert not any(snap.in_majority(i) for i in ("A", "B", "C", "D"))


def test_self_loop_link_rejected():
    with pytest.raises(ValueError):
        PartitionSnapshot(instances=("A", "B"), links=frozenset({("A", "A")}))


def test_unknown_instance_link_rejected():
    with pytest.raises(KeyError):
        PartitionSnapshot(instances=("A",), links=frozenset({("A", "B")}))


def test_component_of_unknown_instance_raises():
    snap = _fully_linked("A", "B")
    with pytest.raises(KeyError):
        snap.in_majority("Z")


# --- SafeDescentPolicy 기본 결정 --------------------------------------------


def test_nominal_when_majority_and_covered():
    policy = SafeDescentPolicy()
    snap = _fully_linked("A", "B", "C")
    d = policy.evaluate("drone1", "A", covered=True, partition=snap)
    assert d.action == NOMINAL
    assert d.reason == "nominal"


def test_orphaned_drone_lands_immediately():
    policy = SafeDescentPolicy()
    snap = _fully_linked("A", "B")
    d = policy.evaluate("drone1", None, covered=True, partition=snap)
    assert d.action == LAND
    assert d.reason == "orphaned"


def test_coverage_loss_triggers_descend():
    policy = SafeDescentPolicy()
    snap = _fully_linked("A", "B", "C")
    d = policy.evaluate("drone1", "A", covered=False, partition=snap)
    assert d.action == DESCEND
    assert d.reason == "coverage_lost"


def test_split_brain_minority_holds():
    policy = SafeDescentPolicy()
    # C 고립 → 과반은 {A,B}; C 관제 드론은 HOLD.
    snap = PartitionSnapshot(instances=("A", "B", "C"), links=frozenset({("A", "B")}))
    d = policy.evaluate("drone1", "C", covered=True, partition=snap)
    assert d.action == HOLD
    assert d.reason == "split_brain_isolated"


def test_even_split_both_sides_hold():
    policy = SafeDescentPolicy()
    snap = PartitionSnapshot(
        instances=("A", "B", "C", "D"),
        links=frozenset({("A", "B"), ("C", "D")}),
    )
    assert policy.evaluate("d1", "A", covered=True, partition=snap).action == HOLD
    assert policy.evaluate("d2", "C", covered=True, partition=snap).action == HOLD


def test_unregistered_controller_raises():
    policy = SafeDescentPolicy()
    snap = _fully_linked("A", "B")
    with pytest.raises(KeyError):
        policy.evaluate("drone1", "Z", covered=True, partition=snap)


def test_empty_drone_id_raises():
    policy = SafeDescentPolicy()
    snap = _fully_linked("A")
    with pytest.raises(ValueError):
        policy.evaluate("", "A", covered=True, partition=snap)


# --- 에스컬레이션·이력현상 ---------------------------------------------------


def test_prolonged_isolation_escalates_hold_to_descend():
    policy = SafeDescentPolicy(hold_limit=2, descend_limit=5)
    snap = PartitionSnapshot(instances=("A", "B", "C"), links=frozenset({("A", "B")}))
    actions = [policy.evaluate("drone1", "C", covered=True, partition=snap).action for _ in range(4)]
    # hold_limit=2 → 처음 2틱 HOLD, 3틱째부터 DESCEND 로 상승.
    assert actions == [HOLD, HOLD, DESCEND, DESCEND]


def test_prolonged_descend_escalates_to_land():
    policy = SafeDescentPolicy(descend_limit=2)
    snap = _fully_linked("A", "B", "C")
    actions = [policy.evaluate("drone1", "A", covered=False, partition=snap).action for _ in range(4)]
    # descend_limit=2 → 처음 2틱 DESCEND, 3틱째부터 LAND.
    assert actions == [DESCEND, DESCEND, LAND, LAND]


def test_recovery_resets_escalation_counters():
    policy = SafeDescentPolicy(descend_limit=2)
    snap_lost = _fully_linked("A", "B", "C")
    # 강하 2틱 누적.
    policy.evaluate("drone1", "A", covered=False, partition=snap_lost)
    policy.evaluate("drone1", "A", covered=False, partition=snap_lost)
    # 정상 복귀 → 카운터 초기화.
    nominal = policy.evaluate("drone1", "A", covered=True, partition=snap_lost)
    assert nominal.action == NOMINAL
    assert nominal.descend_ticks == 0
    # 다시 커버리지 상실 → LAND 가 아니라 DESCEND 부터 재시작.
    again = policy.evaluate("drone1", "A", covered=False, partition=snap_lost)
    assert again.action == DESCEND


# --- 감사 로그·재현성 -------------------------------------------------------


def test_audit_log_seq_is_gapless_and_ordered():
    policy = SafeDescentPolicy()
    snap = _fully_linked("A", "B", "C")
    for _ in range(5):
        policy.evaluate("drone1", "A", covered=True, partition=snap)
    seqs = [d.seq for d in policy.log()]
    assert seqs == [1, 2, 3, 4, 5]


def test_action_counts_summary():
    policy = SafeDescentPolicy(hold_limit=10)
    snap_ok = _fully_linked("A", "B", "C")
    snap_iso = PartitionSnapshot(instances=("A", "B", "C"), links=frozenset({("A", "B")}))
    policy.evaluate("d", "A", covered=True, partition=snap_ok)  # NOMINAL
    policy.evaluate("d", "A", covered=False, partition=snap_ok)  # DESCEND
    policy.evaluate("d", "C", covered=True, partition=snap_iso)  # HOLD
    policy.evaluate("d", None, covered=True, partition=snap_ok)  # LAND
    counts = policy.action_counts()
    assert counts == {NOMINAL: 1, HOLD: 1, DESCEND: 1, LAND: 1}


def test_deterministic_replay_identical_log():
    snap = PartitionSnapshot(instances=("A", "B", "C"), links=frozenset({("A", "B")}))

    def run() -> list[tuple[int, str, str]]:
        policy = SafeDescentPolicy(hold_limit=1)
        out = []
        for covered in (True, True, False, True):
            d = policy.evaluate("drone1", "C", covered=covered, partition=snap)
            out.append((d.seq, d.action, d.reason))
        return out

    assert run() == run()
