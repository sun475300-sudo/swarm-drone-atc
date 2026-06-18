"""ODYSSEY Phase 434 — HLC 통합 인과-안정 배달 단위 테스트.

외부 의존성 0(순수 결정적). Phase 431 HLC + Phase 432 메시 위에서 동작한다.
"""

from __future__ import annotations

import pytest

from simulation.federation_causal_delivery import (
    CausalDeliveryBuffer,
    FederationDeliveryCoordinator,
    FederationEvent,
)
from simulation.federation_discovery import FederationDiscoveryService, Volume4D
from simulation.federation_hybrid_clock import HLCTimestamp
from simulation.federation_mesh import FederationMesh


def _ts(wall: int, counter: int, iid: str) -> HLCTimestamp:
    return HLCTimestamp(wall, counter, iid)


def _evt(wall: int, counter: int, iid: str, payload: object = None) -> FederationEvent:
    return FederationEvent(_ts(wall, counter, iid), payload)


def _tile(x_min: float, x_max: float) -> Volume4D:
    return Volume4D(x_min, x_max, 0, 1000, 0, 120, 0, 600)


def _line_mesh() -> FederationMesh:
    """맞닿은 세 타일: WEST[0,1000)·MID[1000,2000)·EAST[2000,3000)."""
    svc = FederationDiscoveryService(cell_size_m=500.0)
    svc.register("WEST", _tile(0, 1000))
    svc.register("MID", _tile(1000, 2000))
    svc.register("EAST", _tile(2000, 3000))
    return FederationMesh(svc)


# --- FederationEvent --------------------------------------------------------


def test_event_source_is_timestamp_instance():
    evt = _evt(5, 0, "A", payload={"k": 1})
    assert evt.source == "A"
    assert evt.payload == {"k": 1}


def test_event_is_frozen():
    evt = _evt(5, 0, "A")
    with pytest.raises(Exception):
        evt.timestamp = _ts(6, 0, "A")  # type: ignore[misc]


def test_event_default_payload_is_none():
    assert _evt(1, 0, "A").payload is None


# --- CausalDeliveryBuffer: 기본 수신/검증 -----------------------------------


def test_empty_buffer_delivers_nothing():
    buf = CausalDeliveryBuffer("R")
    assert buf.flush() == ()
    assert buf.deliverable() == ()
    assert buf.pending() == ()
    assert buf.last_delivered() is None


def test_blank_instance_id_rejected():
    with pytest.raises(ValueError):
        CausalDeliveryBuffer("")


def test_receive_returns_true_for_new_event():
    buf = CausalDeliveryBuffer("R")
    assert buf.receive(_evt(1, 0, "A")) is True


def test_receive_rejects_non_event():
    buf = CausalDeliveryBuffer("R")
    with pytest.raises(TypeError):
        buf.receive(object())  # type: ignore[arg-type]


def test_receive_rejects_self_sourced_event():
    buf = CausalDeliveryBuffer("R")
    with pytest.raises(ValueError):
        buf.receive(_evt(1, 0, "R"))


# --- 중복/stale 멱등 무시 (멀티홉) ------------------------------------------


def test_duplicate_event_is_idempotently_ignored():
    buf = CausalDeliveryBuffer("R")
    assert buf.receive(_evt(5, 0, "A")) is True
    assert buf.receive(_evt(5, 0, "A")) is False  # 같은 경로 중복


def test_stale_event_below_high_is_ignored():
    buf = CausalDeliveryBuffer("R")
    buf.receive(_evt(5, 0, "A"))
    assert buf.receive(_evt(4, 0, "A")) is False  # FIFO 역행 → stale


def test_strictly_increasing_same_source_accepted():
    buf = CausalDeliveryBuffer("R")
    assert buf.receive(_evt(5, 0, "A")) is True
    assert buf.receive(_evt(5, 1, "A")) is True
    assert buf.receive(_evt(6, 0, "A")) is True


# --- best-effort 워터마크 (관측 출처) ---------------------------------------


