"""
Phase 474: Satellite Mesh Network
Satellite-based mesh networking for global drone swarm connectivity.
"""

import numpy as np
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Optional, Tuple, Any


class SatelliteType(Enum):
    """Satellite types."""

    LEO = auto()  # Low Earth Orbit
    MEO = auto()  # Medium Earth Orbit
    GEO = auto()  # Geostationary
    HAP = auto()  # High Altitude Platform


class LinkStatus(Enum):
    """Link status."""

    ACTIVE = auto()
    DEGRADED = auto()
    INTERMITTENT = auto()
    DOWN = auto()


@dataclass
class Satellite:
    """Satellite node."""

    sat_id: str
    sat_type: SatelliteType
    altitude_km: float
    inclination_deg: float
    position: np.ndarray = field(default_factory=lambda: np.zeros(3))
    velocity: np.ndarray = field(default_factory=lambda: np.zeros(3))
    is_active: bool = True
    coverage_radius_km: float = 1000.0
    bandwidth_gbps: float = 10.0


@dataclass
class SatelliteLink:
    """Link between satellites or satellite-ground."""

    link_id: str
    source: str
    target: str
    latency_ms: float
    bandwidth_gbps: float
    signal_strength_db: float
    status: LinkStatus = LinkStatus.ACTIVE
    doppler_shift_hz: float = 0.0


@dataclass
class GroundStation:
    """Ground station."""

    station_id: str
    position: np.ndarray
    antenna_gain_dbi: float = 40.0
    elevation_mask_deg: float = 5.0
    connected_satellites: List[str] = field(default_factory=list)


@dataclass
class RoutingTable:
    """Satellite routing table."""

    source: str
    destination: str
    path: List[str]
    total_latency_ms: float
    hops: int
    reliability: float


