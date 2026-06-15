"""ODYSSEY Phase 431 — 하이브리드 논리 시계(HLC) 단위 테스트.

검증 목표(AAA 패턴):
- 지역/수신 이벤트의 표준 HLC 갱신 규칙
- 발행 타임스탬프의 엄격한 단조 증가
- 인스턴스 간 인과(happened-before) 보존
- 결정성(같은 이벤트 순서 → 같은 타임스탬프 열)
- 경계 검증(음수 시각·빈 식별자·잘못된 원격 타입)
- 타임스탬프 전순서·인스턴스 동률 처리
"""

import pytest

from simulation.federation_hybrid_clock import HLCTimestamp, HybridLogicalClock


# --------------------------------------------------------------------------- #
# HLCTimestamp — 불변·전순서·인과 키
# --------------------------------------------------------------------------- #
def test_timestamp_total_order_by_wall_then_counter():
    # Arrange / Act
    a = HLCTimestamp(10, 0, "uss-a")
    b = HLCTimestamp(10, 1, "uss-a")
    c = HLCTimestamp(11, 0, "uss-a")
    # Assert — wall 우선, 같으면 counter
    assert a < b < c


def test_timestamp_tiebreak_by_instance_id():
    # 같은 (wall, counter)는 instance_id 사전식으로 결정적 정렬
    a = HLCTimestamp(5, 2, "uss-a")
    b = HLCTimestamp(5, 2, "uss-b")
    assert a < b
    assert sorted([b, a]) == [a, b]


def test_timestamp_is_frozen():
    ts = HLCTimestamp(1, 0, "uss-a")
    with pytest.raises(Exception):
        ts.counter = 9  # type: ignore[misc]


def test_timestamp_causal_key_excludes_instance():
    a = HLCTimestamp(7, 3, "uss-a")
    b = HLCTimestamp(7, 3, "uss-zzz")
    assert a.causal_key == b.causal_key == (7, 3)


def test_timestamp_happened_before_ignores_instance():
    a = HLCTimestamp(4, 1, "uss-z")
    b = HLCTimestamp(4, 2, "uss-a")
    assert a.happened_before(b)
    assert not b.happened_before(a)


def test_timestamp_rejects_negative_wall():
    with pytest.raises(ValueError):
        HLCTimestamp(-1, 0, "uss-a")


def test_timestamp_rejects_negative_counter():
    with pytest.raises(ValueError):
        HLCTimestamp(0, -1, "uss-a")


def test_timestamp_rejects_empty_instance():
    with pytest.raises(ValueError):
        HLCTimestamp(0, 0, "")


# --------------------------------------------------------------------------- #
# HybridLogicalClock — 생성·local_event
# --------------------------------------------------------------------------- #
def test_clock_rejects_empty_instance():
    with pytest.raises(ValueError):
        HybridLogicalClock("")


def test_local_event_advances_wall_resets_counter():
    # Arrange
    clk = HybridLogicalClock("uss-a")
    # Act — 물리 시각이 앞서면 wall 갱신·counter 0
    ts = clk.local_event(100)
    # Assert
    assert ts == HLCTimestamp(100, 0, "uss-a")


def test_local_event_same_wall_increments_counter():
    clk = HybridLogicalClock("uss-a")
    clk.local_event(100)
    ts = clk.local_event(100)  # 물리 시각 정체
    assert ts == HLCTimestamp(100, 1, "uss-a")


def test_local_event_counter_keeps_climbing_when_time_stalls():
    clk = HybridLogicalClock("uss-a")
    clk.local_event(50)
    results = [clk.local_event(50) for _ in range(3)]
    assert [r.counter for r in results] == [1, 2, 3]
    assert all(r.wall_time == 50 for r in results)


def test_local_event_handles_clock_going_backward():
    # 벽시계가 역행해도 논리 고점은 유지·counter만 증가(단조성 유지)
    clk = HybridLogicalClock("uss-a")
    clk.local_event(100)
    ts = clk.local_event(80)  # 역행
    assert ts == HLCTimestamp(100, 1, "uss-a")


