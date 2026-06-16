"""ODYSSEY Phase 442 — ATC 핸드오프 모델 체킹 검증.

올바른 prepare→ack→commit 핸드오프가 상호 배제(관제 공백 부재)·교착 부재를
만족함을 명시적 상태 전수 탐색으로 증명하고, 세 변형 모델(orphan 버그·유실·타임아웃
수정)에서 체커가 의도한 반례를 정확히 찾아냄을 확인한다.
"""
from __future__ import annotations

from collections import deque

import pytest

from simulation.handoff_model_checker import (
    AUTH_A,
    AUTH_B,
    AUTH_NONE,
    LEGAL_AUTH,
    MSG_ACK,
    MSG_NONE,
    CheckResult,
    HandoffState,
    Transitions,
    check_model,
    handoff_transitions,
    is_done,
    lossy_model,
    orphan_bug_model,
    single_controller_invariant,
    timeout_model,
    verify_handoff_deadlock_free,
    verify_handoff_safe,
)


def _reachable(transitions: Transitions) -> set[HandoffState]:
    """초기 상태에서 도달 가능한 전 상태(테스트 보조 BFS)."""
    init = HandoffState()
    seen = {init}
    queue = deque([init])
    while queue:
        s = queue.popleft()
        for nxt in transitions(s):
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return seen


# ── 올바른 프로토콜: 안전 + 교착 부재 ────────────────────────────────────
def test_correct_handoff_satisfies_single_controller_invariant():
    # Arrange / Act
    result = verify_handoff_safe(handoff_transitions)

    # Assert
    assert result.holds
    assert result.violation == ""
    assert result.counterexample == ()


def test_correct_handoff_is_deadlock_free():
    result = verify_handoff_deadlock_free(handoff_transitions)

    assert result.holds
    assert result.violation == ""


def test_correct_handoff_result_is_truthy():
    assert bool(verify_handoff_safe(handoff_transitions)) is True


def test_every_reachable_state_keeps_exactly_one_controller():
    for state in _reachable(handoff_transitions):
        assert state.auth in LEGAL_AUTH


def test_every_nonterminal_state_has_a_transition():
    for state in _reachable(handoff_transitions):
        if not is_done(state):
            assert handoff_transitions(state), f"교착 상태 발견: {state}"


def test_handoff_can_complete_with_authority_transferred_to_b():
    # 수락 경로가 실제로 B 로의 권위 이양 종료에 도달한다.
    done_b = [
        s for s in _reachable(handoff_transitions) if s.done and s.auth == AUTH_B
    ]
    assert done_b
    for s in done_b:
        assert s.b_ready is True
        assert s.msg == MSG_NONE


def test_handoff_can_abort_on_reject_retaining_authority_with_a():
    # 거절 경로는 권위를 A 에 남긴 채 완결한다.
    done_a = [
        s for s in _reachable(handoff_transitions) if s.done and s.auth == AUTH_A
    ]
    assert done_a
    for s in done_a:
        assert s.b_ready is False
        assert s.msg == MSG_NONE


def test_terminal_states_have_empty_channel():
    for state in _reachable(handoff_transitions):
        if state.done:
            assert state.msg == MSG_NONE


# ── orphan 버그 모델: 관제 공백 불변식 위반 검출 ─────────────────────────
def test_orphan_bug_violates_single_controller_invariant():
    result = check_model(
        HandoffState(),
        orphan_bug_model,
        invariant=single_controller_invariant,
        is_accepting=is_done,
    )

    assert not result.holds
    assert result.violation == "invariant"


def test_orphan_bug_counterexample_reaches_no_controller_state():
    result = check_model(
        HandoffState(),
        orphan_bug_model,
        invariant=single_controller_invariant,
        is_accepting=is_done,
    )

    violating = result.counterexample[-1]
    assert violating.auth == AUTH_NONE


def test_orphan_bug_counterexample_starts_at_initial_state():
    result = check_model(
        HandoffState(),
        orphan_bug_model,
        invariant=single_controller_invariant,
        is_accepting=is_done,
    )

    assert result.counterexample[0] == HandoffState()


