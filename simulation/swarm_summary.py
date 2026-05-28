"""
Phase 480: Swarm Summary - Central Aggregation Module
"""

from dataclasses import dataclass


@dataclass
class SwarmStatus:
    """``SwarmStatus`` 관련 기능을 제공한다."""
    total_drones: int
    active_drones: int
    missions_completed: int
    collisions_avoided: int


class SwarmSummary:
    """``SwarmSummary`` 관련 기능을 제공한다."""
    def __init__(self):
        """인스턴스를 초기화한다."""
        self.drones: dict[str, dict] = {}
        self.missions: list[dict] = []

    def add_drone(self, drone_id: str):
        """`drone` 항목을 추가한다."""
        self.drones[drone_id] = {
            "status": "idle",
            "battery": 100.0,
            "position": [0, 0, 0],
        }

    def get_status(self) -> SwarmStatus:
        """`status` 정보를 조회한다."""
        active = sum(1 for d in self.drones.values() if d["status"] != "idle")
        return SwarmStatus(
            total_drones=len(self.drones),
            active_drones=active,
            missions_completed=len(self.missions),
            collisions_avoided=0,
        )
