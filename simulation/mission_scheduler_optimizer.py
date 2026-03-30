"""
Phase 444: Mission Scheduler Optimizer
"""

import numpy as np
from typing import Dict, List
from dataclasses import dataclass
import time


@dataclass
class Mission:
    mission_id: str
    start_time: float
    duration: float
    drones_required: List[str]
    priority: int


class MissionSchedulerOptimizer:
    def __init__(self):
        self.missions: List[Mission] = []
        self.schedule: Dict[str, float] = {}

    def add_mission(self, mission: Mission):
        self.missions.append(mission)
        self.missions.sort(key=lambda m: -m.priority)

    def optimize_schedule(self) -> Dict[str, float]:
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
        for key in list(self.schedule.keys()):
            if key.startswith(mission_id):
                self.schedule[key] += delay
