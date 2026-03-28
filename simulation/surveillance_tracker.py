"""
감시 추적기
==========
비협조 표적 추적 + 예측 궤적 + 요격 경로 계산.

사용법:
    st = SurveillanceTracker()
    st.track("target_1", (500, 500, 50), t=10.0)
    pred = st.predict("target_1", horizon_s=30.0)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class TrackRecord:
    """추적 기록"""
    t: float
    position: tuple[float, float, float]
    velocity: tuple[float, float, float] | None = None


@dataclass
class TrackPrediction:
    """궤적 예측"""
    target_id: str
    predicted_positions: list[tuple[float, float, float]]
    confidence: float
    speed_estimate: float
    heading_deg: float


class SurveillanceTracker:
    """비협조 표적 감시 추적."""

    def __init__(self, max_history: int = 200) -> None:
        self._tracks: dict[str, list[TrackRecord]] = {}
        self._max_history = max_history

    def track(
        self, target_id: str, position: tuple[float, float, float], t: float
    ) -> None:
        if target_id not in self._tracks:
            self._tracks[target_id] = []
        self._tracks[target_id].append(TrackRecord(t=t, position=position))
        if len(self._tracks[target_id]) > self._max_history:
            self._tracks[target_id] = self._tracks[target_id][-self._max_history:]

    def predict(
        self, target_id: str, horizon_s: float = 30.0, steps: int = 10
    ) -> TrackPrediction | None:
        records = self._tracks.get(target_id, [])
        if len(records) < 2:
            return None

        # 속도 추정 (최근 데이터)
        recent = records[-min(10, len(records)):]
        velocities = []
        for i in range(1, len(recent)):
            dt = recent[i].t - recent[i-1].t
            if dt > 0:
                dp = np.array(recent[i].position) - np.array(recent[i-1].position)
                velocities.append(dp / dt)

        if not velocities:
            return None

        avg_vel = np.mean(velocities, axis=0)
        speed = float(np.linalg.norm(avg_vel))
        heading = float(np.degrees(np.arctan2(avg_vel[1], avg_vel[0]))) % 360

        # 예측 위치
        last_pos = np.array(records[-1].position)
        predictions = []
        for i in range(1, steps + 1):
            dt = horizon_s * i / steps
            pred_pos = last_pos + avg_vel * dt
            predictions.append(tuple(pred_pos))

        # 신뢰도 (데이터 많을수록, 속도 안정적일수록 높음)
        data_factor = min(1.0, len(records) / 20)
        speed_std = float(np.std([np.linalg.norm(v) for v in velocities]))
        stability = max(0, 1.0 - speed_std / max(speed, 0.1))
        confidence = data_factor * stability * 0.9

        return TrackPrediction(
            target_id=target_id,
            predicted_positions=predictions,
            confidence=confidence,
            speed_estimate=speed,
            heading_deg=heading,
        )

    def intercept_point(
        self,
        target_id: str,
        interceptor_pos: tuple[float, float, float],
        interceptor_speed: float = 15.0,
    ) -> tuple[float, float, float] | None:
        """요격 지점 계산"""
        pred = self.predict(target_id, horizon_s=60, steps=60)
        if not pred:
            return None

        int_pos = np.array(interceptor_pos)
        for pos in pred.predicted_positions:
            dist = float(np.linalg.norm(np.array(pos) - int_pos))
            # 요격기가 도달 가능한 최초 지점
            time_to_reach = dist / max(interceptor_speed, 0.1)
            if time_to_reach < 60:  # 60초 내 가능
                return pos

        return None

    def active_tracks(self) -> list[str]:
        return list(self._tracks.keys())

    def last_position(self, target_id: str) -> tuple[float, float, float] | None:
        records = self._tracks.get(target_id, [])
        return records[-1].position if records else None

    def remove_track(self, target_id: str) -> None:
        self._tracks.pop(target_id, None)

    def summary(self) -> dict[str, Any]:
        return {
            "active_tracks": len(self._tracks),
            "total_records": sum(len(r) for r in self._tracks.values()),
        }
