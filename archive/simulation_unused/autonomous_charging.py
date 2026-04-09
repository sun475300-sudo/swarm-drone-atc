"""
Autonomous Charging Management System
Phase 260 P0 - Self-driving drone battery management and charging scheduling
"""

import heapq
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
import numpy as np


class ChargingStationStatus(Enum):
    AVAILABLE = "available"
    CHARGING = "charging"
    MAINTENANCE = "maintenance"
    RESERVED = "reserved"


class DroneChargingPriority(Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass
class ChargingStation:
    id: str
    x: float
    y: float
    z: float
    status: ChargingStationStatus = ChargingStationStatus.AVAILABLE
    max_power_watts: float = 500.0
    current_power: float = 0.0
    efficiency: float = 0.95
    charging_slots: int = 4
    occupied_slots: int = 0

    def available_slots(self) -> int:
        return self.charging_slots - self.occupied_slots

    def can_charge(self, drone_count: int = 1) -> bool:
        return (
            self.status == ChargingStationStatus.AVAILABLE
            and self.available_slots() >= drone_count
        )


@dataclass
class DroneBatteryState:
    drone_id: str
    battery_level: float
    capacity_wh: float
    discharge_rate_w: float
    current_position: Tuple[float, float, float]
    target_position: Optional[Tuple[float, float, float]] = None
    is_charging: bool = False
    charging_station_id: Optional[str] = None
    estimated_empty_time: Optional[float] = None
    priority: DroneChargingPriority = DroneChargingPriority.NORMAL

    def remaining_charge_percent(self) -> float:
        return (self.battery_level / self.capacity_wh) * 100

    def time_to_empty(self) -> float:
        if self.discharge_rate_w <= 0:
            return float("inf")
        return self.battery_level / self.discharge_rate_w

    def estimated_range_km(self) -> float:
        cruise_speed = 15.0
        hours = self.time_to_empty()
        return hours * cruise_speed


class ChargingSchedule:
    def __init__(self, max_drones: int = 100):
        self.schedule: List[Tuple[float, str, str]] = []
        self.max_drones = max_drones

    def add_charging_task(
        self, drone_id: str, station_id: str, start_time: float, duration: float
    ):
        end_time = start_time + duration
        heapq.heappush(self.schedule, (start_time, drone_id, station_id))
        heapq.heappush(self.schedule, (end_time, drone_id, "COMPLETE"))

    def get_next_available_time(self, station_id: str, current_time: float) -> float:
        for time_point, drone_id, s_id in self.schedule:
            if (
                time_point >= current_time
                and s_id == station_id
                and drone_id != "COMPLETE"
            ):
                if time_point > current_time:
                    return time_point
        return current_time


class AutonomousChargingManager:
    def __init__(self, num_stations: int = 10):
        self.stations: Dict[str, ChargingStation] = {}
        self.drones: Dict[str, DroneBatteryState] = {}
        self.schedule = ChargingSchedule()
        self.charging_history: List[Dict] = []
        self._init_stations(num_stations)

    def _init_stations(self, num_stations: int):
        for i in range(num_stations):
            x = (i % 5) * 100.0
            y = (i // 5) * 100.0
            station = ChargingStation(
                id=f"CS-{i + 1:03d}",
                x=x,
                y=y,
                z=0.0,
                max_power_watts=np.random.uniform(400, 600),
                charging_slots=np.random.randint(2, 6),
            )
            self.stations[station.id] = station

    def register_drone(
        self,
        drone_id: str,
        battery_level: float,
        capacity_wh: float,
        discharge_rate_w: float,
        position: Tuple[float, float, float],
    ):
        drone = DroneBatteryState(
            drone_id=drone_id,
            battery_level=battery_level,
            capacity_wh=capacity_wh,
            discharge_rate_w=discharge_rate_w,
            current_position=position,
        )
        drone.estimated_empty_time = time.time() + drone.time_to_empty()
        self.drones[drone_id] = drone

    def find_nearest_station(
        self, drone_id: str, require_available: bool = True
    ) -> Optional[ChargingStation]:
        if drone_id not in self.drones:
            return None

        drone = self.drones[drone_id]
        best_station = None
        best_distance = float("inf")

        for station in self.stations.values():
            if require_available and not station.can_charge():
                continue

            dist = self._calculate_distance(
                drone.current_position, (station.x, station.y, station.z)
            )
            if dist < best_distance:
                best_distance = dist
                best_station = station

        return best_station

    def _calculate_distance(
        self, pos1: Tuple[float, float, float], pos2: Tuple[float, float, float]
    ) -> float:
        return np.sqrt(sum((a - b) ** 2 for a, b in zip(pos1, pos2)))

    def calculate_charging_time(self, drone_id: str, station_id: str) -> float:
        if drone_id not in self.drones or station_id not in self.stations:
            return 0.0

        drone = self.drones[drone_id]
        station = self.stations[station_id]

        energy_needed = drone.capacity_wh - drone.battery_level
        effective_power = station.max_power_watts * station.efficiency

        if effective_power <= 0:
            return float("inf")

        return energy_needed / effective_power * 3600

    def assign_charging_station(self, drone_id: str) -> Optional[str]:
        if drone_id not in self.drones:
            return None

        drone = self.drones[drone_id]

        if drone.is_charging:
            return drone.charging_station_id

        critical_threshold = 0.15
        high_threshold = 0.25

        remaining_percent = drone.battery_level / drone.capacity_wh

        if remaining_percent > high_threshold:
            return None

        if remaining_percent <= critical_threshold:
            drone.priority = DroneChargingPriority.CRITICAL
        elif remaining_percent <= high_threshold:
            drone.priority = DroneChargingPriority.HIGH

        station = self.find_nearest_station(drone_id)
        if not station:
            return None

        station.occupied_slots += 1
        if station.occupied_slots >= station.charging_slots:
            station.status = ChargingStationStatus.CHARGING

        drone.is_charging = True
        drone.charging_station_id = station.id

        charging_time = self.calculate_charging_time(drone_id, station.id)
        self.schedule.add_charging_task(
            drone_id, station.id, time.time(), charging_time
        )

        self.charging_history.append(
            {
                "drone_id": drone_id,
                "station_id": station.id,
                "start_time": time.time(),
                "battery_before": drone.battery_level,
                "priority": drone.priority.name,
            }
        )

        return station.id

    def update_charging(self, delta_time: float = 1.0):
        current_time = time.time()

        for drone in self.drones.values():
            if drone.is_charging and drone.charging_station_id:
                station = self.stations[drone.charging_station_id]
                energy_delta = (
                    station.max_power_watts * station.efficiency * delta_time / 3600
                )

                drone.battery_level = min(
                    drone.capacity_wh, drone.battery_level + energy_delta
                )

                if drone.battery_level >= drone.capacity_wh * 0.95:
                    self.complete_charging(drone.drone_id)

    def complete_charging(self, drone_id: str) -> bool:
        if drone_id not in self.drones:
            return False

        drone = self.drones[drone_id]

        if not drone.is_charging or not drone.charging_station_id:
            return False

        station = self.stations[drone.charging_station_id]
        station.occupied_slots = max(0, station.occupied_slots - 1)

        if station.occupied_slots < station.charging_slots:
            station.status = ChargingStationStatus.AVAILABLE

        drone.is_charging = False
        drone.charging_station_id = None
        drone.battery_level = drone.capacity_wh

        return True

    def get_charging_status(self) -> Dict:
        total_drones = len(self.drones)
        charging_drones = sum(1 for d in self.drones.values() if d.is_charging)
        critical_drones = sum(
            1
            for d in self.drones.values()
            if d.priority == DroneChargingPriority.CRITICAL and not d.is_charging
        )

        return {
            "total_drones": total_drones,
            "charging_drones": charging_drones,
            "available_drones": total_drones - charging_drones,
            "critical_drones": critical_drones,
            "total_stations": len(self.stations),
            "utilization": charging_drones / max(1, total_drones) * 100,
        }

    def optimize_charging_schedule(self) -> List[Tuple[str, str, float]]:
        optimization_order = sorted(
            [
                (d.drone_id, d.priority.value, d.estimated_empty_time)
                for d in self.drones.values()
                if not d.is_charging
            ],
            key=lambda x: (x[1], x[2] if x[2] else float("inf")),
        )

        results = []
        for drone_id, _, _ in optimization_order:
            station_id = self.assign_charging_station(drone_id)
            if station_id:
                results.append((drone_id, station_id, time.time()))

        return results


def create_autonomous_charging_system(
    num_stations: int = 10, num_drones: int = 50
) -> AutonomousChargingManager:
    manager = AutonomousChargingManager(num_stations)

    for i in range(num_drones):
        drone_id = f"DRONE-{i + 1:04d}"
        capacity = np.random.uniform(200, 500)
        battery_level = capacity * np.random.uniform(0.1, 0.9)
        discharge_rate = np.random.uniform(50, 150)
        position = (
            np.random.uniform(0, 500),
            np.random.uniform(0, 500),
            np.random.uniform(20, 100),
        )

        manager.register_drone(
            drone_id, battery_level, capacity, discharge_rate, position
        )

    return manager
