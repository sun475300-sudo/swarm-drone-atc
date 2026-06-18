"""ODYSSEY Phase 441 — 5계층 안전망 우선순위 불변식 유한 모델 검사 테스트.

핵심: `check_invariant` 가 *모든 도달 가능 상태* 에서 복원 가능성(컨트롤러
1스텝이면 SAFE 회복)을 전수 검증한다(표본이 아닌 전수). 비공허성
(`controller_necessary`)으로 그 속성이 공허한 참이 아님을 증명하고, 일부러
약화한 컨트롤러가 만든 반례를 검사기가 *최단 경로*로 잡아내는지(음성 테스트)까지
확인해 검사기 자체의 건전성을 보장한다.
"""
from __future__ import annotations

import pytest

from simulation.safety_net_invariant import (
    DISARM,
    EMERGENCY,
    HAZARD_DIMENSIONS,
    LAND,
    NORMAL,
    RTL,
    WARN,
    SafetyState,
    check_invariant,
    controller_necessary,
    controller_step,
    initial_state,
    is_safe,
    reachable_states,
    required_level,
    restore_step,
    successors,
)


# ── required_level: failsafe_manager 임계값 정렬 ─────────────────────────────
def test_required_level_no_hazard_is_normal():
    assert required_level((0, 0, 0, 0)) == NORMAL


def test_required_level_picks_worst_hazard():
    # comm=DISARM(idx3), battery=WARN(idx1) → DISARM 이 이긴다.
    sev = (3, 1, 0, 0)
    assert required_level(sev) == DISARM


def test_required_level_collision_dominates_to_emergency():
    sev = (1, 1, 1, 1)  # collision idx1 → EMERGENCY 최상위
    assert required_level(sev) == EMERGENCY


@pytest.mark.parametrize(
    "sev,expected",
    [
        ((1, 0, 0, 0), WARN),    # comm >2s
        ((2, 0, 0, 0), RTL),     # comm >5s
        ((0, 2, 0, 0), LAND),    # battery <=15%
        ((0, 0, 1, 0), RTL),     # geofence breach
    ],
)
def test_required_level_per_dimension(sev, expected):
    assert required_level(sev) == expected


# ── 핵심: 전수 모델 검사 (복원 가능성 + 비공허성) ─────────────────────────────
def test_controller_recovers_safety_from_all_reachable_states():
    # 도달 가능 전 상태에서 컨트롤러 1스텝이면 SAFE 회복.
    result = check_invariant()  # 기본 step=controller_step, 불변식=복원 가능성
    assert result.holds, f"counterexample: {result.counterexample}"
    assert result.counterexample is None
    # 유한 상태 공간을 실제로 다수 탐색했는지 (자명한 통과 방지).
    assert result.states_explored > 20


def test_controller_is_necessary_some_raw_states_unsafe():
    # 복원 가능성이 공허한 참이 아님: 컨트롤러 없이 환경만 변하면 SAFE 를
    # 위반하는 도달 가능 상태가 실제로 존재한다 (과도 상태).
    assert controller_necessary() is True
    unsafe = [s for s in reachable_states() if not is_safe(s)]
    assert unsafe, "복원 가능성 검증이 공허(vacuous)하면 안 된다"


def test_model_checker_is_deterministic():
    a = check_invariant()
    b = check_invariant()
    assert (a.holds, a.states_explored) == (b.holds, b.states_explored)


def test_broken_controller_under_escalates_is_caught_with_shortest_trace():
    # 약화 모델: collision 위험을 무시하고 래칫 → 복원 가능성 위반.
    from simulation.safety_net_invariant import required_level as rl

    def broken_step(state: SafetyState) -> SafetyState:
        sev_no_collision = state.severities[:3] + (0,)
        return SafetyState(
            level=max(state.level, rl(sev_no_collision)),
            severities=state.severities,
        )

    result = check_invariant(step=broken_step)
    assert not result.holds
    assert result.counterexample is not None
    # 진정한 BFS → 최단 반례: 초기 → 충돌 임박 (2상태).
    assert len(result.counterexample) == 2
    bad = result.counterexample[-1]
    # 반례는 충돌 임박(collision idx1)인데 컨트롤러가 EMERGENCY 로 못 올린다.
    assert bad.severities[3] == 1
    assert broken_step(bad).level < EMERGENCY


# ── 전이 속성 ────────────────────────────────────────────────────────────────
def test_controller_step_monotone_over_all_reachable_states():
    # MONOTONE: 컨트롤러 스텝은 어떤 도달 가능 상태에서도 레벨을 낮추지 않는다.
    for s in reachable_states():
        assert controller_step(s).level >= s.level


def test_controller_step_never_lowers_level():
    state = SafetyState(level=RTL, severities=(0, 0, 0, 0))
    assert controller_step(state).level == RTL  # 위험 없어도 래칫 유지


def test_controller_step_escalates_to_required():
    state = SafetyState(level=NORMAL, severities=(0, 0, 0, 1))  # collision
    assert controller_step(state).level == EMERGENCY


def test_restore_refuses_while_hazard_active():
    state = SafetyState(level=RTL, severities=(2, 0, 0, 0))  # comm RTL active
    assert restore_step(state) == state  # 복귀 거부 (SAFE 보존)


def test_restore_returns_to_normal_when_clear():
    state = SafetyState(level=DISARM, severities=(0, 0, 0, 0))
    assert restore_step(state).level == NORMAL


def test_successors_are_sorted_and_exclude_self():
    state = initial_state()
    succ = successors(state)
    assert succ == sorted(succ)
    assert state not in succ


# ── 상태 검증 ────────────────────────────────────────────────────────────────
def test_state_rejects_out_of_range_level():
    with pytest.raises(ValueError):
        SafetyState(level=99, severities=(0, 0, 0, 0))


def test_state_rejects_severity_arity_mismatch():
    with pytest.raises(ValueError):
        SafetyState(level=NORMAL, severities=(0, 0))


def test_state_rejects_severity_out_of_range():
    n_dims = len(HAZARD_DIMENSIONS)
    with pytest.raises(ValueError):
        SafetyState(level=NORMAL, severities=(99,) + (0,) * (n_dims - 1))