class SatelliteMeshNetwork:
    """Satellite mesh network for drone swarm."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.satellites: Dict[str, Satellite] = {}
        self.links: Dict[Tuple[str, str], SatelliteLink] = {}
        self.ground_stations: Dict[str, GroundStation] = {}
        self.routing_tables: Dict[Tuple[str, str], RoutingTable] = {}
        self.time = 0.0

    def add_satellite(
        self,
        sat_id: str,
        sat_type: SatelliteType,
        altitude_km: float = 550,
        inclination_deg: float = 53.0,
    ) -> Satellite:
        sat = Satellite(sat_id, sat_type, altitude_km, inclination_deg)
        earth_radius = 6371
        angle = self.rng.uniform(0, 2 * np.pi)
        r = earth_radius + altitude_km
        sat.position = np.array([r * np.cos(angle), r * np.sin(angle), 0])
        sat.velocity = np.array([-7.5 * np.sin(angle), 7.5 * np.cos(angle), 0])
        self.satellites[sat_id] = sat
        return sat

    def add_ground_station(
        self, station_id: str, lat: float, lon: float
    ) -> GroundStation:
        earth_radius = 6371
        x = earth_radius * np.cos(np.radians(lat)) * np.cos(np.radians(lon))
        y = earth_radius * np.cos(np.radians(lat)) * np.sin(np.radians(lon))
        z = earth_radius * np.sin(np.radians(lat))
        station = GroundStation(station_id, np.array([x, y, z]))
        self.ground_stations[station_id] = station
        return station

    def create_constellation(
        self, n_planes: int, sats_per_plane: int, altitude_km: float = 550
    ) -> List[Satellite]:
        sats = []
        for plane in range(n_planes):
            for sat in range(sats_per_plane):
                sat_id = f"sat_{plane}_{sat}"
                sat_obj = self.add_satellite(
                    sat_id, SatelliteType.LEO, altitude_km, inclination_deg=53.0
                )
                sats.append(sat_obj)
        return sats

    def establish_links(self) -> int:
        n_links = 0
        sat_list = list(self.satellites.values())
        for i in range(len(sat_list)):
            for j in range(i + 1, len(sat_list)):
                s1, s2 = sat_list[i], sat_list[j]
                distance = np.linalg.norm(s1.position - s2.position)
                if distance < 5000:
                    latency = distance / 300000 * 1000
                    link = SatelliteLink(
                        f"link_{s1.sat_id}_{s2.sat_id}",
                        s1.sat_id,
                        s2.sat_id,
                        latency,
                        min(s1.bandwidth_gbps, s2.bandwidth_gbps),
                        signal_strength_db=10 * np.log10(1 / (distance / 1000) ** 2),
                    )
                    self.links[(s1.sat_id, s2.sat_id)] = link
                    n_links += 1
        for gs in self.ground_stations.values():
            for sat in sat_list:
                distance = np.linalg.norm(gs.position - sat.position)
                if distance < sat.coverage_radius_km * 2:
                    latency = distance / 300000 * 1000
                    link = SatelliteLink(
                        f"link_{gs.station_id}_{sat.sat_id}",
                        gs.station_id,
                        sat.sat_id,
                        latency,
                        sat.bandwidth_gbps,
                        signal_strength_db=10 * np.log10(1 / (distance / 1000) ** 2),
                    )
                    self.links[(gs.station_id, sat.sat_id)] = link
                    gs.connected_satellites.append(sat.sat_id)
                    n_links += 1
        return n_links

    def find_route(self, source: str, destination: str) -> Optional[RoutingTable]:
        visited = set()
        queue = [(source, [source], 0.0)]
        while queue:
            node, path, total_latency = queue.pop(0)
            if node == destination:
                reliability = 1.0
                for i in range(len(path) - 1):
                    key = (path[i], path[i + 1])
                    if key not in self.links:
                        key = (path[i + 1], path[i])
                    if key in self.links:
                        reliability *= 0.99
                return RoutingTable(
                    source, destination, path, total_latency, len(path) - 1, reliability
                )
            visited.add(node)
            for (s, t), link in self.links.items():
                next_node = None
                if s == node and t not in visited:
                    next_node = t
                elif t == node and s not in visited:
                    next_node = s
                if next_node and link.status == LinkStatus.ACTIVE:
                    queue.append(
                        (next_node, path + [next_node], total_latency + link.latency_ms)
                    )
        return None

    def update_positions(self, dt: float = 60.0) -> None:
        for sat in self.satellites.values():
            sat.position += sat.velocity * dt
        self.time += dt

    def get_network_stats(self) -> Dict[str, Any]:
        active_links = sum(
            1 for l in self.links.values() if l.status == LinkStatus.ACTIVE
        )
        avg_latency = (
            np.mean([l.latency_ms for l in self.links.values()]) if self.links else 0
        )
        return {
            "satellites": len(self.satellites),
            "ground_stations": len(self.ground_stations),
            "total_links": len(self.links),
            "active_links": active_links,
            "avg_latency_ms": avg_latency,
            "simulation_time": self.time,
        }


class DroneSatelliteBridge:
    """Bridge between drone swarm and satellite network."""

    def __init__(self, n_drones: int, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.network = SatelliteMeshNetwork(seed)
        self.drone_positions: Dict[str, np.ndarray] = {}
        self.drone_satellite_links: Dict[str, str] = {}
        self._init_infrastructure(n_drones)

    def _init_infrastructure(self, n_drones: int) -> None:
        self.network.create_constellation(
            n_planes=6, sats_per_plane=10, altitude_km=550
        )
        self.network.add_ground_station("gs_main", lat=35.0, lon=127.0)
        self.network.add_ground_station("gs_backup", lat=40.0, lon=140.0)
        self.network.establish_links()
        for i in range(n_drones):
            pos = self.rng.uniform(-100, 100, size=3)
            pos[2] = abs(pos[2]) + 50
            self.drone_positions[f"drone_{i}"] = pos

    def connect_drone_to_satellite(self, drone_id: str) -> Optional[str]:
        if drone_id not in self.drone_positions:
            return None
        drone_pos = self.drone_positions[drone_id]
        best_sat = None
        best_distance = np.inf
        for sat in self.network.satellites.values():
            distance = np.linalg.norm(sat.position - drone_pos)
            if distance < best_distance and distance < sat.coverage_radius_km:
                best_distance = distance
                best_sat = sat.sat_id
        if best_sat:
            self.drone_satellite_links[drone_id] = best_sat
        return best_sat

    def transmit_data(self, drone_id: str, data_size_mb: float) -> Dict[str, Any]:
        sat_id = self.drone_satellite_links.get(drone_id)
        if not sat_id:
            return {"success": False, "reason": "No satellite link"}
        gs_route = self.network.find_route(sat_id, "gs_main")
        if not gs_route:
            return {"success": False, "reason": "No route to ground"}
        total_latency = gs_route.total_latency_ms
        bandwidth = min(
            l.bandwidth_gbps
            for l in self.network.links.values()
            if l.source in gs_route.path or l.target in gs_route.path
        )
        transfer_time = data_size_mb * 8 / (bandwidth * 1000) * 1000
        return {
            "success": True,
            "latency_ms": total_latency,
            "transfer_time_ms": transfer_time,
            "route_hops": gs_route.hops,
            "satellite": sat_id,
        }

    def get_swarm_connectivity(self) -> Dict[str, Any]:
        connected = sum(
            1 for d in self.drone_positions if self.connect_drone_to_satellite(d)
        )
        return {
            "total_drones": len(self.drone_positions),
            "connected_drones": connected,
            "connectivity_rate": connected / len(self.drone_positions)
            if self.drone_positions
            else 0,
            "network_stats": self.network.get_network_stats(),
        }


if __name__ == "__main__":
    bridge = DroneSatelliteBridge(n_drones=10, seed=42)
    connectivity = bridge.get_swarm_connectivity()
    print(
        f"Connectivity: {connectivity['connected_drones']}/{connectivity['total_drones']}"
    )
    print(f"Network: {connectivity['network_stats']}")
    result = bridge.transmit_data("drone_0", 100)
    print(f"Transmission: {result}")
