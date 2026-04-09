"""
Phase 514: Satellite Relay Communication
LEO 위성 릴레이, 지연 보상, 핸드오버 관리.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple


class OrbitType(Enum):
    LEO = "leo"      # 160-2000 km
    MEO = "meo"      # 2000-35786 km
    GEO = "geo"      # 35786 km


class LinkStatus(Enum):
    CONNECTED = "connected"
    HANDOVER = "handover"
    DISCONNECTED = "disconnected"
    DEGRADED = "degraded"


@dataclass
class Satellite:
    sat_id: str
    orbit: OrbitType
    position: np.ndarray  # ECI coordinates
    velocity: np.ndarray
    altitude_km: float
    bandwidth_mbps: float
    latency_ms: float


@dataclass
class RelayLink:
    link_id: str
    drone_id: str
    sat_id: str
    status: LinkStatus
    snr_db: float
    latency_ms: float
    throughput_mbps: float
    handovers: int = 0


class OrbitalMechanics:
    """Simplified orbital propagation."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.earth_radius_km = 6371
        self.mu = 398600.4418  # km³/s²

    def create_constellation(self, n_sats: int = 12, altitude_km: float = 550,
                              orbit: OrbitType = OrbitType.LEO) -> List[Satellite]:
        sats = []
        r = self.earth_radius_km + altitude_km
        v_circ = np.sqrt(self.mu / r)
        for i in range(n_sats):
            angle = 2 * np.pi * i / n_sats + self.rng.uniform(-0.1, 0.1)
            incl = np.radians(self.rng.uniform(50, 98))
            pos = np.array([r * np.cos(angle), r * np.sin(angle) * np.cos(incl),
                          r * np.sin(angle) * np.sin(incl)])
            vel = np.array([-v_circ * np.sin(angle), v_circ * np.cos(angle) * np.cos(incl),
                          v_circ * np.cos(angle) * np.sin(incl)])
            lat = v_circ / r * 1000 * 2  # approx latency
            bw = self.rng.uniform(50, 200)
            sats.append(Satellite(f"SAT-{i:03d}", orbit, pos, vel, altitude_km, bw, round(lat, 1)))
        return sats

    def propagate(self, sat: Satellite, dt_s: float) -> Satellite:
        sat.position = sat.position + sat.velocity * dt_s / 1000
        r = np.linalg.norm(sat.position)
        if r > 0:
            sat.position *= (self.earth_radius_km + sat.altitude_km) / r
        return sat


class HandoverManager:
    """Manage satellite handovers for continuous connectivity."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.handover_log: List[Dict] = []

    def select_best(self, drone_pos_km: np.ndarray,
                    satellites: List[Satellite]) -> Optional[Satellite]:
        best = None
        best_score = -1
        for sat in satellites:
            dist = np.linalg.norm(sat.position - drone_pos_km)
            if dist > sat.altitude_km * 3:
                continue
            elev = np.degrees(np.arcsin(sat.altitude_km / (dist + 1e-8)))
            if elev < 10:
                continue
            score = elev / 90 * sat.bandwidth_mbps / 200
            if score > best_score:
                best_score = score
                best = sat
        return best

    def execute_handover(self, link: RelayLink, new_sat: Satellite) -> RelayLink:
        link.sat_id = new_sat.sat_id
        link.status = LinkStatus.HANDOVER
        link.latency_ms = new_sat.latency_ms + self.rng.uniform(5, 20)
        link.handovers += 1
        self.handover_log.append({
            "drone": link.drone_id, "new_sat": new_sat.sat_id,
            "handover_num": link.handovers})
        link.status = LinkStatus.CONNECTED
        return link


class SatelliteRelay:
    """Satellite relay communication system for drone swarms."""

    def __init__(self, n_drones: int = 10, n_sats: int = 12, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_drones = n_drones
        self.orbital = OrbitalMechanics(seed)
        self.handover = HandoverManager(seed)
        self.satellites = self.orbital.create_constellation(n_sats)
        self.links: Dict[str, RelayLink] = {}
        self.time = 0.0

        for i in range(n_drones):
            did = f"drone_{i}"
            drone_pos = self.rng.uniform(-100, 100, 3)
            drone_pos[2] = self.rng.uniform(0.03, 0.15)  # km altitude
            drone_pos_abs = np.array([self.orbital.earth_radius_km + drone_pos[0] * 0.001,
                                      drone_pos[1] * 0.001, drone_pos[2]])
            best = self.handover.select_best(drone_pos_abs, self.satellites)
            if best:
                snr = 10 + self.rng.uniform(0, 20)
                self.links[did] = RelayLink(
                    f"LNK-{i:03d}", did, best.sat_id, LinkStatus.CONNECTED,
                    round(snr, 1), best.latency_ms, round(best.bandwidth_mbps * snr / 30, 1))

    def step(self, dt_s: float = 10) -> Dict:
        self.time += dt_s
        for sat in self.satellites:
            self.orbital.propagate(sat, dt_s)

        handovers = 0
        for did, link in self.links.items():
            if self.rng.random() < 0.05:
                best = self.handover.select_best(
                    np.array([self.orbital.earth_radius_km, 0, 0.1]),
                    self.satellites)
                if best and best.sat_id != link.sat_id:
                    self.handover.execute_handover(link, best)
                    handovers += 1
            link.snr_db += self.rng.standard_normal() * 0.5
            link.throughput_mbps = max(0, link.throughput_mbps + self.rng.standard_normal() * 2)

        return {"time": self.time, "handovers": handovers,
                "connected": sum(1 for l in self.links.values() if l.status == LinkStatus.CONNECTED)}

    def summary(self) -> Dict:
        return {
            "drones": self.n_drones,
            "satellites": len(self.satellites),
            "active_links": len(self.links),
            "total_handovers": sum(l.handovers for l in self.links.values()),
            "avg_latency_ms": round(
                np.mean([l.latency_ms for l in self.links.values()]) if self.links else 0, 1),
        }
