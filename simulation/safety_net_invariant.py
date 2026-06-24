"""ODYSSEY Phase 441 — 5계층 안전망 충돌 회피 우선순위 불변식 (형식 명세 + 유한 모델 검사).

본 모듈은 `simulation/failsafe_manager.py` 의 이산 Failsafe 에스컬레이션
사다리(NORMAL→WARN→LAND→RTL→DISARM→EMERGENCY)를 **유한 상태 전이계**로
충실히 추상화하고, 그 안전 속성을 *유한 상태 공간 전수 탐색*으로 검증한다 —
표본 단위 테스트가 못 주는 "모든 도달 가능 상태에서 성립"을 보장.

대응 TLA+ 명세는 [`specs/SafetyNetPriority.tla`](../specs/SafetyNetPriority.tla),
해설은 [`docs/SAFETY_NET_TLA_SPEC.md`](../docs/SAFETY_NET_TLA_SPEC.md).

전이계 구성 (위험 변화와 컨트롤러 반응은 *별개* 전이)
------------------------------------------------------
- **환경 전이**: 한 위험 차원이 한 단계 악화/완화 (레벨 불변). 위험이 막 오른
  직후 컨트롤러가 아직 반응하지 않은 *과도 상태(transient)* 가 실제로 도달
  가능하다 — 이 상태는 일시적으로 SAFE 를 위반할 수 있다.
- **응답 전이**: 컨트롤러 래칫(`controller_step`) 또는 의도적 복귀
  (`restore_step`). `_transition` 의 "레벨은 절대 하강 없음" 래칫에 대응.

형식화 대상 속성
----------------
- **RECOVERABLE (복원 가능성)**: 어떤 도달 가능 상태에서도 컨트롤러 1스텝이면
  SAFE 가 회복된다 — `is_safe(controller_step(s))`. 컨트롤러가 위험 차원 하나를
  빠뜨리면(예: 충돌 무시) 이 속성이 깨지고 검사기가 반례를 찾는다.
- **NECESSARY (비공허성)**: 컨트롤러 없이 환경만 변하면 SAFE 를 위반하는
  도달 가능 상태가 *실제로 존재* 한다 — RECOVERABLE 이 공허한 참(vacuously
  true)이 아님을 증명한다.
- **MONOTONE (래칫)**: 컨트롤러 스텝은 레벨을 절대 낮추지 않는다.

정직한 한계: 정상(래칫) 컨트롤러에 대해 `is_safe(controller_step(s))` 는
`max(level, RequiredLevel) ≥ RequiredLevel` 로 *산술적으로* 즉시 참이다. 따라서
전수 탐색의 실질적 가치는 깊은 증명이 아니라 **컨트롤러/복귀 *로직 버그*를
잡아내는 차등 검증**(음성 테스트로 시연)에 있다 — Phase 443·444 와 같은 "정직한
완화점 공시" 원칙. `failsafe_manager.py` 무수정. 무작위성 0·결정적.
"""
from __future__ import annotations

from collections import deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass

# ── Failsafe 레벨 (failsafe_manager.FailsafeLevel 값과 동일) ──────────────────
NORMAL, WARN, LAND, RTL, DISARM, EMERGENCY = range(6)

LEVEL_NAMES = {
    NORMAL: "NORMAL", WARN: "WARN", LAND: "LAND",
    RTL: "RTL", DISARM: "DISARM", EMERGENCY: "EMERGENCY",
}