def test_single_source_delivers_up_to_high():
    buf = CausalDeliveryBuffer("R")
    buf.receive(_evt(1, 0, "A"))
    buf.receive(_evt(2, 0, "A"))
    # 관측 출처가 A 하나뿐 → 워터마크 = A의 고점 (2,0) → 둘 다 안정
    out = buf.flush()
    assert [e.timestamp for e in out] == [_ts(1, 0, "A"), _ts(2, 0, "A")]


def test_watermark_is_min_across_observed_sources():
    buf = CausalDeliveryBuffer("R")
    buf.receive(_evt(5, 0, "A"))  # A 고점 (5,0)
    buf.receive(_evt(2, 0, "B"))  # B 고점 (2,0) → 워터마크 (2,0)
    out = buf.flush()
    # (2,0,B) 만 안정; (5,0,A)는 B가 더 진척해야 안정
    assert [e.timestamp for e in out] == [_ts(2, 0, "B")]
    assert [e.timestamp for e in buf.pending()] == [_ts(5, 0, "A")]


def test_watermark_advances_as_lagging_source_progresses():
    buf = CausalDeliveryBuffer("R")
    buf.receive(_evt(5, 0, "A"))
    buf.receive(_evt(2, 0, "B"))
    buf.flush()  # (2,0,B) 배달
    buf.receive(_evt(7, 0, "B"))  # B가 진척 → 워터마크 (5,0,A)
    out = buf.flush()
    assert [e.timestamp for e in out] == [_ts(5, 0, "A")]


# --- 전순서 배달 정렬 -------------------------------------------------------


def test_delivery_is_total_order_sorted():
    buf = CausalDeliveryBuffer("R")
    # 출처별 FIFO 증가 스트림을 교차 도착시킨다.
    buf.receive(_evt(1, 0, "A"))
    buf.receive(_evt(2, 0, "B"))
    buf.receive(_evt(3, 0, "A"))  # (3,0,A) < (3,0,B) — instance_id 타이브레이크
    buf.receive(_evt(3, 0, "B"))
    # 두 출처를 충분히 진척시켜 워터마크가 위 사건을 모두 덮게 한다.
    buf.receive(_evt(5, 0, "A"))
    buf.receive(_evt(5, 0, "B"))
    out = buf.flush()
    keys = [e.timestamp for e in out]
    assert keys == sorted(keys)
    assert keys.index(_ts(3, 0, "A")) < keys.index(_ts(3, 0, "B"))


def test_concurrent_events_ordered_by_instance_id():
    buf = CausalDeliveryBuffer("R")
    buf.receive(_evt(4, 1, "Z"))
    buf.receive(_evt(4, 1, "A"))  # 동시(동일 causal_key), 다른 인스턴스
    # 워터마크가 두 동시 사건을 모두 덮도록 양쪽을 진척시킨다.
    buf.receive(_evt(5, 0, "Z"))
    buf.receive(_evt(5, 0, "A"))
    out = [e for e in buf.flush() if e.timestamp.causal_key == (4, 1)]
    assert [e.source for e in out] == ["A", "Z"]


# --- 단조 배달 / 상태 -------------------------------------------------------


def test_delivered_events_removed_from_buffer():
    buf = CausalDeliveryBuffer("R")
    buf.receive(_evt(1, 0, "A"))
    buf.flush()
    assert buf.receive(_evt(1, 0, "A")) is False  # 이미 본 출처 고점
    assert buf.flush() == ()  # 재배달 없음


def test_last_delivered_tracks_high():
    buf = CausalDeliveryBuffer("R")
    buf.receive(_evt(1, 0, "A"))
    buf.receive(_evt(3, 0, "A"))
    buf.flush()
    assert buf.last_delivered() == _ts(3, 0, "A")


def test_delivery_monotonic_across_flushes():
    buf = CausalDeliveryBuffer("R")
    buf.receive(_evt(1, 0, "A"))
    first = buf.flush()
    buf.receive(_evt(2, 0, "A"))
    second = buf.flush()
    assert first[-1].timestamp < second[0].timestamp


