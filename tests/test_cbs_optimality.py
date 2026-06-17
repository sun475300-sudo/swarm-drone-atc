"""ODYSSEY Phase 444 — CBS 완전성·최적성 조건 검증 테스트.

``simulation/cbs_optimality.py`` 의 핵심 주장을 핀으로 고정한다:

  O1a. 맨해튼 휴리스틱이 허용적(h ≤ 진짜 최적 비용) — 저수준 최적성 충분조건.
  O1b. 저수준 A* 가 제약 유무와 무관하게 BFS 기준해와 동일한 비용 최적 경로 반환.
  C2.  정점 충돌 분기가 건전(두 자식 제약 논리합이 충돌을 빠짐없이 덮음).
  R1.  에지(swap) 충돌을 정점 제약으로 근사하는 완화점이 감사에 정직히 드러남.
  AUDIT. ``audit_sdacs_cbs`` 가 충족 보장과 완화점을 정확히 분류.
"""
from __future__ import annotations

from simulation.cbs_planner.cbs import Conflict, Constraint, GridNode, cbs_plan, detect_conflict
from simulation.cbs_optimality import (
    audit_sdacs_cbs,
    child_constraints,
    heuristic_is_admissible,
    is_edge_conflict,
    low_level_is_optimal,
    path_cost,
    reference_optimal_steps,
    vertex_branching_is_sound,
)

BOUNDS = {"x": [0, 6], "y": [0, 6], "z": [0, 2]}


# ── O1a. 휴리스틱 허용성 ──────────────────────────────────────────────
def test_manhattan_heuristic_is_admissible_unconstrained():
    """맨해튼 휴리스틱이 제약 없는 표본 쌍에서 허용적이다."""
    pairs = [
        (GridNode(0, 0, 0), GridNode(5, 5, 2)),
        (GridNode(1, 4, 0), GridNode(4, 1, 1)),
        (GridNode(3, 3, 1), GridNode(3, 3, 1)),  # 동일점: h=0
    ]
    for start, goal in pairs:
        assert heuristic_is_admissible(start, goal, BOUNDS)


def test_manhattan_heuristic_admissible_with_constraints():
    """제약이 우회를 강제해 실제 비용이 늘어도 휴리스틱은 여전히 허용적이다."""
    start, goal = GridNode(0, 0, 0), GridNode(2, 0, 0)
    # (1,0,0) 을 t=1,2 에 막아 직진을 방해 → 실제 비용 ≥ 맨해튼(=2)
    constraints = [
        Constraint("d1", GridNode(1, 0, 0), 1),
        Constraint("d1", GridNode(1, 0, 0), 2),
    ]
    assert heuristic_is_admissible(start, goal, BOUNDS, constraints, "d1")


# ── O1b. 저수준 A* 최적성 ────────────────────────────────────────────
def test_low_level_astar_optimal_unconstrained():
    """제약 없는 A* 경로 비용 = BFS 최소 스텝 = 맨해튼 거리."""
    start, goal = GridNode(0, 0, 0), GridNode(3, 2, 0)
    assert low_level_is_optimal(start, goal, [], "d1", BOUNDS)
    assert reference_optimal_steps(start, goal, [], "d1", BOUNDS) == 5


def test_low_level_astar_optimal_with_detour_constraint():
    """제약이 우회를 강제해도 A* 가 BFS 와 동일한 최적 비용을 반환한다."""
    start, goal = GridNode(0, 0, 0), GridNode(2, 0, 0)
    constraints = [
        Constraint("d1", GridNode(1, 0, 0), 1),
        Constraint("d1", GridNode(1, 0, 0), 2),
    ]
    assert low_level_is_optimal(start, goal, constraints, "d1", BOUNDS)


def test_low_level_unreachable_consistent():
    """A* 와 BFS 가 도달 불가를 일관되게 보고한다(둘 다 해 없음).

    단일 노드 공간에서 goal 을 그 노드 밖에 두면, 탐색 지평·상수와 무관하게
    *구조적으로* 도달 불가다(경계가 이동을 전혀 허용하지 않음).
    """
    single = {"x": [0, 0], "y": [0, 0], "z": [0, 0]}  # (0,0,0) 단일 칸
    start, goal = GridNode(0, 0, 0), GridNode(1, 0, 0)  # goal 은 경계 밖
    assert low_level_is_optimal(start, goal, [], "d1", single)


def test_reference_respects_t0_constraint_on_start_goal():
    """start==goal 라도 t=0 금지 제약이 걸리면 BFS 기준해가 비용 0 을 반환하지 않는다.

    시작 상태 (start,0) 은 무조건 큐에 들어가므로, 목표 반환 전 forbidden 검사가
    없으면 t=0 제약을 무시한 위양성(비용 0)이 난다(code-reviewer HIGH 반영).
    """
    node = GridNode(2, 2, 0)
    forbid_start = [Constraint("d1", node, 0)]
    # t=0 제약 → 즉시 머무를 수 없어 (대기 후) 더 늦은 시각에야 목표 충족.
    steps = reference_optimal_steps(node, node, forbid_start, "d1", BOUNDS)
    assert steps is not None and steps >= 1
    # 제약이 없으면 비용 0 (즉시 도달).
    assert reference_optimal_steps(node, node, [], "d1", BOUNDS) == 0


