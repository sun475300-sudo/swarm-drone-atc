"""Phase 287: Energy Harvest Optimizer — 에너지 수확 최적화.

태양광/풍력/RF 에너지 수확 모델링, 충전 스케줄 최적화,
에너지 수확 경로 계획 및 군집 에너지 공유 프로토콜.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class EnergySource(Enum):
    SOLAR = "solar"
    WIND = "wind"
    RF = "rf"
    CHARGING_STATION = "charging_station"
    WIRELESS_POWER = "wireless_power"


@dataclass
class HarvestZone:
    zone_id: str
    center: np.ndarray
    radius: float
    source: EnergySource
    power_density_w: float  # W/m²
    availability: float = 1.0  # 0-1 time availability
    altitude_optimal: float = 50.0


@dataclass
class DroneEnergy:
    drone_id: str
    battery_wh: float = 100.0
    max_battery_wh: float = 100.0
    consumption_rate_w: float = 50.0  # cruise power
    harvest_rate_w: float = 0.0
    solar_panel_area_m2: float = 0.1
    efficiency: float = 0.2


class SolarModel:
    """태양광 에너지 수확 모델."""

    @staticmethod
    def irradiance(hour: float, cloud_cover: float = 0.0, latitude: float = 34.8) -> float:
        """시간대별 태양 복사량 W/m²."""
        if hour < 6 or hour > 18:
            return 0.0
        solar_angle = np.sin(np.pi * (hour - 6) / 12)
        base_irradiance = 1000.0 * solar_angle
        cloud_factor = 1.0 - cloud_cover * 0.8
        return max(0.0, base_irradiance * cloud_factor)

    @staticmethod
    def harvest_power(area_m2: float, efficiency: float, irradiance: float) -> float:
        return area_m2 * efficiency * irradiance


class WindHarvestModel:
    """풍력 에너지 수확 모델 (소형 터빈)."""

    @staticmethod
    def power(wind_speed: float, rotor_area: float = 0.01, efficiency: float = 0.3) -> float:
        air_density = 1.225
        return 0.5 * air_density * rotor_area * efficiency * wind_speed ** 3


class EnergyHarvestOptimizer:
    """에너지 수확 최적화기.

    - 수확 존 관리 및 탐색
    - 태양광/풍력/RF 수확 시뮬레이션
    - 충전 스케줄 최적화
    - 에너지 공유 프로토콜
    """

    def __init__(self, rng_seed: int = 42):
        self._rng = np.random.default_rng(rng_seed)
        self._zones: Dict[str, HarvestZone] = {}
        self._drones: Dict[str, DroneEnergy] = {}
        self._solar = SolarModel()
        self._wind = WindHarvestModel()
        self._history: List[dict] = []
        self._total_harvested_wh: float = 0.0

    def add_zone(self, zone: HarvestZone):
        self._zones[zone.zone_id] = zone

    def register_drone(self, drone: DroneEnergy):
        self._drones[drone.drone_id] = drone

    def compute_harvest_rate(self, drone_id: str, position: np.ndarray, hour: float = 12.0, wind_speed: float = 5.0) -> float:
        drone = self._drones.get(drone_id)
        if not drone:
            return 0.0
        total_power = 0.0
        # Solar harvest
        irr = self._solar.irradiance(hour)
        total_power += self._solar.harvest_power(drone.solar_panel_area_m2, drone.efficiency, irr)
        # Zone-based harvest
        for zone in self._zones.values():
            dist = np.linalg.norm(position[:3] - zone.center[:3])
            if dist <= zone.radius:
                if zone.source == EnergySource.WIND:
                    total_power += self._wind.power(wind_speed)
                elif zone.source == EnergySource.RF:
                    total_power += zone.power_density_w * (1 - dist / zone.radius)
                elif zone.source == EnergySource.CHARGING_STATION:
                    total_power += zone.power_density_w
                elif zone.source == EnergySource.WIRELESS_POWER:
                    total_power += zone.power_density_w * max(0, 1 - (dist / zone.radius) ** 2)
        drone.harvest_rate_w = total_power
        return total_power

    def simulate_step(self, dt_sec: float = 1.0, hour: float = 12.0, positions: Optional[Dict[str, np.ndarray]] = None):
        if positions is None:
            positions = {}
        for did, drone in self._drones.items():
            pos = positions.get(did, np.zeros(3))
            harvest = self.compute_harvest_rate(did, pos, hour)
            net_power = harvest - drone.consumption_rate_w
            energy_delta = net_power * dt_sec / 3600.0  # W·s to Wh
            drone.battery_wh = np.clip(drone.battery_wh + energy_delta, 0, drone.max_battery_wh)
            if energy_delta > 0:
                self._total_harvested_wh += energy_delta

    def find_best_harvest_zone(self, position: np.ndarray) -> Optional[str]:
        best_id, best_score = None, -1
        for zone in self._zones.values():
            dist = np.linalg.norm(position[:3] - zone.center[:3])
            score = zone.power_density_w * zone.availability / max(dist, 1.0)
            if score > best_score:
                best_score = score
                best_id = zone.zone_id
        return best_id

    def plan_harvest_route(self, drone_id: str, current_pos: np.ndarray, n_zones: int = 3) -> List[str]:
        """방문할 수확 존 순서 계획 (그리디 TSP)."""
        visited = []
        pos = current_pos.copy()
        zones = list(self._zones.values())
        for _ in range(min(n_zones, len(zones))):
            best_z, best_dist = None, float("inf")
            for z in zones:
                if z.zone_id in visited:
                    continue
                d = np.linalg.norm(pos[:3] - z.center[:3])
                if d < best_dist:
                    best_dist = d
                    best_z = z
            if best_z:
                visited.append(best_z.zone_id)
                pos = best_z.center.copy()
        return visited

    def energy_share(self, donor_id: str, receiver_id: str, amount_wh: float) -> float:
        donor = self._drones.get(donor_id)
        receiver = self._drones.get(receiver_id)
        if not donor or not receiver:
            return 0.0
        actual = min(amount_wh, donor.battery_wh, receiver.max_battery_wh - receiver.battery_wh)
        transfer_efficiency = 0.85
        donor.battery_wh -= actual
        receiver.battery_wh += actual * transfer_efficiency
        self._history.append({"event": "share", "donor": donor_id, "receiver": receiver_id, "wh": actual})
        return actual * transfer_efficiency

    def get_critical_drones(self, threshold_pct: float = 20.0) -> List[str]:
        return [did for did, d in self._drones.items() if (d.battery_wh / d.max_battery_wh) * 100 < threshold_pct]

    def summary(self) -> dict:
        avg_battery = np.mean([d.battery_wh / d.max_battery_wh * 100 for d in self._drones.values()]) if self._drones else 0
        return {
            "total_zones": len(self._zones),
            "total_drones": len(self._drones),
            "avg_battery_pct": round(float(avg_battery), 1),
            "total_harvested_wh": round(self._total_harvested_wh, 2),
            "critical_drones": len(self.get_critical_drones()),
            "energy_shares": len(self._history),
        }
