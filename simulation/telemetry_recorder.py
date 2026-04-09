"""
텔레메트리 녹화기
=================
전체 시뮬레이션 상태 스냅샷 기록 + 리와인드 + 비교 재생.
시간 역추적 디버깅 + 두 시뮬레이션 결과 동기 비교.

사용법:
    rec = TelemetryRecorder()
    rec.record(t=10.0, drones={"d1": {...}, "d2": {...}})
    snapshot = rec.get_at(t=10.0)
    rec.rewind(t=5.0)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class TelemetrySnapshot:
    """텔레메트리 스냅샷"""
    t: float
    drone_states: dict[str, dict[str, Any]]
    global_metrics: dict[str, Any] = field(default_factory=dict)
    events: list[str] = field(default_factory=list)


class TelemetryRecorder:
    """
    텔레메트리 녹화기.

    시간 순 스냅샷 기록 + 시간 기반 조회 + 비교.
    """

    def __init__(self, max_snapshots: int = 10000) -> None:
        self._snapshots: list[TelemetrySnapshot] = []
        self._max = max_snapshots
        self._cursor: int = -1  # 현재 재생 커서

    def record(
        self,
        t: float,
        drone_states: dict[str, dict[str, Any]],
        global_metrics: dict[str, Any] | None = None,
        events: list[str] | None = None,
    ) -> None:
        """스냅샷 기록"""
        snap = TelemetrySnapshot(
            t=t,
            drone_states=dict(drone_states),
            global_metrics=global_metrics or {},
            events=events or [],
        )
        self._snapshots.append(snap)
        self._cursor = len(self._snapshots) - 1

        if len(self._snapshots) > self._max:
            self._snapshots = self._snapshots[-self._max:]
            self._cursor = len(self._snapshots) - 1

    def get_at(self, t: float) -> TelemetrySnapshot | None:
        """시각 t에 가장 가까운 스냅샷"""
        if not self._snapshots:
            return None

        # 이진 탐색
        idx = self._bisect(t)
        return self._snapshots[idx]

    def get_range(
        self, t_start: float, t_end: float
    ) -> list[TelemetrySnapshot]:
        """시간 범위 스냅샷"""
        return [s for s in self._snapshots if t_start <= s.t <= t_end]

    def rewind(self, t: float) -> TelemetrySnapshot | None:
        """시간 역추적"""
        snap = self.get_at(t)
        if snap:
            self._cursor = self._snapshots.index(snap)
        return snap

    def step_forward(self) -> TelemetrySnapshot | None:
        """다음 스냅샷"""
        if self._cursor < len(self._snapshots) - 1:
            self._cursor += 1
            return self._snapshots[self._cursor]
        return None

    def step_backward(self) -> TelemetrySnapshot | None:
        """이전 스냅샷"""
        if self._cursor > 0:
            self._cursor -= 1
            return self._snapshots[self._cursor]
        return None

    @property
    def current(self) -> TelemetrySnapshot | None:
        if 0 <= self._cursor < len(self._snapshots):
            return self._snapshots[self._cursor]
        return None

    def drone_trajectory(
        self, drone_id: str
    ) -> list[tuple[float, float, float, float]]:
        """드론의 시간별 위치 궤적 [(t, x, y, z), ...]"""
        trajectory = []
        for snap in self._snapshots:
            state = snap.drone_states.get(drone_id)
            if state and "position" in state:
                pos = state["position"]
                trajectory.append((snap.t, pos[0], pos[1], pos[2]))
        return trajectory

    def compare(
        self, other: TelemetryRecorder, t: float
    ) -> dict[str, Any]:
        """두 녹화의 동일 시점 비교"""
        snap_a = self.get_at(t)
        snap_b = other.get_at(t)

        if not snap_a or not snap_b:
            return {"error": "데이터 부족"}

        drones_a = set(snap_a.drone_states.keys())
        drones_b = set(snap_b.drone_states.keys())

        common = drones_a & drones_b
        position_diffs = {}
        for did in common:
            pos_a = snap_a.drone_states[did].get("position")
            pos_b = snap_b.drone_states[did].get("position")
            if pos_a and pos_b:
                diff = np.linalg.norm(
                    np.array(pos_a) - np.array(pos_b)
                )
                position_diffs[did] = float(diff)

        return {
            "t": t,
            "drones_a": len(drones_a),
            "drones_b": len(drones_b),
            "common_drones": len(common),
            "avg_position_diff": float(np.mean(list(position_diffs.values()))) if position_diffs else 0,
            "max_position_diff": max(position_diffs.values()) if position_diffs else 0,
        }

    @property
    def duration(self) -> float:
        if not self._snapshots:
            return 0.0
        return self._snapshots[-1].t - self._snapshots[0].t

    @property
    def snapshot_count(self) -> int:
        return len(self._snapshots)

    def _bisect(self, t: float) -> int:
        """이진 탐색으로 가장 가까운 인덱스"""
        lo, hi = 0, len(self._snapshots) - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if self._snapshots[mid].t < t:
                lo = mid + 1
            else:
                hi = mid
        return lo

    def summary(self) -> dict[str, Any]:
        return {
            "snapshots": self.snapshot_count,
            "duration_s": self.duration,
            "cursor": self._cursor,
            "t_start": self._snapshots[0].t if self._snapshots else 0,
            "t_end": self._snapshots[-1].t if self._snapshots else 0,
        }

    def clear(self) -> None:
        self._snapshots.clear()
        self._cursor = -1
