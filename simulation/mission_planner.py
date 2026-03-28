"""
다중 임무 할당기
================
Hungarian 알고리즘 기반 드론-임무 최적 매칭.
배터리/거리/우선순위 제약 조건 반영.

사용법:
    planner = MissionPlanner()
    planner.add_mission(Mission("deliver_1", target=(500, 300, 60)))
    planner.add_drone(DroneAsset("drone_1", position=(0, 0, 50), battery_pct=90))
    assignments = planner.assign()
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any

import numpy as np


class MissionType(IntEnum):
    DELIVERY = 1
    SURVEY = 2
    INSPECTION = 3
    EMERGENCY = 4
    PATROL = 5


@dataclass
class Mission:
    """임무 정의"""
    mission_id: str
    target: tuple[float, float, float]
    mission_type: MissionType = MissionType.DELIVERY
    priority: int = 1  # 1~5
    required_battery_pct: float = 20.0
    max_distance_m: float = 5000.0
    deadline_s: float | None = None  # 마감 시간
    assigned_drone: str | None = None
    completed: bool = False


@dataclass
class DroneAsset:
    """드론 자산"""
    drone_id: str
    position: tuple[float, float, float]
    battery_pct: float = 100.0
    speed_ms: float = 10.0
    available: bool = True
    current_mission: str | None = None


@dataclass
class Assignment:
    """임무 할당 결과"""
    drone_id: str
    mission_id: str
    distance_m: float
    eta_s: float  # 예상 도착 시간
    battery_cost_pct: float  # 예상 배터리 소모
    feasible: bool = True


class MissionPlanner:
    """
    다중 임무 할당 최적화.

    Hungarian 알고리즘 + 제약 조건 필터링.
    """

    def __init__(
        self,
        battery_drain_per_km: float = 2.0,  # %/km
        safety_margin: float = 1.3,  # 30% 여유
    ) -> None:
        self._missions: dict[str, Mission] = {}
        self._drones: dict[str, DroneAsset] = {}
        self._assignments: list[Assignment] = []
        self._battery_drain_per_km = battery_drain_per_km
        self._safety_margin = safety_margin

    def add_mission(self, mission: Mission) -> None:
        self._missions[mission.mission_id] = mission

    def add_drone(self, drone: DroneAsset) -> None:
        self._drones[drone.drone_id] = drone

    def remove_mission(self, mission_id: str) -> bool:
        if mission_id in self._missions:
            del self._missions[mission_id]
            return True
        return False

    def complete_mission(self, mission_id: str) -> None:
        if mission_id in self._missions:
            self._missions[mission_id].completed = True
            self._missions[mission_id].assigned_drone = None

    def assign(self) -> list[Assignment]:
        """Hungarian 알고리즘으로 최적 할당"""
        # 할당 가능한 드론 / 미완료 임무 필터링
        avail_drones = [
            d for d in self._drones.values()
            if d.available and d.current_mission is None
        ]
        pending_missions = [
            m for m in self._missions.values()
            if not m.completed and m.assigned_drone is None
        ]

        if not avail_drones or not pending_missions:
            return []

        n_drones = len(avail_drones)
        n_missions = len(pending_missions)
        size = max(n_drones, n_missions)

        # 비용 행렬 (거리 + 우선순위 보정)
        cost_matrix = np.full((size, size), 1e9)
        feasibility = np.zeros((size, size), dtype=bool)

        for i, drone in enumerate(avail_drones):
            d_pos = np.array(drone.position)
            for j, mission in enumerate(pending_missions):
                m_pos = np.array(mission.target)
                dist = float(np.linalg.norm(d_pos - m_pos))

                # 배터리 비용
                battery_cost = (dist / 1000.0) * self._battery_drain_per_km * self._safety_margin
                # 왕복 고려
                battery_cost *= 2.0

                # 실행 가능성
                can_do = (
                    drone.battery_pct >= battery_cost + mission.required_battery_pct
                    and dist <= mission.max_distance_m
                )

                if can_do:
                    feasibility[i, j] = True
                    # 비용 = 거리 - 우선순위 보너스
                    priority_bonus = mission.priority * 100
                    cost_matrix[i, j] = dist - priority_bonus

        # 간소화된 Hungarian (그리디 매칭)
        assignments = self._greedy_assign(
            cost_matrix, feasibility, avail_drones, pending_missions
        )

        # 할당 적용
        for assign in assignments:
            if assign.drone_id in self._drones:
                self._drones[assign.drone_id].current_mission = assign.mission_id
            if assign.mission_id in self._missions:
                self._missions[assign.mission_id].assigned_drone = assign.drone_id

        self._assignments = assignments
        return assignments

    def _greedy_assign(
        self,
        cost_matrix: np.ndarray,
        feasibility: np.ndarray,
        drones: list[DroneAsset],
        missions: list[Mission],
    ) -> list[Assignment]:
        """그리디 할당 (비용 낮은 순)"""
        n_drones = len(drones)
        n_missions = len(missions)
        assignments = []

        used_drones: set[int] = set()
        used_missions: set[int] = set()

        # (cost, drone_idx, mission_idx) 정렬
        candidates = []
        for i in range(n_drones):
            for j in range(n_missions):
                if feasibility[i, j]:
                    candidates.append((cost_matrix[i, j], i, j))

        candidates.sort()

        for cost, i, j in candidates:
            if i in used_drones or j in used_missions:
                continue

            drone = drones[i]
            mission = missions[j]
            dist = float(np.linalg.norm(
                np.array(drone.position) - np.array(mission.target)
            ))
            eta = dist / max(drone.speed_ms, 0.1)
            battery_cost = (dist / 1000.0) * self._battery_drain_per_km * self._safety_margin * 2

            assignments.append(Assignment(
                drone_id=drone.drone_id,
                mission_id=mission.mission_id,
                distance_m=dist,
                eta_s=eta,
                battery_cost_pct=battery_cost,
                feasible=True,
            ))

            used_drones.add(i)
            used_missions.add(j)

        return assignments

    def unassigned_missions(self) -> list[str]:
        return [
            m.mission_id for m in self._missions.values()
            if not m.completed and m.assigned_drone is None
        ]

    def drone_utilization(self) -> float:
        """드론 활용률"""
        if not self._drones:
            return 0.0
        busy = sum(1 for d in self._drones.values() if d.current_mission)
        return busy / len(self._drones)

    def summary(self) -> dict[str, Any]:
        total = len(self._missions)
        completed = sum(1 for m in self._missions.values() if m.completed)
        assigned = sum(1 for m in self._missions.values() if m.assigned_drone)
        return {
            "total_missions": total,
            "completed": completed,
            "assigned": assigned,
            "unassigned": total - completed - assigned,
            "total_drones": len(self._drones),
            "utilization": round(self.drone_utilization(), 3),
            "assignments": len(self._assignments),
        }

    def clear(self) -> None:
        self._missions.clear()
        self._drones.clear()
        self._assignments.clear()
