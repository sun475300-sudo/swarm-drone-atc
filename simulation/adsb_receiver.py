"""Phase 682: ADS-B 수신 데이터 통합 시뮬레이션."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class ADSBMessage:
    icao_address: str
    callsign: str
    latitude: float
    longitude: float
    altitude_ft: float
    ground_speed_kt: float
    track_deg: float
    vertical_rate_fpm: float
    squawk: str = "1200"
    timestamp: float = field(default_factory=time.time)
    msg_type: str = "1090ES"  # 1090ES or 978UAT


class ADSBReceiver:
    """Simulated ADS-B receiver for manned aircraft traffic awareness."""

    MIN_SEPARATION_FT = 500.0
    MIN_LATERAL_M = 1852.0  # 1 NM

    def __init__(self, seed: int = 42) -> None:
        self.rng = np.random.default_rng(seed)
        self.listening = False
        self.frequency_mhz = 1090.0
        self.aircraft: Dict[str, ADSBMessage] = {}
        self.stats = {
            "msgs_received": 0, "aircraft_tracked": 0,
            "conflicts_detected": 0, "update_rate_hz": 1.0,
        }

    def start_listening(self, frequency_mhz: float = 1090.0) -> bool:
        self.frequency_mhz = frequency_mhz
        self.listening = True
        return True

    def stop_listening(self) -> None:
        self.listening = False

    def inject_traffic(self, messages: List[ADSBMessage]) -> int:
        """Inject simulated ADS-B messages for testing."""
        count = 0
        for msg in messages:
            self.aircraft[msg.icao_address] = msg
            self.stats["msgs_received"] += 1
            count += 1
        self.stats["aircraft_tracked"] = len(self.aircraft)
        return count

    def get_aircraft_list(self) -> List[ADSBMessage]:
        return list(self.aircraft.values())

    def get_aircraft_by_icao(self, icao: str) -> Optional[ADSBMessage]:
        return self.aircraft.get(icao)

    def detect_conflicts(
        self, drone_positions: List[Tuple[float, float, float]],
    ) -> List[Dict[str, Any]]:
        """Detect conflicts between drones and manned aircraft.

        Args:
            drone_positions: list of (lat, lon, alt_ft) drone positions

        Returns:
            list of conflict dicts
        """
        conflicts = []
        for i, dpos in enumerate(drone_positions):
            for icao, ac in self.aircraft.items():
                lat_diff = (dpos[0] - ac.latitude) * 111320.0
                lon_diff = (dpos[1] - ac.longitude) * 111320.0 * np.cos(np.radians(ac.latitude))
                lateral_m = np.sqrt(lat_diff ** 2 + lon_diff ** 2)
                vert_ft = abs(dpos[2] - ac.altitude_ft)

                if lateral_m < self.MIN_LATERAL_M and vert_ft < self.MIN_SEPARATION_FT:
                    conflicts.append({
                        "drone_index": i,
                        "aircraft_icao": icao,
                        "callsign": ac.callsign,
                        "lateral_m": lateral_m,
                        "vertical_ft": vert_ft,
                        "severity": "HIGH" if lateral_m < 500 else "MEDIUM",
                    })
                    self.stats["conflicts_detected"] += 1

        return conflicts

    def get_traffic_density(
        self, area_bounds: Tuple[float, float, float, float],
    ) -> int:
        """Count aircraft in area (min_lat, min_lon, max_lat, max_lon)."""
        count = 0
        for ac in self.aircraft.values():
            if (area_bounds[0] <= ac.latitude <= area_bounds[2] and
                    area_bounds[1] <= ac.longitude <= area_bounds[3]):
                count += 1
        return count

    def get_receiver_stats(self) -> Dict[str, Any]:
        return {
            "listening": self.listening,
            "frequency_mhz": self.frequency_mhz,
            **self.stats,
        }

    def generate_simulated_traffic(self, count: int = 5, center: Tuple[float, float] = (37.5, 127.0)) -> List[ADSBMessage]:
        """Generate random ADS-B traffic for testing."""
        messages = []
        for i in range(count):
            msg = ADSBMessage(
                icao_address=f"A{self.rng.integers(10000, 99999):05X}",
                callsign=f"KAL{self.rng.integers(100, 999)}",
                latitude=center[0] + self.rng.uniform(-0.5, 0.5),
                longitude=center[1] + self.rng.uniform(-0.5, 0.5),
                altitude_ft=self.rng.uniform(1000, 40000),
                ground_speed_kt=self.rng.uniform(100, 500),
                track_deg=self.rng.uniform(0, 360),
                vertical_rate_fpm=self.rng.uniform(-1000, 1000),
                squawk=f"{self.rng.integers(1000, 7777):04d}",
                msg_type="1090ES" if self.rng.random() > 0.3 else "978UAT",
            )
            messages.append(msg)
        return messages
