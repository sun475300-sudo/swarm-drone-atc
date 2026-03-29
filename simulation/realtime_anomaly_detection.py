"""Real-time Anomaly Detection System for Phase 220-239.

Provides real-time detection of anomalous situations in drone swarm simulations
including collision risks, unusual patterns, and system anomalies.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable

import numpy as np


class AnomalyType(Enum):
    """Types of anomalies that can be detected."""

    COLLISION_RISK = "collision_risk"
    UNUSUAL_SPEED = "unusual_speed"
    PATH_DEVIATION = "path_deviation"
    COMMUNICATION_LOSS = "communication_loss"
    BATTERY_CRITICAL = "battery_critical"
    WEATHER_SEVERE = "weather_severe"
    ZONE_VIOLATION = "zone_violation"
    FORMATION_BREAK = "formation_break"
    GPS_SIGNAL_LOSS = "gps_signal_loss"
    SYSTEM_OVERLOAD = "system_overload"


class SeverityLevel(Enum):
    """Severity levels for anomalies."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Anomaly:
    """Detected anomaly."""

    anomaly_type: AnomalyType
    severity: SeverityLevel
    timestamp: float
    drone_ids: list[int]
    description: str
    metrics: dict[str, float] = field(default_factory=dict)
    recommended_action: str = ""
    resolved: bool = False
    resolution_time: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "anomaly_type": self.anomaly_type.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp,
            "drone_ids": self.drone_ids,
            "description": self.description,
            "metrics": self.metrics,
            "recommended_action": self.recommended_action,
            "resolved": self.resolved,
            "resolution_time": self.resolution_time,
        }


@dataclass
class DetectionThresholds:
    """Thresholds for anomaly detection."""

    collision_distance: float = 50.0
    collision_probability: float = 0.7
    speed_min: float = 0.0
    speed_max: float = 30.0
    battery_critical: float = 10.0
    path_deviation: float = 100.0
    weather_severe: float = 0.8
    zone_margin: float = 10.0


class StatisticalMonitor:
    """Monitor statistical properties for anomaly detection."""

    def __init__(self, window_size: int = 100) -> None:
        self._window_size = window_size
        self._buffers: dict[str, list[float]] = {}
        self._means: dict[str, float] = {}
        self._stds: dict[str, float] = {}

    def update(self, key: str, value: float) -> None:
        """Update statistical monitor with new value."""
        if key not in self._buffers:
            self._buffers[key] = []

        self._buffers[key].append(value)
        if len(self._buffers[key]) > self._window_size:
            self._buffers[key].pop(0)

        if len(self._buffers[key]) >= 10:
            self._means[key] = float(np.mean(self._buffers[key]))
            self._stds[key] = float(np.std(self._buffers[key]))

    def is_anomaly(self, key: str, value: float, n_std: float = 3.0) -> bool:
        """Check if value is anomalous based on statistical bounds."""
        if key not in self._means:
            return False

        lower_bound = self._means[key] - n_std * self._stds[key]
        upper_bound = self._means[key] + n_std * self._stds[key]

        return value < lower_bound or value > upper_bound

    def get_stats(self, key: str) -> dict[str, float]:
        """Get statistics for a key."""
        if key not in self._buffers:
            return {}
        return {
            "mean": self._means.get(key, 0.0),
            "std": self._stds.get(key, 0.0),
            "min": float(np.min(self._buffers[key])),
            "max": float(np.max(self._buffers[key])),
            "count": len(self._buffers[key]),
        }


