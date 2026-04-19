"""
Phase 402: Advanced Path Planner with Dynamic RRT*, A*, and Hybrid Optimization
"""

import numpy as np
from typing import List, Tuple, Optional, Dict, Set
from dataclasses import dataclass, field
from enum import Enum
import heapq
from collections import defaultdict
import time


class PathMetric(Enum):
    DISTANCE = "distance"
    TIME = "time"
    ENERGY = "energy"
    SAFETY = "safety"


@dataclass
class Waypoint:
    x: float
    y: float
    z: float
    velocity: float = 0.0
    timestamp: float = 0.0
    cost: float = 0.0
    parent: Optional["Waypoint"] = None


@dataclass
class PathResult:
    waypoints: List[Waypoint]
    total_distance: float
    total_time: float
    total_energy: float
    safety_score: float
    algorithm: str
    computation_time: float


class AdvancedPathPlanner:
    def __init__(
        self,
        bounds: Tuple[float, float, float, float, float, float] = (
            -500,
            500,
            -500,
            500,
            0,
            200,
        ),
        safety_margin: float = 10.0,
        max_iterations: int = 5000,
        goal_tolerance: float = 5.0,
    ):
        self.bounds = bounds
        self.safety_margin = safety_margin
        self.max_iterations = max_iterations
        self.goal_tolerance = goal_tolerance
        self.obstacles: List[Tuple[float, float, float, float]] = []
        self.no_fly_zones: List[Tuple[float, float, float, float]] = []
        self.wind_field: Optional[callable] = None

    def add_obstacle(self, x: float, y: float, z: float, radius: float):
        self.obstacles.append((x, y, z, radius))

    def add_no_fly_zone(self, x_min: float, x_max: float, y_min: float, y_max: float):
        self.no_fly_zones.append((x_min, x_max, y_min, y_max))

    def set_wind_field(self, wind_func: callable):
        self.wind_field = wind_func

    def is_valid_position(self, x: float, y: float, z: float) -> bool:
        x_min, x_max, y_min, y_max, z_min, z_max = self.bounds
        if not (x_min <= x <= x_max and y_min <= y <= y_max and z_min <= z <= z_max):
            return False
        for ox, oy, oz, r in self.obstacles:
            dist = np.sqrt((x - ox) ** 2 + (y - oy) ** 2 + (z - oz) ** 2)
            if dist < r + self.safety_margin:
                return False
        for nfz in self.no_fly_zones:
            x_min_nfz, x_max_nfz, y_min_nfz, y_max_nfz = nfz
            if x_min_nfz <= x <= x_max_nfz and y_min_nfz <= y <= y_max_nfz:
                if z < 120:
                    return False
        return True

    def distance(
        self, p1: Tuple[float, float, float], p2: Tuple[float, float, float]
    ) -> float:
        return np.sqrt(sum((a - b) ** 2 for a, b in zip(p1, p2)))

    def heuristic(
        self, current: Tuple[float, float, float], goal: Tuple[float, float, float]
    ) -> float:
        base_dist = self.distance(current, goal)
        if self.wind_field:
            wx, wy, _ = self.wind_field(current[0], current[1], current[2])
            wind_factor = 1.0 + 0.1 * np.sqrt(wx**2 + wy**2)
            return base_dist * wind_factor
        return base_dist

    def plan_astar(
        self,
        start: Tuple[float, float, float],
        goal: Tuple[float, float, float],
        resolution: float = 5.0,
    ) -> PathResult:
        start_time = time.time()

        if not self.is_valid_position(*start) or not self.is_valid_position(*goal):
            return PathResult([], 0, 0, 0, 0, "A*", 0)

        open_set: Dict[Tuple[int, int, int], float] = {}
        came_from: Dict[Tuple[int, int, int], Tuple[int, int, int]] = {}
        g_score: Dict[Tuple[int, int, int], float] = {}

        start_key = self._pos_to_key(start, resolution)
        goal_key = self._pos_to_key(goal, resolution)

        open_set[start_key] = self.heuristic(start, goal)
        g_score[start_key] = 0

        directions = [
            (resolution, 0, 0),
            (-resolution, 0, 0),
            (0, resolution, 0),
            (0, -resolution, 0),
            (0, 0, resolution),
            (0, 0, -resolution),
            (resolution, resolution, 0),
            (-resolution, resolution, 0),
            (resolution, -resolution, 0),
            (-resolution, -resolution, 0),
        ]

        iterations = 0
        while open_set and iterations < self.max_iterations:
            iterations += 1
            current = min(open_set, key=open_set.get)
            current_pos = self._key_to_pos(current, resolution)

            if self.distance(current_pos, goal) < self.goal_tolerance:
                return self._reconstruct_path(
                    start, current_pos, came_from, g_score, "A*", start_time
                )

            del open_set[current]

            for dx, dy, dz in directions:
                neighbor_pos = (
                    current_pos[0] + dx,
                    current_pos[1] + dy,
                    current_pos[2] + dz,
                )

                if not self.is_valid_position(*neighbor_pos):
                    continue

                neighbor_key = self._pos_to_key(neighbor_pos, resolution)
                tentative_g = g_score[current] + self.distance(
                    current_pos, neighbor_pos
                )

                if neighbor_key not in g_score or tentative_g < g_score[neighbor_key]:
                    came_from[neighbor_key] = current
                    g_score[neighbor_key] = tentative_g
                    f_score = tentative_g + self.heuristic(neighbor_pos, goal)
                    open_set[neighbor_key] = f_score

        return PathResult([], 0, 0, 0, 0, "A*", time.time() - start_time)

    def _pos_to_key(
        self, pos: Tuple[float, float, float], resolution: float
    ) -> Tuple[int, int, int]:
        return (
            int(round(pos[0] / resolution)),
            int(round(pos[1] / resolution)),
            int(round(pos[2] / resolution)),
        )

    def _key_to_pos(
        self, key: Tuple[int, int, int], resolution: float
    ) -> Tuple[float, float, float]:
        return (
            key[0] * resolution,
            key[1] * resolution,
            key[2] * resolution,
        )

    def _reconstruct_path(
        self,
        start: Tuple[float, float, float],
        current: Tuple[float, float, float],
        came_from: Dict,
        g_score: Dict,
        algorithm: str,
        start_time: float,
    ) -> PathResult:
        path = [current]
        key = self._pos_to_key(current, 5.0)

        while key in came_from:
            key = came_from[key]
            pos = self._key_to_pos(key, 5.0)
            path.append(pos)

        path.reverse()

        waypoints = [Waypoint(x=p[0], y=p[1], z=p[2]) for p in path]

        total_distance = sum(
            self.distance(path[i], path[i + 1]) for i in range(len(path) - 1)
        )
        total_time = total_distance / 10.0
        total_energy = total_distance * 0.1
        safety_score = self._calculate_safety_score(path)

        return PathResult(
            waypoints=waypoints,
            total_distance=total_distance,
            total_time=total_time,
            total_energy=total_energy,
            safety_score=safety_score,
            algorithm=algorithm,
            computation_time=time.time() - start_time,
        )

    def _calculate_safety_score(self, path: List[Tuple[float, float, float]]) -> float:
        if not path:
            return 0.0

        min_distances = []
        for point in path:
            min_dist = (
                min(
                    self.distance(point, (ox, oy, oz))
                    for ox, oy, oz, r in self.obstacles
                )
                if self.obstacles
                else 100.0
            )
            min_distances.append(min_dist)

        avg_min_dist = np.mean(min_distances)
        return min(avg_min_dist / 50.0, 1.0)

    def plan_rrt_star(
        self,
        start: Tuple[float, float, float],
        goal: Tuple[float, float, float],
        step_size: float = 10.0,
        goal_sample_rate: float = 0.1,
    ) -> PathResult:
        start_time = time.time()

        if not self.is_valid_position(*start) or not self.is_valid_position(*goal):
            return PathResult([], 0, 0, 0, 0, "RRT*", 0)

        tree: Dict[Tuple[float, float, float], Tuple[float, float, float]] = {
            start: None
        }
        costs: Dict[Tuple[float, float, float], float] = {start: 0}

        iterations = 0
        while iterations < self.max_iterations:
            iterations += 1

            if np.random.random() < goal_sample_rate:
                sample = goal
            else:
                sample = self._random_sample()

            if not self.is_valid_position(*sample):
                continue

            nearest = min(tree.keys(), key=lambda n: self.distance(n, sample))

            direction = np.array(sample) - np.array(nearest)
            dist = np.linalg.norm(direction)

            if dist < 1e-6:
                continue

            direction = direction / dist
            new_node = tuple(np.array(nearest) + direction * min(step_size, dist))

            if not self.is_valid_position(*new_node):
                continue

            if not self._check_collision_free(nearest, new_node):
                continue

            near_nodes = [
                n for n in tree.keys() if self.distance(n, new_node) < step_size * 3
            ]

            min_cost = costs[nearest] + self.distance(nearest, new_node)
            best_parent = nearest

            for near in near_nodes:
                cost = costs[near] + self.distance(near, new_node)
                if cost < min_cost and self._check_collision_free(near, new_node):
                    min_cost = cost
                    best_parent = near

            tree[new_node] = best_parent
            costs[new_node] = min_cost

            for near in near_nodes:
                new_cost = costs[new_node] + self.distance(new_node, near)
                if new_cost < costs[near] and self._check_collision_free(
                    new_node, near
                ):
                    tree[near] = new_node
                    costs[near] = new_cost

            if self.distance(new_node, goal) < self.goal_tolerance:
                return self._reconstruct_rrt_path(
                    tree, start, new_node, "RRT*", start_time
                )

        return PathResult([], 0, 0, 0, 0, "RRT*", time.time() - start_time)

    def _random_sample(self) -> Tuple[float, float, float]:
        x_min, x_max, y_min, y_max, z_min, z_max = self.bounds
        return (
            np.random.uniform(x_min, x_max),
            np.random.uniform(y_min, y_max),
            np.random.uniform(z_min, z_max),
        )

    def _check_collision_free(
        self,
        p1: Tuple[float, float, float],
        p2: Tuple[float, float, float],
    ) -> bool:
        steps = max(int(self.distance(p1, p2) / 2.0), 2)
        for t in np.linspace(0, 1, steps):
            point = (
                p1[0] + (p2[0] - p1[0]) * t,
                p1[1] + (p2[1] - p1[1]) * t,
                p1[2] + (p2[2] - p1[2]) * t,
            )
            if not self.is_valid_position(*point):
                return False
        return True

    def _reconstruct_rrt_path(
        self,
        tree: Dict,
        start: Tuple[float, float, float],
        goal: Tuple[float, float, float],
        algorithm: str,
        start_time: float,
    ) -> PathResult:
        path = [goal]
        current = goal

        while tree[current] is not None:
            current = tree[current]
            path.append(current)

        path.reverse()

        waypoints = [Waypoint(x=p[0], y=p[1], z=p[2]) for p in path]

        total_distance = sum(
            self.distance(path[i], path[i + 1]) for i in range(len(path) - 1)
        )
        total_time = total_distance / 10.0
        total_energy = total_distance * 0.1
        safety_score = self._calculate_safety_score(path)

        return PathResult(
            waypoints=waypoints,
            total_distance=total_distance,
            total_time=total_time,
            total_energy=total_energy,
            safety_score=safety_score,
            algorithm=algorithm,
            computation_time=time.time() - start_time,
        )

    def plan_hybrid(
        self,
        start: Tuple[float, float, float],
        goal: Tuple[float, float, float],
    ) -> PathResult:
        astar_result = self.plan_astar(start, goal)
        rrt_result = self.plan_rrt_star(start, goal)

        if not astar_result.waypoints and not rrt_result.waypoints:
            return PathResult([], 0, 0, 0, 0, "Hybrid", 0)

        if not astar_result.waypoints:
            return rrt_result
        if not rrt_result.waypoints:
            return astar_result

        if astar_result.computation_time < rrt_result.computation_time:
            return astar_result
        return rrt_result

    def smooth_path(
        self, waypoints: List[Waypoint], iterations: int = 50
    ) -> List[Waypoint]:
        if len(waypoints) < 3:
            return waypoints

        points = np.array([[w.x, w.y, w.z] for w in waypoints])

        for _ in range(iterations):
            for i in range(1, len(points) - 1):
                if i > 0 and i < len(points) - 1:
                    smoothed = (points[i - 1] + points[i + 1]) / 2
                    if self.is_valid_position(*smoothed):
                        points[i] = smoothed

        return [Waypoint(x=p[0], y=p[1], z=p[2]) for p in points]
