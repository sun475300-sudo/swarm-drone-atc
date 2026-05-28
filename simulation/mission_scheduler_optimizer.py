"""
Phase 444: Mission Scheduler Optimizer
"""

import time
from dataclasses import dataclass


@dataclass
class Mission:
    """``Mission`` 관련 기능을 제공한다."""
    mission_id: str
    start_time: float
    duration: float
    drones_required: list[str]
    priority: int


class MissionSchedulerOptimizer:
    """``MissionSchedulerOptimizer`` 관련 기능을 제공한다."""
    def __init__(self):
        """인스턴스를 초기화한다."""
        self.missions: list[Mission] = []
        self.schedule: dict[str, float] = {}

    def add_mission(self, mission: Mission):
        """`mission` 항목을 추가한다."""
        self.missions.append(mission)
        self.missions.sort(key=lambda m: -m.priority)

    def optimize_schedule(self) -> dict[str, float]:
        """``optimize_schedule`` 동작을 수행한다."""
        schedule = {}

        current_time = time.time()

        for mission in self.missions:
            scheduled_time = max(current_time, mission.start_time)

            for drone in mission.drones_required:
                schedule[f"{mission.mission_id}_{drone}"] = scheduled_time

            current_time = scheduled_time + mission.duration

        self.schedule = schedule
        return schedule

    def reschedule_on_delay(self, mission_id: str, delay: float):
        """``reschedule_on_delay`` 동작을 수행한다."""
        for key in list(self.schedule.keys()):
            if key.startswith(mission_id):
                self.schedule[key] += delay
