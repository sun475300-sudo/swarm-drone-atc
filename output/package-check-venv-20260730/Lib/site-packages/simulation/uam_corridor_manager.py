"""
Phase 477: UAM Corridor Manager
도심항공모빌리티 회랑 관리 — 버티포트 스케줄링, 수직이착륙 경로.
"""

from dataclasses import dataclass, field
from enum import Enum

import numpy as np


class CorridorType(Enum):
    """``CorridorType`` 관련 기능을 제공한다."""
    LOW_ALTITUDE = "low_altitude"       # 0-120m
    MEDIUM_ALTITUDE = "medium_altitude"  # 120-300m
    HIGH_ALTITUDE = "high_altitude"      # 300-600m
    TRANSITION = "transition"


class VertiportStatus(Enum):
    """``VertiportStatus`` 관련 기능을 제공한다."""
    OPEN = "open"
    BUSY = "busy"
    CLOSED = "closed"
    EMERGENCY = "emergency"


@dataclass
class Vertiport:
    """``Vertiport`` 관련 기능을 제공한다."""
    port_id: str
    x: float
    y: float
    z: float
    capacity: int = 4
    current_load: int = 0
    status: VertiportStatus = VertiportStatus.OPEN
    landing_pads: int = 2
    charging_slots: int = 4


@dataclass
class UAMCorridor:
    """``UAMCorridor`` 관련 기능을 제공한다."""
    corridor_id: str
    start_port: str
    end_port: str
    corridor_type: CorridorType
    width_m: float = 50.0
    altitude_min: float = 120.0
    altitude_max: float = 300.0
    max_traffic: int = 10
    current_traffic: int = 0
    waypoints: list[tuple[float, float, float]] = field(default_factory=list)


@dataclass
class UAMFlight:
    """``UAMFlight`` 관련 기능을 제공한다."""
    flight_id: str
    origin: str
    destination: str
    corridor_id: str
    departure_time: float
    arrival_time: float = 0
    passengers: int = 1
    status: str = "scheduled"


class UAMCorridorManager:
    """Manages UAM corridors, vertiports, and flight scheduling."""

    def __init__(self, seed: int = 42):
        """인스턴스를 초기화한다."""
        self.rng = np.random.default_rng(seed)
        self.vertiports: dict[str, Vertiport] = {}
        self.corridors: dict[str, UAMCorridor] = {}
        self.flights: dict[str, UAMFlight] = {}
        self.schedule: list[UAMFlight] = []
        self._flight_counter = 0

    def add_vertiport(self, port_id: str, x: float, y: float, z: float = 0,
                      capacity: int = 4) -> Vertiport:
        """`vertiport` 항목을 추가한다."""
        vp = Vertiport(port_id, x, y, z, capacity)
        self.vertiports[port_id] = vp
        return vp

    def create_corridor(self, start: str, end: str,
                        corridor_type: CorridorType = CorridorType.MEDIUM_ALTITUDE,
                        width: float = 50.0) -> UAMCorridor | None:
        """`corridor` 결과를 생성한다."""
        if start not in self.vertiports or end not in self.vertiports:
            return None
        cid = f"COR-{start}-{end}"
        sp, ep = self.vertiports[start], self.vertiports[end]

        n_waypoints = max(3, int(np.sqrt((sp.x - ep.x)**2 + (sp.y - ep.y)**2) / 100))
        waypoints = []
        for i in range(n_waypoints):
            t = i / (n_waypoints - 1)
            wx = sp.x + t * (ep.x - sp.x)
            wy = sp.y + t * (ep.y - sp.y)
            alt = 150 + 100 * np.sin(np.pi * t)  # arc profile
            waypoints.append((wx, wy, alt))

        corridor = UAMCorridor(cid, start, end, corridor_type, width,
                               waypoints=waypoints)
        self.corridors[cid] = corridor
        return corridor

    def auto_create_corridors(self, max_distance: float = 5000) -> int:
        """``auto_create_corridors`` 동작을 수행한다."""
        count = 0
        ports = list(self.vertiports.keys())
        for i in range(len(ports)):
            for j in range(i + 1, len(ports)):
                a, b = self.vertiports[ports[i]], self.vertiports[ports[j]]
                dist = np.sqrt((a.x - b.x)**2 + (a.y - b.y)**2)
                if dist <= max_distance:
                    self.create_corridor(ports[i], ports[j])
                    self.create_corridor(ports[j], ports[i])
                    count += 2
        return count

    def schedule_flight(self, origin: str, destination: str,
                        departure_time: float, passengers: int = 1) -> UAMFlight | None:
        """`flight` 작업을 계획한다."""
        cid = f"COR-{origin}-{destination}"
        corridor = self.corridors.get(cid)
        if not corridor:
            return None
        if corridor.current_traffic >= corridor.max_traffic:
            return None

        op = self.vertiports.get(origin)
        dp = self.vertiports.get(destination)
        if not op or not dp:
            return None
        if op.status == VertiportStatus.CLOSED:
            return None

        dist = np.sqrt((op.x - dp.x)**2 + (op.y - dp.y)**2)
        flight_time = dist / 50.0  # ~180 km/h

        self._flight_counter += 1
        flight = UAMFlight(
            flight_id=f"UAM-{self._flight_counter:06d}",
            origin=origin, destination=destination,
            corridor_id=cid, departure_time=departure_time,
            arrival_time=departure_time + flight_time,
            passengers=passengers
        )
        self.flights[flight.flight_id] = flight
        self.schedule.append(flight)
        corridor.current_traffic += 1
        op.current_load += 1
        return flight

    def complete_flight(self, flight_id: str) -> bool:
        """``complete_flight`` 동작을 수행한다."""
        flight = self.flights.get(flight_id)
        if not flight or flight.status != "scheduled":
            return False
        flight.status = "completed"
        corridor = self.corridors.get(flight.corridor_id)
        if corridor:
            corridor.current_traffic = max(0, corridor.current_traffic - 1)
        dp = self.vertiports.get(flight.destination)
        if dp:
            dp.current_load += 1
        op = self.vertiports.get(flight.origin)
        if op:
            op.current_load = max(0, op.current_load - 1)
        return True

    def find_best_route(self, origin: str, destination: str) -> str | None:
        """``find_best_route`` 동작을 수행한다."""
        best_cid = None
        best_load = float('inf')
        for cid, cor in self.corridors.items():
            if cor.start_port == origin and cor.end_port == destination and cor.current_traffic < best_load:
                best_load = cor.current_traffic
                best_cid = cid
        return best_cid

    def get_corridor_load(self) -> dict[str, float]:
        """`corridor load` 정보를 조회한다."""
        loads = {}
        for cid, cor in self.corridors.items():
            loads[cid] = cor.current_traffic / max(cor.max_traffic, 1) * 100
        return loads

    def summary(self) -> dict:
        """현재 상태 요약을 반환한다."""
        completed = sum(1 for f in self.flights.values() if f.status == "completed")
        total_pax = sum(f.passengers for f in self.flights.values())
        return {
            "vertiports": len(self.vertiports),
            "corridors": len(self.corridors),
            "total_flights": len(self.flights),
            "completed_flights": completed,
            "total_passengers": total_pax,
            "avg_corridor_load": np.mean(list(self.get_corridor_load().values())) if self.corridors else 0,
        }
