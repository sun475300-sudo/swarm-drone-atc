"""Phase 313: Satellite Communication Layer — 위성 통신 계층.

LEO 위성 궤도 전파, 링크 버짓 계산, 핸드오버 관리,
다중 위성 가시성 분석, 지연 시간 모델링.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class OrbitType(Enum):
    LEO = "leo"       # 200-2000 km
    MEO = "meo"       # 2000-35786 km
    GEO = "geo"       # 35786 km
    HEO = "heo"       # highly elliptical


class LinkStatus(Enum):
    CONNECTED = "connected"
    HANDOVER = "handover"
    LOST = "lost"
    DEGRADED = "degraded"


@dataclass
class Satellite:
    sat_id: str
    orbit_type: OrbitType = OrbitType.LEO
    altitude_km: float = 550.0    # Starlink-like
    inclination_deg: float = 53.0
    longitude_deg: float = 0.0
    velocity_kms: float = 7.6     # orbital velocity
    position_ecef: np.ndarray = field(default_factory=lambda: np.zeros(3))
    is_active: bool = True


@dataclass
class SatLink:
    satellite_id: str
    drone_id: str
    status: LinkStatus = LinkStatus.LOST
    snr_db: float = 0.0
    latency_ms: float = 0.0
    bandwidth_mbps: float = 0.0
    elevation_deg: float = 0.0
    data_rate_kbps: float = 0.0


@dataclass
class LinkBudget:
    tx_power_dbw: float = 10.0
    tx_gain_dbi: float = 5.0
    rx_gain_dbi: float = 30.0
    frequency_ghz: float = 12.0   # Ku-band
    path_loss_db: float = 0.0
    atmospheric_loss_db: float = 2.0
    margin_db: float = 3.0
    snr_db: float = 0.0
    link_available: bool = False


class SatelliteCommLayer:
    """위성 통신 계층.

    - LEO/MEO/GEO 위성 궤도 전파
    - 링크 버짓 (자유공간 경로손실)
    - 가시성 분석 (최소 앙각)
    - 핸드오버 관리
    - 지연 시간 모델
    """

    EARTH_RADIUS_KM = 6371.0
    SPEED_OF_LIGHT_KMS = 299792.458
    MIN_ELEVATION_DEG = 10.0

    def __init__(self, rng_seed: int = 42):
        self._rng = np.random.default_rng(rng_seed)
        self._satellites: Dict[str, Satellite] = {}
        self._links: Dict[str, SatLink] = {}
        self._handover_count = 0
        self._total_data_kb = 0.0

    def add_satellite(self, sat: Satellite):
        """Add satellite and compute initial ECEF position."""
        lon_rad = np.radians(sat.longitude_deg)
        r = self.EARTH_RADIUS_KM + sat.altitude_km
        sat.position_ecef = np.array([
            r * np.cos(lon_rad),
            r * np.sin(lon_rad),
            r * np.sin(np.radians(sat.inclination_deg)) * 0.1,
        ])
        self._satellites[sat.sat_id] = sat

    def propagate_orbits(self, dt_sec: float):
        """Simple circular orbit propagation."""
        for sat in self._satellites.values():
            if not sat.is_active:
                continue
            r = self.EARTH_RADIUS_KM + sat.altitude_km
            angular_vel = sat.velocity_kms / r  # rad/s
            angle = angular_vel * dt_sec
            cos_a, sin_a = np.cos(angle), np.sin(angle)
            x, y = sat.position_ecef[0], sat.position_ecef[1]
            sat.position_ecef[0] = x * cos_a - y * sin_a
            sat.position_ecef[1] = x * sin_a + y * cos_a

    def compute_link_budget(self, sat: Satellite, drone_pos_km: np.ndarray) -> LinkBudget:
        """Compute link budget between satellite and ground drone."""
        budget = LinkBudget()
        slant_range_km = np.linalg.norm(sat.position_ecef - drone_pos_km)

        # Free space path loss: FSPL = 20*log10(d) + 20*log10(f) + 92.45
        if slant_range_km > 0:
            budget.path_loss_db = (
                20 * np.log10(slant_range_km) +
                20 * np.log10(budget.frequency_ghz) + 92.45
            )
        else:
            budget.path_loss_db = 0

        budget.snr_db = (
            budget.tx_power_dbw + budget.tx_gain_dbi + budget.rx_gain_dbi
            - budget.path_loss_db - budget.atmospheric_loss_db - budget.margin_db
        )
        budget.link_available = budget.snr_db > 5.0
        return budget

    def compute_elevation(self, sat: Satellite, drone_pos_km: np.ndarray) -> float:
        """Compute elevation angle from drone to satellite (degrees)."""
        diff = sat.position_ecef - drone_pos_km
        horiz_dist = np.sqrt(diff[0] ** 2 + diff[1] ** 2)
        vert_dist = diff[2]
        if horiz_dist < 0.01:
            return 90.0
        return float(np.degrees(np.arctan2(vert_dist, horiz_dist)))

    def compute_latency(self, sat: Satellite, drone_pos_km: np.ndarray) -> float:
        """One-way propagation delay in ms."""
        dist_km = np.linalg.norm(sat.position_ecef - drone_pos_km)
        return (dist_km / self.SPEED_OF_LIGHT_KMS) * 1000.0  # ms

    def find_best_satellite(self, drone_pos_km: np.ndarray) -> Optional[str]:
        """Find satellite with highest elevation above minimum threshold."""
        best_sat = None
        best_elev = self.MIN_ELEVATION_DEG
        for sat in self._satellites.values():
            if not sat.is_active:
                continue
            elev = self.compute_elevation(sat, drone_pos_km)
            if elev > best_elev:
                best_elev = elev
                best_sat = sat.sat_id
        return best_sat

    def update_links(self, drone_positions: Dict[str, np.ndarray]):
        """Update all drone-satellite links."""
        for drone_id, pos in drone_positions.items():
            best_sat = self.find_best_satellite(pos)
            current_link = self._links.get(drone_id)

            if best_sat is None:
                self._links[drone_id] = SatLink(
                    satellite_id="", drone_id=drone_id, status=LinkStatus.LOST,
                )
                continue

            sat = self._satellites[best_sat]
            budget = self.compute_link_budget(sat, pos)
            latency = self.compute_latency(sat, pos)
            elev = self.compute_elevation(sat, pos)

            if current_link and current_link.satellite_id != best_sat:
                self._handover_count += 1

            status = LinkStatus.CONNECTED if budget.link_available else LinkStatus.DEGRADED
            data_rate = max(0, (budget.snr_db - 5.0) * 100)  # simple rate model

            self._links[drone_id] = SatLink(
                satellite_id=best_sat, drone_id=drone_id,
                status=status, snr_db=round(budget.snr_db, 2),
                latency_ms=round(latency, 2), elevation_deg=round(elev, 2),
                data_rate_kbps=round(data_rate, 1),
            )

    def get_link(self, drone_id: str) -> Optional[SatLink]:
        return self._links.get(drone_id)

    def get_visible_satellites(self, drone_pos_km: np.ndarray) -> List[str]:
        return [
            sat.sat_id for sat in self._satellites.values()
            if sat.is_active and self.compute_elevation(sat, drone_pos_km) > self.MIN_ELEVATION_DEG
        ]

    def summary(self) -> dict:
        connected = sum(1 for l in self._links.values() if l.status == LinkStatus.CONNECTED)
        return {
            "total_satellites": len(self._satellites),
            "active_satellites": sum(1 for s in self._satellites.values() if s.is_active),
            "total_links": len(self._links),
            "connected_links": connected,
            "handovers": self._handover_count,
            "avg_latency_ms": round(
                np.mean([l.latency_ms for l in self._links.values()]) if self._links else 0, 2
            ),
        }
