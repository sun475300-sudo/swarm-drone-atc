"""ODYSSEY Phase 442 — ATC 핸드오프 데드락 부재 모델 체킹.

Phase 441 이 TLA+ 로 *명세* 한 5계층 안전망 우선순위 불변식과 짝을 이루어, 본
모듈은 인스턴스 간 **관제권 핸드오프 프로토콜**(Phase 423
:class:`~simulation.federation_handover.HandoverCoordinator` 가 다루는 경계 통과
이양)이 어떤 메시지 인터리빙에서도 **교착(deadlock)에 빠지지 않고**, 드론이 한순간도
**관제 공백(orphan)** 상태가 되지 않음을 *유한 상태 명시적 탐색*으로 증명한다.

TLA+/TLC 가 없는 환경에서도 동작하도록, 표준 TLC 의 핵심 능력 — 도달 가능 상태
공간 BFS 전수 탐색 + 불변식 위반·교착 반례(counterexample) 추적 — 을 순수 파이썬
결정적 체커로 구현한다. 외부 의존·랜덤 없이, 동일 모델은 항상 동일한 반례를 낸다.

검증하는 두 핵심 성질:

- **상호 배제 / 관제 공백 부재 (안전)** — 어느 도달 상태에서도 드론의 관제 권위는
  정확히 한 인스턴스가 보유한다(``auth ∈ {A, B}``). 두 인스턴스가 동시에 권위를
  주장(``AB``)하거나, 아무도 보유하지 않는(``NONE``) 상태는 도달 불가다.
- **교착 부재 (진행)** — 도달 가능한 모든 상태는 (a) 핸드오프가 완결된 종료
  상태이거나, (b) 활성화된 전이가 최소 하나 존재한다. 즉 "완료되지 않았는데 더는
  진행할 수 없는" 막힌 상태가 없다.

올바른 2단계(prepare→ack→commit) 프로토콜은 위 둘을 모두 만족함을 보이고, 이를
대조하기 위해 세 변형 모델을 함께 제공한다:

- :func:`orphan_bug_model` — A 가 ACK 수신 *전에* 권위를 미리 내려놓는 흔한 버그.
  체커가 ``NONE`` 도달(관제 공백) 반례를 찾아낸다.
- :func:`lossy_model` — ACK 가 유실될 수 있으나 재전송이 없는 모델. 체커가 교착
  상태("B 는 준비됐다고 믿지만 A 는 영영 권위를 넘기지 못함") 반례를 찾아낸다.
- :func:`timeout_model` — 유실 모델에 B 측 타임아웃 재전송을 더한 수정본. 교착이
  사라진다(단, 적대적 무한 유실 하의 *무조건적 liveness* 가 아니라 교착 부재를
  복원한다는 점을 명시).
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace
from typing import Callable, Hashable

# ── 관제 권위 보유자 도메인 ──────────────────────────────────────────────
AUTH_A = "A"  # 현재(원) 관제 인스턴스
AUTH_B = "B"  # 대상(목적) 관제 인스턴스
AUTH_NONE = "NONE"  # 관제 공백 — 불변식 위반(드론 고아)
AUTH_BOTH = "AB"  # 이중 관제 — 불변식 위반(모순 명령 위험)

LEGAL_AUTH: frozenset[str] = frozenset({AUTH_A, AUTH_B})

# ── 채널 메시지 ───────────────────────────────────────────────────────────
MSG_NONE = ""
MSG_PREPARE = "PREPARE"  # A → B: 이양 개시
MSG_ACK = "ACK"  # B → A: 권위 수락
MSG_REJECT = "REJECT"  # B → A: 커버리지 없음, 거절

# 상태 공간 폭발을 막기 위한 방어적 상한(유한 모델이므로 실제로는 수십 상태).
DEFAULT_MAX_STATES: int = 100_000


@dataclass(frozen=True, order=True)
class HandoffState:
    """핸드오프 프로토콜의 전역 상태(불변).

    한 번에 채널 메시지는 최대 하나만 비행 중(``msg``)이라고 모델링한다 — 단일
    드론 한 대의 단일 경계 통과를 추적하기에 충분하며 상태 공간을 작게 유지한다.
    """

    auth: str = AUTH_A
    msg: str = MSG_NONE
    b_ready: bool = False  # B 가 권위 수락을 확정했는가
    done: bool = False  # 핸드오프 완결(이양 또는 거절 확정)


# 전이 함수 타입: 한 상태 → 후속 상태들의 모음(순서 무관, 체커가 정렬).
Transitions = Callable[[HandoffState], "list[HandoffState]"]


@dataclass(frozen=True)
class CheckResult:
    """모델 체킹 결과(불변)."""

    holds: bool
    violation: str  # "", "invariant", "deadlock"
    states_explored: int
    counterexample: tuple[HandoffState, ...]  # 초기→위반 상태 추적, holds 면 빈 튜플

    def __bool__(self) -> bool:
        return self.holds


# ── 명시적 상태 모델 체커 (BFS 전수 탐색) ────────────────────────────────
def check_model(
    initial: HandoffState,
    successors: Transitions,
    *,
    invariant: Callable[[HandoffState], bool] | None = None,
    is_accepting: Callable[[HandoffState], bool] | None = None,
    max_states: int = DEFAULT_MAX_STATES,
) -> CheckResult:
    """초기 상태에서 도달 가능한 전 상태를 BFS 로 전수 탐색한다.

    - ``invariant`` 위반 상태를 만나면 초기→그 상태 최단 경로를 반례로 즉시 반환.
    - 후속이 없는데 ``is_accepting`` 이 아닌(또는 미지정) 상태를 만나면 교착으로
      판정하고 반례를 반환.

    탐색 순서·반례는 후속 상태를 정렬해 결정적이다(동일 모델→동일 반례).

    Raises:
        ValueError: 도달 상태 수가 ``max_states`` 를 초과(유한성 가정 위반).
    """
    visited: set[HandoffState] = {initial}
    parent: dict[HandoffState, HandoffState | None] = {initial: None}
    queue: deque[HandoffState] = deque([initial])

    def trace_to(state: HandoffState) -> tuple[HandoffState, ...]:
        path: list[HandoffState] = []
        node: HandoffState | None = state
        while node is not None:
            path.append(node)
            node = parent[node]
        return tuple(reversed(path))

    while queue:
        state = queue.popleft()

        if invariant is not None and not invariant(state):
            return CheckResult(False, "invariant", len(visited), trace_to(state))

        succs = sorted(set(successors(state)))

        if not succs and not (is_accepting is not None and is_accepting(state)):
            return CheckResult(False, "deadlock", len(visited), trace_to(state))

        for nxt in succs:
            if nxt not in visited:
                visited.add(nxt)
                parent[nxt] = state
                queue.append(nxt)
                if len(visited) > max_states:
                    raise ValueError(
                        f"상태 공간이 max_states={max_states} 를 초과 — 모델 유한성 확인 필요"
                    )

    return CheckResult(True, "", len(visited), ())


# ── 공통 불변식 / 종료 술어 ──────────────────────────────────────────────
def single_controller_invariant(state: HandoffState) -> bool:
    """드론의 관제 권위는 항상 정확히 한 인스턴스가 보유한다(공백·이중 금지)."""
    return state.auth in LEGAL_AUTH


def is_done(state: HandoffState) -> bool:
    """핸드오프가 완결된 종료(accepting) 상태인가."""
    return state.done


# ── 올바른 2단계 핸드오프 프로토콜 ───────────────────────────────────────
def handoff_transitions(state: HandoffState) -> list[HandoffState]:
    """올바른 prepare→ack→commit 핸드오프.

    핵심: A 는 **ACK 를 받은 바로 그 순간** 권위를 A→B 로 *직접* 넘긴다. 권위가
    ``NONE`` 을 거치는 중간 틈이 없으므로 관제 공백이 생기지 않는다. B 의 수락/거절은
    비결정적으로 분기해 모든 인터리빙을 탐색한다.
    """
    if state.done:
        return []

    succ: list[HandoffState] = []

    # A: 경계 통과 감지 → 이양 개시(채널이 비고 아직 B 가 준비 전일 때).
    if state.auth == AUTH_A and state.msg == MSG_NONE and not state.b_ready:
        succ.append(replace(state, msg=MSG_PREPARE))

    # B: PREPARE 수신 → 수락(ACK + 준비 확정) 또는 거절(REJECT). 비결정적 분기.
    if state.msg == MSG_PREPARE:
        succ.append(replace(state, msg=MSG_ACK, b_ready=True))  # 수락
        succ.append(replace(state, msg=MSG_REJECT))  # 커버리지 없음 → 거절

    # A: ACK 수신 → 권위를 A→B 직접 이양하며 완결(중간 공백 없음).
    if state.msg == MSG_ACK and state.auth == AUTH_A:
        succ.append(replace(state, msg=MSG_NONE, auth=AUTH_B, done=True))

    # A: REJECT 수신 → 권위 유지(auth=A)한 채 이양 중단 완결.
    if state.msg == MSG_REJECT and state.auth == AUTH_A:
        succ.append(replace(state, msg=MSG_NONE, done=True))

    return succ


def orphan_bug_model(state: HandoffState) -> list[HandoffState]:
    """버그 모델: A 가 PREPARE 를 보내며 권위를 *미리* 내려놓는다.

    "전송했으니 곧 넘어가겠지" 라는 흔한 낙관적 오류 — B 가 수락하기 전 권위가
    ``NONE`` 이 되어 관제 공백이 발생한다. 체커가 불변식 반례로 검출해야 한다.
    """
    if state.done:
        return []

    succ: list[HandoffState] = []

    if state.auth == AUTH_A and state.msg == MSG_NONE and not state.b_ready:
        # 버그: 권위를 미리 NONE 으로 — orphan!
        succ.append(replace(state, msg=MSG_PREPARE, auth=AUTH_NONE))

    if state.msg == MSG_PREPARE:
        succ.append(replace(state, msg=MSG_ACK, b_ready=True))

    if state.msg == MSG_ACK:
        succ.append(replace(state, msg=MSG_NONE, auth=AUTH_B, done=True))

    return succ


def lossy_model(state: HandoffState) -> list[HandoffState]:
    """유실 모델: ACK 가 유실될 수 있으나 재전송이 없다.

    B 가 ``b_ready`` 를 확정한 뒤 ACK 가 사라지면, A 는 권위를 넘기지 못하고 B 가
    이미 준비됐다는 이유로 PREPARE 재전송도 막혀 영영 멈춘다 — 교착. 체커가 교착
    반례로 검출해야 한다.
    """
    succ = handoff_transitions(state)
    # 비행 중 ACK 가 유실(채널 비움)될 수 있다 — 재전송 없음.
    if state.msg == MSG_ACK:
        succ.append(replace(state, msg=MSG_NONE))
    return succ


def timeout_model(state: HandoffState) -> list[HandoffState]:
    """타임아웃 수정본: 유실 모델 + B 측 ACK 재전송.

    B 가 준비됐고(``b_ready``) 채널이 비었는데 아직 완결 전이면(즉 ACK 유실 후) B 가
    타임아웃으로 ACK 를 재전송한다. 이로써 모든 도달 상태가 다시 전이를 가져 교착이
    사라진다. 단, 적대적 무한 유실 하에서도 *반드시 완료* 한다는 무조건적 liveness
    가 아니라, **교착 부재**(어느 상태든 진행 가능)를 복원함을 검증한다.
    """
    succ = lossy_model(state)
    if state.b_ready and state.msg == MSG_NONE and not state.done:
        succ.append(replace(state, msg=MSG_ACK))  # B 타임아웃 재전송
    return succ


def verify_handoff_safe(
    transitions: Transitions = handoff_transitions,
    initial: HandoffState | None = None,
) -> CheckResult:
    """관제 공백 부재(상호 배제) 안전 성질을 검증한다.

    먼저 안전 불변식(단일 관제권)을 확인하고, 통과 시 교착 부재까지 함께 검증한
    결과를 반환한다(불변식 위반이 있으면 그 반례를 우선 반환).
    """
    return check_model(
        initial if initial is not None else HandoffState(),
        transitions,
        invariant=single_controller_invariant,
        is_accepting=is_done,
    )


def verify_handoff_deadlock_free(
    transitions: Transitions = handoff_transitions,
    initial: HandoffState | None = None,
) -> CheckResult:
    """교착 부재만 독립적으로 검증한다(불변식 검사 없이)."""
    return check_model(
        initial if initial is not None else HandoffState(),
        transitions,
        is_accepting=is_done,
    )
