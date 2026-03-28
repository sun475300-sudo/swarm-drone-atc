"""
비행 로그 분석
==============
비행 패턴 통계 + 이상 탐지 + KPI 리포트.

사용법:
    fla = FlightLogAnalyzer()
    fla.add_entry("d1", duration_s=300, distance_m=2000, energy_wh=20)
    stats = fla.drone_stats("d1")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class FlightEntry:
    """비행 로그 항목"""
    drone_id: str
    duration_s: float
    distance_m: float
    energy_wh: float
    max_speed_ms: float = 0.0
    avg_altitude_m: float = 50.0
    incidents: int = 0
    t: float = 0.0


@dataclass
class DroneStats:
    """드론별 통계"""
    drone_id: str
    total_flights: int
    total_distance_m: float
    total_duration_s: float
    total_energy_wh: float
    avg_efficiency_wh_km: float
    avg_speed_ms: float
    incident_rate: float


class FlightLogAnalyzer:
    """비행 로그 분석."""

    def __init__(self) -> None:
        self._entries: list[FlightEntry] = []
        self._by_drone: dict[str, list[FlightEntry]] = {}

    def add_entry(
        self, drone_id: str, duration_s: float, distance_m: float,
        energy_wh: float, max_speed: float = 0.0,
        avg_altitude: float = 50.0, incidents: int = 0, t: float = 0.0,
    ) -> FlightEntry:
        entry = FlightEntry(
            drone_id=drone_id, duration_s=duration_s,
            distance_m=distance_m, energy_wh=energy_wh,
            max_speed_ms=max_speed, avg_altitude_m=avg_altitude,
            incidents=incidents, t=t,
        )
        self._entries.append(entry)
        if drone_id not in self._by_drone:
            self._by_drone[drone_id] = []
        self._by_drone[drone_id].append(entry)
        return entry

    def drone_stats(self, drone_id: str) -> DroneStats | None:
        entries = self._by_drone.get(drone_id, [])
        if not entries:
            return None

        total_dist = sum(e.distance_m for e in entries)
        total_dur = sum(e.duration_s for e in entries)
        total_energy = sum(e.energy_wh for e in entries)
        total_incidents = sum(e.incidents for e in entries)

        efficiency = (total_energy / max(total_dist / 1000, 0.001))
        avg_speed = total_dist / max(total_dur, 1)

        return DroneStats(
            drone_id=drone_id,
            total_flights=len(entries),
            total_distance_m=total_dist,
            total_duration_s=total_dur,
            total_energy_wh=total_energy,
            avg_efficiency_wh_km=efficiency,
            avg_speed_ms=avg_speed,
            incident_rate=total_incidents / len(entries),
        )

    def detect_anomalies(self, z_threshold: float = 2.0) -> list[dict[str, Any]]:
        """에너지 효율 이상치 탐지"""
        if len(self._entries) < 5:
            return []

        efficiencies = []
        for e in self._entries:
            if e.distance_m > 10:
                efficiencies.append(e.energy_wh / (e.distance_m / 1000))
            else:
                efficiencies.append(0)

        arr = np.array(efficiencies)
        mean = np.mean(arr)
        std = np.std(arr)
        if std < 1e-6:
            return []

        anomalies = []
        for i, e in enumerate(self._entries):
            z = abs(arr[i] - mean) / std
            if z > z_threshold:
                anomalies.append({
                    "drone_id": e.drone_id,
                    "z_score": round(float(z), 2),
                    "efficiency": round(float(arr[i]), 2),
                    "mean": round(float(mean), 2),
                })
        return anomalies

    def fleet_kpi(self) -> dict[str, float]:
        """함대 KPI"""
        if not self._entries:
            return {"avg_efficiency": 0, "avg_speed": 0, "incident_rate": 0}

        total_dist = sum(e.distance_m for e in self._entries)
        total_dur = sum(e.duration_s for e in self._entries)
        total_energy = sum(e.energy_wh for e in self._entries)
        total_incidents = sum(e.incidents for e in self._entries)

        return {
            "avg_efficiency_wh_km": round(total_energy / max(total_dist / 1000, 0.001), 2),
            "avg_speed_ms": round(total_dist / max(total_dur, 1), 2),
            "incident_rate": round(total_incidents / len(self._entries), 3),
            "total_flights": len(self._entries),
        }

    def top_drones(self, metric: str = "distance", n: int = 5) -> list[tuple[str, float]]:
        """상위 드론"""
        stats = {}
        for did in self._by_drone:
            s = self.drone_stats(did)
            if not s:
                continue
            if metric == "distance":
                stats[did] = s.total_distance_m
            elif metric == "efficiency":
                stats[did] = s.avg_efficiency_wh_km
            else:
                stats[did] = s.total_flights
        return sorted(stats.items(), key=lambda x: -x[1])[:n]

    def summary(self) -> dict[str, Any]:
        return {
            "total_entries": len(self._entries),
            "unique_drones": len(self._by_drone),
            "anomalies": len(self.detect_anomalies()),
            **self.fleet_kpi(),
        }
