"""Phase 301: Digital Twin Sync Engine — 디지털 트윈 동기화 엔진.

물리적 드론과 디지털 트윈 간 실시간 상태 동기화,
지연 보정, 상태 예측, 이벤트 스트림 관리.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
from collections import deque


class SyncMode(Enum):
    REAL_TIME = "real_time"
    BATCH = "batch"
    EVENT_DRIVEN = "event_driven"


class TwinStatus(Enum):
    SYNCED = "synced"
    LAGGING = "lagging"
    PREDICTED = "predicted"
    DISCONNECTED = "disconnected"


@dataclass
class TwinState:
    twin_id: str
    physical_state: dict = field(default_factory=dict)
    digital_state: dict = field(default_factory=dict)
    sync_timestamp: float = 0.0
    lag_ms: float = 0.0
    status: TwinStatus = TwinStatus.DISCONNECTED
    divergence: float = 0.0


@dataclass
class SyncEvent:
    event_id: str
    twin_id: str
    event_type: str  # "state_update", "command", "alert", "prediction"
    data: dict = field(default_factory=dict)
    timestamp: float = 0.0


class StatePredictor:
    """칼만 필터 기반 상태 예측기."""

    def __init__(self, dt: float = 0.1):
        self.dt = dt

    def predict(self, position: np.ndarray, velocity: np.ndarray, dt: float) -> np.ndarray:
        return position + velocity * dt

    def estimate_divergence(self, physical: dict, digital: dict) -> float:
        p_pos = np.array(physical.get("position", [0, 0, 0]), dtype=float)
        d_pos = np.array(digital.get("position", [0, 0, 0]), dtype=float)
        return float(np.linalg.norm(p_pos - d_pos))


class DigitalTwinSyncEngine:
    """디지털 트윈 동기화 엔진.

    - 물리/디지털 상태 페어링
    - 지연 보정 및 상태 예측
    - 이벤트 기반 동기화
    - 다이버전스 모니터링
    """

    MAX_LAG_MS = 500.0
    MAX_DIVERGENCE_M = 5.0

    def __init__(self, mode: SyncMode = SyncMode.REAL_TIME, rng_seed: int = 42):
        self._rng = np.random.default_rng(rng_seed)
        self.mode = mode
        self._twins: Dict[str, TwinState] = {}
        self._predictor = StatePredictor()
        self._event_log: List[SyncEvent] = []
        self._sync_count = 0
        self._event_counter = 0

    def register_twin(self, twin_id: str) -> TwinState:
        state = TwinState(twin_id=twin_id)
        self._twins[twin_id] = state
        return state

    def update_physical(self, twin_id: str, state: dict, timestamp: float = 0.0):
        twin = self._twins.get(twin_id)
        if not twin:
            return
        twin.physical_state = state.copy()
        twin.sync_timestamp = timestamp

    def update_digital(self, twin_id: str, state: dict, timestamp: float = 0.0):
        twin = self._twins.get(twin_id)
        if not twin:
            return
        twin.digital_state = state.copy()

    def sync(self, twin_id: str, current_time: float = 0.0) -> TwinStatus:
        twin = self._twins.get(twin_id)
        if not twin:
            return TwinStatus.DISCONNECTED

        self._sync_count += 1
        twin.lag_ms = (current_time - twin.sync_timestamp) * 1000.0
        twin.divergence = self._predictor.estimate_divergence(twin.physical_state, twin.digital_state)

        if twin.lag_ms > self.MAX_LAG_MS:
            twin.status = TwinStatus.DISCONNECTED
        elif twin.divergence > self.MAX_DIVERGENCE_M:
            twin.status = TwinStatus.LAGGING
            # Force sync
            twin.digital_state = twin.physical_state.copy()
        elif twin.lag_ms > 100:
            twin.status = TwinStatus.PREDICTED
            # Predict forward
            pos = np.array(twin.physical_state.get("position", [0, 0, 0]), dtype=float)
            vel = np.array(twin.physical_state.get("velocity", [0, 0, 0]), dtype=float)
            predicted = self._predictor.predict(pos, vel, twin.lag_ms / 1000.0)
            twin.digital_state["position"] = predicted.tolist()
        else:
            twin.status = TwinStatus.SYNCED
            twin.digital_state = twin.physical_state.copy()

        self._event_counter += 1
        self._event_log.append(SyncEvent(
            event_id=f"SYNC-{self._event_counter:06d}", twin_id=twin_id,
            event_type="state_update", data={"status": twin.status.value, "lag": twin.lag_ms},
            timestamp=current_time,
        ))
        return twin.status

    def sync_all(self, current_time: float = 0.0) -> Dict[str, TwinStatus]:
        return {tid: self.sync(tid, current_time) for tid in self._twins}

    def get_twin(self, twin_id: str) -> Optional[TwinState]:
        return self._twins.get(twin_id)

    def get_divergent_twins(self, threshold_m: float = 2.0) -> List[str]:
        return [tid for tid, t in self._twins.items() if t.divergence > threshold_m]

    def get_events(self, twin_id: Optional[str] = None, limit: int = 100) -> List[SyncEvent]:
        events = self._event_log
        if twin_id:
            events = [e for e in events if e.twin_id == twin_id]
        return events[-limit:]

    def summary(self) -> dict:
        status_counts = {}
        avg_lag = 0.0
        avg_div = 0.0
        for t in self._twins.values():
            status_counts[t.status.value] = status_counts.get(t.status.value, 0) + 1
            avg_lag += t.lag_ms
            avg_div += t.divergence
        n = max(len(self._twins), 1)
        return {
            "total_twins": len(self._twins),
            "sync_count": self._sync_count,
            "avg_lag_ms": round(avg_lag / n, 2),
            "avg_divergence_m": round(avg_div / n, 3),
            "status_counts": status_counts,
            "total_events": len(self._event_log),
        }
