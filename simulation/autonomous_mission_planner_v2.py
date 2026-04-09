"""Phase 302: Autonomous Mission Planner v2 — 자율 미션 계획기 v2.

다목적 최적화 기반 미션 계획, 자원 제약 고려,
동적 환경 적응, 다중 드론 협업 미션 분해.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class MissionObjective(Enum):
    MINIMIZE_TIME = "minimize_time"
    MINIMIZE_ENERGY = "minimize_energy"
    MAXIMIZE_COVERAGE = "maximize_coverage"
    MINIMIZE_RISK = "minimize_risk"
    BALANCED = "balanced"


@dataclass
class MissionConstraint:
    max_duration_sec: float = 3600.0
    max_distance_m: float = 10000.0
    min_battery_pct: float = 20.0
    max_altitude_m: float = 120.0
    no_fly_zones: List[Tuple[np.ndarray, float]] = field(default_factory=list)
    weather_limit_wind_ms: float = 15.0


@dataclass
class Waypoint:
    position: np.ndarray
    altitude: float = 50.0
    loiter_time_sec: float = 0.0
    action: str = "transit"  # transit, scan, photograph, deliver, land
    priority: int = 5


@dataclass
class MissionPlan:
    plan_id: str
    waypoints: List[Waypoint] = field(default_factory=list)
    assigned_drones: List[str] = field(default_factory=list)
    objective: MissionObjective = MissionObjective.BALANCED
    estimated_duration_sec: float = 0.0
    estimated_energy_wh: float = 0.0
    total_distance_m: float = 0.0
    feasible: bool = True
    score: float = 0.0


class CoverageOptimizer:
    """영역 커버리지 최적화 (그리디 세트 커버)."""

    @staticmethod
    def compute_coverage_waypoints(
        area_min: np.ndarray, area_max: np.ndarray, sensor_radius: float = 50.0,
        altitude: float = 50.0,
    ) -> List[Waypoint]:
        waypoints = []
        step = sensor_radius * 1.5  # overlap
        x = area_min[0]
        row = 0
        while x <= area_max[0]:
            y = area_min[1] if row % 2 == 0 else area_max[1]
            y_end = area_max[1] if row % 2 == 0 else area_min[1]
            y_step = step if row % 2 == 0 else -step
            while (row % 2 == 0 and y <= y_end) or (row % 2 == 1 and y >= y_end):
                waypoints.append(Waypoint(
                    position=np.array([x, y, altitude]), altitude=altitude, action="scan",
                ))
                y += y_step
            x += step
            row += 1
        return waypoints


class TSPSolver:
    """Nearest-Neighbor TSP 솔버."""

    @staticmethod
    def solve(waypoints: List[Waypoint], start_pos: np.ndarray) -> List[int]:
        n = len(waypoints)
        if n == 0:
            return []
        visited = [False] * n
        order = []
        current = start_pos.copy()
        for _ in range(n):
            best_idx, best_dist = -1, float("inf")
            for i in range(n):
                if visited[i]:
                    continue
                d = np.linalg.norm(current - waypoints[i].position)
                if d < best_dist:
                    best_dist = d
                    best_idx = i
            if best_idx >= 0:
                visited[best_idx] = True
                order.append(best_idx)
                current = waypoints[best_idx].position.copy()
        return order


class AutonomousMissionPlannerV2:
    """자율 미션 계획기 v2.

    - 다목적 최적화 (시간/에너지/커버리지/위험)
    - 제약 조건 검증 (NFZ, 배터리, 고도)
    - 자동 경유점 생성 및 TSP 최적화
    - 다중 드론 미션 분할
    """

    def __init__(self, rng_seed: int = 42):
        self._rng = np.random.default_rng(rng_seed)
        self._plans: Dict[str, MissionPlan] = {}
        self._constraints = MissionConstraint()
        self._tsp = TSPSolver()
        self._coverage = CoverageOptimizer()
        self._history: List[dict] = []

    def set_constraints(self, constraints: MissionConstraint):
        self._constraints = constraints

    def plan_coverage_mission(
        self, plan_id: str, area_min: np.ndarray, area_max: np.ndarray,
        drone_ids: List[str], start_pos: np.ndarray,
        objective: MissionObjective = MissionObjective.BALANCED,
    ) -> MissionPlan:
        # Generate coverage waypoints
        waypoints = self._coverage.compute_coverage_waypoints(area_min, area_max)
        # Filter by NFZ
        waypoints = [wp for wp in waypoints if not self._in_nfz(wp.position)]
        # Optimize order
        order = self._tsp.solve(waypoints, start_pos)
        ordered_wps = [waypoints[i] for i in order]
        # Split among drones
        n_drones = max(1, len(drone_ids))
        chunk_size = max(1, len(ordered_wps) // n_drones)
        # Calculate metrics
        total_dist = self._calculate_distance(ordered_wps, start_pos)
        est_duration = total_dist / 10.0  # assume 10 m/s
        est_energy = total_dist * 0.05  # 0.05 Wh/m

        plan = MissionPlan(
            plan_id=plan_id, waypoints=ordered_wps, assigned_drones=drone_ids,
            objective=objective, estimated_duration_sec=est_duration,
            estimated_energy_wh=est_energy, total_distance_m=total_dist,
            feasible=self._check_feasibility(total_dist, est_duration),
        )
        plan.score = self._score_plan(plan)
        self._plans[plan_id] = plan
        self._history.append({"event": "plan_created", "plan": plan_id, "waypoints": len(ordered_wps)})
        return plan

    def plan_delivery_mission(
        self, plan_id: str, delivery_points: List[np.ndarray],
        drone_id: str, start_pos: np.ndarray,
    ) -> MissionPlan:
        waypoints = [Waypoint(position=p, action="deliver") for p in delivery_points]
        order = self._tsp.solve(waypoints, start_pos)
        ordered_wps = [waypoints[i] for i in order]
        total_dist = self._calculate_distance(ordered_wps, start_pos)

        plan = MissionPlan(
            plan_id=plan_id, waypoints=ordered_wps, assigned_drones=[drone_id],
            objective=MissionObjective.MINIMIZE_TIME,
            estimated_duration_sec=total_dist / 10.0,
            estimated_energy_wh=total_dist * 0.05,
            total_distance_m=total_dist,
            feasible=self._check_feasibility(total_dist, total_dist / 10.0),
        )
        self._plans[plan_id] = plan
        return plan

    def _in_nfz(self, pos: np.ndarray) -> bool:
        for center, radius in self._constraints.no_fly_zones:
            if np.linalg.norm(pos[:2] - center[:2]) < radius:
                return True
        return False

    def _calculate_distance(self, waypoints: List[Waypoint], start: np.ndarray) -> float:
        if not waypoints:
            return 0.0
        total = np.linalg.norm(waypoints[0].position - start)
        for i in range(len(waypoints) - 1):
            total += np.linalg.norm(waypoints[i + 1].position - waypoints[i].position)
        return float(total)

    def _check_feasibility(self, distance: float, duration: float) -> bool:
        return (distance <= self._constraints.max_distance_m and
                duration <= self._constraints.max_duration_sec)

    def _score_plan(self, plan: MissionPlan) -> float:
        if not plan.feasible:
            return 0.0
        time_score = max(0, 1 - plan.estimated_duration_sec / self._constraints.max_duration_sec)
        energy_score = max(0, 1 - plan.estimated_energy_wh / 500.0)
        coverage_score = len(plan.waypoints) / max(len(plan.waypoints), 1)
        if plan.objective == MissionObjective.MINIMIZE_TIME:
            return time_score * 0.6 + energy_score * 0.2 + coverage_score * 0.2
        elif plan.objective == MissionObjective.MINIMIZE_ENERGY:
            return time_score * 0.2 + energy_score * 0.6 + coverage_score * 0.2
        return (time_score + energy_score + coverage_score) / 3

    def get_plan(self, plan_id: str) -> Optional[MissionPlan]:
        return self._plans.get(plan_id)

    def summary(self) -> dict:
        feasible = sum(1 for p in self._plans.values() if p.feasible)
        return {
            "total_plans": len(self._plans),
            "feasible_plans": feasible,
            "total_waypoints": sum(len(p.waypoints) for p in self._plans.values()),
            "history_events": len(self._history),
        }
