"""ODYSSEY Phase 429 (Federation) 연합 감사 로그 단위 테스트.

변조 탐지 해시 체인 + 결정적 CRDT 류 병합의 불변식을 검증한다.
"""

import pytest

from simulation.federation_audit import (
    GENESIS_DIGEST,
    AuditEntry,
    FederationAuditLog,
)

# --- record / 기본 체인 ---------------------------------------------------


def test_empty_log_head_is_genesis():
    log = FederationAuditLog()
    assert log.entries() == ()
    assert log.head_digest() == GENESIS_DIGEST
    assert log.verify() is True


def test_record_returns_chained_entry():
    log = FederationAuditLog()
    entry = log.record("uss-a", "HANDOVER", "drone-1 ACQUIRED", logical_clock=1)
    assert entry.seq == 0
    assert entry.instance_id == "uss-a"
    assert entry.prev_digest == GENESIS_DIGEST
    assert entry.digest != GENESIS_DIGEST
    assert log.head_digest() == entry.digest


def test_second_entry_links_to_first():
    log = FederationAuditLog()
    first = log.record("uss-a", "NOTAM", "nfz-1 DELIVERED", logical_clock=1)
    second = log.record("uss-a", "CONFLICT", "intent-x loses", logical_clock=2)
    assert second.seq == 1
    assert second.prev_digest == first.digest
    assert log.head_digest() == second.digest


def test_entries_returns_immutable_copy():
    log = FederationAuditLog()
    log.record("uss-a", "TRUST", "uss-b trusted", logical_clock=1)
    snapshot = log.entries()
    assert isinstance(snapshot, tuple)
    log.record("uss-a", "TRUST", "uss-c trusted", logical_clock=2)
    assert len(snapshot) == 1  # 기존 스냅샷은 영향받지 않음


def test_determinism_same_sequence_same_digest():
    def build():
        log = FederationAuditLog()
        log.record("uss-a", "HANDOVER", "d1", logical_clock=1)
        log.record("uss-b", "NOTAM", "n1", logical_clock=5)
        return log

    assert build().head_digest() == build().head_digest()


# --- 경계 검증 ------------------------------------------------------------


def test_empty_instance_id_rejected():
    log = FederationAuditLog()
    with pytest.raises(ValueError, match="instance_id"):
        log.record("", "HANDOVER", "x", logical_clock=1)


def test_empty_event_type_rejected():
    log = FederationAuditLog()
    with pytest.raises(ValueError, match="event_type"):
        log.record("uss-a", "", "x", logical_clock=1)


def test_separator_in_instance_id_rejected():
    log = FederationAuditLog()
    with pytest.raises(ValueError, match="구분자"):
        log.record("us|s", "HANDOVER", "ok", logical_clock=1)


def test_separator_in_event_type_rejected():
    log = FederationAuditLog()
    with pytest.raises(ValueError, match="구분자"):
        log.record("uss-a", "HAND|OVER", "ok", logical_clock=1)


def test_separator_in_detail_rejected():
    log = FederationAuditLog()
    with pytest.raises(ValueError, match="구분자"):
        log.record("uss-a", "HANDOVER", "de|tail", logical_clock=1)


def test_non_monotonic_clock_same_instance_rejected():
    log = FederationAuditLog()
    log.record("uss-a", "HANDOVER", "x", logical_clock=5)
    with pytest.raises(ValueError, match="단조 증가"):
        log.record("uss-a", "HANDOVER", "y", logical_clock=5)
    with pytest.raises(ValueError, match="단조 증가"):
        log.record("uss-a", "HANDOVER", "z", logical_clock=4)


def test_clocks_independent_per_instance():
    log = FederationAuditLog()
    log.record("uss-a", "HANDOVER", "x", logical_clock=10)
    # 다른 인스턴스는 더 작은 시각이어도 허용(인스턴스별 독립 시계).
    entry = log.record("uss-b", "HANDOVER", "y", logical_clock=1)
    assert entry.instance_id == "uss-b"


# --- verify / 변조 탐지 ---------------------------------------------------


def test_verify_true_for_untampered_chain():
    log = FederationAuditLog()
    for i in range(1, 6):
        log.record("uss-a", "EVENT", f"e{i}", logical_clock=i)
    assert log.verify() is True


def test_verify_detects_tampered_detail():
    log = FederationAuditLog()
    log.record("uss-a", "EVENT", "original", logical_clock=1)
    log.record("uss-a", "EVENT", "next", logical_clock=2)
    # 중간 항목의 detail 을 몰래 바꾼다(frozen 이라 리스트 슬롯을 교체).
    tampered = AuditEntry(
        seq=0,
        logical_clock=1,
        instance_id="uss-a",
        event_type="EVENT",
        detail="forged",
        prev_digest=GENESIS_DIGEST,
        digest=log.entries()[0].digest,  # 옛 다이제스트 유지 → 불일치
    )
    log._entries[0] = tampered
    assert log.verify() is False


def test_verify_detects_deleted_entry():
    log = FederationAuditLog()
    log.record("uss-a", "EVENT", "a", logical_clock=1)
    log.record("uss-a", "EVENT", "b", logical_clock=2)
    log.record("uss-a", "EVENT", "c", logical_clock=3)
    del log._entries[1]  # 중간 항목 삭제 → 체인 prev_digest 깨짐
    assert log.verify() is False


# --- query ---------------------------------------------------------------


