"""Phase 698: 비행 추적(Flight Following) 서비스."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Tuple

import numpy as np


class TrackState(Enum):
    ENROUTE = "enroute"
    HOLDING = "holding"
    DIVERTED = "diverted"
    LOST_COMMS = "lost_comms"
    COMPLETED = "completed"


@dataclass
class TrackPoint:
    ts: float
    position: Tuple[float, float, float]
    velocity: Tuple[float, float, float]
    fuel_pct: float


_DEFAULT_TRACK_POINTS = 2_000


@dataclass
class FlightTrack:
    callsign: str
    plan_id: str
    # maxlen은 FlightFollowingService.register_flight()에서 재설정된다.
    # 직접 생성 시 기본값 _DEFAULT_TRACK_POINTS가 적용된다.
    points: Deque[TrackPoint] = field(
        default_factory=lambda: deque(maxlen=_DEFAULT_TRACK_POINTS)
    )
    state: TrackState = TrackState.ENROUTE
    last_contact: float = 0.0
    deviation_alerts: int = 0


class FlightFollowingService:
    """비행 계획 대비 실제 경로를 추적하고 이탈/통신두절을 감시."""

    def __init__(
        self,
        comms_timeout_s: float = 60.0,
        deviation_tolerance_m: float = 500.0,
        max_points_per_track: int = _DEFAULT_TRACK_POINTS,
    ) -> None:
        if max_points_per_track <= 0:
            raise ValueError("max_points_per_track must be positive")
        self.tracks: Dict[str, FlightTrack] = {}
        self.plans: Dict[str, List[Tuple[float, float, float]]] = {}
        self.comms_timeout_s = comms_timeout_s
        self.deviation_tolerance_m = deviation_tolerance_m
        self.max_points_per_track = max_points_per_track

    def register_flight(
        self, callsign: str, plan_id: str, planned_waypoints: List[Tuple[float, float, float]]
    ) -> None:
        track = FlightTrack(callsign=callsign, plan_id=plan_id)
        # deque(maxlen=) — O(1) append-and-drop-left, 수동 trim 불필요
        track.points = deque(maxlen=self.max_points_per_track)
        self.tracks[callsign] = track
        self.plans[callsign] = list(planned_waypoints)

    def report_position(
        self,
        callsign: str,
        position: Tuple[float, float, float],
        velocity: Tuple[float, float, float],
        fuel_pct: float,
    ) -> Dict[str, Any]:
        track = self.tracks.get(callsign)
        if track is None:
            return {"ok": False, "reason": "not_registered"}
        now = time.time()
        # deque(maxlen=max_points_per_track) 이 자동으로 오래된 항목 제거
        track.points.append(TrackPoint(ts=now, position=position, velocity=velocity, fuel_pct=fuel_pct))
        track.last_contact = now
        if track.state == TrackState.LOST_COMMS:
            track.state = TrackState.ENROUTE
        deviation = self._deviation(callsign, position)
        if deviation > self.deviation_tolerance_m:
            track.deviation_alerts += 1
        return {"ok": True, "deviation_m": deviation, "state": track.state.value}

    def _deviation(self, callsign: str, position: Tuple[float, float, float]) -> float:
        plan = self.plans.get(callsign, [])
        if len(plan) < 2:
            return 0.0
        best = float("inf")
        for a, b in zip(plan[:-1], plan[1:]):
            d = self._segment_3d_distance(a, b, position)
            if d < best:
                best = d
        return best

    @staticmethod
    def _segment_3d_distance(
        a: Tuple[float, float, float],
        b: Tuple[float, float, float],
        p: Tuple[float, float, float],
    ) -> float:
        av = np.asarray(a, dtype=float)
        bv = np.asarray(b, dtype=float)
        pv = np.asarray(p, dtype=float)
        d = bv - av
        denom = float(np.dot(d, d))
        if denom == 0:
            return float(np.linalg.norm(pv - av))
        t = max(0.0, min(1.0, float(np.dot(pv - av, d) / denom)))
        closest = av + t * d
        return float(np.linalg.norm(pv - closest))

    def sweep_lost_comms(self, current_time: Optional[float] = None) -> List[str]:
        current_time = current_time if current_time is not None else time.time()
        lost: List[str] = []
        for cs, track in self.tracks.items():
            if track.state in (TrackState.COMPLETED, TrackState.LOST_COMMS):
                continue
            if track.last_contact == 0:
                continue
            if current_time - track.last_contact > self.comms_timeout_s:
                track.state = TrackState.LOST_COMMS
                lost.append(cs)
        return lost

    def declare_diversion(self, callsign: str) -> bool:
        t = self.tracks.get(callsign)
        if t is None:
            return False
        t.state = TrackState.DIVERTED
        return True

    def declare_hold(self, callsign: str) -> bool:
        t = self.tracks.get(callsign)
        if t is None:
            return False
        t.state = TrackState.HOLDING
        return True

    def declare_completed(self, callsign: str) -> bool:
        t = self.tracks.get(callsign)
        if t is None:
            return False
        t.state = TrackState.COMPLETED
        return True

    def get_track(self, callsign: str) -> Optional[FlightTrack]:
        return self.tracks.get(callsign)

    def stats(self) -> Dict[str, Any]:
        counts: Dict[str, int] = {}
        total_points = 0
        for t in self.tracks.values():
            counts[t.state.value] = counts.get(t.state.value, 0) + 1
            total_points += len(t.points)
        return {
            "tracks": len(self.tracks),
            "by_state": counts,
            "total_track_points": total_points,
        }
