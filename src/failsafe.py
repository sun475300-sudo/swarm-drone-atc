"""
Failsafe Logic for Swarm Drones — P695
=======================================
Geofence boundary enforcement + communication-loss RTL triggering.

Classes:
    GeofenceZone    — Cylindrical no-fly boundary
    FailsafeConfig  — Configurable thresholds
    FailsafeAction  — Enum of actions
    FailsafeMonitor — Per-drone state machine
    SwarmFailsafe   — Fleet-level coordinator
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np


class FailsafeAction(Enum):
    """Action the failsafe system requests."""
    NONE = "none"
    RTL = "rtl"           # Return-to-Launch
    LAND = "land"         # Emergency land in place
    GEOFENCE_RTL = "geofence_rtl"  # RTL triggered by geofence breach


@dataclass(frozen=True)
class GeofenceZone:
    """
    Cylindrical geofence boundary (keep-in or keep-out).

    Attributes:
        center_xy: Center [x, y] in meters
        radius_m: Horizontal radius in meters
        min_alt_m: Minimum altitude (floor) in meters
        max_alt_m: Maximum altitude (ceiling) in meters
        keep_in: True = drone must stay inside; False = keep-out zone
    """
    center_xy: tuple[float, float]
    radius_m: float
    min_alt_m: float = 0.0
    max_alt_m: float = 400.0
    keep_in: bool = True

    def contains(self, position: np.ndarray) -> bool:
        """Return True if position is inside the cylindrical zone."""
        pos = np.asarray(position, dtype=np.float64)
        dx = pos[0] - self.center_xy[0]
        dy = pos[1] - self.center_xy[1]
        horizontal_dist = float(np.sqrt(dx * dx + dy * dy))
        alt = float(pos[2]) if len(pos) > 2 else 0.0
        return (
            horizontal_dist <= self.radius_m
            and self.min_alt_m <= alt <= self.max_alt_m
        )

    def is_violated(self, position: np.ndarray) -> bool:
        """
        Return True if the geofence is violated.

        For keep-in zones: violated when drone leaves.
        For keep-out zones: violated when drone enters.
        """
        inside = self.contains(position)
        return not inside if self.keep_in else inside


@dataclass
class FailsafeConfig:
    """
    Failsafe configuration thresholds.

    Attributes:
        comm_timeout_s: Seconds without telemetry before triggering RTL
        geofence_zones: List of geofence zones to enforce
        low_battery_pct: Battery percentage below which LAND is triggered
        enable_comm_failsafe: Enable communication loss failsafe
        enable_geofence: Enable geofence enforcement
        enable_battery: Enable low-battery failsafe
    """
    comm_timeout_s: float = 5.0
    geofence_zones: list[GeofenceZone] = field(default_factory=list)
    low_battery_pct: float = 15.0
    enable_comm_failsafe: bool = True
    enable_geofence: bool = True
    enable_battery: bool = True


@dataclass
class FailsafeStatus:
    """Current failsafe evaluation result."""
    action: FailsafeAction
    reason: str
    drone_id: int
    timestamp: float


class FailsafeMonitor:
    """
    Per-drone failsafe state machine.

    Tracks last telemetry time, evaluates geofence and battery thresholds,
    and emits FailsafeAction when a trigger condition is met.
    """

    def __init__(self, drone_id: int, config: FailsafeConfig):
        self.drone_id = drone_id
        self.config = config
        self._last_comm_time: float | None = None
        self._active_action = FailsafeAction.NONE

    def update_comm(self, timestamp: float) -> None:
        """Record a successful telemetry heartbeat at the given time."""
        self._last_comm_time = timestamp

    def evaluate(
        self,
        current_time: float,
        position: np.ndarray,
        battery_pct: float = 100.0,
    ) -> FailsafeStatus:
        """
        Evaluate all failsafe conditions and return the highest-priority action.

        Priority: LAND (battery) > GEOFENCE_RTL > RTL (comm loss) > NONE
        Once an action is active it persists until cleared externally.

        Args:
            current_time: Simulation clock (seconds)
            position: Current drone position [x, y, z]
            battery_pct: Battery state of charge (0-100)

        Returns:
            FailsafeStatus with the recommended action and reason
        """
        pos = np.asarray(position, dtype=np.float64)

        # Battery check — highest priority
        if self.config.enable_battery and battery_pct <= self.config.low_battery_pct:
            self._active_action = FailsafeAction.LAND
            return FailsafeStatus(
                action=FailsafeAction.LAND,
                reason=f"Low battery: {battery_pct:.1f}%",
                drone_id=self.drone_id,
                timestamp=current_time,
            )

        # Geofence check
        if self.config.enable_geofence:
            for zone in self.config.geofence_zones:
                if zone.is_violated(pos):
                    self._active_action = FailsafeAction.GEOFENCE_RTL
                    zone_type = "keep-in" if zone.keep_in else "keep-out"
                    return FailsafeStatus(
                        action=FailsafeAction.GEOFENCE_RTL,
                        reason=f"Geofence breach ({zone_type} zone at {zone.center_xy})",
                        drone_id=self.drone_id,
                        timestamp=current_time,
                    )

        # Communication loss check
        if self.config.enable_comm_failsafe:
            if self._last_comm_time is None:
                elapsed = current_time
            else:
                elapsed = current_time - self._last_comm_time

            if elapsed > self.config.comm_timeout_s:
                self._active_action = FailsafeAction.RTL
                return FailsafeStatus(
                    action=FailsafeAction.RTL,
                    reason=f"Comm loss: {elapsed:.1f}s > {self.config.comm_timeout_s}s timeout",
                    drone_id=self.drone_id,
                    timestamp=current_time,
                )

        self._active_action = FailsafeAction.NONE
        return FailsafeStatus(
            action=FailsafeAction.NONE,
            reason="nominal",
            drone_id=self.drone_id,
            timestamp=current_time,
        )

    def reset(self) -> None:
        """Clear the active action (call after drone has responded to failsafe)."""
        self._active_action = FailsafeAction.NONE
        self._last_comm_time = None

    @property
    def active_action(self) -> FailsafeAction:
        return self._active_action


class SwarmFailsafe:
    """
    Fleet-level failsafe coordinator.

    Manages FailsafeMonitor instances for all drones and aggregates
    the fleet status.
    """

    def __init__(self, config: FailsafeConfig | None = None):
        self.config = config or FailsafeConfig()
        self._monitors: dict[int, FailsafeMonitor] = {}

    def get_monitor(self, drone_id: int) -> FailsafeMonitor:
        """Get or create a FailsafeMonitor for the given drone."""
        if drone_id not in self._monitors:
            self._monitors[drone_id] = FailsafeMonitor(drone_id, self.config)
        return self._monitors[drone_id]

    def update_comm(self, drone_id: int, timestamp: float) -> None:
        """Record a telemetry heartbeat for the given drone."""
        self.get_monitor(drone_id).update_comm(timestamp)

    def evaluate_all(
        self,
        current_time: float,
        drone_states: dict[int, tuple[np.ndarray, float]],
    ) -> list[FailsafeStatus]:
        """
        Evaluate failsafe for all known drones.

        Args:
            current_time: Simulation clock (seconds)
            drone_states: {drone_id: (position_array, battery_pct)}

        Returns:
            List of FailsafeStatus for every drone; sorted by drone_id.
        """
        statuses = []
        for drone_id, (position, battery_pct) in drone_states.items():
            monitor = self.get_monitor(drone_id)
            status = monitor.evaluate(current_time, position, battery_pct)
            statuses.append(status)
        return sorted(statuses, key=lambda s: s.drone_id)

    def active_alerts(
        self,
        current_time: float,
        drone_states: dict[int, tuple[np.ndarray, float]],
    ) -> list[FailsafeStatus]:
        """Return only the drones that require action (action != NONE)."""
        return [
            s for s in self.evaluate_all(current_time, drone_states)
            if s.action != FailsafeAction.NONE
        ]

    def reset(self, drone_id: int | None = None) -> None:
        """Reset one or all drone monitors."""
        if drone_id is not None:
            if drone_id in self._monitors:
                self._monitors[drone_id].reset()
        else:
            for monitor in self._monitors.values():
                monitor.reset()