def test_local_event_resets_counter_on_new_higher_time():
    clk = HybridLogicalClock("uss-a")
    clk.local_event(100)
    clk.local_event(100)  # counter -> 1
    ts = clk.local_event(200)  # 새 고점
    assert ts == HLCTimestamp(200, 0, "uss-a")


def test_local_event_rejects_negative_time():
    clk = HybridLogicalClock("uss-a")
    with pytest.raises(ValueError):
        clk.local_event(-1)


def test_local_event_zero_time_first_event_resets_counter():
    # cold-start: 첫 이벤트는 물리 시각이 0이어도 counter 0 (sentinel -1 < 0)
    clk = HybridLogicalClock("uss-a")
    ts = clk.local_event(0)
    assert ts == HLCTimestamp(0, 0, "uss-a")


def test_fresh_clock_current_is_zero_baseline():
    # 아직 아무것도 발행하지 않은 시계는 (0,0) 중립 기준점 (내부 sentinel 비노출)
    clk = HybridLogicalClock("uss-a")
    assert clk.current() == HLCTimestamp(0, 0, "uss-a")


def test_local_events_strictly_monotonic():
    clk = HybridLogicalClock("uss-a")
    times = [10, 10, 9, 12, 12, 12, 8, 20]
    stamps = [clk.local_event(t) for t in times]
    for earlier, later in zip(stamps, stamps[1:]):
        assert earlier < later


# --------------------------------------------------------------------------- #
# HybridLogicalClock — receive_event
# --------------------------------------------------------------------------- #
def test_receive_takes_remote_wall_when_ahead():
    clk = HybridLogicalClock("uss-b")
    clk.local_event(10)
    remote = HLCTimestamp(100, 5, "uss-a")
    ts = clk.receive_event(20, remote)  # 원격 wall 100이 최대
    assert ts == HLCTimestamp(100, 6, "uss-b")  # 원격 counter +1


def test_receive_local_and_remote_tie_takes_max_counter_plus_one():
    clk = HybridLogicalClock("uss-b")
    clk.local_event(100)
    clk.local_event(100)  # 지역 (100, 1)
    remote = HLCTimestamp(100, 4, "uss-a")
    ts = clk.receive_event(50, remote)  # wall 100 동률, max(1,4)+1
    assert ts == HLCTimestamp(100, 5, "uss-b")


def test_receive_local_wall_dominates_increments_local_counter():
    clk = HybridLogicalClock("uss-b")
    clk.local_event(200)  # 지역 (200, 0)
    remote = HLCTimestamp(100, 9, "uss-a")
    ts = clk.receive_event(50, remote)  # 지역 200이 최대
    assert ts == HLCTimestamp(200, 1, "uss-b")


def test_receive_physical_time_dominates_resets_counter():
    clk = HybridLogicalClock("uss-b")
    clk.local_event(100)
    remote = HLCTimestamp(120, 3, "uss-a")
    ts = clk.receive_event(300, remote)  # 물리 시각 300이 최대 → counter 0
    assert ts == HLCTimestamp(300, 0, "uss-b")


def test_receive_rejects_negative_time():
    clk = HybridLogicalClock("uss-b")
    with pytest.raises(ValueError):
        clk.receive_event(-5, HLCTimestamp(1, 0, "uss-a"))


def test_receive_rejects_non_timestamp_remote():
    clk = HybridLogicalClock("uss-b")
    with pytest.raises(TypeError):
        clk.receive_event(10, (100, 0, "uss-a"))  # type: ignore[arg-type]


def test_receive_keeps_monotonicity_after_local():
    clk = HybridLogicalClock("uss-b")
    t1 = clk.local_event(100)
    t2 = clk.receive_event(50, HLCTimestamp(100, 0, "uss-a"))
    t3 = clk.local_event(100)
    assert t1 < t2 < t3


