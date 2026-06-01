"""
Swarm Frame Synchronization — P696
====================================
Simulates NTP/PTP-style clock synchronization across swarm drones.
Measures per-drone offset and jitter; supports coordinator election.

Classes:
    DroneClockState  — Immutable per-drone clock snapshot
    SwarmClock       — Mutable per-drone sync state machine
    SwarmSyncManager — Fleet-level synchronizer + jitter reporter
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np


_JITTER_TARGET_MS = 10.0  # P696 requirement: <10ms jitter


@dataclass(frozen=True)
class DroneClockState:
    """
    Immutable snapshot of one drone's clock alignment.

    Attributes:
        drone_id: Unique drone identifier
        offset_s: Estimated clock offset from reference (seconds, can be negative)
        stratum: NTP stratum level (0 = reference, 1 = directly synced, …)
        last_sync_time: Reference time of the last sync round
        synced: True if this drone has completed at least one sync exchange
    """
    drone_id: int
    offset_s: float
    stratum: int
    last_sync_time: float
    synced: bool


@dataclass
class SwarmClock:
    """
    Per-drone clock state machine for NTP-style offset estimation.

    Uses a rolling window of offset samples to estimate the true offset
    and compute round-trip jitter.

    Attributes:
        drone_id: Unique drone identifier
        initial_offset_s: Simulated hardware clock skew at start
        window_size: Number of samples kept for jitter/offset estimation
    """

    drone_id: int
    initial_offset_s: float = 0.0
    window_size: int = 8

    def __post_init__(self) -> None:
        self._offset_s: float = self.initial_offset_s
        self._samples: list[float] = []
        self._stratum: int = 255  # unsynchronized
        self._last_sync_time: float = 0.0
        self._synced: bool = False

    def record_sync(
        self,
        ref_time: float,
        measured_offset_s: float,
    ) -> None:
        """
        Record one NTP exchange result.

        Args:
            ref_time: Reference clock time at which the exchange completed
            measured_offset_s: Offset computed from the four NTP timestamps
        """
        self._last_sync_time = ref_time
        self._samples.append(measured_offset_s)
        if len(self._samples) > self.window_size:
            self._samples.pop(0)
        # Estimate offset as median of recent samples (robust to outliers)
        sorted_samples = sorted(self._samples)
        n = len(sorted_samples)
        mid = n // 2
        if n % 2 == 0:
            self._offset_s = (sorted_samples[mid - 1] + sorted_samples[mid]) / 2.0
        else:
            self._offset_s = sorted_samples[mid]
        self._synced = True
        self._stratum = 1

    @property
    def offset_s(self) -> float:
        return self._offset_s

    @property
    def jitter_ms(self) -> float:
        """Standard deviation of recorded offset samples in milliseconds."""
        if len(self._samples) < 2:
            return float("inf")
        mean = sum(self._samples) / len(self._samples)
        variance = sum((s - mean) ** 2 for s in self._samples) / (len(self._samples) - 1)
        return math.sqrt(variance) * 1000.0

    @property
    def stratum(self) -> int:
        return self._stratum

    @property
    def is_synced(self) -> bool:
        return self._synced

    @property
    def meets_jitter_target(self) -> bool:
        """Return True if jitter is below the 10ms P696 requirement."""
        return self.jitter_ms < _JITTER_TARGET_MS

    def snapshot(self) -> DroneClockState:
        """Return an immutable snapshot of the current state."""
        return DroneClockState(
            drone_id=self.drone_id,
            offset_s=self._offset_s,
            stratum=self._stratum,
            last_sync_time=self._last_sync_time,
            synced=self._synced,
        )

    def reset(self) -> None:
        """Return clock to unsynchronized state."""
        self._offset_s = self.initial_offset_s
        self._samples.clear()
        self._stratum = 255
        self._synced = False


class SwarmSyncManager:
    """
    Fleet-level synchronizer.

    Maintains a SwarmClock for each drone.  Each call to `run_sync_round`
    simulates one NTP exchange: the manager generates a noisy offset
    observation for each drone and records it via `SwarmClock.record_sync`.

    Attributes:
        seed: RNG seed for reproducible simulations
        noise_std_s: Standard deviation of per-exchange timing noise (seconds)
    """

    def __init__(
        self,
        noise_std_s: float = 0.001,
        window_size: int = 8,
        seed: int = 42,
    ):
        self.noise_std_s = noise_std_s
        self.window_size = window_size
        self._rng = np.random.default_rng(seed)
        self._clocks: dict[int, SwarmClock] = {}

    def add_drone(self, drone_id: int, initial_offset_s: float = 0.0) -> None:
        """Register a drone with an optional simulated hardware clock skew."""
        self._clocks[drone_id] = SwarmClock(
            drone_id=drone_id,
            initial_offset_s=initial_offset_s,
            window_size=self.window_size,
        )

    def run_sync_round(self, ref_time: float) -> list[DroneClockState]:
        """
        Simulate one NTP exchange for all registered drones.

        Each drone receives a noisy measurement of its true offset.
        Returns immutable snapshots after the round.

        Args:
            ref_time: Current reference clock time (seconds)

        Returns:
            List of DroneClockState snapshots, sorted by drone_id
        """
        snapshots = []
        for drone_id, clock in sorted(self._clocks.items()):
            true_offset = clock.initial_offset_s
            noise = float(self._rng.normal(0.0, self.noise_std_s))
            measured_offset = true_offset + noise
            clock.record_sync(ref_time, measured_offset)
            snapshots.append(clock.snapshot())
        return snapshots

    def get_clock(self, drone_id: int) -> SwarmClock | None:
        return self._clocks.get(drone_id)

    def fleet_jitter_ms(self) -> dict[int, float]:
        """Return per-drone jitter in milliseconds."""
        return {
            drone_id: clock.jitter_ms
            for drone_id, clock in self._clocks.items()
        }

    def all_meet_jitter_target(self) -> bool:
        """Return True if every synced drone meets the <10ms jitter target."""
        return all(
            clock.meets_jitter_target
            for clock in self._clocks.values()
            if clock.is_synced and len(clock._samples) >= 2
        )

    def sync_summary(self) -> dict:
        """
        Return a summary dict suitable for logging or metrics export.

        Keys: synced_count, total_count, max_jitter_ms, all_meet_target
        """
        clocks = list(self._clocks.values())
        synced = [c for c in clocks if c.is_synced]
        jitters = [
            c.jitter_ms for c in synced if len(c._samples) >= 2
        ]
        return {
            "synced_count": len(synced),
            "total_count": len(clocks),
            "max_jitter_ms": max(jitters) if jitters else float("inf"),
            "all_meet_target": self.all_meet_jitter_target(),
        }

    def reset(self, drone_id: int | None = None) -> None:
        """Reset one or all drone clocks to unsynchronized state."""
        if drone_id is not None:
            if drone_id in self._clocks:
                self._clocks[drone_id].reset()
        else:
            for clock in self._clocks.values():
                clock.reset()
