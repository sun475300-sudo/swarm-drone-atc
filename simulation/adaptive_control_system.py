"""Phase 298: Adaptive Control System — 적응형 제어 시스템.

PID 자동 튜닝, Model Reference Adaptive Control (MRAC),
풍속 적응, 페이로드 보정, 에이전트별 제어 프로파일.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class ControlMode(Enum):
    PID = "pid"
    MRAC = "mrac"
    FUZZY = "fuzzy"
    ROBUST = "robust"


@dataclass
class PIDGains:
    kp: float = 1.0
    ki: float = 0.1
    kd: float = 0.05
    integral_limit: float = 10.0


@dataclass
class ControlState:
    drone_id: str
    mode: ControlMode = ControlMode.PID
    gains: PIDGains = field(default_factory=PIDGains)
    error_integral: np.ndarray = field(default_factory=lambda: np.zeros(3))
    error_prev: np.ndarray = field(default_factory=lambda: np.zeros(3))
    reference: np.ndarray = field(default_factory=lambda: np.zeros(3))
    output: np.ndarray = field(default_factory=lambda: np.zeros(3))
    adaptation_rate: float = 0.01


class PIDController:
    """3D PID 제어기."""

    @staticmethod
    def compute(state: ControlState, current: np.ndarray, target: np.ndarray, dt: float = 0.1) -> np.ndarray:
        error = target - current
        state.error_integral += error * dt
        # Anti-windup
        mag = np.linalg.norm(state.error_integral)
        if mag > state.gains.integral_limit:
            state.error_integral = state.error_integral / mag * state.gains.integral_limit
        derivative = (error - state.error_prev) / max(dt, 1e-6)
        state.error_prev = error.copy()
        output = (state.gains.kp * error + state.gains.ki * state.error_integral + state.gains.kd * derivative)
        state.output = output
        return output


class MRACController:
    """모델 참조 적응 제어 (MRAC)."""

    @staticmethod
    def compute(state: ControlState, current: np.ndarray, target: np.ndarray, model_output: np.ndarray, dt: float = 0.1) -> np.ndarray:
        tracking_error = model_output - current
        # Adaptation law (MIT rule)
        state.gains.kp += state.adaptation_rate * np.dot(tracking_error, target - current) * dt
        state.gains.kp = np.clip(state.gains.kp, 0.1, 10.0)
        return PIDController.compute(state, current, target, dt)


class AutoTuner:
    """PID 자동 튜닝 (Ziegler-Nichols 방법)."""

    def __init__(self):
        self._oscillation_history: Dict[str, List[float]] = {}

    def record_response(self, drone_id: str, error: float):
        if drone_id not in self._oscillation_history:
            self._oscillation_history[drone_id] = []
        self._oscillation_history[drone_id].append(error)

    def compute_gains(self, drone_id: str, dt: float = 0.1) -> Optional[PIDGains]:
        history = self._oscillation_history.get(drone_id, [])
        if len(history) < 20:
            return None
        # Find oscillation period
        crossings = []
        for i in range(1, len(history)):
            if history[i - 1] * history[i] < 0:
                crossings.append(i)
        if len(crossings) < 2:
            return None
        avg_period = np.mean(np.diff(crossings)) * dt * 2
        ku = 4.0 / (np.pi * max(np.max(np.abs(history[-20:])), 0.01))  # Ultimate gain
        tu = avg_period
        # Ziegler-Nichols PID
        return PIDGains(kp=0.6 * ku, ki=1.2 * ku / max(tu, 0.01), kd=0.075 * ku * tu)


class AdaptiveControlSystem:
    """적응형 제어 시스템.

    - PID/MRAC 제어 모드
    - 자동 게인 튜닝
    - 풍속/페이로드 적응
    - 드론별 제어 프로파일 관리
    """

    def __init__(self, rng_seed: int = 42):
        self._rng = np.random.default_rng(rng_seed)
        self._states: Dict[str, ControlState] = {}
        self._tuner = AutoTuner()
        self._history: List[dict] = []
        self._wind_compensation: Dict[str, np.ndarray] = {}

    def register_drone(self, drone_id: str, mode: ControlMode = ControlMode.PID, gains: Optional[PIDGains] = None) -> ControlState:
        state = ControlState(drone_id=drone_id, mode=mode, gains=gains or PIDGains())
        self._states[drone_id] = state
        return state

    def compute_control(self, drone_id: str, current_pos: np.ndarray, target_pos: np.ndarray, dt: float = 0.1) -> np.ndarray:
        state = self._states.get(drone_id)
        if not state:
            return np.zeros(3)
        if state.mode == ControlMode.PID:
            output = PIDController.compute(state, current_pos, target_pos, dt)
        elif state.mode == ControlMode.MRAC:
            model_out = target_pos  # Simplified
            output = MRACController.compute(state, current_pos, target_pos, model_out, dt)
        else:
            output = PIDController.compute(state, current_pos, target_pos, dt)
        # Apply wind compensation
        wind_comp = self._wind_compensation.get(drone_id, np.zeros(3))
        output += wind_comp
        self._tuner.record_response(drone_id, float(np.linalg.norm(target_pos - current_pos)))
        return output

    def set_wind_compensation(self, drone_id: str, wind_vector: np.ndarray):
        self._wind_compensation[drone_id] = wind_vector * 0.3  # 30% feed-forward

    def auto_tune(self, drone_id: str, dt: float = 0.1) -> Optional[PIDGains]:
        gains = self._tuner.compute_gains(drone_id, dt)
        if gains:
            state = self._states.get(drone_id)
            if state:
                state.gains = gains
                self._history.append({"event": "auto_tune", "drone": drone_id, "kp": gains.kp, "ki": gains.ki, "kd": gains.kd})
        return gains

    def set_mode(self, drone_id: str, mode: ControlMode):
        state = self._states.get(drone_id)
        if state:
            state.mode = mode

    def get_state(self, drone_id: str) -> Optional[ControlState]:
        return self._states.get(drone_id)

    def get_tracking_error(self, drone_id: str) -> float:
        state = self._states.get(drone_id)
        if not state:
            return 0.0
        return float(np.linalg.norm(state.error_prev))

    def summary(self) -> dict:
        modes = {}
        avg_error = 0.0
        for s in self._states.values():
            modes[s.mode.value] = modes.get(s.mode.value, 0) + 1
            avg_error += np.linalg.norm(s.error_prev)
        avg_error /= max(len(self._states), 1)
        return {
            "total_drones": len(self._states),
            "control_modes": modes,
            "avg_tracking_error": round(float(avg_error), 4),
            "auto_tune_events": sum(1 for h in self._history if h["event"] == "auto_tune"),
            "wind_compensations": len(self._wind_compensation),
        }
