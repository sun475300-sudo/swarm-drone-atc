"""드론 에이전트 (SimPy 10 Hz 프로세스).

SDACS Layer 1 — 드론 1기의 물리/상태 머신 처리.

이 모듈은 simulation/simulator.py의 _DroneAgent 클래스를 분리한 것이다.
SwarmSimulator(Layer 3)에서 import하여 사용한다.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
import simpy

from simulation.apf_engine.apf import APFState
from src.airspace_control.agents.drone_profiles import DRONE_PROFILES
from src.airspace_control.agents.drone_state import (
    CommsStatus,
    DroneState,
    FailureType,
    FlightPhase,
)
from src.airspace_control.comms.communication_bus import CommMessage, CommunicationBus
from src.airspace_control.comms.message_types import (
    ClearanceResponse,
    ResolutionAdvisory,
    TelemetryMessage,
)

if TYPE_CHECKING:
    from simulation.simulator import SwarmSimulator

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# 공유 유틸리티
# ─────────────────────────────────────────────────────────────


def _drone_to_apf(d: DroneState) -> APFState:
    return APFState(
        position=d.position.copy(),
        velocity=d.velocity.copy(),
        drone_id=d.drone_id,
    )


def _estimate_power_w(
    speed_ms: float,
    profile,
    altitude_m: float = 60.0,
    headwind_ms: float = 0.0,
    climb_rate_ms: float = 0.0,
) -> float:
    """정밀 동력 모델 (W)

    - 호버 기본 소모 (배터리 용량 / 체공 시간)
    - 공기 저항: 속도² 비례
    - 고도 보정: 공기 밀도 저하 → 효율 감소 (1% / 100m)
    - 역풍 보정: 실효 속도 증가분만큼 추가 소모
    - 상승/하강: 상승 시 추가 에너지, 하강 시 미세 회수
    """
    endurance_s = profile.endurance_min * 60.0
    p_hover = profile.battery_wh * 3600.0 / endurance_s if endurance_s > 0 else 0.0

    effective_speed = max(0.0, speed_ms + headwind_ms * 0.5)
    p_drag = 0.5 * effective_speed**2

    alt_factor = 1.0 + altitude_m * 0.00012

    if climb_rate_ms > 0:
        p_climb = climb_rate_ms * 25.0
    else:
        p_climb = climb_rate_ms * 5.0

    return max(0.0, (p_hover + p_drag) * alt_factor + p_climb)


def _clamp_speed(vel: np.ndarray, max_spd: float, wind_speed: float = 0.0) -> np.ndarray:
    """속도 클램핑 (강풍 조건에서 비상 속도 모드 활성화).

    강풍(>10 m/s) 시 바람 속도보다 최소 5 m/s 빠르게 비행할 수 있도록 보장.
    """
    effective_max_spd = max(max_spd, wind_speed + 5.0) if wind_speed > 10.0 else max_spd
    spd = float(np.linalg.norm(vel))
    if spd > effective_max_spd:
        return vel / spd * effective_max_spd
    return vel


# ─────────────────────────────────────────────────────────────
# 드론 에이전트 (SimPy 프로세스)
# ─────────────────────────────────────────────────────────────


class DroneAgent:
    """드론 1기를 담당하는 SimPy 프로세스 래퍼 (Layer 1, 10 Hz).

    ``sim``은 ``SwarmSimulator`` 인스턴스를 받는다. 순환 import를 피하기 위해
    타입 힌트에만 TYPE_CHECKING 가드를 사용하고, 런타임에는 duck-typing으로 접근한다.
    """

    CRUISE_ALT = 60.0
    TAKEOFF_RATE = 3.5
    LAND_RATE = 2.5
    WAYPOINT_TOL = 80.0
    BATTERY_TICK_INTERVAL = 5
    BATTERY_CRITICAL_PCT = 5.0
    TELEMETRY_INTERVAL = 5
    EMERGENCY_WIND_SPEED = 10.0

    def __init__(
        self,
        env: simpy.Environment,
        drone: DroneState,
        sim: "SwarmSimulator",
        dt: float,
    ) -> None:
        self.env = env
        self.drone = drone
        self.sim = sim
        self.dt = dt

        sim.comm_bus.subscribe(drone.drone_id, self._on_message)

    def _on_message(self, msg: CommMessage) -> None:
        payload = msg.payload
        drone = self.drone

        if isinstance(payload, ResolutionAdvisory):
            if drone.flight_phase in (FlightPhase.ENROUTE, FlightPhase.HOLDING, FlightPhase.EVADING):
                t_now = float(self.env.now)
                if payload.advisory_type in ("EVADE_APF", "CLIMB", "DESCEND", "TURN_LEFT", "TURN_RIGHT"):
                    drone.flight_phase = FlightPhase.EVADING
                    new_end = t_now + float(getattr(payload, "duration_s", 10.0))
                    if drone.evade_end_s is None or new_end > drone.evade_end_s:
                        drone.evade_end_s = new_end
                elif payload.advisory_type == "HOLD":
                    drone.flight_phase = FlightPhase.HOLDING
                    drone.hold_start_s = None
                    drone.evade_end_s = None

        elif isinstance(payload, ClearanceResponse):
            if payload.approved and payload.assigned_waypoints:
                drone.waypoints = [np.array(wp) for wp in payload.assigned_waypoints]
                drone.current_waypoint_idx = 0

    def run(self):
        drone = self.drone
        sim = self.sim
        dt = self.dt
        profile = DRONE_PROFILES.get(drone.profile_name, DRONE_PROFILES["COMMERCIAL_DELIVERY"])

        while True:
            yield self.env.timeout(dt)
            t = float(self.env.now)

            # 1. 배터리 (2Hz: 매 5틱마다 계산)
            tick_count = int(round(t / dt))
            if tick_count % 5 == 0 and drone.flight_phase not in (FlightPhase.GROUNDED, FlightPhase.FAILED):
                dt_bat = dt * 5
                alt = float(drone.position[2]) if len(drone.position) > 2 else 60.0
                climb_rate = float(drone.velocity[2]) if len(drone.velocity) > 2 else 0.0
                headwind = 0.0
                if hasattr(sim, "_wind_cache") and drone.speed > 0.1:
                    wind_v = sim._wind_cache
                    move_dir = drone.velocity / max(drone.speed, 0.1)
                    headwind = -float(np.dot(wind_v, move_dir))
                pw = _estimate_power_w(
                    drone.speed,
                    profile,
                    altitude_m=alt,
                    headwind_ms=headwind,
                    climb_rate_ms=climb_rate,
                )
                drone.battery_pct -= (pw * dt_bat) / (profile.battery_wh * 3600.0) * 100.0
                drone.battery_pct = max(0.0, drone.battery_pct)
                if drone.battery_pct < 5.0 and drone.failure_type == FailureType.NONE:
                    drone.failure_type = FailureType.BATTERY_CRITICAL
                    drone.flight_phase = FlightPhase.LANDING

            # 2. 통신 상태 → Lost-link 처리
            self._handle_comms(drone, t, profile)

            # 3. 고장 처리
            self._handle_failure(drone, t)

            # 4. 바람 (tick 캐시: 동일 tick에서 재계산 방지)
            cache_key = round(t, 1)
            if not hasattr(sim, "_wind_cache") or sim._wind_cache_tick != cache_key:
                sim._wind_cache = sum(
                    (m.get_wind_vector(np.zeros(3), t) for m in sim.wind_models),
                    np.zeros(3),
                )
                sim._wind_cache_tick = cache_key
            wind = sim._wind_cache.copy()
            wind_speed = float(np.linalg.norm(wind))

            # 5. APF (EVADING/RTL 모드)
            if drone.flight_phase in (FlightPhase.EVADING, FlightPhase.RTL):
                force = sim.apf_forces.get(drone.drone_id, np.zeros(3))
            else:
                force = np.zeros(3)

            # 6. 비행 단계 상태 머신
            self._state_machine(drone, dt, profile, force, wind, t, sim)

            # 7. 위치 적분
            if drone.flight_phase not in (
                FlightPhase.GROUNDED,
                FlightPhase.FAILED,
                FlightPhase.TAKEOFF,
                FlightPhase.LANDING,
            ):
                if drone.flight_phase in (FlightPhase.EVADING, FlightPhase.RTL):
                    drone.velocity += force * dt
                drone.velocity[:2] += wind[:2]
                if drone.flight_phase == FlightPhase.EVADING and wind_speed > 10.0:
                    drone.velocity = _clamp_speed(drone.velocity, profile.max_speed_ms, wind_speed)
                else:
                    drone.velocity = _clamp_speed(drone.velocity, profile.max_speed_ms)
                drone.position += drone.velocity * dt
                drone.position[0] = float(np.clip(drone.position[0], -sim.bounds_m, sim.bounds_m))
                drone.position[1] = float(np.clip(drone.position[1], -sim.bounds_m, sim.bounds_m))
                drone.position[2] = float(np.clip(drone.position[2], 0.0, 120.0))
                drone.distance_flown_m += float(np.linalg.norm(drone.velocity * dt))

                geofence_margin = sim.bounds_m * 0.9
                if abs(drone.position[0]) > geofence_margin or abs(drone.position[1]) > geofence_margin:
                    if drone.flight_phase in (FlightPhase.ENROUTE, FlightPhase.EVADING):
                        drone.flight_phase = FlightPhase.RTL
                        drone.goal = None

            if drone.flight_phase not in (FlightPhase.GROUNDED, FlightPhase.FAILED):
                drone.flight_time_s += dt
            drone.last_update_s = t

            sim.comm_bus.update_position(drone.drone_id, drone.position.copy())

            # 8. 텔레메트리 송신 (5틱마다 ≈ 0.5s)
            tick = int(round(t / dt))
            if tick % 5 == 0:
                from src.airspace_control.comms.message_types import TelemetryMessage
                sim.comm_bus.send(
                    CommMessage(
                        sender_id=drone.drone_id,
                        receiver_id="CONTROLLER",
                        payload=TelemetryMessage(
                            drone_id=drone.drone_id,
                            position=drone.position.tolist(),
                            velocity=drone.velocity.tolist(),
                            battery_pct=drone.battery_pct,
                            flight_phase=drone.flight_phase.name,
                            timestamp_s=t,
                            is_registered=(drone.profile_name != "ROGUE"),
                        ),
                        sent_time=t,
                        channel="telemetry",
                    )
                )

            # 9. 분석 스냅샷
            if drone.flight_phase == FlightPhase.EVADING or getattr(sim, "_debug_snapshot", False):
                sim.analytics.record_snapshot({drone.drone_id: drone}, t)

    # ── 상태 머신 ──────────────────────────────────────────────

    def _state_machine(self, drone, dt, profile, force, wind, t, sim):
        phase = drone.flight_phase

        if phase == FlightPhase.GROUNDED:
            if drone.battery_pct > 20.0 and sim.rng.random() < 0.012:
                drone.flight_phase = FlightPhase.TAKEOFF
                sim._request_clearance(drone, t)

        elif phase == FlightPhase.TAKEOFF:
            if drone.position[2] < self.CRUISE_ALT - 2.0:
                drone.velocity = np.array([0.0, 0.0, self.TAKEOFF_RATE])
                drone.position[2] += self.TAKEOFF_RATE * dt
            else:
                drone.position[2] = self.CRUISE_ALT
                drone.velocity = np.zeros(3)
                drone.flight_phase = FlightPhase.ENROUTE

        elif phase == FlightPhase.ENROUTE:
            if drone.goal is None:
                if sim.analytics:
                    sim.analytics.record_event("ENROUTE_NO_GOAL_LANDING", t, drone_id=drone.drone_id)
                drone.flight_phase = FlightPhase.LANDING
                return
            target = drone.goal
            if drone.waypoints and drone.current_waypoint_idx < len(drone.waypoints):
                wp = drone.waypoints[drone.current_waypoint_idx]
                if not isinstance(wp, np.ndarray):
                    wp = np.array(wp, dtype=float)
                wp_dist = float(np.linalg.norm(wp[:2] - drone.position[:2]))
                if wp_dist < self.WAYPOINT_TOL:
                    drone.current_waypoint_idx += 1
                    if drone.current_waypoint_idx >= len(drone.waypoints):
                        target = drone.goal
                    else:
                        target = np.array(drone.waypoints[drone.current_waypoint_idx], dtype=float)
                else:
                    target = wp
            diff = target - drone.position
            dist_xy = float(np.linalg.norm(diff[:2]))
            if dist_xy < self.WAYPOINT_TOL:
                drone.flight_phase = FlightPhase.LANDING
                return
            spd = profile.cruise_speed_ms
            norm = np.linalg.norm(diff) + 1e-6
            drone.velocity = diff / norm * spd
            drone.velocity[2] = (self.CRUISE_ALT - drone.position[2]) * 0.4

        elif phase == FlightPhase.EVADING:
            should_exit = False
            if drone.evade_end_s is not None and t >= drone.evade_end_s:
                should_exit = True
                drone.evade_end_s = None
            elif sim.rng.random() < 0.03:
                should_exit = True
            if should_exit:
                drone.flight_phase = FlightPhase.LANDING if drone.goal is None else FlightPhase.ENROUTE

        elif phase == FlightPhase.HOLDING:
            drone.velocity = np.zeros(3)
            if drone.hold_start_s is None:
                drone.hold_start_s = t
            if t > drone.hold_start_s + 5.0:
                drone.hold_start_s = None
                drone.flight_phase = FlightPhase.ENROUTE

        elif phase == FlightPhase.LANDING:
            if drone.position[2] > 1.5:
                drone.velocity = np.array([0.0, 0.0, -self.LAND_RATE])
                drone.position[2] -= self.LAND_RATE * dt
            else:
                drone.position[2] = 0.0
                drone.velocity = np.zeros(3)
                drone.flight_phase = FlightPhase.GROUNDED
                drone.failure_type = FailureType.NONE
                drone.battery_pct = min(100.0, drone.battery_pct + 40.0)
                sim._assign_goal(drone)
                sim.analytics.record_planned_distance(drone.drone_id, drone.planned_distance_m)

        elif phase == FlightPhase.FAILED:
            if drone.position[2] > 0.0:
                drone.position[2] = max(0.0, drone.position[2] - 1.5 * dt)
                drone.velocity = np.zeros(3)
            else:
                drone.position[2] = 0.0
                drone.velocity = np.zeros(3)
                drone.flight_phase = FlightPhase.GROUNDED

        elif phase == FlightPhase.RTL:
            rtl_alt = 80.0
            if drone.position[2] < rtl_alt - 2.0:
                drone.velocity = np.array([0.0, 0.0, self.TAKEOFF_RATE])
            else:
                drone.position[2] = rtl_alt
                pads = list(sim.landing_pads.values())
                home = min(pads, key=lambda p: float(np.linalg.norm(p[:2] - drone.position[:2])))
                diff = home - drone.position
                if float(np.linalg.norm(diff[:2])) < 100.0:
                    drone.flight_phase = FlightPhase.LANDING
                else:
                    spd = profile.cruise_speed_ms
                    norm = np.linalg.norm(diff) + 1e-6
                    drone.velocity = diff / norm * spd

    def _handle_comms(self, drone, t, profile):
        if drone.comms_status == CommsStatus.LOST:
            if drone.flight_phase not in (
                FlightPhase.RTL,
                FlightPhase.LANDING,
                FlightPhase.FAILED,
                FlightPhase.GROUNDED,
                FlightPhase.HOLDING,
            ):
                drone.flight_phase = FlightPhase.HOLDING
                drone.hold_start_s = None

    def _handle_failure(self, drone, t):
        if drone.failure_type == FailureType.MOTOR_FAILURE:
            drone.flight_phase = FlightPhase.FAILED
        elif drone.failure_type == FailureType.GPS_LOSS:
            drone.velocity = np.zeros(3)


# 하위 호환 별칭 — 기존 코드가 _DroneAgent를 직접 import하는 경우를 위해
_DroneAgent = DroneAgent
