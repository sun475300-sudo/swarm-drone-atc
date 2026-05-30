"""Formal evaluation metrics — Phase P705.

Standardised metrics for SDACS benchmarking and paper comparison.
Reference: near-miss rate, airspace utilisation, path efficiency.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class FormalMetrics:
    """Structured metric bundle for a single simulation run."""
    # Safety
    near_miss_rate: float          # near-miss events per drone per minute
    collision_rate: float          # collision events per drone per minute
    conflict_resolution_rate: float  # fraction of conflicts resolved without collision

    # Efficiency
    airspace_utilization: float    # mean fraction of available corridor cells occupied
    path_efficiency: float         # planned_distance / actual_distance  (1.0 = perfect)
    throughput_mpm: float          # missions completed per minute

    # System
    mean_advisory_latency_ms: float  # controller response latency
    controller_hz: float             # effective controller update rate

    def to_dict(self) -> dict[str, float]:
        """Return a flat dict of all metrics."""
        return {
            "near_miss_rate": self.near_miss_rate,
            "collision_rate": self.collision_rate,
            "conflict_resolution_rate": self.conflict_resolution_rate,
            "airspace_utilization": self.airspace_utilization,
            "path_efficiency": self.path_efficiency,
            "throughput_mpm": self.throughput_mpm,
            "mean_advisory_latency_ms": self.mean_advisory_latency_ms,
            "controller_hz": self.controller_hz,
        }


def compute_near_miss_rate(near_miss_count: int, n_drones: int, duration_s: float) -> float:
    """Near-miss events per drone per minute."""
    if n_drones <= 0 or duration_s <= 0:
        return 0.0
    return near_miss_count / n_drones / (duration_s / 60.0)


def compute_collision_rate(collision_count: int, n_drones: int, duration_s: float) -> float:
    """Collision events per drone per minute."""
    if n_drones <= 0 or duration_s <= 0:
        return 0.0
    return collision_count / n_drones / (duration_s / 60.0)


def compute_conflict_resolution_rate(
    collisions: int,
    conflicts_total: int,
) -> float:
    """Fraction of detected conflicts resolved without collision.

    Formula from CLAUDE.md: 1 - collisions / (conflicts + collisions)
    """
    denom = conflicts_total + collisions
    if denom <= 0:
        return 1.0
    return 1.0 - collisions / denom


def compute_path_efficiency(
    planned_distance_m: float,
    actual_distance_m: float,
) -> float:
    """Ratio of planned to actual distance travelled.

    Perfect efficiency = 1.0 (actual == planned).
    Values < 1.0 indicate shorter-than-planned paths (unlikely).
    Values > 1.0 indicate detours from collision avoidance.
    Returns the INVERSE so higher = better: planned / actual.
    """
    if actual_distance_m <= 0:
        return 1.0
    return min(planned_distance_m / actual_distance_m, 1.0)


def compute_airspace_utilization(
    occupied_cells: int,
    total_cells: int,
) -> float:
    """Fraction of total airspace cells occupied at peak."""
    if total_cells <= 0:
        return 0.0
    return occupied_cells / total_cells


def from_simulation_result(
    metrics_dict: dict[str, Any],
    n_drones: int,
    duration_s: float,
) -> FormalMetrics:
    """Construct FormalMetrics from a SwarmSimulator result dict."""
    collisions = int(metrics_dict.get("collision_count", 0))
    near_misses = int(metrics_dict.get("near_miss_count", 0))
    conflicts = int(metrics_dict.get("conflicts_total", 0))
    advisories = int(metrics_dict.get("advisories_issued", 0))
    planned_dist = float(metrics_dict.get("total_planned_distance_m", 0.0))
    actual_dist = float(metrics_dict.get("total_distance_m", planned_dist))
    missions = int(metrics_dict.get("routes_completed", 0))

    occupied = int(metrics_dict.get("occupied_cells", 0))
    total_cells = int(metrics_dict.get("total_cells", max(occupied, 1)))

    latency_ms = float(metrics_dict.get("mean_advisory_latency_ms", 1000.0))
    ctrl_hz = float(metrics_dict.get("controller_hz", 1.0))

    return FormalMetrics(
        near_miss_rate=compute_near_miss_rate(near_misses, n_drones, duration_s),
        collision_rate=compute_collision_rate(collisions, n_drones, duration_s),
        conflict_resolution_rate=compute_conflict_resolution_rate(collisions, conflicts),
        airspace_utilization=compute_airspace_utilization(occupied, total_cells),
        path_efficiency=compute_path_efficiency(planned_dist, actual_dist),
        throughput_mpm=missions / max(duration_s / 60.0, 1e-9),
        mean_advisory_latency_ms=latency_ms,
        controller_hz=ctrl_hz,
    )


def compare_algorithms(
    baseline: FormalMetrics,
    proposed: FormalMetrics,
) -> dict[str, Any]:
    """Return a comparison dict showing relative improvement of proposed vs baseline.

    Positive values mean proposed is better.
    """
    def _delta(b: float, p: float) -> float:
        return (p - b) / max(abs(b), 1e-9)

    return {
        "near_miss_rate_delta": _delta(baseline.near_miss_rate, proposed.near_miss_rate) * -1,
        "collision_rate_delta": _delta(baseline.collision_rate, proposed.collision_rate) * -1,
        "conflict_resolution_delta": _delta(
            baseline.conflict_resolution_rate, proposed.conflict_resolution_rate
        ),
        "path_efficiency_delta": _delta(baseline.path_efficiency, proposed.path_efficiency),
        "airspace_utilization_delta": _delta(
            baseline.airspace_utilization, proposed.airspace_utilization
        ),
        "throughput_delta": _delta(baseline.throughput_mpm, proposed.throughput_mpm),
    }
