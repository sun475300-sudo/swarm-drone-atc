"""
Digital Twin — 실제 드론 텔레메트리 ↔ 시뮬레이션 동기화

외부 텔레메트리 소스로부터 데이터를 수신하여
시뮬레이션 드론 상태를 실시간 동기화.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np


@dataclass
class TelemetrySnapshot:
    """외부 텔레메트리 스냅샷."""
    drone_id: str
    position: np.ndarray
    velocity: np.ndarray
    battery_pct: float
    timestamp: float
    source: str = "external"


class DigitalTwin:
    """시뮬레이션 ↔ 실세계 동기화 관리자."""

    def __init__(self, max_history: int = 100):
        self._snapshots: dict[str, TelemetrySnapshot] = {}
        self._history: dict[str, list[TelemetrySnapshot]] = {}
        self._max_history = max_history

    def update_from_telemetry(
        self, drone_id: str, position, velocity,
        battery_pct: float = 100.0, source: str = "external",
    ) -> TelemetrySnapshot:
        """외부 텔레메트리로 드론 상태 갱신."""
        snap = TelemetrySnapshot(
            drone_id=drone_id,
            position=np.array(position, dtype=float),
            velocity=np.array(velocity, dtype=float),
            battery_pct=battery_pct,
            timestamp=time.time(),
            source=source,
        )
        self._snapshots[drone_id] = snap
        hist = self._history.setdefault(drone_id, [])
        hist.append(snap)
        if len(hist) > self._max_history:
            del hist[: len(hist) - self._max_history]
        return snap

    def get_state(self, drone_id: str) -> TelemetrySnapshot | None:
        return self._snapshots.get(drone_id)

    def get_prediction(self, drone_id: str, lookahead_s: float = 30.0) -> dict:
        """선형 외삽 기반 미래 위치 예측."""
        snap = self._snapshots.get(drone_id)
        if snap is None:
            return {"error": f"drone {drone_id} not found"}
        predicted = snap.position + snap.velocity * lookahead_s
        return {
            "drone_id": drone_id,
            "current_position": snap.position.tolist(),
            "predicted_position": predicted.tolist(),
            "lookahead_s": lookahead_s,
            "speed_ms": float(np.linalg.norm(snap.velocity)),
            "staleness_s": time.time() - snap.timestamp,
        }

    def get_divergence(self, drone_id: str, sim_position: np.ndarray) -> float:
        """실세계 ↔ 시뮬레이션 위치 차이 (m)."""
        snap = self._snapshots.get(drone_id)
        if snap is None:
            return float("inf")
        return float(np.linalg.norm(snap.position - sim_position))

    def summary(self) -> dict:
        return {
            "tracked_drones": len(self._snapshots),
            "total_snapshots": sum(len(h) for h in self._history.values()),
        }