# ── 위험 차원별 심각도 → 요구 레벨 (failsafe_manager 임계값에 정렬) ───────────
# 각 차원은 0(없음)에서 시작하는 정수 심각도 사다리이며, 값이 클수록 위험하다.
# 매핑 값은 해당 심각도가 *최소한* 요구하는 Failsafe 레벨.
COMM_LEVELS = (NORMAL, WARN, RTL, DISARM)          # >2s / >5s / >30s
BATTERY_LEVELS = (NORMAL, WARN, LAND, DISARM)      # ≤25% / ≤15% / ≤5%
GEOFENCE_LEVELS = (NORMAL, RTL)                    # breach → RTL
# collision → EMERGENCY 는 *지향(aspirational)* 매핑이다: failsafe_manager 는
# FailsafeLevel.EMERGENCY=5 를 enum 에 예약해 두었으나 update() 에 아직 충돌
# 임박 트리거를 배선하지 않았다(현재 EMERGENCY 도달 경로 없음). 본 명세는 그
# 트리거가 배선됐을 때 유지되어야 할 불변식을 미리 규정한다. (Phase 442/후속
# 트리거 구현 시 failsafe_manager 와 정합.)
COLLISION_LEVELS = (NORMAL, EMERGENCY)             # 충돌 임박 → EMERGENCY (지향)

HAZARD_DIMENSIONS = (
    ("comm", COMM_LEVELS),
    ("battery", BATTERY_LEVELS),
    ("geofence", GEOFENCE_LEVELS),
    ("collision", COLLISION_LEVELS),
)


@dataclass(frozen=True, order=True)
class SafetyState:
    """안전망 전이계의 한 상태.

    `level` 은 현재 Failsafe 레벨, `severities` 는 `HAZARD_DIMENSIONS` 순서와
    같은 길이의 차원별 심각도 인덱스 튜플.
    """

    level: int
    severities: tuple[int, ...]

    def __post_init__(self) -> None:
        if not 0 <= self.level <= EMERGENCY:
            raise ValueError(f"level out of range: {self.level}")
        if len(self.severities) != len(HAZARD_DIMENSIONS):
            raise ValueError("severities arity mismatch")
        for sev, (name, levels) in zip(self.severities, HAZARD_DIMENSIONS, strict=True):
            if not 0 <= sev < len(levels):
                raise ValueError(f"{name} severity out of range: {sev}")


def required_level(severities: tuple[int, ...]) -> int:
    """활성 위험들이 요구하는 최소 Failsafe 레벨 (= 각 차원 요구 레벨의 최댓값).

    failsafe_manager 가 여러 트리거를 평가하며 `_transition` 으로 가장 높은
    레벨로 래칫하는 동작의 추상화 — "worst active hazard wins".
    """
    return max(
        (levels[sev] for sev, (_, levels) in zip(severities, HAZARD_DIMENSIONS, strict=False)),
        default=NORMAL,
    )


def is_safe(state: SafetyState) -> bool:
    """SAFE: 레벨 ≥ 활성 위험 요구 레벨 (우선순위 비역전)."""
    return state.level >= required_level(state.severities)


def controller_step(state: SafetyState) -> SafetyState:
    """컨트롤러 재평가 1스텝 — 레벨을 활성 위험 요구치로 래칫(절대 하강 없음).

    `failsafe_manager.update()` + `_transition()` 래칫 규칙 대응.
    """
    return SafetyState(
        level=max(state.level, required_level(state.severities)),
        severities=state.severities,
    )


def restore_step(state: SafetyState) -> SafetyState:
    """모든 위험 해제 시의 의도적 복귀 — 활성 위험이 없을 때만 NORMAL 로.

    `failsafe_manager.restore_comm()` 류의 명시적 de-escalation 대응.
    `required_level == NORMAL` ⟺ 모든 심각도 0 이므로 그 조건이 복귀 게이트다.
    """
    if required_level(state.severities) == NORMAL:
        return SafetyState(level=NORMAL, severities=state.severities)
    return state


Step = Callable[[SafetyState], SafetyState]


def _environment_successors(state: SafetyState) -> Iterable[SafetyState]:
    """환경(위험)의 한 차원이 한 단계 악화/완화한 후행 상태들 (레벨 불변)."""
    for i, (_, levels) in enumerate(HAZARD_DIMENSIONS):
        sev = state.severities[i]
        for nxt in (sev - 1, sev + 1):
            if 0 <= nxt < len(levels):
                new_sev = state.severities[:i] + (nxt,) + state.severities[i + 1:]
                yield SafetyState(level=state.level, severities=new_sev)