def test_orphan_bug_counterexample_is_a_valid_transition_path():
    # 반례의 각 단계는 이전 단계의 실제 후속이어야 한다.
    result = check_model(
        HandoffState(),
        orphan_bug_model,
        invariant=single_controller_invariant,
        is_accepting=is_done,
    )
    trace = result.counterexample
    for prev, nxt in zip(trace, trace[1:]):
        assert nxt in orphan_bug_model(prev)


# ── 유실 모델: 교착 검출 ─────────────────────────────────────────────────
def test_lossy_model_deadlocks():
    result = verify_handoff_deadlock_free(lossy_model)

    assert not result.holds
    assert result.violation == "deadlock"


def test_lossy_deadlock_counterexample_is_stuck_nonterminal():
    result = verify_handoff_deadlock_free(lossy_model)
    stuck = result.counterexample[-1]

    assert stuck.done is False
    assert lossy_model(stuck) == []  # 후속이 정말 없다(교착)


def test_lossy_model_is_still_safe_no_orphan():
    # 유실이 있어도 권위는 늘 정확히 하나 — 안전(mutex)은 깨지지 않는다.
    result = check_model(
        HandoffState(),
        lossy_model,
        invariant=single_controller_invariant,
        is_accepting=lambda _s: True,  # 교착 무시, 안전만 본다
    )

    assert result.holds


# ── 타임아웃 수정본: 교착 부재 복원 ──────────────────────────────────────
def test_timeout_model_restores_deadlock_freedom():
    result = verify_handoff_deadlock_free(timeout_model)

    assert result.holds


def test_timeout_model_is_safe():
    result = verify_handoff_safe(timeout_model)

    assert result.holds


# ── 체커 자체 성질 ───────────────────────────────────────────────────────
def test_check_model_is_deterministic():
    r1 = check_model(
        HandoffState(), orphan_bug_model, invariant=single_controller_invariant
    )
    r2 = check_model(
        HandoffState(), orphan_bug_model, invariant=single_controller_invariant
    )

    assert r1 == r2


def test_check_model_explores_finite_state_space():
    result = verify_handoff_safe(handoff_transitions)

    # 단일 드론 단일 경계 통과 모델은 소수 상태로 유한.
    assert 0 < result.states_explored < 50


def test_check_model_raises_when_exceeding_max_states():
    with pytest.raises(ValueError):
        check_model(
            HandoffState(),
            handoff_transitions,
            is_accepting=is_done,
            max_states=2,
        )


def test_terminal_only_model_is_not_a_deadlock_when_accepting():
    # 초기 상태가 곧 종료(accepting)면 후속이 없어도 교착이 아니다.
    result = check_model(
        HandoffState(done=True),
        lambda _s: [],
        is_accepting=is_done,
    )

    assert result.holds


def test_terminal_state_without_accepting_is_a_deadlock():
    result = check_model(HandoffState(), lambda _s: [])

    assert not result.holds
    assert result.violation == "deadlock"


# ── 술어 단위 검사 ───────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "auth,expected",
    [(AUTH_A, True), (AUTH_B, True), (AUTH_NONE, False), ("AB", False)],
)
def test_single_controller_invariant_predicate(auth, expected):
    assert single_controller_invariant(HandoffState(auth=auth)) is expected


def test_is_done_predicate():
    assert is_done(HandoffState(done=True)) is True
    assert is_done(HandoffState(done=False)) is False


def test_handoff_state_is_hashable_and_ordered():
    # frozen+order 라 집합/정렬에 안전(결정적 탐색의 전제).
    a = HandoffState(auth=AUTH_A)
    b = HandoffState(auth=AUTH_B)
    assert len({a, b, HandoffState(auth=AUTH_A)}) == 2
    assert sorted([b, a])[0] == a


def test_check_result_counterexample_empty_when_holds():
    result: CheckResult = verify_handoff_safe(handoff_transitions)
    assert result.counterexample == ()


def test_msg_ack_constant_used_in_lossy_path():
    # 유실되는 메시지는 ACK 다 — 교착에 이르는 경로에 ACK 채널 상태가 반드시 등장.
    trace = verify_handoff_deadlock_free(lossy_model).counterexample
    assert any(s.msg == MSG_ACK for s in trace)