class AnomalyDetector:
    """Core anomaly detection engine."""

    def __init__(self, thresholds: DetectionThresholds | None = None) -> None:
        self._thresholds = thresholds or DetectionThresholds()
        self._stat_monitors: dict[str, StatisticalMonitor] = {}
        self._anomaly_history: list[Anomaly] = []
        self._enabled_detectors: set[str] = {
            "collision",
            "speed",
            "battery",
            "weather",
            "zone",
        }

    def enable_detector(self, detector: str) -> None:
        """Enable a specific detector."""
        self._enabled_detectors.add(detector)

    def disable_detector(self, detector: str) -> None:
        """Disable a specific detector."""
        self._enabled_detectors.discard(detector)

    def detect_collision_risk(
        self,
        positions: np.ndarray,
        velocities: np.ndarray,
        drone_ids: list[int],
    ) -> list[Anomaly]:
        """Detect collision risks."""
        if "collision" not in self._enabled_detectors:
            return []

        anomalies = []
        n = len(positions)

        for i in range(n):
            for j in range(i + 1, n):
                dist = float(np.linalg.norm(positions[i] - positions[j]))

                if dist < self._thresholds.collision_distance:
                    rel_vel = float(np.linalg.norm(velocities[i] - velocities[j]))
                    t_cpa = dist / (rel_vel + 1e-6)
                    collision_prob = max(0, 1 - t_cpa / 30)

                    if collision_prob > self._thresholds.collision_probability:
                        severity = self._get_collision_severity(dist, t_cpa)
                        anomalies.append(
                            Anomaly(
                                anomaly_type=AnomalyType.COLLISION_RISK,
                                severity=severity,
                                timestamp=time.time(),
                                drone_ids=[drone_ids[i], drone_ids[j]],
                                description=f"Collision risk detected: distance={dist:.1f}m, TCA={t_cpa:.1f}s",
                                metrics={
                                    "distance": dist,
                                    "time_to_collision": t_cpa,
                                    "collision_probability": collision_prob,
                                },
                                recommended_action="Immediate evasive maneuver required",
                            )
                        )

        return anomalies

    def _get_collision_severity(self, distance: float, t_cpa: float) -> SeverityLevel:
        """Get collision severity based on distance and time."""
        if distance < 20 or t_cpa < 10:
            return SeverityLevel.CRITICAL
        elif distance < 35 or t_cpa < 20:
            return SeverityLevel.HIGH
        elif distance < 45 or t_cpa < 30:
            return SeverityLevel.MEDIUM
        else:
            return SeverityLevel.LOW

    def detect_speed_anomalies(
        self,
        speeds: np.ndarray,
        drone_ids: list[int],
    ) -> list[Anomaly]:
        """Detect unusual speed anomalies."""
        if "speed" not in self._enabled_detectors:
            return []

        anomalies = []
        for i, speed in enumerate(speeds):
            if speed < self._thresholds.speed_min or speed > self._thresholds.speed_max:
                severity = (
                    SeverityLevel.HIGH
                    if speed > self._thresholds.speed_max
                    else SeverityLevel.MEDIUM
                )
                anomalies.append(
                    Anomaly(
                        anomaly_type=AnomalyType.UNUSUAL_SPEED,
                        severity=severity,
                        timestamp=time.time(),
                        drone_ids=[drone_ids[i]],
                        description=f"Unusual speed detected: {speed:.1f} m/s",
                        metrics={
                            "speed": speed,
                            "threshold": self._thresholds.speed_max,
                        },
                        recommended_action="Check drone propulsion system",
                    )
                )

                self._stat_monitors.setdefault(
                    f"speed_{drone_ids[i]}", StatisticalMonitor()
                ).update(f"speed_{drone_ids[i]}", speed)

        return anomalies

    def detect_battery_anomalies(
        self,
        battery_levels: np.ndarray,
        drone_ids: list[int],
    ) -> list[Anomaly]:
        """Detect low battery anomalies."""
        if "battery" not in self._enabled_detectors:
            return []

        anomalies = []
        for i, battery in enumerate(battery_levels):
            if battery < self._thresholds.battery_critical:
                severity = SeverityLevel.CRITICAL if battery < 5 else SeverityLevel.HIGH
                anomalies.append(
                    Anomaly(
                        anomaly_type=AnomalyType.BATTERY_CRITICAL,
                        severity=severity,
                        timestamp=time.time(),
                        drone_ids=[drone_ids[i]],
                        description=f"Critical battery level: {battery:.1f}%",
                        metrics={"battery_level": battery},
                        recommended_action="Immediate landing required",
                    )
                )

        return anomalies

    def detect_weather_anomalies(
        self,
        wind_speed: float,
        visibility: float,
        precipitation: float,
    ) -> list[Anomaly]:
        """Detect severe weather anomalies."""
        if "weather" not in self._enabled_detectors:
            return []

        anomalies = []

        if wind_speed > 20:
            severity = SeverityLevel.HIGH if wind_speed < 30 else SeverityLevel.CRITICAL
            anomalies.append(
                Anomaly(
                    anomaly_type=AnomalyType.WEATHER_SEVERE,
                    severity=severity,
                    timestamp=time.time(),
                    drone_ids=[],
                    description=f"Severe wind conditions: {wind_speed:.1f} m/s",
                    metrics={"wind_speed": wind_speed},
                    recommended_action="Reduce drone speeds or land",
                )
            )

        if precipitation > self._thresholds.weather_severe:
            anomalies.append(
                Anomaly(
                    anomaly_type=AnomalyType.WEATHER_SEVERE,
                    severity=SeverityLevel.HIGH,
                    timestamp=time.time(),
                    drone_ids=[],
                    description=f"Heavy precipitation: {precipitation:.1%}",
                    metrics={"precipitation": precipitation},
                    recommended_action="Suspend outdoor operations",
                )
            )

        return anomalies

    def detect_zone_violations(
        self,
        positions: np.ndarray,
        boundaries: dict[str, tuple[float, float]],
        drone_ids: list[int],
    ) -> list[Anomaly]:
        """Detect airspace zone violations."""
        if "zone" not in self._enabled_detectors:
            return []

        anomalies = []
        for i, pos in enumerate(positions):
            for axis, (min_val, max_val) in boundaries.items():
                axis_idx = {"x": 0, "y": 1, "z": 2}.get(axis, 0)
                if (
                    pos[axis_idx] < min_val - self._thresholds.zone_margin
                    or pos[axis_idx] > max_val + self._thresholds.zone_margin
                ):
                    anomalies.append(
                        Anomaly(
                            anomaly_type=AnomalyType.ZONE_VIOLATION,
                            severity=SeverityLevel.MEDIUM,
                            timestamp=time.time(),
                            drone_ids=[drone_ids[i]],
                            description=f"Zone violation: {axis}={pos[axis_idx]:.1f}",
                            metrics={"axis": axis, "position": float(pos[axis_idx])},
                            recommended_action="Return to designated airspace",
                        )
                    )
                    break

        return anomalies

    def detect_formation_break(
        self,
        positions: np.ndarray,
        expected_formation: list[np.ndarray],
        drone_ids: list[int],
    ) -> list[Anomaly]:
        """Detect formation flight break anomalies."""
        if len(positions) != len(expected_formation):
            return []

        anomalies = []
        for i, (pos, expected) in enumerate(zip(positions, expected_formation)):
            deviation = float(np.linalg.norm(pos - expected))
            if deviation > self._thresholds.path_deviation:
                self._stat_monitors.setdefault(
                    f"formation_{drone_ids[i]}", StatisticalMonitor()
                ).update(f"formation_{drone_ids[i]}", deviation)

                if self._stat_monitors[f"formation_{drone_ids[i]}"].is_anomaly(
                    f"formation_{drone_ids[i]}", deviation
                ):
                    anomalies.append(
                        Anomaly(
                            anomaly_type=AnomalyType.FORMATION_BREAK,
                            severity=SeverityLevel.HIGH,
                            timestamp=time.time(),
                            drone_ids=[drone_ids[i]],
                            description=f"Formation break: deviation={deviation:.1f}m",
                            metrics={
                                "deviation": deviation,
                                "threshold": self._thresholds.path_deviation,
                            },
                            recommended_action="Rejoin formation",
                        )
                    )

        return anomalies