def test_buffer_size_distinguishes_empty_from_blocked():
    buf = CausalDeliveryBuffer("R", sources={"A", "B", "R"})
    assert buf.buffer_size() == 0  # 진짜 빔
    buf.receive(_evt(5, 0, "A"))  # B 미보고 → 워터마크 None
    assert buf.deliverable() == () and buf.pending() != ()
    assert buf.buffer_size() == 1  # 비었지 않고 보류 중


def test_flush_handles_unhashable_payload():
    # 페이로드가 비해시(dict)여도 워터마크 분할 배달은 안전해야 한다.
    buf = CausalDeliveryBuffer("R")
    buf.receive(_evt(1, 0, "A", payload={"k": 1}))
    out = buf.flush()
    assert out[0].payload == {"k": 1}
    assert buf.buffer_size() == 0  # 배달 후 제거됨, 재배달 없음
    assert buf.flush() == ()


def test_deliverable_does_not_mutate_buffer():
    buf = CausalDeliveryBuffer("R")
    buf.receive(_evt(1, 0, "A"))
    assert buf.deliverable() != ()
    assert buf.deliverable() == buf.deliverable()  # 비파괴 — 반복 동일
    assert buf.flush() != ()  # 여전히 배달 가능


# --- 예상 출처 집합 (보수적 워터마크) ---------------------------------------


def test_expected_sources_hold_until_all_report():
    buf = CausalDeliveryBuffer("R", sources={"A", "B", "R"})
    buf.receive(_evt(5, 0, "A"))
    # B 미보고 → 워터마크 None → 아무것도 배달 안 됨
    assert buf.flush() == ()
    assert [e.timestamp for e in buf.pending()] == [_ts(5, 0, "A")]
    buf.receive(_evt(9, 0, "B"))  # 이제 모두 보고 → 워터마크 (5,0,A)
    out = buf.flush()
    assert [e.timestamp for e in out] == [_ts(5, 0, "A")]


def test_expected_sources_excludes_self():
    # 자기 자신(R)은 예상 출처에서 제외 → A·B만 보고하면 워터마크 성립
    buf = CausalDeliveryBuffer("R", sources={"A", "B", "R"})
    buf.receive(_evt(2, 0, "A"))
    buf.receive(_evt(3, 0, "B"))
    assert buf.flush() != ()


def test_unexpected_source_rejected():
    buf = CausalDeliveryBuffer("R", sources={"A", "R"})
    with pytest.raises(ValueError):
        buf.receive(_evt(1, 0, "C"))


def test_expected_self_only_never_delivers():
    # 자기 자신만 예상 출처 → 제외 후 빈 집합 → 워터마크 None
    buf = CausalDeliveryBuffer("R", sources={"R"})
    assert buf.flush() == ()


# --- 결정성 -----------------------------------------------------------------


def test_delivery_is_deterministic_across_source_interleavings():
    # 각 출처의 사건은 FIFO 로 증가 순서를 지키되, 출처 간 교차(interleaving)만 다르게.
    interleave_1 = [
        _evt(1, 0, "A"),
        _evt(3, 0, "B"),
        _evt(2, 0, "C"),
        _evt(4, 0, "A"),
        _evt(3, 0, "C"),
    ]
    interleave_2 = [
        _evt(2, 0, "C"),
        _evt(1, 0, "A"),
        _evt(3, 0, "C"),
        _evt(3, 0, "B"),
        _evt(4, 0, "A"),
    ]
    buf1 = CausalDeliveryBuffer("R")
    for e in interleave_1:
        buf1.receive(e)
    buf2 = CausalDeliveryBuffer("R")
    for e in interleave_2:
        buf2.receive(e)
    assert [e.timestamp for e in buf1.deliverable()] == [
        e.timestamp for e in buf2.deliverable()
    ]


# --- FederationDeliveryCoordinator (메시 통합) ------------------------------


