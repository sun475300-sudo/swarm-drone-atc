"""ODYSSEY Phase 444 — CBS 완전성·최적성 조건 정리 (논문 §보강의 수치 검증부).

다중 에이전트 경로 계획기 ``simulation/cbs_planner/cbs.py`` 가 구현하는
Conflict-Based Search(CBS, Sharon et al. 2015)의 **완전성(completeness)**·
**최적성(optimality)** 보장이 어떤 전제 위에서 성립하는지를 형식화하고,
그 전제를 본 구현이 어디까지 충족하고 어디서 완화하는지를 수치적으로 감사한다.
형식 증명 서술은 ``docs/CBS_COMPLETENESS_OPTIMALITY.md``.

핵심 결과(Sharon et al. 2015, Thm 1·2):
  • **최적성**: CBS 가 비용 합(sum-of-costs) 최적해를 반환하려면 ─
      (O1) 저수준(low-level)이 제약 하에서 *비용 최적* 일치 경로를 반환하고,
      (O2) 고수준(high-level) CT 탐색이 비용을 1순위 키로 *최선 우선* 확장.
    본 구현은 (O1) 시공간 A*(허용적 맨해튼 휴리스틱)·(O2) ``heapq`` 비용 정렬로
    둘 다 충족한다 ─ 단, 무한 탐색을 가정할 때.
  • **완전성**: 해가 존재하면 찾으려면 ─
      (C1) 저수준이 완전하고,
      (C2) 충돌 분기가 *건전(sound)* 하다(두 자식 제약의 논리합이 충돌을 빠짐없이
           덮어 어떤 해도 잃지 않음),
      (C3) 탐색이 무한(노드 수 무제한).

본 구현의 **완화점**(honest gap):
  R1. 정점(vertex) 충돌 분기는 건전하나, **에지(swap) 충돌**도 정점 제약으로
      근사한다 ─ 정준 CBS 에지 제약이 아니므로 스왑 해소·완전성이 보장되지 않는다.
  R2. ``max_ct_nodes``·``max_astars``·``max_time`` 상한 → *유한·anytime* 변형.
      해가 깊으면 최적·완전 보장이 끊기고 best-effort 경로를 반환한다.
  R3. 고수준 동률 타이브레이크가 ``id(node)``(메모리 주소) ─ 비결정적이라
      프로젝트 재현성 규칙과 충돌(해의 최적성은 불변, 동률 해 선택만 흔들림).

본 모듈은 ``cbs.py`` 를 수정하지 않는 순수 추가이며 무작위성이 없는 결정적 함수다.
독립 BFS 기준해로 저수준 A* 의 최적성을, 논리합 검사로 분기 건전성을 핀으로 고정한다
(``tests/test_cbs_optimality.py``).
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from simulation.cbs_planner.cbs import (
    Conflict,
    Constraint,
    GridNode,
    get_neighbors,
    heuristic,
    low_level_astar,
)


def path_cost(path: list[GridNode]) -> int:
    """경로 비용 = 이동 스텝 수 = ``len(path) - 1`` (시작점 제외).

    ``cbs_plan`` 내부 합산 비용 ``sum(len(p))`` 은 여기에 에이전트 수 상수를 더한
    것과 단조 동등하므로, 최적성 판정에는 본 스텝 비용을 쓴다.
    """
    return max(len(path) - 1, 0)


# BFS 기준해 탐색 지평. 저수준 A* 기본 ``max_time=200`` 보다 높여, A* 가 지평에
# 절단당한 경우에도 BFS 는 진짜 최적을 찾아 불일치를 드러내게 한다(독립성 보강).
REFERENCE_MAX_TIME = 300


def reference_optimal_steps(
    start: GridNode,
    goal: GridNode,
    constraints: list[Constraint],
    drone_id: str,
    bounds: dict,
    max_time: int = REFERENCE_MAX_TIME,
) -> int | None:
    """제약 하에서 start→goal 최소 스텝 수를 BFS 로 독립 계산(기준해).

    저수준 A* 와 *무관한* 너비 우선 탐색이라, A* 가 반환한 비용이 진짜 최적인지
    교차 검증하는 근거가 된다. 단위 비용 시공간 그래프에서 BFS 는 최단(최소 스텝)을
    보장한다. 도달 불가(또는 ``max_time`` 지평 내 미도달)면 ``None``.

    한계(정직 공시): 이웃 생성은 ``cbs.py`` 의 ``get_neighbors`` 를 공유하므로
    그래프 구조(대기 포함 7-이웃)는 A* 와 동일하다 — 독립성은 *탐색 알고리즘*
    (BFS vs A*) 차원이지 그래프 정의 차원이 아니다. ``max_time`` 기본값을 A* 보다
    높여(``REFERENCE_MAX_TIME``) 탐색 지평 공유로 인한 위양성(둘 다 절단)을 줄인다.
    """
    forbidden = {(c.node, c.t) for c in constraints if c.drone_id == drone_id}
    # 상태 = (노드, 시간). 시작 (start, 0).
    queue: deque[tuple[GridNode, int]] = deque([(start, 0)])
    seen: set[tuple[GridNode, int]] = {(start, 0)}
    while queue:
        node, t = queue.popleft()
        # 시작 상태 (start, 0) 은 무조건 큐에 들어가므로, 목표 도달 반환 전
        # 해당 (노드, 시각) 이 금지 제약이 아닌지 확인한다. 이웃 확장은 이미
        # forbidden 을 거르지만 시작 상태는 거르지 않아, start==goal 에 t=0 제약이
        # 걸린 경우 위양성(비용 0)을 막기 위함.
        if node == goal and (node, t) not in forbidden:
            return t
        if t >= max_time:
            continue
        for nxt in get_neighbors(node, bounds):
            nt = t + 1
            if (nxt, nt) in forbidden:
                continue
            state = (nxt, nt)
            if state in seen:
                continue
            seen.add(state)
            queue.append((nxt, nt))
    return None


def heuristic_is_admissible(
    start: GridNode,
    goal: GridNode,
    bounds: dict,
    constraints: list[Constraint] | None = None,
    drone_id: str = "_probe",
) -> bool:
    """맨해튼 휴리스틱이 허용적(admissible)인지 검사: ``h(start) ≤ 진짜 최적 비용``.

    허용적 휴리스틱은 저수준 A* 최적성(O1)의 충분조건이다. 6-이웃+대기 단위
    비용 그래프에서 한 스텝은 좌표 하나만 ±1 바꾸므로 맨해튼 거리가 비용을 결코
    과대평가하지 않는다 ─ 이를 독립 BFS 기준해로 표본 검증한다.
    """
    opt = reference_optimal_steps(start, goal, constraints or [], drone_id, bounds)
    if opt is None:
        # 도달 불가(또는 지평 내 미도달) → 비용 무한대로 간주, 유한 휴리스틱은
        # 자명히 허용적. 단, max_time 절단으로 None 인 경우 h ≤ opt 를 *실제로*
        # 검증하지 않고 통과시키므로, 호출측은 도달 가능 인스턴스로 검사할 것.
        return True
    return heuristic(start, goal) <= opt


def low_level_is_optimal(
    start: GridNode,
    goal: GridNode,
    constraints: list[Constraint],
    drone_id: str,
    bounds: dict,
    astar_max_time: int = 200,
) -> bool:
    """저수준 A* 가 *비용 최적*(O1) 경로를 반환하는지 BFS 기준해로 검증.

    A* 경로 비용이 독립 BFS 최소 스텝과 정확히 일치하면 최적. A* 가 경로를
    못 찾으면(빈 리스트) BFS 도 도달 불가여야 일관(둘 다 ``None``/빈).

    ``astar_max_time`` 은 A* 에 명시 전달하고(기본 200 = ``cbs.py`` 기본값과 동기),
    BFS 기준해는 ``REFERENCE_MAX_TIME``(>200) 지평을 써 A* 가 절단당한 깊은
    최적해를 BFS 가 잡아 불일치로 드러내게 한다.

    한계(정직 공시): A* 가 빈 경로를 반환하는 두 원인 — *진짜 도달 불가* 와
    *``max_iterations`` 절단 타임아웃*(``cbs.py`` 의 ``low_level_astar``) — 을
    이 함수는 구별하지 못한다. ``astar_path == []`` 이고 ``bfs_steps is None`` 이면
    "양측이 각자 지평 안에서 해 없음에 합의"를 뜻하지 *증명된 도달 불가* 가 아니다.
    절단 타임아웃을 도달 불가로부터 분리하려면 ``low_level_astar`` 가 타임아웃 시
    별도 sentinel 을 반환하도록 ``cbs.py`` 를 확장해야 한다(본 모듈 범위 밖).
    """
    astar_path = low_level_astar(start, goal, constraints, drone_id, bounds, max_time=astar_max_time)
    bfs_steps = reference_optimal_steps(start, goal, constraints, drone_id, bounds)
    if not astar_path:
        return bfs_steps is None
    if bfs_steps is None:
        return False
    return path_cost(astar_path) == bfs_steps


def child_constraints(conflict: Conflict) -> tuple[Constraint, Constraint]:
    """``cbs_plan`` 이 한 충돌에 대해 생성하는 두 자식 제약(cbs.py 분기 로직 반영).

    ``cbs.py`` 는 ``for constrained_id in [conflict.drone_a, conflict.drone_b]`` 로
    각 드론에 ``Constraint(constrained_id, conflict.node, conflict.t)`` 정점 제약을
    추가한다. 본 헬퍼는 그 계약을 그대로 재현해, 건전성 검사가 *실제 분기 산출물*
    구조에 묶이게 한다(분기 로직이 바뀌면 검사가 깨지도록).
    """
    return (
        Constraint(conflict.drone_a, conflict.node, conflict.t),
        Constraint(conflict.drone_b, conflict.node, conflict.t),
    )


def vertex_branching_is_sound(conflict: Conflict) -> bool:
    """정점 충돌 분기의 건전성(C2): 두 자식 제약 논리합이 충돌을 빠짐없이 덮음.

    정점 충돌은 두 드론이 같은 (node, t) 를 점유한다(``A@node,t ∧ B@node,t``).
    ``cbs.py`` 가 생성하는 두 자식 제약(``child_constraints``)은 각각
    ``A≠node@t``·``B≠node@t`` 를 강제하므로, 그 논리합 ``¬(A@node,t) ∨ ¬(B@node,t)``
    은 정점 충돌 술어의 *정확한 부정* 이다 ─ 따라서 충돌 없는 모든 해를 덮어
    분기로 잃는 해가 없다(건전·완전). 본 함수는 (1) 서로 다른 두 드론, (2) 두
    제약이 정확히 충돌의 (node, t) 를 각 드론에 대해 금지함을 구조적으로 확인한다.
    """
    if conflict.drone_a == conflict.drone_b:
        return False
    ca, cb = child_constraints(conflict)
    return (
        ca.drone_id != cb.drone_id
        and ca.node == conflict.node == cb.node
        and ca.t == conflict.t == cb.t
    )


def is_edge_conflict(paths: dict[str, list[GridNode]], conflict: Conflict) -> bool:
    """주어진 충돌이 에지(swap) 충돌인지 판정.

    에지 충돌은 t-1→t 사이 두 드론이 서로의 위치를 맞바꾼다(A: u→v, B: v→u).
    ``cbs.py`` 의 ``detect_conflict`` 는 이때 ``Conflict(a, b, node=v, t)`` 를
    반환하고(v = A 가 t 에 도달하는 칸 = B 의 t-1 위치), 분기는 두 드론에
    정점 제약 ``≠ v@t`` 만 추가한다. 이는 정준 CBS 에지 제약이 아니라 R1 완화점이다:
    A 측 제약 ``A≠v@t`` 는 A 를 실제로 막지만, **B 측 제약 ``B≠v@t`` 는 공허(vacuous)**
    하다 ─ B 는 t 에 이미 u(≠v)에 있어 v 를 점유하지 않으므로 B 경로에 영향이 없다.
    따라서 스왑이 해소되지 않을 수 있고, 이것이 R1 이 *최적성이 아니라 완전성* 을
    깨는 정확한 메커니즘이다.
    """
    t = conflict.t
    if t == 0:
        return False
    pa, pb = paths.get(conflict.drone_a), paths.get(conflict.drone_b)
    if pa is None or pb is None:
        return False
    a_now = pa[min(t, len(pa) - 1)]
    a_prev = pa[min(t - 1, len(pa) - 1)]
    b_now = pb[min(t, len(pb) - 1)]
    b_prev = pb[min(t - 1, len(pb) - 1)]
    # 정점 충돌(같은 칸)이면 에지 충돌 아님.
    if a_now == b_now:
        return False
    return a_now == b_prev and b_now == a_prev


@dataclass(frozen=True)
class CBSGuaranteeAudit:
    """본 구현이 충족/완화하는 CBS 이론 보장 감사 결과.

    True = 정준 CBS 조건 충족, False = 완화(honest gap). 상세는 모듈 docstring·
    ``docs/CBS_COMPLETENESS_OPTIMALITY.md`` 참조.
    """

    low_level_admissible: bool  # O1 충분조건: 허용적 휴리스틱
    low_level_optimal: bool  # O1: 제약 하 비용 최적 경로
    high_level_best_first: bool  # O2: 비용 1순위 최선 우선 확장
    sound_vertex_branching: bool  # C2: 정점 충돌 분기 건전
    sound_edge_branching: bool  # R1: 에지 충돌 정준 제약 (False=정점 근사)
    unbounded_complete: bool  # C3: 무제한 탐색 (False=anytime 상한)
    deterministic_tiebreak: bool  # R3: 동률 타이브레이크 결정성 (False=id())

    @property
    def is_optimal_when_terminates(self) -> bool:
        """정점 충돌만 있는 인스턴스에서 *종료했다면* 비용 최적해 보장 여부.

        조건부 최적성이다 ─ ``unbounded_complete`` 를 포함하지 않으므로 종료 자체는
        보장하지 않는다(R2 상한에 걸리면 best-effort 반환). "종료 시"는 전제이지
        보장이 아니다.
        """
        return (
            self.low_level_admissible
            and self.low_level_optimal
            and self.high_level_best_first
            and self.sound_vertex_branching
        )

    @property
    def is_textbook_complete(self) -> bool:
        """교과서적 완전성(에지 포함·무한 탐색) 보장 여부."""
        return self.sound_edge_branching and self.unbounded_complete


def audit_sdacs_cbs() -> CBSGuaranteeAudit:
    """현행 ``simulation/cbs_planner/cbs.py`` 의 CBS 보장 감사(고정 상수).

    구현을 정적으로 분석한 결론을 명시한다. 동적 검증(저수준 최적·분기 건전)은
    ``tests/test_cbs_optimality.py`` 가 구체 인스턴스로 핀 고정한다.
    """
    return CBSGuaranteeAudit(
        low_level_admissible=True,  # 맨해튼 거리 = 단위 비용 그래프 허용적
        low_level_optimal=True,  # 허용적 A* + 일관 비용 → 최적 (BFS 교차 검증)
        high_level_best_first=True,  # heapq 1순위 키 = cost
        sound_vertex_branching=True,  # 정점 제약 논리합이 충돌 전부 덮음
        sound_edge_branching=False,  # R1: 에지 충돌도 정점 제약으로 근사
        unbounded_complete=False,  # R2: max_ct_nodes/max_astars/max_time 상한
        deterministic_tiebreak=False,  # R3: id() 메모리 주소 타이브레이크
    )
