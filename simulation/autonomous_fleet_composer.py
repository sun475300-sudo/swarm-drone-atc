"""
Phase 411: Autonomous Fleet Composer for Dynamic Mission Assignment
"""

import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import time
from collections import defaultdict


class DroneCapability(Enum):
    SURVEILLANCE = "surveillance"
    DELIVERY = "delivery"
    TRANSPORT = "transport"
    RESCUE = "rescue"
    MONITORING = "monitoring"
    COMMUNICATION = "communication"


class DroneStatus(Enum):
    AVAILABLE = "available"
    IN_MISSION = "in_mission"
    CHARGING = "charging"
    MAINTENANCE = "maintenance"
    EMERGENCY = "emergency"


@dataclass
class Drone:
    drone_id: str
    capabilities: List[DroneCapability]
    max_payload_kg: float
    max_range_km: float
    battery_capacity_wh: float
    current_battery: float
    status: DroneStatus
    position: np.ndarray


@dataclass
class Mission:
    mission_id: str
    required_capabilities: List[DroneCapability]
    required_payload_kg: float
    priority: int
    deadline: float
    estimated_duration: float
    waypoints: List[np.ndarray] = field(default_factory=list)


@dataclass
class FleetAssignment:
    mission_id: str
    assigned_drones: List[str]
    total_payload_capacity: float
    estimated_completion: float


class AutonomousFleetComposer:
    def __init__(
        self,
        fleet_id: str,
        min_drones_per_mission: int = 1,
        max_drones_per_mission: int = 10,
        battery_threshold: float = 0.2,
        load_balance_enabled: bool = True,
    ):
        self.fleet_id = fleet_id
        self.min_drones_per_mission = min_drones_per_mission
        self.max_drones_per_mission = max_drones_per_mission
        self.battery_threshold = battery_threshold
        self.load_balance_enabled = load_balance_enabled

        self.drones: Dict[str, Drone] = {}
        self.missions: Dict[str, Mission] = {}
        self.assignments: Dict[str, FleetAssignment] = {}

        self.mission_history: List[Dict] = []

        self._initialize_fleet()

    def _initialize_fleet(self):
        capability_sets = [
            [DroneCapability.SURVEILLANCE, DroneCapability.MONITORING],
            [DroneCapability.DELIVERY],
            [DroneCapability.TRANSPORT, DroneCapability.MONITORING],
            [DroneCapability.RESCUE],
            [DroneCapability.COMMUNICATION],
        ]

        for i in range(20):
            drone_id = f"drone_{i:03d}"
            capabilities = capability_sets[i % len(capability_sets)]

            self.register_drone(
                drone_id=drone_id,
                capabilities=capabilities,
                max_payload_kg=np.random.uniform(5, 25),
                max_range_km=np.random.uniform(10, 50),
                battery_capacity_wh=np.random.uniform(500, 2000),
                position=np.random.uniform(-500, 500, 3),
            )

    def register_drone(
        self,
        drone_id: str,
        capabilities: List[DroneCapability],
        max_payload_kg: float,
        max_range_km: float,
        battery_capacity_wh: float,
        position: np.ndarray,
    ):
        drone = Drone(
            drone_id=drone_id,
            capabilities=capabilities,
            max_payload_kg=max_payload_kg,
            max_range_km=max_range_km,
            battery_capacity_wh=battery_capacity_wh,
            current_battery=battery_capacity_wh,
            status=DroneStatus.AVAILABLE,
            position=position,
        )
        self.drones[drone_id] = drone

    def submit_mission(self, mission: Mission) -> bool:
        self.missions[mission.mission_id] = mission
        return True

    def compose_fleet(self, mission_id: str) -> Optional[FleetAssignment]:
        if mission_id not in self.missions:
            return None

        mission = self.missions[mission_id]

        candidates = self._find_candidates(mission)

        if len(candidates) < self.min_drones_per_mission:
            return None

        assignment = self._optimize_assignment(mission, candidates)

        if assignment:
            self.assignments[mission_id] = assignment

            for drone_id in assignment.assigned_drones:
                self.drones[drone_id].status = DroneStatus.IN_MISSION

            self.mission_history.append(
                {
                    "mission_id": mission_id,
                    "assigned_drones": assignment.assigned_drones,
                    "timestamp": time.time(),
                }
            )

        return assignment

    def _find_candidates(self, mission: Mission) -> List[Drone]:
        candidates = []

        for drone in self.drones.values():
            if drone.status != DroneStatus.AVAILABLE:
                continue

            if (
                drone.current_battery / drone.battery_capacity_wh
                < self.battery_threshold
            ):
                continue

            has_required_capability = any(
                cap in drone.capabilities for cap in mission.required_capabilities
            )

            if not has_required_capability:
                continue

            if (
                drone.max_payload_kg
                < mission.required_payload_kg / self.max_drones_per_mission
            ):
                continue

            candidates.append(drone)

        return candidates

    def _optimize_assignment(
        self, mission: Mission, candidates: List[Drone]
    ) -> Optional[FleetAssignment]:
        if not candidates:
            return None

        num_drones = min(
            max(self.min_drones_per_mission, len(candidates)),
            self.max_drones_per_mission,
            len(candidates),
        )

        if self.load_balance_enabled:
            sorted_candidates = sorted(
                candidates,
                key=lambda d: d.current_battery / d.battery_capacity_wh,
                reverse=True,
            )
        else:
            sorted_candidates = candidates

        selected_drones = sorted_candidates[:num_drones]

        total_payload = sum(d.max_payload_kg for d in selected_drones)

        if total_payload < mission.required_payload_kg:
            return None

        return FleetAssignment(
            mission_id=mission.mission_id,
            assigned_drones=[d.drone_id for d in selected_drones],
            total_payload_capacity=total_payload,
            estimated_completion=time.time() + mission.estimated_duration,
        )

    def complete_mission(self, mission_id: str):
        if mission_id not in self.assignments:
            return

        assignment = self.assignments[mission_id]

        for drone_id in assignment.assigned_drones:
            if drone_id in self.drones:
                self.drones[drone_id].status = DroneStatus.AVAILABLE

        if mission_id in self.missions:
            del self.missions[mission_id]

        del self.assignments[mission_id]

    def rebalance_fleet(self) -> Dict[str, Any]:
        rebalancing_actions = []

        available_drones = [
            d for d in self.drones.values() if d.status == DroneStatus.AVAILABLE
        ]

        in_mission_count = sum(
            1 for d in self.drones.values() if d.status == DroneStatus.IN_MISSION
        )

        if in_mission_count < len(self.drones) * 0.3:
            for drone in available_drones[:5]:
                drone.status = DroneStatus.CHARGING
                rebalancing_actions.append(
                    {
                        "drone_id": drone.drone_id,
                        "action": "charging",
                    }
                )

        return {
            "actions": rebalancing_actions,
            "available": len(available_drones),
            "in_mission": in_mission_count,
        }

    def get_fleet_status(self) -> Dict[str, Any]:
        status_counts = defaultdict(int)
        for drone in self.drones.values():
            status_counts[drone.status.value] += 1

        return {
            "fleet_id": self.fleet_id,
            "total_drones": len(self.drones),
            "status_breakdown": dict(status_counts),
            "active_missions": len(self.missions),
            "active_assignments": len(self.assignments),
        }

    def predict_fleet_availability(
        self, time_horizon_hours: float = 24
    ) -> Dict[str, float]:
        available_predictions = {}

        for status in DroneStatus:
            count = sum(1 for d in self.drones.values() if d.status == status)
            available_predictions[status.value] = count

        return available_predictions
