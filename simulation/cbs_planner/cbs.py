"""
CBS (Conflict-Based Search) 다중 에이전트 경로 계획
분산 드론 시스템에서 전역 충돌 없는 경로 세트를 계산

알고리즘:
  High Level: 충돌 트리(CT) 탐색 - 제약 조건 추가하며 최적 경로 쌍 탐색
  Low Level:  개별 드론 A* 경로 계획 (제약 조건 적용)

참고: Sharon et al. (2015) "Conflict-based search for optimal multi-agent pathfinding"
"""
from __future__ import annotations
import heapq
from dataclasses import dataclass, field
from typing import Optional
import numpy as np


# 공역 그리드 설정
GRID_RESOLUTION = 50.0    # 격자 해상도 (m) - 드론 이격 기준에 맞춤
TIME_STEP = 1.0           # 시간 스텝 (s)


@dataclass
class GridNode:
    """공역 격자 노드"""
    x: int
    y: int
    z: int

    def __eq__(self, other):
        return (self.x, self.y, self.z) == (other.x, other.y, other.z)

    def __hash__(self):
        return hash((self.x, self.y, self.z))

    def to_position(self, res: float = GRID_RESOLUTION) -> np.ndarray:
        return np.array([self.x * res, self.y * res, self.z * res])


@dataclass(order=True)
class AStarNode:
    """A* 탐색 노드"""
    f: float
    g: float = field(compare=False)
    node: GridNode = field(compare=False)
    t: int = field(compare=False)           # 시간 스텝
    parent: Optional["AStarNode"] = field(compare=False, default=None)


@dataclass
class Constraint:
    """CBS 제약 조건"""
    drone_id: str
    node: GridNode
    t: int                                   # 금지 시간 스텝


@dataclass
class Conflict:
    """두 드론 간 충돌"""
    drone_a: str
    drone_b: str
    node: GridNode
    t: int


@dataclass
class CTNode:
    """충돌 트리 노드"""
    constraints: list[Constraint]
    paths: dict[str, list[GridNode]]
    cost: float                              # 모든 경로 합산 비용


def heuristic(node: GridNode, goal: GridNode) -> float:
    """맨해튼 거리 휴리스틱 (3D)"""
    return abs(node.x - goal.x) + abs(node.y - goal.y) + abs(node.z - goal.z)


def get_neighbors(node: GridNode, bounds: dict) -> list[GridNode]:
    """6방향 이웃 + 정지(wait) 포함"""
    moves = [
        (1, 0, 0), (-1, 0, 0),
        (0, 1, 0), (0, -1, 0),
        (0, 0, 1), (0, 0, -1),
        (0, 0, 0),  # 대기
    ]
    neighbors = []
    for dx, dy, dz in moves:
        nx, ny, nz = node.x + dx, node.y + dy, node.z + dz
        if (bounds["x"][0] <= nx <= bounds["x"][1] and
                bounds["y"][0] <= ny <= bounds["y"][1] and
                bounds["z"][0] <= nz <= bounds["z"][1]):
            neighbors.append(GridNode(nx, ny, nz))
    return neighbors


def low_level_astar(
    start: GridNode,
    goal: GridNode,
    constraints: list[Constraint],
    drone_id: str,
    bounds: dict,
    max_time: int = 200,
) -> list[GridNode]:
    """
    제약 조건을 고려한 시공간 A* (Low Level CBS)
    """
    constraint_set = {(c.node, c.t) for c in constraints if c.drone_id == drone_id}

    open_heap: list[AStarNode] = []
    start_node = AStarNode(f=heuristic(start, goal), g=0, node=start, t=0)
    heapq.heappush(open_heap, start_node)

    visited = {}
    max_expansions = max_time * 500  # 탐색 노드 수 상한 (무한루프 방지)
    expansions = 0

    while open_heap and expansions < max_expansions:
        current = heapq.heappop(open_heap)
        expansions += 1

        if current.node == goal:
            # 경로 역추적
            path = []
            node = current
            while node is not None:
                path.append(node.node)
                node = node.parent
            return list(reversed(path))

        state = (current.node, current.t)
        if state in visited:
            continue
        visited[state] = current.g

        if current.t >= max_time:
            continue

        for neighbor in get_neighbors(current.node, bounds):
            next_t = current.t + 1
            if (neighbor, next_t) in constraint_set:
                continue  # 제약 조건 위반

            g_new = current.g + 1
            f_new = g_new + heuristic(neighbor, goal)
            next_node = AStarNode(
                f=f_new, g=g_new,
                node=neighbor, t=next_t,
                parent=current
            )
            heapq.heappush(open_heap, next_node)

    return []  # 경로 없음


