# Phase 647: Mission Scheduler — Priority-Based Task Assignment
"""
우선순위 기반 미션 스케줄링: 배송, 순찰, 정찰, 긴급 미션을
드론 상태(배터리, 위치, 부하)에 따라 최적 할당.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import IntEnum
import heapq


class MissionType(IntEnum):
    EMERGENCY = 1
    SURVEILLANCE = 2
    DELIVERY = 3
    PATROL = 4
    INSPECTION = 5


@dataclass
class Mission:
    mission_id: str
    mission_type: MissionType
    origin: np.ndarray
    destination: np.ndarray
    priority: int  # 1=highest
    deadline_s: float
    payload_kg: float = 0.0
    assigned_drone: str | None = None
    status: str = "pending"  # pending, assigned, in_progress, completed, failed

    def __lt__(self, other):
        return self.priority < other.priority


@dataclass
class DroneCapability:
    drone_id: str
    position: np.ndarray
    battery_pct: float
    max_payload_kg: float
    speed_ms: float
    current_missions: int = 0


class MissionScheduler:
    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self._queue: list[Mission] = []
        self._drones: dict[str, DroneCapability] = {}
        self._assigned: dict[str, Mission] = {}
        self._completed: list[Mission] = []
        self._failed: list[Mission] = []

    def register_drone(self, cap: DroneCapability) -> None:
        self._drones[cap.drone_id] = cap

    def submit_mission(self, mission: Mission) -> None:
        heapq.heappush(self._queue, mission)

    def _fitness(self, drone: DroneCapability, mission: Mission) -> float:
        dist = float(np.linalg.norm(drone.position - mission.origin))
        travel_time = dist / max(drone.speed_ms, 1.0)
        battery_ok = 1.0 if drone.battery_pct > 20.0 else 0.0
        payload_ok = 1.0 if drone.max_payload_kg >= mission.payload_kg else 0.0
        load_penalty = drone.current_missions * 0.2

        score = battery_ok * payload_ok * (1.0 / (1.0 + travel_time / 100.0)) - load_penalty
        return score

    def schedule(self) -> list[tuple[str, str]]:
        assignments = []
        next_queue = []

        while self._queue:
            mission = heapq.heappop(self._queue)
            best_drone = None
            best_score = -float("inf")

            for did, drone in self._drones.items():
                if drone.battery_pct < 10.0:
                    continue
                score = self._fitness(drone, mission)
                if score > best_score:
                    best_score = score
                    best_drone = did

            if best_drone is not None and best_score > 0:
                mission.assigned_drone = best_drone
                mission.status = "assigned"
                self._assigned[mission.mission_id] = mission
                self._drones[best_drone].current_missions += 1
                assignments.append((best_drone, mission.mission_id))
            else:
                mission.status = "failed"
                self._failed.append(mission)

        return assignments

    def complete_mission(self, mission_id: str) -> None:
        if mission_id in self._assigned:
            m = self._assigned.pop(mission_id)
            m.status = "completed"
            self._completed.append(m)
            if m.assigned_drone and m.assigned_drone in self._drones:
                self._drones[m.assigned_drone].current_missions -= 1

    def summary(self) -> dict:
        return {
            "pending": len(self._queue),
            "assigned": len(self._assigned),
            "completed": len(self._completed),
            "failed": len(self._failed),
            "drones": len(self._drones),
        }

    def run(self, n_missions: int = 20) -> dict:
        # Register drones
        for i in range(10):
            self.register_drone(DroneCapability(
                drone_id=f"D-{i:04d}",
                position=self.rng.uniform(-2000, 2000, 3),
                battery_pct=self.rng.uniform(30, 100),
                max_payload_kg=self.rng.uniform(1, 10),
                speed_ms=self.rng.uniform(5, 20),
            ))

        # Submit missions
        for i in range(n_missions):
            mtype = MissionType(self.rng.integers(1, 6))
            self.submit_mission(Mission(
                mission_id=f"M-{i:04d}",
                mission_type=mtype,
                origin=self.rng.uniform(-2000, 2000, 3),
                destination=self.rng.uniform(-2000, 2000, 3),
                priority=int(mtype),
                deadline_s=self.rng.uniform(60, 600),
                payload_kg=self.rng.uniform(0, 5),
            ))

        self.schedule()

        # Complete some missions
        for mid in list(self._assigned.keys())[:len(self._assigned) // 2]:
            self.complete_mission(mid)

        return self.summary()


if __name__ == "__main__":
    scheduler = MissionScheduler(42)
    result = scheduler.run(30)
    for k, v in result.items():
        print(f"  {k}: {v}")
