"""Phase 695: 전파 간섭·통신 단절 대비 Failsafe 로직 (RTL / Geofence)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

import numpy as np


class FailsafeLevel(Enum):
    """5단계 Failsafe 체인."""
    NORMAL = 0
    WARN = 1
    LAND = 2
    RTL = 3
    DISARM = 4
    EMERGENCY = 5


class FailsafeTrigger(Enum):
    """Failsafe 트리거 원인."""
    NONE = auto()
    COMM_LOSS = auto()
    LOW_BATTERY = auto()
    CRITICAL_BATTERY = auto()
    GEOFENCE_BREACH = auto()
    SENSOR_FAILURE = auto()
    MANUAL_OVERRIDE = auto()


@dataclass
class GeofenceZone:
    """비행 허용 구역 정의."""
    center_lat: float
    center_lon: float
    radius_m: float
    max_alt_m: float = 120.0
    min_alt_m: float = 0.0


@dataclass
class FailsafeState:
    """드론별 Failsafe 상태."""
    drone_id: str
    level: FailsafeLevel = FailsafeLevel.NORMAL
    trigger: FailsafeTrigger = FailsafeTrigger.NONE
    comm_loss_since: float | None = None
    last_comm: float = field(default_factory=time.time)
    escalation_count: int = 0
    rtl_initiated: bool = False
    home_position: tuple[float, float, float] = (35.1, 126.9, 0.0)
    triggered_at: float | None = None


COMM_LOSS_WARN_S = 2.0
COMM_LOSS_RTL_S = 5.0
COMM_LOSS_DISARM_S = 30.0
BATTERY_WARN_PCT = 25.0
BATTERY_LAND_PCT = 15.0
BATTERY_DISARM_PCT = 5.0

LEVEL_ACTION: dict[FailsafeLevel, str] = {
    FailsafeLevel.NORMAL: "continue_mission",
    FailsafeLevel.WARN: "alert_operator",
    FailsafeLevel.LAND: "land_in_place",
    FailsafeLevel.RTL: "return_to_launch",
    FailsafeLevel.DISARM: "force_disarm",
    FailsafeLevel.EMERGENCY: "emergency_stop",
}


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371_000.0
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = np.sin(dlat / 2) ** 2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon / 2) ** 2
    return R * 2 * np.arcsin(np.sqrt(a))


class FailsafeManager:
    """다중 기체 독립 Failsafe 상태 추적기."""

    def __init__(
        self,
        geofence: GeofenceZone | None = None,
        seed: int = 42,
    ) -> None:
        self.rng = np.random.default_rng(seed)
        self.geofence = geofence
        self._states: dict[str, FailsafeState] = {}
        self._action_log: list[dict[str, Any]] = []

    def register(
        self,
        drone_id: str,
        home_lat: float = 35.1,
        home_lon: float = 126.9,
        home_alt: float = 0.0,
    ) -> FailsafeState:
        state = FailsafeState(
            drone_id=drone_id,
            home_position=(home_lat, home_lon, home_alt),
        )
        self._states[drone_id] = state
        return state

    def heartbeat(self, drone_id: str) -> None:
        """통신 수신 확인 — 마지막 통신 시각 갱신."""
        if drone_id not in self._states:
            self.register(drone_id)
        state = self._states[drone_id]
        state.last_comm = time.time()
        state.comm_loss_since = None
        if state.level == FailsafeLevel.WARN and state.trigger == FailsafeTrigger.COMM_LOSS:
            state.level = FailsafeLevel.NORMAL
            state.trigger = FailsafeTrigger.NONE

    def update(
        self,
        drone_id: str,
        battery_pct: float,
        lat: float,
        lon: float,
        alt_m: float,
    ) -> FailsafeState:
        """상태 갱신 및 Failsafe 레벨 재평가."""
        if drone_id not in self._states:
            self.register(drone_id)
        state = self._states[drone_id]

        now = time.time()
        comm_age = now - state.last_comm

        if comm_age > COMM_LOSS_DISARM_S:
            self._transition(state, FailsafeLevel.DISARM, FailsafeTrigger.COMM_LOSS)
        elif comm_age > COMM_LOSS_RTL_S:
            self._transition(state, FailsafeLevel.RTL, FailsafeTrigger.COMM_LOSS)
            state.rtl_initiated = True
        elif comm_age > COMM_LOSS_WARN_S:
            if state.comm_loss_since is None:
                state.comm_loss_since = now
            self._transition(state, FailsafeLevel.WARN, FailsafeTrigger.COMM_LOSS)

        if battery_pct <= BATTERY_DISARM_PCT:
            self._transition(state, FailsafeLevel.DISARM, FailsafeTrigger.CRITICAL_BATTERY)
        elif battery_pct <= BATTERY_LAND_PCT:
            self._transition(state, FailsafeLevel.LAND, FailsafeTrigger.CRITICAL_BATTERY)
        elif battery_pct <= BATTERY_WARN_PCT:
            if state.level == FailsafeLevel.NORMAL:
                self._transition(state, FailsafeLevel.WARN, FailsafeTrigger.LOW_BATTERY)

        if self.geofence is not None:
            dist = _haversine_m(lat, lon, self.geofence.center_lat, self.geofence.center_lon)
            alt_ok = self.geofence.min_alt_m <= alt_m <= self.geofence.max_alt_m
            if dist > self.geofence.radius_m or not alt_ok:
                self._transition(state, FailsafeLevel.RTL, FailsafeTrigger.GEOFENCE_BREACH)

        return state

    def _transition(
        self,
        state: FailsafeState,
        new_level: FailsafeLevel,
        trigger: FailsafeTrigger,
    ) -> None:
        if new_level.value <= state.level.value:
            return
        state.level = new_level
        state.trigger = trigger
        state.triggered_at = time.time()
        state.escalation_count += 1
        self._action_log.append({
            "drone_id": state.drone_id,
            "level": new_level.name,
            "trigger": trigger.name,
            "action": LEVEL_ACTION[new_level],
            "timestamp": state.triggered_at,
        })

    def get_action(self, drone_id: str) -> str:
        state = self._states.get(drone_id)
        if state is None:
            return LEVEL_ACTION[FailsafeLevel.NORMAL]
        return LEVEL_ACTION[state.level]

    def get_all_states(self) -> dict[str, dict[str, Any]]:
        return {
            did: {
                "level": s.level.name,
                "trigger": s.trigger.name,
                "action": LEVEL_ACTION[s.level],
                "rtl_initiated": s.rtl_initiated,
                "escalations": s.escalation_count,
            }
            for did, s in self._states.items()
        }

    def action_log(self) -> list[dict[str, Any]]:
        return list(self._action_log)