def detect_conflict(
    paths: dict[str, list[GridNode]]
) -> Optional[Conflict]:
    """모든 드론 쌍에서 첫 번째 충돌 탐지"""
    drone_ids = list(paths.keys())
    if not paths:
        return None
    max_t = max(len(p) for p in paths.values())

    for i in range(len(drone_ids)):
        for j in range(i + 1, len(drone_ids)):
            id_a, id_b = drone_ids[i], drone_ids[j]
            path_a, path_b = paths[id_a], paths[id_b]

            for t in range(max_t):
                node_a = path_a[min(t, len(path_a) - 1)]
                node_b = path_b[min(t, len(path_b) - 1)]

                if node_a == node_b:
                    return Conflict(id_a, id_b, node_a, t)

                # 에지 충돌 (스왑)
                if t > 0:
                    prev_a = path_a[min(t - 1, len(path_a) - 1)]
                    prev_b = path_b[min(t - 1, len(path_b) - 1)]
                    if node_a == prev_b and node_b == prev_a:
                        return Conflict(id_a, id_b, node_a, t)

    return None


def cbs_plan(
    starts: dict[str, GridNode],
    goals: dict[str, GridNode],
    bounds: dict,
    max_ct_nodes: int = 1000,
) -> dict[str, list[GridNode]]:
    """
    CBS 메인 알고리즘
    충돌 없는 경로 세트 반환

    Args:
        starts:  {drone_id: start_node}
        goals:   {drone_id: goal_node}
        bounds:  {"x": [min, max], "y": [...], "z": [...]}

    Returns:
        {drone_id: [GridNode, ...]} 충돌 없는 경로
    """
    drone_ids = list(starts.keys())

    # 초기 경로 계산 (제약 조건 없음)
    initial_paths = {}
    for did in drone_ids:
        path = low_level_astar(starts[did], goals[did], [], did, bounds)
        if not path:
            # 경로 없음 → 시작 위치에서 대기
            initial_paths[did] = [starts[did]]
        else:
            initial_paths[did] = path

    root = CTNode(
        constraints=[],
        paths=initial_paths,
        cost=sum(len(p) for p in initial_paths.values())
    )

    open_list = [(root.cost, id(root), root)]
    explored = 0

    while open_list and explored < max_ct_nodes:
        _, _, current_ct = heapq.heappop(open_list)
        explored += 1

        conflict = detect_conflict(current_ct.paths)
        if conflict is None:
            return current_ct.paths  # 충돌 없음 → 완료

        # 두 드론에 각각 제약 조건 추가 → 두 자식 노드 생성
        for constrained_id in [conflict.drone_a, conflict.drone_b]:
            new_constraint = Constraint(constrained_id, conflict.node, conflict.t)
            new_constraints = current_ct.constraints + [new_constraint]

            new_paths = dict(current_ct.paths)
            new_path = low_level_astar(
                starts[constrained_id], goals[constrained_id],
                new_constraints, constrained_id, bounds
            )
            if new_path:
                new_paths[constrained_id] = new_path

                child = CTNode(
                    constraints=new_constraints,
                    paths=new_paths,
                    cost=sum(len(p) for p in new_paths.values())
                )
                heapq.heappush(open_list, (child.cost, id(child), child))

    # 최대 탐색 노드 초과 → 현재 최선의 경로 반환 (충돌 미해결 가능)
    # 호출자는 반환된 경로에 잔여 충돌이 있을 수 있음을 인지해야 함
    return current_ct.paths


def position_to_grid(pos: np.ndarray, res: float = GRID_RESOLUTION) -> GridNode:
    """연속 위치 → 격자 노드"""
    return GridNode(
        x=int(round(pos[0] / res)),
        y=int(round(pos[1] / res)),
        z=int(round(pos[2] / res)),
    )