def test_receive_on_fresh_clock_takes_remote_wall():
    # cold-start receive: 첫 행위가 수신이어도 원격을 인과적으로 추월
    clk = HybridLogicalClock("uss-b")
    remote = HLCTimestamp(0, 0, "uss-a")
    ts = clk.receive_event(0, remote)
    assert ts == HLCTimestamp(0, 1, "uss-b")  # 원격 (0,0)을 엄격히 추월
    assert remote.happened_before(ts)


def test_receive_on_fresh_clock_physical_time_dominates():
    clk = HybridLogicalClock("uss-b")
    ts = clk.receive_event(50, HLCTimestamp(20, 3, "uss-a"))
    assert ts == HLCTimestamp(50, 0, "uss-b")  # 물리 시각 50이 최대 → counter 0


# --------------------------------------------------------------------------- #
# 인과(happened-before) 보존 — 핵심 HLC 성질
# --------------------------------------------------------------------------- #
def test_causality_preserved_across_two_instances():
    # A에서 보낸 메시지를 B가 받으면 send < receive (인과 보존)
    a = HybridLogicalClock("uss-a")
    b = HybridLogicalClock("uss-b")
    send = a.local_event(100)
    recv = b.receive_event(40, send)  # B 물리 시각이 뒤처져도
    assert send.happened_before(recv)


def test_causality_chain_three_instances():
    # A -> B -> C 메시지 사슬에서 타임스탬프가 인과 순서대로 증가
    a = HybridLogicalClock("uss-a")
    b = HybridLogicalClock("uss-b")
    c = HybridLogicalClock("uss-c")
    m1 = a.local_event(10)
    m2 = b.receive_event(5, m1)
    m3 = c.receive_event(3, m2)
    assert m1.happened_before(m2)
    assert m2.happened_before(m3)
    assert m1.happened_before(m3)


def test_equal_causal_key_is_concurrent_not_ordered():
    # 서로 다른 인스턴스의 동률 타임스탬프는 동시(concurrent) — 양방향 happened_before False
    a = HLCTimestamp(100, 2, "uss-a")
    b = HLCTimestamp(100, 2, "uss-b")
    assert not a.happened_before(b)
    assert not b.happened_before(a)
    assert a.is_concurrent_with(b)
    assert b.is_concurrent_with(a)


def test_causally_ordered_pair_is_not_concurrent():
    a = HLCTimestamp(100, 1, "uss-a")
    b = HLCTimestamp(100, 2, "uss-b")
    assert a.happened_before(b)
    assert not a.is_concurrent_with(b)


def test_current_does_not_advance_state():
    clk = HybridLogicalClock("uss-a")
    clk.local_event(100)
    before = clk.current()
    again = clk.current()
    assert before == again == HLCTimestamp(100, 0, "uss-a")


# --------------------------------------------------------------------------- #
# 결정성 — 같은 이벤트 순서 → 같은 타임스탬프 열
# --------------------------------------------------------------------------- #
def _run_scenario():
    a = HybridLogicalClock("uss-a")
    b = HybridLogicalClock("uss-b")
    out = []
    out.append(a.local_event(100))
    out.append(a.local_event(100))
    out.append(b.receive_event(90, out[-1]))
    out.append(b.local_event(95))
    out.append(a.receive_event(80, out[-1]))
    return out


def test_clock_is_deterministic():
    first = _run_scenario()
    second = _run_scenario()
    assert first == second


def test_deterministic_global_ordering_with_tiebreak():
    # 여러 인스턴스 타임스탬프를 모아 정렬하면 결정적 전순서(동률은 instance_id)
    stamps = [
        HLCTimestamp(100, 1, "uss-b"),
        HLCTimestamp(100, 1, "uss-a"),
        HLCTimestamp(100, 0, "uss-c"),
        HLCTimestamp(99, 9, "uss-a"),
    ]
    ordered = sorted(stamps)
    assert ordered == [
        HLCTimestamp(99, 9, "uss-a"),
        HLCTimestamp(100, 0, "uss-c"),
        HLCTimestamp(100, 1, "uss-a"),
        HLCTimestamp(100, 1, "uss-b"),
    ]
