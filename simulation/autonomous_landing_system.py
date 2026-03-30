"""Phase 283: Autonomous Landing System — 자율 착륙 시스템.

정밀 착륙 시퀀스, 패드 관리, 접근 경로 최적화,
바람 보정 및 비상 착륙 프로토콜을 구현합니다.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class LandingPhase(Enum):
    APPROACH = "approach"
    ALIGNMENT = "alignment"
    DESCENT = "descent"
    TOUCHDOWN = "touchdown"
    LANDED = "landed"
    ABORTED = "aborted"


class PadStatus(Enum):
    AVAILABLE = "available"
    RESERVED = "reserved"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"


@dataclass
class LandingPad:
    pad_id: str
    position: np.ndarray
    status: PadStatus = PadStatus.AVAILABLE
    size_m: float = 3.0
    reserved_for: Optional[str] = None
    wind_exposure: float = 1.0  # 1.0 = fully exposed


@dataclass
class LandingSequence:
    drone_id: str
    pad_id: str
    phase: LandingPhase = LandingPhase.APPROACH
    approach_altitude: float = 30.0
    descent_rate: float = 1.5  # m/s
    wind_correction: np.ndarray = field(default_factory=lambda: np.zeros(3))
    elapsed_sec: float = 0.0
    is_emergency: bool = False


class DescentProfile:
    """착륙 하강 프로파일 생성기."""

    @staticmethod
    def standard_descent(start_alt: float, rate: float, dt: float = 0.1) -> List[float]:
        altitudes = []
        alt = start_alt
        while alt > 0:
            alt = max(0, alt - rate * dt)
            altitudes.append(alt)
        return altitudes

    @staticmethod
    def exponential_descent(start_alt: float, tau: float = 5.0, dt: float = 0.1) -> List[float]:
        altitudes = []
        alt = start_alt
        t = 0.0
        while alt > 0.1:
            t += dt
            alt = start_alt * np.exp(-t / tau)
            altitudes.append(max(0, alt))
        altitudes.append(0.0)
        return altitudes

    @staticmethod
    def wind_corrected_trajectory(
        start_pos: np.ndarray, pad_pos: np.ndarray, wind: np.ndarray, n_points: int = 50
    ) -> List[np.ndarray]:
        trajectory = []
        for i in range(n_points):
            t = i / (n_points - 1)
            pos = start_pos * (1 - t) + pad_pos * t
            # Wind correction increases as drone descends (lower altitude = more correction)
            correction = wind * (1 - t) * 0.5
            trajectory.append(pos - correction)
        return trajectory


class AutonomousLandingSystem:
    """자율 착륙 시스템.

    - 착륙 패드 관리 및 예약
    - 접근/정렬/하강/터치다운 시퀀스
    - 바람 보정 착륙 궤적
    - 비상 착륙 프로토콜
    """

    def __init__(self, rng_seed: int = 42):
        self._rng = np.random.default_rng(rng_seed)
        self._pads: Dict[str, LandingPad] = {}
        self._sequences: Dict[str, LandingSequence] = {}
        self._history: List[dict] = []
        self._profile = DescentProfile()

    def add_pad(self, pad: LandingPad):
        self._pads[pad.pad_id] = pad

    def reserve_pad(self, pad_id: str, drone_id: str) -> bool:
        pad = self._pads.get(pad_id)
        if not pad or pad.status != PadStatus.AVAILABLE:
            return False
        pad.status = PadStatus.RESERVED
        pad.reserved_for = drone_id
        return True

    def find_best_pad(self, drone_pos: np.ndarray, wind: Optional[np.ndarray] = None) -> Optional[str]:
        best_id, best_score = None, float("inf")
        for pad in self._pads.values():
            if pad.status != PadStatus.AVAILABLE:
                continue
            dist = np.linalg.norm(drone_pos[:3] - pad.position[:3])
            wind_penalty = pad.wind_exposure * 10.0 if wind is not None and np.linalg.norm(wind) > 5 else 0
            score = dist + wind_penalty
            if score < best_score:
                best_score = score
                best_id = pad.pad_id
        return best_id

    def initiate_landing(self, drone_id: str, pad_id: str, is_emergency: bool = False) -> Optional[LandingSequence]:
        pad = self._pads.get(pad_id)
        if not pad:
            return None
        if not is_emergency and pad.status not in (PadStatus.AVAILABLE, PadStatus.RESERVED):
            return None
        if pad.reserved_for and pad.reserved_for != drone_id and not is_emergency:
            return None
        pad.status = PadStatus.OCCUPIED
        pad.reserved_for = drone_id
        seq = LandingSequence(drone_id=drone_id, pad_id=pad_id, is_emergency=is_emergency)
        self._sequences[drone_id] = seq
        self._history.append({"event": "initiate", "drone": drone_id, "pad": pad_id, "emergency": is_emergency})
        return seq

    def advance_phase(self, drone_id: str) -> Optional[LandingPhase]:
        seq = self._sequences.get(drone_id)
        if not seq:
            return None
        phase_order = [LandingPhase.APPROACH, LandingPhase.ALIGNMENT, LandingPhase.DESCENT, LandingPhase.TOUCHDOWN, LandingPhase.LANDED]
        try:
            idx = phase_order.index(seq.phase)
            if idx < len(phase_order) - 1:
                seq.phase = phase_order[idx + 1]
                self._history.append({"event": "phase_advance", "drone": drone_id, "phase": seq.phase.value})
        except ValueError:
            pass
        return seq.phase

    def abort_landing(self, drone_id: str) -> bool:
        seq = self._sequences.get(drone_id)
        if not seq or seq.phase == LandingPhase.LANDED:
            return False
        seq.phase = LandingPhase.ABORTED
        pad = self._pads.get(seq.pad_id)
        if pad:
            pad.status = PadStatus.AVAILABLE
            pad.reserved_for = None
        self._history.append({"event": "abort", "drone": drone_id})
        return True

    def complete_landing(self, drone_id: str) -> bool:
        seq = self._sequences.get(drone_id)
        if not seq:
            return False
        seq.phase = LandingPhase.LANDED
        self._history.append({"event": "landed", "drone": drone_id, "pad": seq.pad_id})
        return True

    def release_pad(self, pad_id: str) -> bool:
        pad = self._pads.get(pad_id)
        if not pad:
            return False
        pad.status = PadStatus.AVAILABLE
        pad.reserved_for = None
        return True

    def get_descent_profile(self, drone_id: str) -> List[float]:
        seq = self._sequences.get(drone_id)
        if not seq:
            return []
        return self._profile.standard_descent(seq.approach_altitude, seq.descent_rate)

    def get_sequence(self, drone_id: str) -> Optional[LandingSequence]:
        return self._sequences.get(drone_id)

    def summary(self) -> dict:
        available = sum(1 for p in self._pads.values() if p.status == PadStatus.AVAILABLE)
        active = sum(1 for s in self._sequences.values() if s.phase not in (LandingPhase.LANDED, LandingPhase.ABORTED))
        return {
            "total_pads": len(self._pads),
            "available_pads": available,
            "active_landings": active,
            "total_landings": len(self._history),
        }
