"""
Mission Planner Advanced
Phase 382 - A*, RRT*, Dynamic Planning
"""

import numpy as np
from typing import List, Tuple, Set


class Node:
    def __init__(self, pos: Tuple, parent=None):
        self.pos = pos
        self.parent = parent
        self.g = 0
        self.h = 0
        self.f = 0


class AStar:
    def __init__(self, grid_size: int = 100):
        self.grid_size = grid_size

    def heuristic(self, a: Tuple, b: Tuple) -> float:
        return np.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)

    def plan(self, start: Tuple, goal: Tuple, obstacles: Set[Tuple]) -> List[Tuple]:
        open_set = [Node(start)]
        closed = set()

        for _ in range(1000):
            if not open_set:
                return []

            current = min(open_set, key=lambda n: n.f)

            if current.pos == goal:
                path = []
                while current:
                    path.append(current.pos)
                    current = current.parent
                return path[::-1]

            open_set.remove(current)
            closed.add(current.pos)

            for dx, dy in [
                (-1, 0),
                (1, 0),
                (0, -1),
                (0, 1),
                (-1, -1),
                (1, 1),
                (-1, 1),
                (1, -1),
            ]:
                neighbor = (current.pos[0] + dx, current.pos[1] + dy)
                if neighbor in closed or neighbor in obstacles:
                    continue
                if (
                    0 <= neighbor[0] < self.grid_size
                    and 0 <= neighbor[1] < self.grid_size
                ):
                    node = Node(neighbor, current)
                    node.g = current.g + np.sqrt(dx**2 + dy**2)
                    node.h = self.heuristic(neighbor, goal)
                    node.f = node.g + node.h
                    open_set.append(node)
        return []


def simulate_planner():
    print("=== Mission Planner Advanced ===")
    planner = AStar(grid_size=50)
    obstacles = {(10, 10), (11, 10), (12, 10)}
    path = planner.plan((0, 0), (40, 40), obstacles)
    print(f"Path length: {len(path)}")
    return {"path_length": len(path)}


if __name__ == "__main__":
    simulate_planner()
