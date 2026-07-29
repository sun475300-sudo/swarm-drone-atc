"""
자율 미션 플래너
===============
목표 기반 자동 미션 생성 + 자원 할당.

사용법:
    amp = AutoMissionPlanner()
    amp.add_objective("survey", area=[(0,0),(1000,1000)], priority=8)
    missions = amp.generate_missions(available_drones=["d1","d2","d3"])
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Objective:
    """``Objective`` 관련 기능을 제공한다."""
    name: str
    area: list[tuple[float, float]]
    priority: int = 5
    duration_min: float = 30
    drones_needed: int = 1


@dataclass
class GeneratedMission:
    """``GeneratedMission`` 관련 기능을 제공한다."""
    mission_id: str
    objective: str
    assigned_drones: list[str]
    waypoints: list[tuple[float, float, float]]
    estimated_duration_min: float


class AutoMissionPlanner:
    """``AutoMissionPlanner`` 역할을 담당한다."""
    def __init__(self, default_altitude: float = 50) -> None:
        """인스턴스를 초기화한다."""
        self.default_altitude = default_altitude
        self._objectives: list[Objective] = []
        self._missions: list[GeneratedMission] = []

    def add_objective(self, name: str, area: list[tuple[float, float]] | None = None, priority: int = 5, duration: float = 30, drones: int = 1) -> None:
        """`objective` 항목을 추가한다."""
        self._objectives.append(Objective(name=name, area=area or [(0,0),(500,500)], priority=priority, duration_min=duration, drones_needed=drones))

    def generate_missions(self, available_drones: list[str] | None = None) -> list[GeneratedMission]:
        """`missions` 결과를 생성한다."""
        drones = list(available_drones or [])
        sorted_obj = sorted(self._objectives, key=lambda o: -o.priority)
        missions = []
        drone_idx = 0

        for obj in sorted_obj:
            if drone_idx + obj.drones_needed > len(drones):
                break
            assigned = drones[drone_idx:drone_idx + obj.drones_needed]
            drone_idx += obj.drones_needed

            # 웨이포인트 생성 (영역 코너 순회)
            wps = [(p[0], p[1], self.default_altitude) for p in obj.area]
            wps.append(wps[0])  # 복귀

            mission = GeneratedMission(
                mission_id=f"auto_{obj.name}_{len(missions)}",
                objective=obj.name,
                assigned_drones=assigned,
                waypoints=wps,
                estimated_duration_min=obj.duration_min,
            )
            missions.append(mission)

        self._missions.extend(missions)
        return missions

    def summary(self) -> dict[str, Any]:
        """현재 상태 요약을 반환한다."""
        return {
            "objectives": len(self._objectives),
            "missions_generated": len(self._missions),
            "drones_assigned": sum(len(m.assigned_drones) for m in self._missions),
        }