def test_query_by_instance():
    log = FederationAuditLog()
    log.record("uss-a", "HANDOVER", "x", logical_clock=1)
    log.record("uss-b", "NOTAM", "y", logical_clock=1)
    log.record("uss-a", "CONFLICT", "z", logical_clock=2)
    result = log.query(instance_id="uss-a")
    assert [e.detail for e in result] == ["x", "z"]


def test_query_by_event_type():
    log = FederationAuditLog()
    log.record("uss-a", "HANDOVER", "x", logical_clock=1)
    log.record("uss-b", "HANDOVER", "y", logical_clock=1)
    log.record("uss-a", "NOTAM", "z", logical_clock=2)
    result = log.query(event_type="HANDOVER")
    assert [e.detail for e in result] == ["x", "y"]


def test_query_combined_filters():
    log = FederationAuditLog()
    log.record("uss-a", "HANDOVER", "x", logical_clock=1)
    log.record("uss-a", "NOTAM", "y", logical_clock=2)
    log.record("uss-b", "HANDOVER", "z", logical_clock=1)
    result = log.query(instance_id="uss-a", event_type="HANDOVER")
    assert [e.detail for e in result] == ["x"]


def test_query_no_filter_returns_all():
    log = FederationAuditLog()
    log.record("uss-a", "E", "x", logical_clock=1)
    log.record("uss-b", "E", "y", logical_clock=1)
    assert len(log.query()) == 2


# --- merge ---------------------------------------------------------------


def _make(instance, events):
    log = FederationAuditLog()
    for clock, etype, detail in events:
        log.record(instance, etype, detail, logical_clock=clock)
    return log


def test_merge_is_valid_chain():
    a = _make("uss-a", [(1, "E", "a1"), (2, "E", "a2")])
    b = _make("uss-b", [(1, "E", "b1"), (3, "E", "b2")])
    merged = a.merge(b)
    assert merged.verify() is True
    assert len(merged.entries()) == 4
    # seq 는 0..n-1 로 재부여된다.
    assert [e.seq for e in merged.entries()] == [0, 1, 2, 3]


def test_merge_is_commutative():
    a = _make("uss-a", [(1, "E", "a1"), (4, "E", "a2")])
    b = _make("uss-b", [(2, "E", "b1"), (3, "E", "b2")])
    assert a.merge(b).head_digest() == b.merge(a).head_digest()


def test_merge_is_idempotent_with_self():
    a = _make("uss-a", [(1, "E", "a1"), (2, "E", "a2")])
    assert a.merge(a).head_digest() == a.head_digest()


def test_merge_dedups_identical_entries():
    a = _make("uss-a", [(1, "E", "shared"), (2, "E", "only-a")])
    b = _make("uss-a", [(1, "E", "shared"), (3, "E", "only-b")])
    merged = a.merge(b)
    # (1,uss-a,E,shared) 는 한 번만 — 중복 제거.
    details = [e.detail for e in merged.entries()]
    assert details.count("shared") == 1
    assert set(details) == {"shared", "only-a", "only-b"}


def test_merge_absorption_idempotent():
    # CRDT 흡수(absorption): 이미 b를 합친 원장에 b를 또 합쳐도 변하지 않는다.
    a = _make("uss-a", [(1, "E", "a1")])
    b = _make("uss-b", [(2, "E", "b1")])
    once = a.merge(b)
    assert once.merge(b).head_digest() == once.head_digest()
    assert once.merge(a).head_digest() == once.head_digest()


def test_record_after_merge_appends_valid_entry():
    a = _make("uss-a", [(1, "E", "a1")])
    b = _make("uss-b", [(2, "E", "b1")])
    merged = a.merge(b)
    # 병합 원장에 이어 record 해도 체인이 유효하게 연장된다.
    entry = merged.record("uss-a", "E", "a2", logical_clock=9)
    assert merged.verify() is True
    assert entry.prev_digest == merged.entries()[-2].digest
    assert len(merged.entries()) == 3


def test_merge_is_associative():
    a = _make("uss-a", [(1, "E", "a")])
    b = _make("uss-b", [(2, "E", "b")])
    c = _make("uss-c", [(3, "E", "c")])
    left = a.merge(b).merge(c)
    right = a.merge(b.merge(c))
    assert left.head_digest() == right.head_digest()


def test_merge_handles_forked_same_instance_same_clock():
    # 분기(fork): 같은 인스턴스·같은 시각에 서로 다른 결정 — 병합이 깨지면 안 됨.
    a = _make("uss-a", [(1, "E", "decision-x")])
    b = _make("uss-a", [(1, "E", "decision-y")])
    merged = a.merge(b)
    assert merged.verify() is True
    assert len(merged.entries()) == 2  # 두 분기 결정 모두 보존


def test_merge_does_not_mutate_operands():
    a = _make("uss-a", [(1, "E", "a1")])
    b = _make("uss-b", [(1, "E", "b1")])
    a.merge(b)
    assert len(a.entries()) == 1
    assert len(b.entries()) == 1


def test_merged_log_orders_by_content_key():
    a = _make("uss-b", [(5, "E", "late")])
    b = _make("uss-a", [(1, "E", "early")])
    merged = a.merge(b)
    # logical_clock 우선 정렬 → (1,uss-a) 가 (5,uss-b) 보다 앞.
    assert [e.detail for e in merged.entries()] == ["early", "late"]
