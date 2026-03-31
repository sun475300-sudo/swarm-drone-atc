"""
군집드론 공역통제 메인 시뮬레이터
==================================
SimPy 기반 이산 이벤트 시뮬레이션.

구성 요소:
  SwarmSimulator   — 최상위 오케스트레이터
  _DroneAgent      — 드론 1기의 10 Hz SimPy 프로세스

실행 예시:
  from simulation.simulator import SwarmSimulator
  sim = SwarmSimulator("config/default_simulation.yaml")
  result = sim.run()
  print(result.to_dict())
"""
from __future__ import annotations
import logging
import os
import sys
from typing import Any

logger = logging.getLogger(__name__)

import numpy as np
import simpy
import yaml

# 프로젝트 루트를 sys.path에 추가 (직접 실행 지원)
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from simulation.apf_engine.apf import (
    APFState, batch_compute_forces, force_to_velocity,
)
from simulation.weather import WindModel, build_wind_models
from simulation.analytics import SimulationAnalytics, SimulationResult
from src.airspace_control.agents.drone_state import (
    DroneState, FlightPhase, CommsStatus, FailureType,
)
from src.airspace_control.agents.drone_profiles import DRONE_PROFILES
from src.airspace_control.comms.communication_bus import CommunicationBus, CommMessage
from src.airspace_control.comms.message_types import (
    TelemetryMessage, ClearanceRequest, ClearanceResponse, ResolutionAdvisory,
)
from src.airspace_control.controller.priority_queue import FlightPriorityQueue
from src.airspace_control.planning.flight_path_planner import FlightPathPlanner
from src.airspace_control.avoidance.resolution_advisory import AdvisoryGenerator
from src.airspace_control.controller.airspace_controller import AirspaceController
from src.airspace_control.utils.geo_math import distance_3d
from simulation.spatial_hash import SpatialHash


# ─────────────────────────────────────────────────────────────
# 유틸리티
# ─────────────────────────────────────────────────────────────

