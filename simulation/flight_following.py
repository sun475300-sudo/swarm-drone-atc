"""Phase 698: 비행 추적(Flight Following) 서비스."""

from __future__ import annotations

import math
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

    _DEFAULT_MAX_TRACKS = 10_000

    def __init__(
        self,
        comms_timeout_s: float = 60.0,
        deviation_tolerance_m: float = 500.0,
        max_points_per_track: int = _DEFAULT_TRACK_POINTS,
        max_tracks: int = _DEFAULT_MAX_TRACKS,
    ) -> None:
        if comms_timeout_s <= 0:
            raise ValueError("comms_timeout_s must be positive")
        if deviation_tolerance_m < 0:
            raise ValueError("deviation_tolerance_m must be non-negative")
        if max_points_per_track <= 0:
            raise ValueError("max_points_per_track must be positive")
        if max_tracks <= 0:
            raise ValueError("max_tracks must be positive")
        self.tracks: Dict[str, FlightTrack] = {}
        self.plans: Dict[str, List[Tuple[float, float, float]]] = {}
        self.comms_timeout_s = comms_timeout_s
        self.deviation_tolerance_m = deviation_tolerance_m
        self.max_points_per_track = max_points_per_track
        self.max_tracks = max_tracks

    def register_flight(
        self, callsign: str, plan_id: str, planned_waypoints: List[Tuple[float, float, float]]
    ) -> None:
        existing = self.tracks.get(callsign)
        if existing is not None and existing.state != TrackState.COMPLETED:
            raise ValueError(
                f"callsign {callsign!r} is already tracked "
                f"(state={existing.state.value!r}); call declare_completed() first"
            )
        track = FlightTrack(callsign=callsign, plan_id=plan_id)
        # deque(maxlen=) — O(1) append-and-drop-left, 수동 trim 불필요
        track.points = deque(maxlen=self.max_points_per_track)
        self.tracks[callsign] = track
        self.plans[callsign] = list(planned_waypoints)
        # max_tracks 초과 시 완료된 트랙 자동 정리
        if len(self.tracks) > self.max_tracks:
            self.purge_completed()
        # 제거 후에도 초과 중이면 가장 오래된 항목 강제 제거
        if len(self.tracks) > self.max_tracks:
            oldest = next(iter(self.tracks))
            self.plans.pop(oldest, None)
            del self.tracks[oldest]

    def report_position(
        self,
        callsign: str,
        position: Tuple[float, float, float],
        velocity: Tuple[float, float, float],
        fuel_pct: float,
    ) -> Dict[str, Any]:
        if not (0.0 <= fuel_pct <= 100.0):
            raise ValueError(f"fuel_pct must be in [0.0, 100.0], got {fuel_pct}")
        if len(position) != 3:
            raise ValueError(
                f"position must be a 3-element (lat, lon, alt) tuple, got {len(position)} elements"
            )
        if not all(math.isfinite(v) for v in position):
            raise ValueError(f"position components must be finite, got {position}")
        if len(velocity) != 3:
            raise ValueError(
                f"velocity must be a 3-element tuple, got {len(velocity)} elements"
            )
        if not all(math.isfinite(v) for v in velocity):
            raise ValueError(f"velocity components must be finite, got {velocity}")
        track = self.tracks.get(callsign)
        if track is None:
            return {"ok": False, "reason": "not_registered"}
        if track.state == TrackState.COMPLETED:
            return {"ok": False, "reason": "flight_completed"}
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
            if track.last_contact == 0.0:  # 등록 후 한 번도 보고 없음 — 센티널
                continue
            if current_time - track.last_contact > self.comms_timeout_s:
                track.state = TrackState.LOST_COMMS
                lost.append(cs)
        return lost

    def declare_diversion(self, callsign: str) -> bool:
        t = self.tracks.get(callsign)
        if t is None or t.state == TrackState.COMPLETED:
            return False
        t.state = TrackState.DIVERTED
        return True

    def declare_hold(self, callsign: str) -> bool:
        t = self.tracks.get(callsign)
        if t is None or t.state == TrackState.COMPLETED:
            return False
        t.state = TrackState.HOLDING
        return True

    def declare_completed(self, callsign: str) -> bool:
        t = self.tracks.get(callsign)
        if t is None:
            return False
        t.state = TrackState.COMPLETED
        return True

    def purge_completed(self) -> int:
        """COMPLETED 상태의 트랙과 계획을 제거해 메모리를 회수한다.

        max_tracks 초과 시 자동 호출되며, 수동으로도 호출 가능하다.
        반환값: 제거된 트랙 수.
        """
        done = [cs for cs, t in self.tracks.items() if t.state == TrackState.COMPLETED]
        for cs in done:
            del self.tracks[cs]
            self.plans.pop(cs, None)
        return len(done)

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
