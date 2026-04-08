"""
시뮬레이션 KPI 수집기 (DEPRECATED - DO NOT USE)

WARNING: This module is deprecated and should not be used in new code.
충돌률, 근접 위반, 경로 효율성, 배터리 소모 통계

REPLACEMENT: Use simulation.analytics.SimulationAnalytics instead.
This legacy metrics module has been superseded by the analytics submodule.
새 코드에서는 analytics.py를 사용하세요.

Legacy behavior is preserved for backward compatibility only. This module
will be removed in a future version. Migrate to SimulationAnalytics immediately.

.. deprecated::
    이 모듈은 simulation.analytics.SimulationAnalytics로 대체되었습니다.
    새 코드에서는 analytics.py를 사용하세요.
"""
from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field


@dataclass
class SimulationMetrics:
    """한 시뮬레이션 런의 KPI 집계"""

    # 안전 지표
    collision_count: int = 0
    near_miss_count: int = 0
    conflict_detected: int = 0
    conflict_resolved: int = 0

    # 경로 효율성
    total_planned_distance_m: float = 0.0
    total_actual_distance_m: float = 0.0
    routes_completed: int = 0
    routes_total: int = 0

    # 배터리
    battery_depleted_count: int = 0
    avg_battery_remaining_pct: float = 100.0

    # 타이밍
    avg_clearance_time_s: float = 0.0
    emergency_response_times_s: list[float] = field(default_factory=list)

    # 기록용
    trajectory_log: list[dict] = field(default_factory=list)
    event_log: list[dict] = field(default_factory=list)

    # ── KPI 계산 ──────────────────────────────────────────────

    @property
    def conflict_resolution_rate(self) -> float:
        if self.conflict_detected == 0:
            return 1.0
        return self.conflict_resolved / self.conflict_detected

    @property
    def route_efficiency(self) -> float:
        if self.total_planned_distance_m < 1.0:
            return 1.0
        return self.total_actual_distance_m / self.total_planned_distance_m

    @property
    def emergency_response_p50_s(self) -> float:
        if not self.emergency_response_times_s:
            return 0.0
        return float(np.percentile(self.emergency_response_times_s, 50))

    @property
    def emergency_response_p99_s(self) -> float:
        if not self.emergency_response_times_s:
            return 0.0
        return float(np.percentile(self.emergency_response_times_s, 99))

    def record_event(self, time_s: float, event_type: str, **kwargs):
        self.event_log.append({"t": time_s, "type": event_type, **kwargs})
        if event_type == "collision":
            self.collision_count += 1
        elif event_type == "near_miss":
            self.near_miss_count += 1
        elif event_type == "conflict_detected":
            self.conflict_detected += 1
        elif event_type == "conflict_resolved":
            self.conflict_resolved += 1

    def record_trajectory(self, time_s: float, drone_id: str,
                          position: np.ndarray, velocity: np.ndarray,
                          battery_pct: float, phase: str):
        self.trajectory_log.append({
            "t": time_s,
            "drone_id": drone_id,
            "x": float(position[0]),
            "y": float(position[1]),
            "z": float(position[2]),
            "vx": float(velocity[0]),
            "vy": float(velocity[1]),
            "vz": float(velocity[2]),
            "battery_pct": battery_pct,
            "phase": phase,
        })

    def summary_dict(self) -> dict:
        return {
            "collision_count": self.collision_count,
            "near_miss_count": self.near_miss_count,
            "conflict_resolution_rate": f"{self.conflict_resolution_rate:.1%}",
            "route_efficiency": f"{self.route_efficiency:.3f}",
            "routes_completed": f"{self.routes_completed}/{self.routes_total}",
            "battery_depleted": self.battery_depleted_count,
            "avg_battery_remaining": f"{self.avg_battery_remaining_pct:.1f}%",
            "emergency_p50_s": f"{self.emergency_response_p50_s:.2f}",
            "emergency_p99_s": f"{self.emergency_response_p99_s:.2f}",
        }

    def summary_table(self) -> str:
        lines = ["┌─────────────────────────────────┬───────────────┐",
                 "│ KPI                             │ Value         │",
                 "├─────────────────────────────────┼───────────────┤"]
        for k, v in self.summary_dict().items():
            lines.append(f"│ {k:<31} │ {str(v):>13} │")
        lines.append("└─────────────────────────────────┴───────────────┘")
        return "\n".join(lines)


def check_sla(metrics: SimulationMetrics, thresholds: dict) -> dict[str, bool]:
    """SLA 기준 통과 여부 판정"""
    results = {}
    if "collision_rate_per_1000h" in thresholds:
        results["zero_collision"] = metrics.collision_count == 0
    if "conflict_resolution_rate_pct" in thresholds:
        results["conflict_resolution"] = (
            metrics.conflict_resolution_rate * 100
            >= thresholds["conflict_resolution_rate_pct"]
        )
    if "route_efficiency_max" in thresholds:
        results["route_efficiency"] = (
            metrics.route_efficiency <= thresholds["route_efficiency_max"]
        )
    if "emergency_response_p50_s" in thresholds:
        results["emergency_p50"] = (
            metrics.emergency_response_p50_s
            <= thresholds["emergency_response_p50_s"]
        )
    return results
