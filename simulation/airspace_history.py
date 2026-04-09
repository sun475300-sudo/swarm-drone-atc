"""
공역 이력 관리
==============
공역 상태 이력 + 시간 쿼리 + 트렌드 비교.

사용법:
    ah = AirspaceHistory()
    ah.record(t=10.0, drone_count=50, conflicts=2, collisions=0)
    trend = ah.query(t_start=0, t_end=60)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class AirspaceSnapshot:
    """공역 상태 스냅샷"""
    t: float
    drone_count: int
    conflicts: int
    collisions: int
    avg_separation_m: float = 100.0
    congestion: float = 0.0
    active_advisories: int = 0


class AirspaceHistory:
    """공역 상태 이력 관리."""

    def __init__(self, max_records: int = 1000) -> None:
        self._records: list[AirspaceSnapshot] = []
        self._max = max_records

    def record(
        self, t: float, drone_count: int = 0,
        conflicts: int = 0, collisions: int = 0,
        avg_separation: float = 100.0, congestion: float = 0.0,
        advisories: int = 0,
    ) -> AirspaceSnapshot:
        snap = AirspaceSnapshot(
            t=t, drone_count=drone_count,
            conflicts=conflicts, collisions=collisions,
            avg_separation_m=avg_separation,
            congestion=congestion,
            active_advisories=advisories,
        )
        self._records.append(snap)
        if len(self._records) > self._max:
            self._records = self._records[-self._max:]
        return snap

    def query(
        self, t_start: float | None = None, t_end: float | None = None,
    ) -> list[AirspaceSnapshot]:
        result = self._records
        if t_start is not None:
            result = [r for r in result if r.t >= t_start]
        if t_end is not None:
            result = [r for r in result if r.t <= t_end]
        return result

    def latest(self) -> AirspaceSnapshot | None:
        return self._records[-1] if self._records else None

    def collision_rate(self, window_s: float = 60.0) -> float:
        """최근 윈도우의 충돌률"""
        if not self._records:
            return 0.0
        t_end = self._records[-1].t
        recent = [r for r in self._records if r.t >= t_end - window_s]
        total_conflicts = sum(r.conflicts + r.collisions for r in recent)
        total_collisions = sum(r.collisions for r in recent)
        if total_conflicts == 0:
            return 0.0
        return total_collisions / total_conflicts

    def avg_metric(self, metric: str, n: int = 20) -> float:
        recent = self._records[-n:]
        if not recent:
            return 0.0
        values = [getattr(r, metric, 0) for r in recent]
        return float(np.mean(values))

    def trend(self, metric: str, n: int = 20) -> str:
        """트렌드 방향"""
        recent = self._records[-n:]
        if len(recent) < 3:
            return "STABLE"
        values = [getattr(r, metric, 0) for r in recent]
        slope = np.polyfit(range(len(values)), values, 1)[0]
        if slope > 0.5:
            return "INCREASING"
        elif slope < -0.5:
            return "DECREASING"
        return "STABLE"

    def compare_periods(
        self, t_start_a: float, t_end_a: float,
        t_start_b: float, t_end_b: float,
    ) -> dict[str, dict[str, float]]:
        """두 기간 비교"""
        period_a = self.query(t_start_a, t_end_a)
        period_b = self.query(t_start_b, t_end_b)

        def avg(records: list[AirspaceSnapshot], attr: str) -> float:
            if not records:
                return 0.0
            return float(np.mean([getattr(r, attr, 0) for r in records]))

        metrics = ["drone_count", "conflicts", "collisions", "congestion"]
        result = {}
        for m in metrics:
            result[m] = {"period_a": avg(period_a, m), "period_b": avg(period_b, m)}
        return result

    def summary(self) -> dict[str, Any]:
        return {
            "total_records": len(self._records),
            "time_range": (self._records[0].t, self._records[-1].t) if self._records else (0, 0),
            "collision_rate": round(self.collision_rate(), 4),
            "avg_congestion": round(self.avg_metric("congestion"), 3),
        }
