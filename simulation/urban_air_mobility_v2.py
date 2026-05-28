"""
Phase 489: Urban Air Mobility V2
도심항공교통 통합, 버티포트 네트워크, 수요 예측.
"""

from dataclasses import dataclass
from enum import Enum

import numpy as np


class VehicleType(Enum):
    """``VehicleType`` 관련 기능을 제공한다."""
    EVTOL = "evtol"
    DRONE_CARGO = "drone_cargo"
    AIR_TAXI = "air_taxi"
    EMERGENCY = "emergency"


class VertiportStatus(Enum):
    """``VertiportStatus`` 관련 기능을 제공한다."""
    OPEN = "open"
    BUSY = "busy"
    CLOSED = "closed"
    MAINTENANCE = "maintenance"


@dataclass
class Vertiport:
    """``Vertiport`` 관련 기능을 제공한다."""
    port_id: str
    position: np.ndarray  # (lat, lon, alt)
    capacity: int = 4
    current_load: int = 0
    status: VertiportStatus = VertiportStatus.OPEN
    charge_rate_kw: float = 150.0
    landing_pads: int = 2

    @property
    def available_pads(self) -> int:
        """``available_pads`` 동작을 수행한다."""
        return max(0, self.landing_pads - self.current_load)

    @property
    def utilization(self) -> float:
        """``utilization`` 동작을 수행한다."""
        return self.current_load / max(self.capacity, 1)


@dataclass
class UAMFlight:
    """``UAMFlight`` 관련 기능을 제공한다."""
    flight_id: str
    vehicle_type: VehicleType
    origin: str
    destination: str
    departure_time: float
    arrival_time: float = 0.0
    passengers: int = 0
    cargo_kg: float = 0.0
    status: str = "scheduled"
    energy_kwh: float = 0.0


@dataclass
class DemandForecast:
    """``DemandForecast`` 관련 기능을 제공한다."""
    hour: int
    origin: str
    destination: str
    predicted_demand: float
    confidence: float


class DemandPredictor:
    """Time-series demand prediction for UAM routes."""

    def __init__(self, seed: int = 42):
        """인스턴스를 초기화한다."""
        self.rng = np.random.default_rng(seed)
        self.history: dict[str, list[float]] = {}

    def add_observation(self, route: str, demand: float):
        """`observation` 항목을 추가한다."""
        if route not in self.history:
            self.history[route] = []
        self.history[route].append(demand)

    def predict(self, route: str, hour: int) -> DemandForecast:
        """`대상` 결과를 계산하거나 판정한다."""
        base = 10 + 15 * np.sin(np.pi * hour / 12)  # peak at noon
        if 7 <= hour <= 9 or 17 <= hour <= 19:
            base *= 1.5  # rush hour
        noise = self.rng.standard_normal() * 3

        if route in self.history and len(self.history[route]) >= 5:
            recent = np.mean(self.history[route][-5:])
            base = 0.6 * base + 0.4 * recent

        parts = route.split("->")
        origin = parts[0] if len(parts) > 1 else route
        dest = parts[1] if len(parts) > 1 else route

        return DemandForecast(hour, origin, dest,
                             round(max(0, base + noise), 1),
                             round(0.7 + self.rng.random() * 0.25, 3))


class UrbanAirMobilityV2:
    """Urban Air Mobility network management system."""

    def __init__(self, seed: int = 42):
        """인스턴스를 초기화한다."""
        self.rng = np.random.default_rng(seed)
        self.vertiports: dict[str, Vertiport] = {}
        self.flights: list[UAMFlight] = []
        self.demand = DemandPredictor(seed)
        self.time = 0.0
        self._flight_counter = 0
        self.corridors: dict[str, dict] = {}

    def add_vertiport(self, port_id: str, lat: float, lon: float, alt: float = 0,
                      capacity: int = 4, pads: int = 2) -> Vertiport:
        """`vertiport` 항목을 추가한다."""
        vp = Vertiport(port_id, np.array([lat, lon, alt]), capacity, landing_pads=pads)
        self.vertiports[port_id] = vp
        return vp

    def create_corridor(self, origin: str, dest: str, altitude_m: float = 300,
                        width_m: float = 100) -> dict:
        """`corridor` 결과를 생성한다."""
        key = f"{origin}->{dest}"
        p1 = self.vertiports[origin].position
        p2 = self.vertiports[dest].position
        dist = np.linalg.norm(p2 - p1) * 111000  # rough deg->m
        corridor = {
            "origin": origin, "destination": dest,
            "altitude_m": altitude_m, "width_m": width_m,
            "distance_m": round(dist, 0),
            "flight_time_min": round(dist / 200 * 60 / 1000, 1),  # ~200km/h
        }
        self.corridors[key] = corridor
        self.corridors[f"{dest}->{origin}"] = {**corridor, "origin": dest, "destination": origin}
        return corridor

    def schedule_flight(self, origin: str, dest: str,
                        vehicle: VehicleType = VehicleType.AIR_TAXI,
                        passengers: int = 2) -> UAMFlight | None:
        """`flight` 작업을 계획한다."""
        if origin not in self.vertiports or dest not in self.vertiports:
            return None
        op = self.vertiports[origin]
        dp = self.vertiports[dest]
        if op.status == VertiportStatus.CLOSED or dp.status == VertiportStatus.CLOSED:
            return None

        self._flight_counter += 1
        key = f"{origin}->{dest}"
        flight_time = self.corridors.get(key, {}).get("flight_time_min", 15)

        flight = UAMFlight(
            f"UAM-{self._flight_counter:05d}", vehicle,
            origin, dest, self.time,
            self.time + flight_time * 60,
            passengers=passengers,
            energy_kwh=round(flight_time * 2.5, 1))
        self.flights.append(flight)
        op.current_load += 1
        return flight

    def tick(self, dt: float = 60) -> dict:
        """``tick`` 동작을 수행한다."""
        self.time += dt
        departed = 0
        arrived = 0
        for f in self.flights:
            if f.status == "scheduled" and self.time >= f.departure_time:
                f.status = "airborne"
                departed += 1
            elif f.status == "airborne" and self.time >= f.arrival_time:
                f.status = "arrived"
                arrived += 1
                if f.origin in self.vertiports:
                    self.vertiports[f.origin].current_load = max(0, self.vertiports[f.origin].current_load - 1)
                if f.destination in self.vertiports:
                    dp = self.vertiports[f.destination]
                    dp.current_load = min(dp.capacity, dp.current_load + 1)
        return {"time": self.time, "departed": departed, "arrived": arrived}

    def network_status(self) -> dict:
        """``network_status`` 동작을 수행한다."""
        return {
            "vertiports": len(self.vertiports),
            "corridors": len(self.corridors) // 2,
            "total_flights": len(self.flights),
            "airborne": sum(1 for f in self.flights if f.status == "airborne"),
            "completed": sum(1 for f in self.flights if f.status == "arrived"),
            "avg_utilization": round(float(np.mean(
                [v.utilization for v in self.vertiports.values()])), 3) if self.vertiports else 0,
            "total_passengers": sum(f.passengers for f in self.flights),
        }

    def summary(self) -> dict:
        """현재 상태 요약을 반환한다."""
        return self.network_status()