def test_path_cost_counts_steps():
    """path_cost 는 시작점을 제외한 이동 스텝 수다."""
    path = [GridNode(0, 0, 0), GridNode(1, 0, 0), GridNode(2, 0, 0)]
    assert path_cost(path) == 2
    assert path_cost([GridNode(0, 0, 0)]) == 0
    assert path_cost([]) == 0


# ── C2. 분기 건전성 ──────────────────────────────────────────────────
def test_vertex_branching_is_sound_for_distinct_drones():
    """서로 다른 두 드론의 정점 충돌 분기는 건전하다."""
    conflict = Conflict("a", "b", GridNode(2, 2, 0), 3)
    assert vertex_branching_is_sound(conflict)


def test_child_constraints_mirror_cbs_branching():
    """child_constraints 가 cbs.py 분기 산출물(두 드론·동일 node·t)을 정확히 재현."""
    conflict = Conflict("a", "b", GridNode(2, 2, 0), 3)
    ca, cb = child_constraints(conflict)
    assert ca == Constraint("a", GridNode(2, 2, 0), 3)
    assert cb == Constraint("b", GridNode(2, 2, 0), 3)


def test_branching_unsound_for_self_conflict():
    """동일 드론 충돌(자기 자신)은 분기 건전성이 성립하지 않는다."""
    conflict = Conflict("a", "a", GridNode(1, 1, 0), 2)
    assert not vertex_branching_is_sound(conflict)


def test_branching_disjunction_resolves_crossing_conflict():
    """정점 분기 건전성의 실증: 교차(crossing) 정점 충돌을 CBS 가 충돌 없이 해소한다.

    수평 이동 a 와 수직 이동 b 가 (1,1,0) 을 t=1 에 동시 점유하는 *순수 정점*
    충돌이다(스왑 아님). 정점 제약 분기가 건전하므로 한쪽이 우회/대기해 해소된다.
    정면 스왑(에지 충돌)은 R1 완화점 ─ 별도 ``is_edge_conflict`` 로 다룬다.
    """
    starts = {"a": GridNode(0, 1, 0), "b": GridNode(1, 0, 0)}
    goals = {"a": GridNode(2, 1, 0), "b": GridNode(1, 2, 0)}
    root_paths = {
        "a": [GridNode(0, 1, 0), GridNode(1, 1, 0), GridNode(2, 1, 0)],
        "b": [GridNode(1, 0, 0), GridNode(1, 1, 0), GridNode(1, 2, 0)],
    }
    root_conflict = detect_conflict(root_paths)
    assert root_conflict is not None and not is_edge_conflict(root_paths, root_conflict)
    paths = cbs_plan(starts, goals, BOUNDS)
    assert detect_conflict(paths) is None


# ── R1. 에지 충돌 완화점 ─────────────────────────────────────────────
def test_edge_conflict_detection():
    """t-1→t 위치 교환(swap)을 에지 충돌로 식별한다."""
    paths = {
        "a": [GridNode(0, 0, 0), GridNode(1, 0, 0)],
        "b": [GridNode(1, 0, 0), GridNode(0, 0, 0)],
    }
    conflict = Conflict("a", "b", GridNode(1, 0, 0), 1)
    assert is_edge_conflict(paths, conflict)


def test_vertex_conflict_not_flagged_as_edge():
    """같은 칸 점유(정점 충돌)는 에지 충돌로 오분류되지 않는다."""
    paths = {
        "a": [GridNode(0, 0, 0), GridNode(1, 0, 0)],
        "b": [GridNode(2, 0, 0), GridNode(1, 0, 0)],
    }
    conflict = Conflict("a", "b", GridNode(1, 0, 0), 1)
    assert not is_edge_conflict(paths, conflict)


# ── AUDIT. 보장·완화 분류 ────────────────────────────────────────────
def test_audit_reports_satisfied_guarantees():
    """감사가 충족 보장(O1·O2·C2)을 True 로 보고한다."""
    audit = audit_sdacs_cbs()
    assert audit.low_level_admissible
    assert audit.low_level_optimal
    assert audit.high_level_best_first
    assert audit.sound_vertex_branching


def test_audit_reports_honest_relaxations():
    """감사가 완화점(R1·R2·R3)을 False 로 정직히 드러낸다."""
    audit = audit_sdacs_cbs()
    assert not audit.sound_edge_branching  # R1
    assert not audit.unbounded_complete  # R2
    assert not audit.deterministic_tiebreak  # R3


def test_audit_derived_conclusions():
    """파생 결론: 정점 인스턴스 종료 시 최적이나 교과서적 완전성은 미보장."""
    audit = audit_sdacs_cbs()
    assert audit.is_optimal_when_terminates
    assert not audit.is_textbook_complete