def successors(state: SafetyState, step: Step = controller_step) -> list[SafetyState]:
    """결정적 정렬된 1-스텝 후행 — 환경 위험 변화(레벨 불변) + 응답(step·복귀).

    환경 전이와 응답 전이가 *별개* 이므로, 위험이 오른 직후 컨트롤러가 아직
    반응 안 한 과도 상태도 도달 가능하다(의도된 모델링).
    """
    succ = set(_environment_successors(state))
    succ.add(step(state))
    succ.add(restore_step(state))
    succ.discard(state)
    return sorted(succ)


def initial_state() -> SafetyState:
    """초기 상태 — 모든 위험 없음·NORMAL (SAFE)."""
    return SafetyState(level=NORMAL, severities=(0,) * len(HAZARD_DIMENSIONS))


@dataclass(frozen=True)
class CheckResult:
    """모델 검사 결과."""

    holds: bool
    states_explored: int
    counterexample: tuple[SafetyState, ...] | None = None


def _recoverable(step: Step) -> Callable[[SafetyState], bool]:
    """기본 불변식 — 컨트롤러 1스텝이면 SAFE 회복 (복원 가능성)."""
    return lambda s: is_safe(step(s))


def check_invariant(
    invariant: Callable[[SafetyState], bool] | None = None,
    step: Step = controller_step,
    *,
    start: SafetyState | None = None,
) -> CheckResult:
    """초기 상태에서 도달 가능한 전 상태에 불변식을 전수 검증(BFS, 최단 반례).

    환경 전이와 `step` 응답 전이를 *모두* 따라가며 도달 가능 그래프를 BFS
    (`deque.popleft`, 진정한 너비 우선)로 전수 탐색한다. 기본 불변식은
    **복원 가능성** `is_safe(step(s))` — `step` 을 일부러 약화하면(예: 충돌
    무시) 검사기가 *최단* 반례 경로를 찾아낸다(음성 테스트).

    상태 공간은 유한(레벨 6 × 심각도 조합)이므로 종료가 보장된다.
    """
    if invariant is None:
        invariant = _recoverable(step)
    if start is None:
        start = initial_state()
    parent: dict[SafetyState, SafetyState | None] = {start: None}
    queue: deque[SafetyState] = deque([start])
    explored = 0
    while queue:
        cur = queue.popleft()
        explored += 1
        if not invariant(cur):
            return CheckResult(False, explored, _trace(parent, cur))
        for nxt in successors(cur, step):
            if nxt not in parent:
                parent[nxt] = cur
                queue.append(nxt)
    return CheckResult(True, explored, None)


def reachable_states(step: Step = controller_step) -> list[SafetyState]:
    """초기 상태에서 도달 가능한 전 상태 (정렬, BFS)."""
    seen = {initial_state()}
    queue: deque[SafetyState] = deque(seen)
    while queue:
        cur = queue.popleft()
        for nxt in successors(cur, step):
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return sorted(seen)


def controller_necessary(step: Step = controller_step) -> bool:
    """비공허성: 컨트롤러 없이 환경만 변하면 SAFE 를 위반하는 도달 가능 상태가
    실제로 존재하는가 — RECOVERABLE 이 공허한 참이 아님을 증명한다.
    """
    return any(not is_safe(s) for s in reachable_states(step))


def _trace(
    parent: dict[SafetyState, SafetyState | None], end: SafetyState
) -> tuple[SafetyState, ...]:
    """parent 링크를 따라 초기→위반 상태 경로 복원."""
    path: list[SafetyState] = []
    node: SafetyState | None = end
    while node is not None:
        path.append(node)
        node = parent[node]
    return tuple(reversed(path))