def test_broadcast_reaches_all_via_multihop():
    coord = FederationDeliveryCoordinator(_line_mesh())
    # WEST origin → MID(1홉)·EAST(2홉) 도달, WEST(origin) 제외
    targets = coord.broadcast(_evt(1, 0, "WEST"))
    assert targets == ("EAST", "MID")


def test_broadcast_excludes_origin():
    coord = FederationDeliveryCoordinator(_line_mesh())
    coord.broadcast(_evt(1, 0, "MID"))
    # MID 버퍼는 자기 사건을 받지 않음
    assert coord.buffer("MID").pending() == ()


def test_broadcast_ttl_limits_reach():
    coord = FederationDeliveryCoordinator(_line_mesh())
    targets = coord.broadcast(_evt(1, 0, "WEST"), ttl=1)
    assert targets == ("MID",)  # EAST(2홉)는 TTL=1로 차단


def test_broadcast_unknown_origin_raises():
    coord = FederationDeliveryCoordinator(_line_mesh())
    with pytest.raises(KeyError):
        coord.broadcast(_evt(1, 0, "NORTH"))


def test_coordinator_buffer_uses_all_instances_as_sources():
    coord = FederationDeliveryCoordinator(_line_mesh())
    # WEST 버퍼의 예상 출처는 {MID, EAST}. EAST만 보고했으니 MID 미보고로 보류.
    coord.broadcast(_evt(5, 0, "EAST"))
    assert coord.flush("WEST") == ()


def test_coordinator_delivers_same_order_to_all_receivers():
    coord = FederationDeliveryCoordinator(_line_mesh())
    # 모든 origin 이 한 번씩 broadcast → 각 수신자가 동일한 안정 순서로 배달
    coord.broadcast(_evt(1, 0, "WEST"))
    coord.broadcast(_evt(2, 0, "MID"))
    coord.broadcast(_evt(3, 0, "EAST"))
    flushed = coord.flush_all()
    # WEST 수신자: MID·EAST 사건; MID 수신자: WEST·EAST; EAST 수신자: WEST·MID
    west_keys = [e.timestamp for e in flushed["WEST"]]
    mid_keys = [e.timestamp for e in flushed["MID"]]
    east_keys = [e.timestamp for e in flushed["EAST"]]
    # 각 수신자 내부는 전순서 정렬
    assert west_keys == sorted(west_keys)
    assert mid_keys == sorted(mid_keys)
    assert east_keys == sorted(east_keys)


def test_coordinator_idempotent_duplicate_broadcast():
    coord = FederationDeliveryCoordinator(_line_mesh())
    coord.broadcast(_evt(1, 0, "WEST"))
    again = coord.broadcast(_evt(1, 0, "WEST"))  # 같은 사건 재방송
    assert again == ()  # 모두 멱등 무시


def test_coordinator_flush_all_keys_sorted():
    coord = FederationDeliveryCoordinator(_line_mesh())
    result = coord.flush_all()
    assert list(result.keys()) == ["EAST", "MID", "WEST"]


def test_full_stable_delivery_end_to_end():
    coord = FederationDeliveryCoordinator(_line_mesh())
    # WEST·EAST 만 발행, MID 는 침묵.
    coord.broadcast(_evt(4, 0, "WEST"))
    coord.broadcast(_evt(6, 0, "EAST"))
    # MID 수신자의 예상 출처는 {WEST, EAST}(자기 제외) → 둘 다 보고됨.
    # 워터마크 = min((4,0,WEST),(6,0,EAST)) = (4,0,WEST). WEST 사건만 안정,
    # EAST 사건은 WEST 가 더 진척할 때까지 보류(안정 워터마크의 보수성).
    mid_out = coord.flush("MID")
    assert [e.timestamp for e in mid_out] == [_ts(4, 0, "WEST")]
    assert [e.timestamp for e in coord.buffer("MID").pending()] == [_ts(6, 0, "EAST")]
    # WEST 수신자는 MID(미보고) 때문에 워터마크 None → 보류.
    assert coord.flush("WEST") == ()