def _load_yaml(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


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
    """
    정밀 동력 모델 (W)

    - 호버 기본 소모 (배터리 용량 / 체공 시간)
    - 공기 저항: 속도² 비례
    - 고도 보정: 공기 밀도 저하 → 효율 감소 (1% / 100m)
    - 역풍 보정: 실효 속도 증가분만큼 추가 소모
    - 상승/하강: 상승 시 추가 에너지, 하강 시 미세 회수
    """
    endurance_s = max(profile.endurance_min * 60.0, 1.0)
    p_hover = profile.battery_wh * 3600.0 / endurance_s

    # 공기 저항 (속도² 비례)
    effective_speed = max(0.0, speed_ms + headwind_ms * 0.5)
    p_drag = 0.5 * effective_speed ** 2

    # 고도 보정 (공기 밀도 저하: ~1.2% / 100m AGL)
    alt_factor = 1.0 + altitude_m * 0.00012

    # 상승/하강 (상승: +25W/m/s, 하강: -5W/m/s 회수)
    if climb_rate_ms > 0:
        p_climb = climb_rate_ms * 25.0
    else:
        p_climb = climb_rate_ms * 5.0  # 약간 회수 (음수)

    return max(0.0, (p_hover + p_drag) * alt_factor + p_climb)


# ─────────────────────────────────────────────────────────────
# 드론 에이전트 (SimPy 프로세스)
# ─────────────────────────────────────────────────────────────

class _DroneAgent:
    """드론 1기를 담당하는 SimPy 프로세스 래퍼"""

    CRUISE_ALT = 60.0           # 기본 순항 고도 (m)
    TAKEOFF_RATE = 3.5          # 상승 속도 (m/s)
    LAND_RATE    = 2.5          # 하강 속도 (m/s)
    WAYPOINT_TOL = 80.0         # 웨이포인트 도달 허용 오차 (m)
    BATTERY_TICK_INTERVAL = 5   # 배터리 계산 주기 (틱, 2Hz = 매 5틱)
    BATTERY_CRITICAL_PCT = 5.0  # 배터리 임계 잔량 (%)
    TELEMETRY_INTERVAL = 5      # 텔레메트리 전송 주기 (틱)
    EMERGENCY_WIND_SPEED = 10.0 # 비상 속도 모드 풍속 임계 (m/s)

    def __init__(
        self,
        env: simpy.Environment,
        drone: DroneState,
        sim: "SwarmSimulator",
        dt: float,
    ) -> None:
        self.env   = env
        self.drone = drone
        self.sim   = sim
        self.dt    = dt

        # CommunicationBus 메시지 수신 등록
        sim.comm_bus.subscribe(drone.drone_id, self._on_message)

    def _on_message(self, msg: CommMessage) -> None:
        """컨트롤러로부터 Advisory/Clearance 수신 처리"""
        payload = msg.payload
        drone = self.drone

        if isinstance(payload, ResolutionAdvisory):
            # 충돌 회피 어드바이저리 → EVADING 전환
            if drone.flight_phase in (FlightPhase.ENROUTE, FlightPhase.HOLDING, FlightPhase.EVADING):
                t_now = float(self.env.now)
                if payload.advisory_type in ("EVADE_APF", "CLIMB", "DESCEND",
                                              "TURN_LEFT", "TURN_RIGHT"):
                    drone.flight_phase = FlightPhase.EVADING
                    new_end = t_now + float(getattr(payload, 'duration_s', 10.0))
                    if drone.evade_end_s is None or new_end > drone.evade_end_s:
                        drone.evade_end_s = new_end
                elif payload.advisory_type == "HOLD":
                    drone.flight_phase = FlightPhase.HOLDING
                    drone.hold_start_s = None
                    drone.evade_end_s = None  # 잔류 EVADING 타이머 초기화

        elif isinstance(payload, ClearanceResponse):
            if payload.approved and payload.assigned_waypoints:
                drone.waypoints = [np.array(wp) for wp in payload.assigned_waypoints]
                drone.current_waypoint_idx = 0

    def run(self):
        drone   = self.drone
        sim     = self.sim
        dt      = self.dt
        profile = DRONE_PROFILES.get(drone.profile_name,
                                      DRONE_PROFILES["COMMERCIAL_DELIVERY"])

        while True:
            yield self.env.timeout(dt)
            t = float(self.env.now)

            # 1. 배터리 (2Hz: 매 BATTERY_TICK_INTERVAL틱마다 계산)
            tick_count = int(round(t / dt))
            if tick_count % self.BATTERY_TICK_INTERVAL == 0 and drone.flight_phase not in (FlightPhase.GROUNDED, FlightPhase.FAILED):
                dt_bat = dt * self.BATTERY_TICK_INTERVAL
                # 고도/풍향/상승률 기반 정밀 소모
                alt = float(drone.position[2]) if len(drone.position) > 2 else 60.0
                climb_rate = float(drone.velocity[2]) if len(drone.velocity) > 2 else 0.0
                # 역풍 추정: 바람 벡터와 이동 방향의 내적
                headwind = 0.0
                if hasattr(sim, '_wind_cache') and drone.speed > 0.1:
                    wind_v = sim._wind_cache
                    move_dir = drone.velocity / max(drone.speed, 0.1)
                    headwind = -float(np.dot(wind_v, move_dir))
                pw = _estimate_power_w(
                    drone.speed, profile,
                    altitude_m=alt, headwind_ms=headwind,
                    climb_rate_ms=climb_rate,
                )
                drone.battery_pct -= (pw * dt_bat) / (profile.battery_wh * 3600.0) * 100.0
                drone.battery_pct  = max(0.0, drone.battery_pct)
                if drone.battery_pct < self.BATTERY_CRITICAL_PCT and drone.failure_type == FailureType.NONE:
                    drone.failure_type = FailureType.BATTERY_CRITICAL
                    drone.flight_phase = FlightPhase.LANDING

            # 2. 통신 상태 → Lost-link 복귀
            self._handle_comms(drone, t, profile)

            # 3. 고장 처리
            self._handle_failure(drone, t)

            # 4. 바람 (tick 캐시: 동일 tick에서 재계산 방지)
            cache_key = int(round(t / dt))
            if not hasattr(sim, '_wind_cache') or sim._wind_cache_tick != cache_key:
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

            # 7. 위치 적분 (TAKEOFF/LANDING은 state_machine에서 직접 처리)
            if drone.flight_phase not in (FlightPhase.GROUNDED, FlightPhase.FAILED,
                                           FlightPhase.TAKEOFF, FlightPhase.LANDING):
                # APF force는 EVADING/RTL 상태일 때 적용
                if drone.flight_phase in (FlightPhase.EVADING, FlightPhase.RTL):
                    drone.velocity += force * dt
                # wind는 속도 벡터(m/s)로서 직접 가산 (force가 아니므로 dt 미적용)
                drone.velocity[:2] += wind[:2]
                # 비상 속도 모드: EVADING 모드이면서 강풍일 때만 활성화
                if drone.flight_phase == FlightPhase.EVADING and wind_speed > self.EMERGENCY_WIND_SPEED:
                    drone.velocity  = _clamp_speed(drone.velocity, profile.max_speed_ms, wind_speed)
                else:
                    drone.velocity  = _clamp_speed(drone.velocity, profile.max_speed_ms)
                drone.position += drone.velocity * dt
                drone.position[0] = float(np.clip(drone.position[0],
                                                   -sim.bounds_m, sim.bounds_m))
                drone.position[1] = float(np.clip(drone.position[1],
                                                   -sim.bounds_m, sim.bounds_m))
                drone.position[2] = float(np.clip(drone.position[2], 0.0, 120.0))
                drone.distance_flown_m += float(np.linalg.norm(drone.velocity * dt))

                # Geofence: 공역 경계 90% 도달 시 RTL 자동 전환
                geofence_margin = sim.bounds_m * 0.9
                if (abs(drone.position[0]) > geofence_margin or
                    abs(drone.position[1]) > geofence_margin):
                    if drone.flight_phase in (FlightPhase.ENROUTE, FlightPhase.EVADING):
                        drone.flight_phase = FlightPhase.RTL
                        drone.goal = None  # RTL에서 가장 가까운 패드로 재설정

            if drone.flight_phase not in (FlightPhase.GROUNDED, FlightPhase.FAILED):
                drone.flight_time_s += dt
            drone.last_update_s  = t

            # 통신 범위 계산용 위치 업데이트
            sim.comm_bus.update_position(drone.drone_id, drone.position.copy())

            # 8. 텔레메트리 송신 (TELEMETRY_INTERVAL틱마다 ≈ 0.5 s)
            tick = int(round(t / dt))
            if tick % self.TELEMETRY_INTERVAL == 0:
                sim.comm_bus.send(CommMessage(
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
                ))

            # 9. 분석 — EVADING 고주파 현상 추적용 조건부 스냅샷
            if drone.flight_phase == FlightPhase.EVADING or getattr(sim, '_debug_snapshot', False):
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
                drone.position[2]  = self.CRUISE_ALT
                drone.velocity     = np.zeros(3)
                drone.flight_phase = FlightPhase.ENROUTE

        elif phase == FlightPhase.ENROUTE:
            if drone.goal is None:
                if sim.analytics:
                    sim.analytics.record_event("ENROUTE_NO_GOAL_LANDING", t,
                                               drone_id=drone.drone_id)
                drone.flight_phase = FlightPhase.LANDING
                return
            # 웨이포인트 추종: 할당된 경로가 있으면 순차 비행
            target = drone.goal
            if drone.waypoints and drone.current_waypoint_idx < len(drone.waypoints):
                wp = drone.waypoints[drone.current_waypoint_idx]
                if not isinstance(wp, np.ndarray):
                    wp = np.array(wp, dtype=float)
                wp_dist = float(np.linalg.norm(wp[:2] - drone.position[:2]))
                if wp_dist < self.WAYPOINT_TOL:
                    drone.current_waypoint_idx += 1
                    if drone.current_waypoint_idx >= len(drone.waypoints):
                        target = drone.goal  # 마지막 웨이포인트 → 최종 목표
                    else:
                        target = np.array(drone.waypoints[drone.current_waypoint_idx], dtype=float)
                else:
                    target = wp

            diff    = target - drone.position
            dist_xy = float(np.linalg.norm(diff[:2]))
            if dist_xy < self.WAYPOINT_TOL:
                drone.flight_phase = FlightPhase.LANDING
                return
            spd      = profile.cruise_speed_ms
            norm     = np.linalg.norm(diff) + 1e-6
            drone.velocity = diff / norm * spd
            # 고도 유지
            drone.velocity[2] = (self.CRUISE_ALT - drone.position[2]) * 0.4

        elif phase == FlightPhase.EVADING:
            # APF 처리는 위에서 force로 전달됨 — 속도는 적분 단계에서 갱신
            # evade_end_s 타이머 만료 또는 확률적 전환
            should_exit = False
            if drone.evade_end_s is not None and t >= drone.evade_end_s:
                should_exit = True
                drone.evade_end_s = None
            elif sim.rng.random() < 0.03:
                should_exit = True

            if should_exit:
                # A2: goal=None 방어 — goal이 없으면 LANDING으로 안전하게 전환
                if drone.goal is None:
                    drone.flight_phase = FlightPhase.LANDING
                else:
                    drone.flight_phase = FlightPhase.ENROUTE

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
                drone.position[2]  = 0.0
                drone.velocity     = np.zeros(3)
                drone.flight_phase = FlightPhase.GROUNDED
                drone.failure_type = FailureType.NONE
                drone.battery_pct  = min(100.0, drone.battery_pct + 40.0)
                sim._assign_goal(drone)
                sim.analytics.record_planned_distance(
                    drone.drone_id, drone.planned_distance_m)

        elif phase == FlightPhase.FAILED:
            if drone.position[2] > 0.0:
                drone.position[2] = max(0.0, drone.position[2] - 1.5 * dt)
                drone.velocity     = np.zeros(3)
            else:
                drone.position[2]  = 0.0
                drone.velocity     = np.zeros(3)
                drone.flight_phase = FlightPhase.GROUNDED

        elif phase == FlightPhase.RTL:
            # 귀환: 80m 상승 → 가장 가까운 패드로
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
            if drone.flight_phase not in (FlightPhase.RTL, FlightPhase.LANDING,
                                           FlightPhase.FAILED, FlightPhase.GROUNDED,
                                           FlightPhase.HOLDING):
                # Lost-Link 3단계: HOLDING(30s) → CLIMB(RTL_ALT) → RTL
                drone.flight_phase = FlightPhase.HOLDING
                drone.hold_start_s = None  # 타이머 시작

    def _handle_failure(self, drone, t):
        if drone.failure_type == FailureType.MOTOR_FAILURE:
            drone.flight_phase = FlightPhase.FAILED
        elif drone.failure_type == FailureType.GPS_LOSS:
            drone.velocity = np.zeros(3)


def _clamp_speed(vel: np.ndarray, max_spd: float, wind_speed: float = 0.0) -> np.ndarray:
    """
    속도 클램핑 (강풍 조건에서 비상 속도 모드 활성화)

    Args:
        vel: 속도 벡터
        max_spd: 기본 최대 속도
        wind_speed: 현재 바람 속도 (m/s)

    Returns:
        클램핑된 속도 벡터
    """
    # 강풍 조건(10 m/s 이상)에서 비상 속도 모드
    # 바람 속도보다 최소 5 m/s 빠르게 비행할 수 있도록 보장
    if wind_speed > 10.0:
        effective_max_spd = max(max_spd, wind_speed + 5.0)
    else:
        effective_max_spd = max_spd

    spd = float(np.linalg.norm(vel))
    if spd > effective_max_spd:
        return vel / spd * effective_max_spd
    return vel


# ─────────────────────────────────────────────────────────────
# 메인 시뮬레이터
# ─────────────────────────────────────────────────────────────

class SwarmSimulator:
    """
    군집드론 공역통제 메인 시뮬레이터.

    Parameters
    ----------
    config_path:  default_simulation.yaml 경로
    scenario_cfg: 시나리오 오버라이드 dict (None이면 기본값 사용)
    seed:         재현성 시드
    """

    LANDING_PADS = {
        "PAD_NW":     np.array([-3000.0,  3000.0, 0.0]),
        "PAD_NE":     np.array([ 3000.0,  3000.0, 0.0]),
        "PAD_SW":     np.array([-3000.0, -3000.0, 0.0]),
        "PAD_SE":     np.array([ 3000.0, -3000.0, 0.0]),
        "PAD_CENTER": np.array([    0.0,     0.0, 0.0]),
    }
    NFZ = [{"center": np.array([0.0, 0.0, 60.0]), "radius_m": 600.0}]

    def __init__(
        self,
        config_path: str = "config/default_simulation.yaml",
        scenario_cfg: dict | None = None,
        seed: int = 42,
    ) -> None:
        self.seed     = seed
        self.rng      = np.random.default_rng(seed)

        # YAML 로드
        base_cfg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                     config_path)
        if not os.path.exists(base_cfg_path):
            base_cfg_path = config_path
        if not os.path.exists(base_cfg_path):
            logger.warning("Config file not found: %s — using defaults", base_cfg_path)
        self.cfg: dict = _load_yaml(base_cfg_path) if os.path.exists(base_cfg_path) else {}
        if scenario_cfg:
            self._deep_merge(self.cfg, scenario_cfg)

        # 공역 경계
        bounds_km    = self.cfg.get("airspace", {}).get("bounds_km", {})
        x_bounds     = bounds_km.get("x", [-5, 5])
        self.bounds_m = abs(float(x_bounds[1] if len(x_bounds) >= 2 else 5)) * 1000.0

        # SimPy
        self.env = simpy.Environment()

        # 서브시스템
        comms_cfg = self.cfg.get("drones", {})
        self.comm_bus = CommunicationBus(
            env=self.env,
            rng=self.rng,
            latency_ms_mean=20.0,
            packet_loss_rate=float(np.clip(
                float(self.cfg.get("comms_loss_rate", 0.0)), 0.0, 1.0)),
            comm_range_m=float(comms_cfg.get("comm_range_m", 2000.0)),
        )
        airspace_bounds = {
            "x": [-self.bounds_m, self.bounds_m],
            "y": [-self.bounds_m, self.bounds_m],
            "z": [0.0, 120.0],
        }
        self.planner = FlightPathPlanner(
            airspace_bounds=airspace_bounds,
            no_fly_zones=self.NFZ,
        )
        self.advisory_gen  = AdvisoryGenerator(
            separation_lateral_m=float(
                self.cfg.get("separation_standards", {}).get("lateral_min_m", 50.0)),
            separation_vertical_m=float(
                self.cfg.get("separation_standards", {}).get("vertical_min_m", 15.0)),
        )
        self.priority_queue = FlightPriorityQueue()
        self.analytics      = SimulationAnalytics(self.cfg)
        self.controller     = AirspaceController(
            env=self.env,
            comm_bus=self.comm_bus,
            planner=self.planner,
            advisory_gen=self.advisory_gen,
            priority_queue=self.priority_queue,
            config=self.cfg,
            analytics=self.analytics,
        )
        self.wind_models: list[WindModel] = build_wind_models(
            self.cfg.get("weather", {}), self.rng
        )
        self.landing_pads = self.LANDING_PADS

        # APF 힘 캐시 (배치 계산 → 각 드론 프로세스 참조)
        self.apf_forces: dict[str, np.ndarray] = {}

        # 고장 주입 설정
        fi = self.cfg.get("failure_injection", {})
        self._failure_rate: float = float(fi.get("drone_failure_rate", 0.0))
        self._comms_loss_rate: float = float(fi.get("comms_loss_rate", 0.0))
        self._failure_types_pool = [FailureType.MOTOR_FAILURE, FailureType.BATTERY_CRITICAL,
                                     FailureType.GPS_LOSS]

        # 드론 관리
        self._drones:  dict[str, DroneState]  = {}
        self._n_drones = int(self.cfg.get("drones", {}).get("default_count", 30))

        self._scenario_name = str(self.cfg.get("scenario", {}).get("name", "default"))

    # ── 공개 API ─────────────────────────────────────────────

    def run(self, duration_s: float | None = None) -> SimulationResult:
        dur = duration_s or float(
            self.cfg.get("simulation", {}).get("duration_minutes", 10)) * 60.0

        self._spawn_drones()
        self.env.process(self.controller.run())
        self.env.process(self._apf_batch_loop())
        self.env.process(self._analytics_loop())
        if self._failure_rate > 0 or self._comms_loss_rate > 0:
            self.env.process(self._failure_injection_loop())
        self.env.run(until=dur)

        # 컨트롤러/통신 통계 기록
        self.analytics.record_controller_stats(
            cbs_attempts=self.controller._cbs_attempts,
            cbs_successes=self.controller._cbs_successes,
            astar_count=self.controller._astar_count,
            clearances_per_sec=self.controller._clearances_per_sec,
        )
        comm_stats = self.comm_bus.stats
        self.analytics.record_comm_stats(
            sent=comm_stats["sent"],
            delivered=comm_stats["delivered"],
            dropped=comm_stats["dropped"],
        )

        return self.analytics.finalize(
            seed=self.seed,
            scenario=self._scenario_name,
            duration_s=dur,
            n_drones=self._n_drones,
        )

    # ── 드론 스폰 ────────────────────────────────────────────

    def _spawn_drones(self) -> None:
        dt = 1.0 / float(self.cfg.get("simulation", {}).get("time_step_hz", 10))
        profiles = ["COMMERCIAL_DELIVERY", "SURVEILLANCE", "EMERGENCY", "RECREATIONAL"]
        weights  = [0.55, 0.25, 0.10, 0.10]
        pad_list = list(self.LANDING_PADS.values())

        scenario_drones = self.cfg.get("scenario", {}).get("drones", {})
        n_rogue = int(scenario_drones.get("n_rogue", 0))

        for i in range(self._n_drones):
            pad   = pad_list[i % len(pad_list)].copy()
            jitter = self.rng.uniform(-300, 300, 3) * np.array([1, 1, 0])
            start  = pad + jitter
            start[2] = 0.0
            start[:2] = np.clip(start[:2], -self.bounds_m + 300, self.bounds_m - 300)

            profile = str(self.rng.choice(profiles, p=weights))
            if i < n_rogue:
                profile = "ROGUE"

            drone = DroneState(
                drone_id=f"DR{i:03d}",
                position=start.copy(),
                velocity=np.zeros(3),
                profile_name=profile,
                flight_phase=FlightPhase.GROUNDED,
                battery_pct=float(self.rng.uniform(70, 100)),
            )
            self._assign_goal(drone)
            self._drones[drone.drone_id] = drone

            agent = _DroneAgent(self.env, drone, self, dt)
            self.env.process(agent.run())

    def _assign_goal(self, drone: DroneState) -> None:
        pad_list = list(self.LANDING_PADS.values())
        goal     = pad_list[self.rng.integers(len(pad_list))].copy()
        for _ in range(10):
            if np.linalg.norm(goal[:2] - drone.position[:2]) > 1500:
                break
            goal = pad_list[self.rng.integers(len(pad_list))].copy()
        goal[2] = 60.0  # 순항 고도
        # NFZ 회피: 모든 NFZ에 대해 검증
        for nfz in self.NFZ:
            if np.linalg.norm(goal[:2] - nfz["center"][:2]) < nfz["radius_m"]:
                goal[0] += float(self.rng.choice([-900.0, 900.0]))
                break
        # 범위 클램핑
        goal[0] = float(np.clip(goal[0], -self.bounds_m + 200, self.bounds_m - 200))
        goal[1] = float(np.clip(goal[1], -self.bounds_m + 200, self.bounds_m - 200))
        drone.goal = goal
        drone.planned_distance_m = float(np.linalg.norm(goal - drone.position))
        self.analytics.record_planned_distance(drone.drone_id, drone.planned_distance_m)

    def _request_clearance(self, drone: DroneState, t: float) -> None:
        if drone.goal is None:
            return
        self.comm_bus.send(CommMessage(
            sender_id=drone.drone_id,
            receiver_id="CONTROLLER",
            payload=ClearanceRequest(
                drone_id=drone.drone_id,
                origin=drone.position.copy(),
                destination=drone.goal.copy(),
                priority=DRONE_PROFILES.get(drone.profile_name,
                                             DRONE_PROFILES["COMMERCIAL_DELIVERY"]).priority,
                timestamp_s=t,
                profile_name=drone.profile_name,
            ),
            sent_time=t,
            channel="clearance_req",
        ))

    # ── APF 배치 루프 ─────────────────────────────────────────

    def _apf_batch_loop(self):
        """10 Hz: EVADING/RTL 드론에 대해 APF 힘 배치 계산"""
        dt = 0.1
        nfz_centers = [n["center"] for n in self.NFZ]
        while True:
            yield self.env.timeout(dt)
            # L-3: RTL 드론도 APF 회피 대상에 포함
            evading = [d for d in self._drones.values()
                       if d.flight_phase in (FlightPhase.EVADING, FlightPhase.RTL)
                       and d.goal is not None]
            if evading:
                states = [_drone_to_apf(d) for d in evading]
                goals  = {d.drone_id: d.goal.copy() for d in evading}

                # 각 드론 위치의 바람 속도 계산 (강풍 조건 APF 파라미터 자동 선택용)
                wind_speeds = {}
                t = float(self.env.now)
                for d in evading:
                    # 모든 wind_models의 바람 벡터를 합산
                    wind_vec = np.zeros(3)
                    for wm in self.wind_models:
                        wind_vec += wm.get_wind_vector(d.position, t)
                    # 바람 속도 (m/s) 계산
                    wind_speeds[d.drone_id] = float(np.linalg.norm(wind_vec))

                # L-2 설계 결정: all_active에 TAKEOFF/LANDING 포함 (이웃 풀로 가시)
                # → 다른 드론이 이착륙 드론을 피하지만, 이착륙 드론 자체는 고정 수직 프로파일 유지
                all_active = [_drone_to_apf(d) for d in self._drones.values() if d.is_active]
                self.apf_forces = batch_compute_forces(states, goals, nfz_centers,
                                                      wind_speeds=wind_speeds,
                                                      neighbor_states=all_active)
            else:
                self.apf_forces = {}

    # ── 분석 루프 ─────────────────────────────────────────────

    def _failure_injection_loop(self):
        """5초 주기: 확률 기반 고장/통신 두절 자동 주입"""
        INJECT_INTERVAL_S = 5.0
        while True:
            yield self.env.timeout(INJECT_INTERVAL_S)
            t = float(self.env.now)

            for drone in self._drones.values():
                if not drone.is_active or drone.flight_phase in (
                    FlightPhase.GROUNDED, FlightPhase.FAILED, FlightPhase.LANDING
                ):
                    continue

                # 드론 고장 주입 (매 5초 간격 확률)
                if self._failure_rate > 0 and drone.failure_type == FailureType.NONE:
                    if self.rng.random() < self._failure_rate * INJECT_INTERVAL_S / 60.0:
                        failure = self.rng.choice(self._failure_types_pool)
                        drone.failure_type = failure
                        if failure == FailureType.MOTOR_FAILURE:
                            drone.flight_phase = FlightPhase.FAILED
                        elif failure == FailureType.BATTERY_CRITICAL:
                            drone.battery_pct = 3.0
                            drone.flight_phase = FlightPhase.LANDING
                        if self.analytics:
                            self.analytics.record_event(
                                "FAILURE_INJECTED", t,
                                drone_id=drone.drone_id,
                                failure_type=failure.name,
                            )

                # 통신 두절 주입
                if self._comms_loss_rate > 0 and drone.comms_status == CommsStatus.NOMINAL:
                    if self.rng.random() < self._comms_loss_rate * INJECT_INTERVAL_S / 60.0:
                        drone.comms_status = CommsStatus.LOST
                        if self.analytics:
                            self.analytics.record_event(
                                "COMMS_LOSS_INJECTED", t,
                                drone_id=drone.drone_id,
                            )

    def _analytics_loop(self):
        """1 Hz: 전체 드론 스냅샷 + 충돌 감지 (Spatial Hash 기반)"""
        sh = SpatialHash(cell_size=50.0)
        while True:
            yield self.env.timeout(1.0)
            t = float(self.env.now)
            self.analytics.record_snapshot(self._drones, t)

            # 컨트롤러에 현재 풍속 전달 → 동적 분리간격 조정
            if self.wind_models:
                avg_wind = np.zeros(3)
                for wm in self.wind_models:
                    avg_wind += wm.get_wind_vector(np.zeros(3), t)
                self.controller.update_wind_speed(float(np.linalg.norm(avg_wind)))

            # Spatial Hash로 충돌 감지 (5 m 이내) — O(N·k)
            # A1: LANDING 드론은 충돌 스캔에서 제외 (착지 중 수직 프로파일은 안전)
            sh.clear()
            for did, d in self._drones.items():
                if d.is_active and d.flight_phase != FlightPhase.LANDING:
                    sh.insert(did, d.position)

            for id_a, id_b, dist in sh.query_pairs_with_dist(5.0):
                self.analytics.record_event("COLLISION", t,
                                            drone_a=id_a, drone_b=id_b)

    # ── 유틸리티 ─────────────────────────────────────────────

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> None:
        for k, v in override.items():
            if k in base and isinstance(base[k], dict) and isinstance(v, dict):
                SwarmSimulator._deep_merge(base[k], v)
            else:
                base[k] = v


# ─────────────────────────────────────────────────────────────
# CLI 진입점
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse, json
    parser = argparse.ArgumentParser(description="군집드론 시뮬레이터")
    parser.add_argument("--config",   default="config/default_simulation.yaml")
    parser.add_argument("--duration", type=float, default=None, help="시뮬레이션 시간 (초)")
    parser.add_argument("--seed",     type=int,   default=42)
    parser.add_argument("--drones",   type=int,   default=None)
    args = parser.parse_args()

    override: dict = {}
    if args.drones:
        override = {"drones": {"default_count": args.drones}}

    sim    = SwarmSimulator(args.config, scenario_cfg=override or None, seed=args.seed)
    result = sim.run(args.duration)
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