class RealTimeAnomalyMonitor:
    """Real-time anomaly monitoring system."""

    def __init__(self, thresholds: DetectionThresholds | None = None) -> None:
        self._detector = AnomalyDetector(thresholds)
        self._anomalies: list[Anomaly] = []
        self._alert_callbacks: list[Callable[[Anomaly], None]] = []
        self._stats = {
            "total_detections": 0,
            "by_type": {},
            "by_severity": {},
            "resolution_rate": 0.0,
        }

    def add_alert_callback(self, callback: Callable[[Anomaly], None]) -> None:
        """Add callback for anomaly alerts."""
        self._alert_callbacks.append(callback)

    def detect_all(
        self,
        positions: np.ndarray,
        velocities: np.ndarray,
        speeds: np.ndarray,
        battery_levels: np.ndarray,
        drone_ids: list[int],
        weather: dict[str, float] | None = None,
        boundaries: dict[str, tuple[float, float]] | None = None,
        expected_formation: list[np.ndarray] | None = None,
    ) -> list[Anomaly]:
        """Detect all types of anomalies."""
        all_anomalies: list[Anomaly] = []

        all_anomalies.extend(
            self._detector.detect_collision_risk(positions, velocities, drone_ids)
        )
        all_anomalies.extend(self._detector.detect_speed_anomalies(speeds, drone_ids))
        all_anomalies.extend(
            self._detector.detect_battery_anomalies(battery_levels, drone_ids)
        )

        if weather:
            all_anomalies.extend(
                self._detector.detect_weather_anomalies(
                    weather.get("wind_speed", 0),
                    weather.get("visibility", 10000),
                    weather.get("precipitation", 0),
                )
            )

        if boundaries:
            all_anomalies.extend(
                self._detector.detect_zone_violations(positions, boundaries, drone_ids)
            )

        if expected_formation is not None:
            all_anomalies.extend(
                self._detector.detect_formation_break(
                    positions, expected_formation, drone_ids
                )
            )

        self._anomalies.extend(all_anomalies)
        self._update_stats(all_anomalies)

        for anomaly in all_anomalies:
            for callback in self._alert_callbacks:
                callback(anomaly)

        return all_anomalies

    def _update_stats(self, anomalies: list[Anomaly]) -> None:
        """Update monitoring statistics."""
        self._stats["total_detections"] += len(anomalies)

        for anomaly in anomalies:
            atype = anomaly.anomaly_type.value
            severity = anomaly.severity.value

            self._stats["by_type"][atype] = self._stats["by_type"].get(atype, 0) + 1
            self._stats["by_severity"][severity] = (
                self._stats["by_severity"].get(severity, 0) + 1
            )

        total = len(self._anomalies)
        resolved = sum(1 for a in self._anomalies if a.resolved)
        if total > 0:
            self._stats["resolution_rate"] = resolved / total

    def resolve_anomaly(self, anomaly: Anomaly) -> None:
        """Mark anomaly as resolved."""
        for a in self._anomalies:
            if (
                a.timestamp == anomaly.timestamp
                and a.anomaly_type == anomaly.anomaly_type
            ):
                a.resolved = True
                a.resolution_time = time.time()
                break

    def get_active_anomalies(
        self, severity: SeverityLevel | None = None
    ) -> list[Anomaly]:
        """Get currently active anomalies."""
        if severity:
            return [
                a for a in self._anomalies if not a.resolved and a.severity == severity
            ]
        return [a for a in self._anomalies if not a.resolved]

    def get_anomaly_summary(self) -> dict[str, Any]:
        """Get summary of all anomalies."""
        return {
            "total_anomalies": len(self._anomalies),
            "active_anomalies": len(self.get_active_anomalies()),
            "resolved_anomalies": len([a for a in self._anomalies if a.resolved]),
            "by_type": self._stats["by_type"],
            "by_severity": self._stats["by_severity"],
            "resolution_rate": self._stats["resolution_rate"],
        }

    def export_anomalies(self, filepath: str | Path) -> None:
        """Export anomalies to JSON file."""
        with open(filepath, "w") as f:
            json.dump(
                {
                    "anomalies": [a.to_dict() for a in self._anomalies],
                    "summary": self.get_anomaly_summary(),
                    "export_time": datetime.now().isoformat(),
                },
                f,
                indent=2,
            )

    def clear_resolved(self) -> int:
        """Clear resolved anomalies and return count."""
        count = len([a for a in self._anomalies if a.resolved])
        self._anomalies = [a for a in self._anomalies if not a.resolved]
        return count


def anomaly_alert_handler(anomaly: Anomaly) -> None:
    """Default alert handler for anomalies."""
    severity_emoji = {
        SeverityLevel.LOW: "INFO",
        SeverityLevel.MEDIUM: "WARNING",
        SeverityLevel.HIGH: "ALERT",
        SeverityLevel.CRITICAL: "CRITICAL",
    }
    print(
        f"[{severity_emoji[anomaly.severity]}] {anomaly.anomaly_type.value}: {anomaly.description}"
    )


def demo_anomaly_detection() -> None:
    """Demonstration of anomaly detection."""
    monitor = RealTimeAnomalyMonitor()
    monitor.add_alert_callback(anomaly_alert_handler)

    n_drones = 20
    np.random.seed(42)
    positions = np.random.uniform(-200, 200, (n_drones, 3))
    velocities = np.random.uniform(-5, 5, (n_drones, 3))
    speeds = np.linalg.norm(velocities, axis=1)
    battery_levels = np.random.uniform(20, 100, n_drones)
    drone_ids = list(range(n_drones))

    battery_levels[0] = 5

    positions[5] = positions[6] + np.array([30, 0, 0])

    anomalies = monitor.detect_all(
        positions=positions,
        velocities=velocities,
        speeds=speeds,
        battery_levels=battery_levels,
        drone_ids=drone_ids,
        weather={"wind_speed": 25.0, "visibility": 5000, "precipitation": 0.3},
        boundaries={"x": (-300, 300), "y": (-300, 300), "z": (0, 200)},
    )

    print(f"\nDetected {len(anomalies)} anomalies:")
    for anomaly in anomalies:
        print(f"  - [{anomaly.severity.value.upper()}] {anomaly.description}")

    print("\nSummary:")
    summary = monitor.get_anomaly_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    demo_anomaly_detection()
