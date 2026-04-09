"""
군집드론 공역통제 자동화 시스템 — 3D 실시간 시각화 시뮬레이터
=============================================================
실행:  python visualization/simulator_3d.py
브라우저: http://localhost:8050

기능:
  - APF 기반 충돌 회피 실시간 시뮬레이션
  - Plotly Dash 3D 인터랙티브 뷰포트
  - 비행 단계별 드론 색상 구분
  - NFZ / 회랑 / 착륙 패드 3D 렌더링
  - 드론 궤적 트레일
  - 실시간 통계 패널 (충돌 경보, 어드바이저리)
  - 바람 효과 토글
"""

from __future__ import annotations
import sys
import os
import threading
import time
import math

import numpy as np

# 프로젝트 루트를 Python 경로에 추가
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import dash
from dash import dcc, html, Input, Output, State, callback_context
import plotly.graph_objects as go

from simulation.apf_engine.apf import (
    APFState, batch_compute_forces, force_to_velocity, APF_PARAMS,
    compute_total_force,
)
from src.airspace_control.agents.drone_state import (
    DroneState, FlightPhase, CommsStatus, FailureType,
)
from src.airspace_control.agents.drone_profiles import DRONE_PROFILES
from visualization.metrics_stream import MetricsCollector
from simulation.threat_assessment import ThreatAssessmentEngine, ThreatLevel
from simulation.multi_controller import MultiControllerManager
from simulation.sla_monitor import SLAMonitor
from simulation.event_timeline import EventTimeline

# ─────────────────────────────────────────────────────────────
# 공역 상수
# ─────────────────────────────────────────────────────────────
BOUNDS_M   = 5000.0   # ±5 km
ALT_MAX    = 120.0    # m AGL
ALT_MIN    = 30.0     # m AGL
CRUISE_ALT = 60.0     # 기본 순항 고도

# NFZ — 중심 1 km × 1 km 박스
NFZ_X = (-500.0, 500.0)
NFZ_Y = (-500.0, 500.0)
NFZ_Z = (0.0, 120.0)

# 착륙 패드 (x, y, z=0)
LANDING_PADS: dict[str, np.ndarray] = {
    "PAD_NW":     np.array([-3000.0,  3000.0, 0.0]),
    "PAD_NE":     np.array([ 3000.0,  3000.0, 0.0]),
    "PAD_SW":     np.array([-3000.0, -3000.0, 0.0]),
    "PAD_SE":     np.array([ 3000.0, -3000.0, 0.0]),
    "PAD_CENTER": np.array([    0.0,     0.0, 0.0]),
}
_PAD_LIST = list(LANDING_PADS.values())

# 회랑 웨이포인트 (m 단위)
CORRIDOR_EW = [np.array([x * 1000, 0.0, 60.0]) for x in (-5, -2.5, 0, 2.5, 5)]
CORRIDOR_NS = [np.array([0.0, y * 1000, 80.0]) for y in (-5, -2.5, 0, 2.5, 5)]

# 비행 단계별 색상
PHASE_COLORS: dict[FlightPhase, str] = {
    FlightPhase.GROUNDED: "#606060",
    FlightPhase.TAKEOFF:  "#FFD700",
    FlightPhase.ENROUTE:  "#00E676",
    FlightPhase.HOLDING:  "#29B6F6",
    FlightPhase.LANDING:  "#FF9800",
    FlightPhase.FAILED:   "#F44336",
    FlightPhase.RTL:      "#EC407A",
    FlightPhase.EVADING:  "#FF5722",
}

PHASE_KO: dict[FlightPhase, str] = {
    FlightPhase.GROUNDED: "지상 대기",
    FlightPhase.TAKEOFF:  "이륙",
    FlightPhase.ENROUTE:  "비행 중",
    FlightPhase.HOLDING:  "공중 대기",
    FlightPhase.LANDING:  "착륙",
    FlightPhase.FAILED:   "장애 발생",
    FlightPhase.RTL:      "귀환",
    FlightPhase.EVADING:  "회피 기동",
}

# 장애물 포인트 (NFZ 경계 샘플)
_NFZ_OBSTACLES: list[np.ndarray] = [
    np.array([  0.0,    0.0, CRUISE_ALT]),
    np.array([ 500.0,   0.0, CRUISE_ALT]),
    np.array([-500.0,   0.0, CRUISE_ALT]),
    np.array([  0.0,  500.0, CRUISE_ALT]),
    np.array([  0.0, -500.0, CRUISE_ALT]),
    np.array([ 400.0,  400.0, CRUISE_ALT]),
    np.array([-400.0,  400.0, CRUISE_ALT]),
    np.array([ 400.0, -400.0, CRUISE_ALT]),
    np.array([-400.0, -400.0, CRUISE_ALT]),
]


# ─────────────────────────────────────────────────────────────
# 시뮬레이션 상태
# ─────────────────────────────────────────────────────────────
class SimState:
    """스레드 공유 시뮬레이션 상태"""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.drones: dict[str, DroneState] = {}
        self.trails: dict[str, list[tuple]] = {}
        self.trail_len = 40

        self.t = 0.0
        self.dt = 0.1
        self.running = False

        self.wind = np.zeros(3)
        self.n_drones = 30
        self.speed_multiplier = 1.0  # 시뮬레이션 속도 배율 (0.25x ~ 5x)
        self.rng = np.random.default_rng(42)  # 재현성 보장 RNG
        self.show_apf_field = False  # APF 벡터 필드 표시 여부

        # 통계
        self.conflicts = 0
        self.near_misses = 0
        self.advisories = 0
        self.collisions = 0

        # 메트릭 수집기
        self.metrics = MetricsCollector(max_history=600)

        # 동적 NFZ 목록 (런타임 추가/제거)
        self.dynamic_nfzs: dict[str, dict] = {}  # id -> {x_range, y_range, z_range}

        # 위협 평가 엔진
        self.threat_engine = ThreatAssessmentEngine()
        self.threat_matrix: dict = {}

        # 다중 관제 구역
        self.sector_mgr = MultiControllerManager(bounds=BOUNDS_M, n_sectors=4)

        # SLA 모니터
        self.sla_monitor = SLAMonitor()
        self.sla_violations: list[dict] = []

        # 이벤트 타임라인
        self.timeline = EventTimeline()

        # 성능 모니터
        self.tick_times_ms: list[float] = []
        self.max_tick_history = 300

    def reset(self, n_drones: int | None = None) -> None:
        if n_drones is not None:
            self.n_drones = n_drones

        self.rng = np.random.default_rng(42)
        rng = self.rng
        profiles = ["COMMERCIAL_DELIVERY", "SURVEILLANCE", "EMERGENCY", "RECREATIONAL"]
        weights   = [0.55, 0.25, 0.10, 0.10]

        drones: dict[str, DroneState] = {}
        trails: dict[str, list] = {}

        for i in range(self.n_drones):
            pad = _PAD_LIST[i % len(_PAD_LIST)].copy()
            jitter = rng.uniform(-300, 300, 3) * np.array([1, 1, 0])
            start = (pad + jitter).copy()
            start[2] = 0.0
            start[0] = float(np.clip(start[0], -BOUNDS_M + 200, BOUNDS_M - 200))
            start[1] = float(np.clip(start[1], -BOUNDS_M + 200, BOUNDS_M - 200))

            # 반대편으로 목적지 배정
            goal_pad = _PAD_LIST[(i + len(_PAD_LIST) // 2) % len(_PAD_LIST)].copy()
            goal = goal_pad.copy()
            goal[2] = CRUISE_ALT
            # NFZ 통과 회피: 목적지를 NFZ 밖으로 조정
            if abs(goal[0]) < 700 and abs(goal[1]) < 700:
                goal[0] += float(rng.choice([-900.0, 900.0]))

            profile = str(rng.choice(profiles, p=weights))
            drone_id = f"DR{i:03d}"

            d = DroneState(
                drone_id=drone_id,
                position=start.copy(),
                velocity=np.zeros(3),
                profile_name=profile,
                flight_phase=FlightPhase.GROUNDED,
                battery_pct=float(rng.uniform(70, 100)),
            )
            d.goal = goal
            drones[drone_id] = d
            trails[drone_id] = []

        with self.lock:
            self.drones = drones
            self.trails = trails
            self.t = 0.0
            self.conflicts = 0
            self.near_misses = 0
            self.advisories = 0
            self.collisions = 0
            self.dynamic_nfzs = {}
            self.metrics.reset()
            self.threat_engine.clear()
            self.threat_matrix = {}
            self.sector_mgr = MultiControllerManager(bounds=BOUNDS_M, n_sectors=4)
            self.sla_monitor = SLAMonitor()
            self.sla_violations = []
            self.timeline = EventTimeline()
            self.tick_times_ms = []


# ─────────────────────────────────────────────────────────────
# 시뮬레이션 로직
# ─────────────────────────────────────────────────────────────
def _in_nfz(pos: np.ndarray) -> bool:
    return (NFZ_X[0] < pos[0] < NFZ_X[1]
            and NFZ_Y[0] < pos[1] < NFZ_Y[1])


def _assign_goal(drone: DroneState, rng: np.random.Generator | None = None) -> None:
    """착륙 후 새 목적지 무작위 배정"""
    rng = rng or np.random.default_rng()
    goal = _PAD_LIST[rng.integers(len(_PAD_LIST))].copy()
    for _ in range(10):
        if np.linalg.norm(goal[:2] - drone.position[:2]) > 1500:
            break
        goal = _PAD_LIST[rng.integers(len(_PAD_LIST))].copy()
    goal[2] = CRUISE_ALT
    if abs(goal[0]) < 700 and abs(goal[1]) < 700:
        goal[0] += float(rng.choice([-900.0, 900.0]))
    drone.goal = goal


def _step(sim: SimState) -> None:
    """시뮬레이션 틱 1회"""
    with sim.lock:
        drones = sim.drones
        dt = sim.dt

        # EVADING 드론에 대한 APF 배치 계산
        evading = [d for d in drones.values()
                   if d.flight_phase == FlightPhase.EVADING and d.goal is not None]
        if evading:
            apf_states = [APFState(d.position.copy(), d.velocity.copy(), d.drone_id)
                          for d in evading]
            goals_map  = {d.drone_id: d.goal.copy() for d in evading}
            forces = batch_compute_forces(apf_states, goals_map, _NFZ_OBSTACLES)
        else:
            forces = {}

        for drone in drones.values():
            _update(drone, forces, sim, dt)

        # 근접/충돌 감지 — SpatialHash O(N·k)
        if not hasattr(sim, '_spatial_hash'):
            from simulation.spatial_hash import SpatialHash
            sim._spatial_hash = SpatialHash(cell_size=50.0)
        if not hasattr(sim, '_active_conflict_pairs'):
            sim._active_conflict_pairs = set()

        sh = sim._spatial_hash
        sh.clear()
        for did, d in drones.items():
            if d.is_active:
                sh.insert(did, d.position)

        current_conflicts = set()
        for id_a, id_b, dist in sh.query_pairs_with_dist(50.0):
            pair = frozenset((id_a, id_b))
            if dist < 5.0:
                sim.collisions += 1
                drones[id_a].flight_phase = FlightPhase.FAILED
                drones[id_b].flight_phase = FlightPhase.FAILED
            elif dist < 10.0:
                if pair not in sim._active_conflict_pairs:
                    sim.near_misses += 1
                current_conflicts.add(pair)
            else:
                current_conflicts.add(pair)
                if pair not in sim._active_conflict_pairs:
                    sim.conflicts += 1
                    sim.advisories += 1
                    if drones[id_a].flight_phase == FlightPhase.ENROUTE:
                        drones[id_a].flight_phase = FlightPhase.EVADING
                    if drones[id_b].flight_phase == FlightPhase.ENROUTE:
                        drones[id_b].flight_phase = FlightPhase.EVADING
        sim._active_conflict_pairs = current_conflicts

        sim.t += dt

        # 틱 성능 기록
        import time as _time
        _tick_end = _time.perf_counter()
        if hasattr(sim, '_tick_start'):
            tick_ms = (_tick_end - sim._tick_start) * 1000
            sim.tick_times_ms.append(tick_ms)
            if len(sim.tick_times_ms) > sim.max_tick_history:
                sim.tick_times_ms = sim.tick_times_ms[-sim.max_tick_history:]
        sim._tick_start = _tick_end

        # 메트릭 수집 (매 1초 = 10틱)
        if int(sim.t * 10) % 10 == 0:
            sim.metrics.record(
                t=sim.t,
                drones=list(drones.values()),
                conflicts=sim.conflicts,
                collisions=sim.collisions,
                near_misses=sim.near_misses,
                advisories=sim.advisories,
                dt=dt,
            )

            # 위협 평가 (매 1초)
            evading_cnt = sum(1 for d in drones.values()
                              if d.flight_phase == FlightPhase.EVADING)
            failed_cnt = sum(1 for d in drones.values()
                             if d.flight_phase == FlightPhase.FAILED)
            low_bat_cnt = sum(1 for d in drones.values()
                              if d.battery_pct < 20 and d.is_active)
            wind_spd = float(np.linalg.norm(sim.wind[:2]))

            threats = sim.threat_engine.assess(
                collision_count=sim.collisions,
                near_miss_count=sim.near_misses,
                wind_speed=wind_spd,
                failure_count=failed_cnt,
                low_battery_count=low_bat_cnt,
                evading_count=evading_cnt,
            )
            sim.threat_matrix = sim.threat_engine.priority_matrix(threats)

            # 구역 업데이트
            for did, d in drones.items():
                if d.is_active:
                    sim.sector_mgr.update_drone_position(did, d.position)

            # SLA 체크
            active_cnt = sum(1 for d in drones.values() if d.is_active)
            cr_rate = 1.0 - (sim.collisions / max(sim.conflicts + sim.collisions, 1))
            violations = sim.sla_monitor.check(
                collision_rate=sim.collisions / max(active_cnt, 1),
                resolution_rate=cr_rate,
                near_miss_rate=sim.near_misses / max(active_cnt, 1),
            )
            if violations:
                sim.sla_violations = violations

            # 이벤트 타임라인 기록
            if sim.collisions > 0 and (not sim.timeline._events or
                    sim.timeline._events[-1].details.get("count") != sim.collisions):
                sim.timeline.add(
                    event_type="COLLISION",
                    t=sim.t,
                    severity="CRITICAL",
                    details={"count": sim.collisions},
                )
            if evading_cnt > 0:
                sim.timeline.add(
                    event_type="EVADING",
                    t=sim.t,
                    severity="HIGH" if evading_cnt >= 3 else "MEDIUM",
                    details={"count": evading_cnt},
                )


def _update(drone: DroneState, forces: dict, sim: SimState, dt: float) -> None:
    """드론 1기 상태 머신 업데이트"""
    profile = DRONE_PROFILES.get(drone.profile_name,
                                  DRONE_PROFILES["COMMERCIAL_DELIVERY"])

    # 배터리 소모 (비행 중)
    if drone.flight_phase not in (FlightPhase.GROUNDED, FlightPhase.FAILED):
        rate = 100.0 / (profile.endurance_min * 60.0 / dt)
        drone.battery_pct = max(0.0, drone.battery_pct - rate)
        if drone.battery_pct < 5.0 and drone.failure_type == FailureType.NONE:
            drone.failure_type = FailureType.BATTERY_CRITICAL
            drone.flight_phase = FlightPhase.LANDING

    phase = drone.flight_phase

    # ── 지상 대기
    if phase == FlightPhase.GROUNDED:
        if drone.battery_pct > 20.0 and sim.rng.random() < 0.015:
            drone.flight_phase = FlightPhase.TAKEOFF

    # ── 이륙
    elif phase == FlightPhase.TAKEOFF:
        if drone.position[2] < CRUISE_ALT - 2.0:
            drone.velocity = np.array([0.0, 0.0, 3.5])
            drone.position += drone.velocity * dt
        else:
            drone.position[2] = CRUISE_ALT
            drone.velocity    = np.zeros(3)
            drone.flight_phase = FlightPhase.ENROUTE

    # ── 비행
    elif phase == FlightPhase.ENROUTE:
        if drone.goal is None:
            drone.flight_phase = FlightPhase.LANDING
            return

        # NFZ 진입 직전 회피 전환
        lookahead = drone.position + drone.velocity * 3.0
        if _in_nfz(lookahead) or _in_nfz(drone.position):
            drone.flight_phase = FlightPhase.EVADING
            return

        diff = drone.goal - drone.position
        dist_xy = float(np.linalg.norm(diff[:2]))

        if dist_xy < 80.0:
            drone.flight_phase = FlightPhase.LANDING
        else:
            spd = profile.cruise_speed_ms
            norm = float(np.linalg.norm(diff))
            if norm < 0.1:
                drone.flight_phase = FlightPhase.LANDING
                return
            direction = diff / norm
            drone.velocity = direction * spd + sim.wind
            # 고도 유지
            drone.velocity[2] += (CRUISE_ALT - drone.position[2]) * 0.4
            drone.position += drone.velocity * dt
            drone.position[0] = float(np.clip(drone.position[0], -BOUNDS_M, BOUNDS_M))
            drone.position[1] = float(np.clip(drone.position[1], -BOUNDS_M, BOUNDS_M))
            drone.position[2] = float(np.clip(drone.position[2], ALT_MIN, ALT_MAX))
            drone.distance_flown_m += float(np.linalg.norm(drone.velocity[:2])) * dt
            if np.linalg.norm(drone.velocity[:2]) > 0.1:
                drone.heading = math.degrees(
                    math.atan2(float(drone.velocity[1]), float(drone.velocity[0]))
                )

    # ── APF 회피 기동
    elif phase == FlightPhase.EVADING:
        force = forces.get(drone.drone_id, np.zeros(3))
        drone.velocity = force_to_velocity(
            drone.velocity, force, dt, profile.max_speed_ms
        )
        drone.velocity += sim.wind
        drone.position += drone.velocity * dt
        drone.position[0] = float(np.clip(drone.position[0], -BOUNDS_M, BOUNDS_M))
        drone.position[1] = float(np.clip(drone.position[1], -BOUNDS_M, BOUNDS_M))
        drone.position[2] = float(np.clip(drone.position[2], ALT_MIN, ALT_MAX))
        drone.distance_flown_m += float(np.linalg.norm(drone.velocity[:2])) * dt

        # NFZ 밖이면 ENROUTE 복귀 (evade_end_s 타이머 또는 확률적 전환)
        should_exit = False
        if hasattr(drone, 'evade_end_s') and drone.evade_end_s is not None and sim.t >= drone.evade_end_s:
            should_exit = True
            drone.evade_end_s = None
        elif not _in_nfz(drone.position) and sim.rng.random() < 0.04 * dt * 10:
            should_exit = True

        if should_exit:
            if drone.goal is None:
                drone.flight_phase = FlightPhase.LANDING
            else:
                drone.flight_phase = FlightPhase.ENROUTE

    # ── 착륙
    elif phase == FlightPhase.LANDING:
        if drone.position[2] > 1.5:
            drone.velocity = np.array([0.0, 0.0, -2.5])
            drone.position += drone.velocity * dt
        else:
            drone.position[2] = 0.0
            drone.velocity    = np.zeros(3)
            drone.flight_phase = FlightPhase.GROUNDED
            drone.failure_type = FailureType.NONE
            # 배터리 부분 충전
            drone.battery_pct = min(100.0, drone.battery_pct + 40.0)
            _assign_goal(drone, sim.rng)

    # ── 공중 대기 (HOLDING) — Lost-Link Phase 1
    elif phase == FlightPhase.HOLDING:
        drone.velocity = np.zeros(3)
        # 5초 후 고도 상승(RTL 준비)으로 전이
        if not hasattr(drone, 'hold_start_s') or drone.hold_start_s is None:
            drone.hold_start_s = sim.t
        if sim.t > drone.hold_start_s + 5.0:
            drone.hold_start_s = None
            drone.flight_phase = FlightPhase.RTL

    # ── 귀환 (RTL)
    elif phase == FlightPhase.RTL:
        # 가장 가까운 착륙 패드로 귀환
        if drone.goal is None or drone.goal[2] > 0.1:
            nearest = min(_PAD_LIST, key=lambda p: float(np.linalg.norm(p[:2] - drone.position[:2])))
            drone.goal = nearest.copy()
            drone.goal[2] = 0.0

        diff = drone.goal - drone.position
        dist = float(np.linalg.norm(diff[:2]))
        if dist < 50.0:
            drone.flight_phase = FlightPhase.LANDING
        else:
            spd = profile.cruise_speed_ms * 0.7  # 감속 귀환
            norm = float(np.linalg.norm(diff))
            if norm < 0.1:
                drone.flight_phase = FlightPhase.LANDING
                return
            direction = diff / norm
            drone.velocity = direction * spd
            drone.position += drone.velocity * dt
            drone.position[0] = float(np.clip(drone.position[0], -BOUNDS_M, BOUNDS_M))
            drone.position[1] = float(np.clip(drone.position[1], -BOUNDS_M, BOUNDS_M))
            drone.position[2] = float(np.clip(drone.position[2], ALT_MIN, ALT_MAX))
            drone.distance_flown_m += float(np.linalg.norm(drone.velocity[:2])) * dt

    # ── 장애 발생
    elif phase == FlightPhase.FAILED:
        if drone.position[2] > 0.0:
            drone.position[2] = max(0.0, drone.position[2] - 1.5 * dt)

    drone.last_update_s = sim.t
    if drone.flight_phase not in (FlightPhase.GROUNDED, FlightPhase.FAILED):
        drone.flight_time_s += dt

    # 트레일 갱신
    trail = sim.trails.get(drone.drone_id, [])
    trail.append((float(drone.position[0]),
                  float(drone.position[1]),
                  float(drone.position[2])))
    if len(trail) > sim.trail_len:
        trail = trail[-sim.trail_len:]
    sim.trails[drone.drone_id] = trail


def _sim_loop(sim: SimState) -> None:
    """백그라운드 시뮬레이션 스레드 (20 Hz 기준, 속도 배율 적용)"""
    while True:
        if sim.running:
            spd = max(0.25, sim.speed_multiplier)
            for _ in range(max(1, int(spd))):
                _step(sim)
        time.sleep(0.05 / max(0.25, sim.speed_multiplier))


# ─────────────────────────────────────────────────────────────
# UI 헬퍼
# ─────────────────────────────────────────────────────────────
def _btn(label: str, color: str, **extra) -> dict:
    style: dict = {
        "backgroundColor": color,
        "color": "#ffffff",
        "border": "none",
        "borderRadius": "5px",
        "padding": "7px 12px",
        "cursor": "pointer",
        "fontSize": "12px",
        "fontWeight": "600",
        "letterSpacing": "0.5px",
    }
    style.update(extra)
    return style


def _legend_row(phase: FlightPhase) -> html.Div:
    return html.Div([
        html.Span(style={
            "display": "inline-block",
            "width": "11px", "height": "11px",
            "borderRadius": "50%",
            "backgroundColor": PHASE_COLORS[phase],
            "marginRight": "7px",
            "verticalAlign": "middle",
        }),
        html.Span(PHASE_KO[phase],
                  style={"color": "#c9d1d9", "fontSize": "11px",
                         "verticalAlign": "middle"}),
    ], style={"marginBottom": "5px"})


def _stat(label: str, value: str, warn: bool = False) -> html.Div:
    return html.Div([
        html.Span(label, style={"color": "#8b949e", "fontSize": "11px"}),
        html.Span(value, style={
            "color": "#FF4500" if warn else "#e6edf3",
            "fontSize": "11px",
            "fontWeight": "700",
            "float": "right",
        }),
    ], style={"marginBottom": "6px", "overflow": "hidden"})


# ─────────────────────────────────────────────────────────────
# 3D Figure 생성
# ─────────────────────────────────────────────────────────────
def _nfz_mesh() -> go.Mesh3d:
    """NFZ 반투명 박스"""
    x0, x1 = NFZ_X
    y0, y1 = NFZ_Y
    z0, z1 = NFZ_Z
    vx = [x0, x1, x1, x0, x0, x1, x1, x0]
    vy = [y0, y0, y1, y1, y0, y0, y1, y1]
    vz = [z0, z0, z0, z0, z1, z1, z1, z1]
    # 12개 삼각형 인덱스 (6면 × 2삼각형)
    ii = [0, 0,  4, 4,  0, 0,  2, 2,  0, 0,  1, 1]
    jj = [1, 2,  5, 6,  1, 5,  3, 7,  3, 7,  2, 6]
    kk = [2, 3,  6, 7,  5, 4,  7, 6,  7, 4,  6, 5]
    return go.Mesh3d(
        x=vx, y=vy, z=vz,
        i=ii, j=jj, k=kk,
        color="#FF1744",
        opacity=0.12,
        flatshading=True,
        name="비행금지구역",
        showlegend=True,
        hoverinfo="name",
        lighting=dict(ambient=0.8),
    )


def _nfz_edges() -> list[go.Scatter3d]:
    """NFZ 외곽선"""
    x0, x1 = NFZ_X
    y0, y1 = NFZ_Y
    traces = []
    for z in NFZ_Z:
        traces.append(go.Scatter3d(
            x=[x0, x1, x1, x0, x0],
            y=[y0, y0, y1, y1, y0],
            z=[z, z, z, z, z],
            mode="lines",
            line=dict(color="#FF5252", width=2, dash="dot"),
            showlegend=False, hoverinfo="skip",
        ))
    # 수직 모서리
    for cx, cy in [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]:
        traces.append(go.Scatter3d(
            x=[cx, cx], y=[cy, cy], z=list(NFZ_Z),
            mode="lines",
            line=dict(color="#FF5252", width=1, dash="dot"),
            showlegend=False, hoverinfo="skip",
        ))
    return traces


def _corridor_traces() -> list[go.Scatter3d]:
    """회랑 중심선"""
    def make(pts, color, name):
        return go.Scatter3d(
            x=[p[0] for p in pts],
            y=[p[1] for p in pts],
            z=[p[2] for p in pts],
            mode="lines",
            line=dict(color=color, width=5),
            opacity=0.55,
            name=name,
        )
    return [
        make(CORRIDOR_EW, "#448AFF", "동서 회랑 (60 m)"),
        make(CORRIDOR_NS, "#69F0AE", "남북 회랑 (80 m)"),
    ]


def _pad_trace() -> go.Scatter3d:
    pad_names = list(LANDING_PADS.keys())
    pads      = list(LANDING_PADS.values())
    return go.Scatter3d(
        x=[p[0] for p in pads],
        y=[p[1] for p in pads],
        z=[p[2] for p in pads],
        mode="markers+text",
        marker=dict(
            size=14, color="#FFD600", symbol="circle",
            opacity=1.0, line=dict(color="#ffffff", width=2),
        ),
        text=pad_names,
        textposition="top center",
        textfont=dict(color="#FFD600", size=9),
        name="착륙 패드",
        hovertemplate="%{text}<extra>착륙 패드</extra>",
    )


def _ground_grid() -> go.Scatter3d:
    """지면 그리드 (z=0 평면)"""
    lines_x, lines_y, lines_z = [], [], []
    step = 1000.0
    for v in np.arange(-BOUNDS_M, BOUNDS_M + step, step):
        lines_x += [v, v, None, -BOUNDS_M, BOUNDS_M, None]
        lines_y += [-BOUNDS_M, BOUNDS_M, None, v, v, None]
        lines_z += [0, 0, None, 0, 0, None]
    return go.Scatter3d(
        x=lines_x, y=lines_y, z=lines_z,
        mode="lines",
        line=dict(color="#1c2128", width=1),
        showlegend=False, hoverinfo="skip",
        opacity=0.6,
    )


def _apf_vector_field(drones: list[DroneState], wind: np.ndarray) -> list:
    """APF 벡터 필드를 그리드 포인트에서 Cone3d 트레이스로 렌더링"""
    active = [d for d in drones if d.is_active and d.flight_phase not in
              (FlightPhase.GROUNDED, FlightPhase.LANDING)]
    if not active:
        return []

    # 그리드: 공역을 1km 간격으로 샘플 (순항 고도)
    grid_step = 1000.0
    xs = np.arange(-BOUNDS_M + 500, BOUNDS_M, grid_step)
    ys = np.arange(-BOUNDS_M + 500, BOUNDS_M, grid_step)
    z_sample = CRUISE_ALT

    # 이웃 상태 준비
    neighbors = [
        APFState(d.position.copy(), d.velocity.copy(), d.drone_id)
        for d in active
    ]

    wind_speed = float(np.linalg.norm(wind[:2]))

    gx, gy, gz = [], [], []
    fu, fv, fw = [], [], []

    for xi in xs:
        for yi in ys:
            pos = np.array([xi, yi, z_sample])
            # 가상 프로브 드론
            probe = APFState(pos, np.zeros(3), "__probe__")
            # 가장 가까운 착륙 패드를 목표로 사용
            goal_pad = min(_PAD_LIST, key=lambda p: float(np.linalg.norm(p[:2] - pos[:2])))
            goal = goal_pad.copy()
            goal[2] = z_sample

            force = compute_total_force(
                probe, goal, neighbors, _NFZ_OBSTACLES,
                wind_speed=wind_speed,
            )
            mag = float(np.linalg.norm(force))
            if mag < 0.01:
                continue

            gx.append(xi)
            gy.append(yi)
            gz.append(z_sample)
            fu.append(float(force[0]))
            fv.append(float(force[1]))
            fw.append(float(force[2]))

    if not gx:
        return []

    # 크기 정규화 (시각적 일관성)
    mags = np.sqrt(np.array(fu)**2 + np.array(fv)**2 + np.array(fw)**2)
    max_mag = float(np.max(mags)) if len(mags) > 0 else 1.0

    return [go.Cone(
        x=gx, y=gy, z=gz,
        u=fu, v=fv, w=fw,
        sizemode="scaled",
        sizeref=max_mag * 2.0,
        anchor="tail",
        colorscale=[[0, "#1a237e"], [0.5, "#42A5F5"], [1, "#FF7043"]],
        cmin=0, cmax=max_mag,
        opacity=0.4,
        showscale=False,
        name="APF 벡터 필드",
        hovertemplate="Force: %{u:.1f}, %{v:.1f}, %{w:.1f}<extra>APF</extra>",
    )]


def _wind_arrow(wind: np.ndarray) -> list[go.Scatter3d]:
    """공역 우측 상단에 바람 방향 화살표 표시"""
    speed = float(np.linalg.norm(wind[:2]))
    if speed < 0.1:
        return []

    # 바람 화살표: 공역 좌측 상단에 고정 표시
    origin = np.array([-4000.0, 4000.0, ALT_MAX - 10])
    arrow_len = 800.0
    direction = wind[:3].copy()
    direction[2] = 0
    norm = float(np.linalg.norm(direction[:2]))
    if norm > 0:
        direction = direction / norm * arrow_len

    end = origin + direction
    return [go.Scatter3d(
        x=[float(origin[0]), float(end[0])],
        y=[float(origin[1]), float(end[1])],
        z=[float(origin[2]), float(end[2])],
        mode="lines+text",
        line=dict(color="#4FC3F7", width=6),
        text=[f"Wind {speed:.1f}m/s", ""],
        textposition="top center",
        textfont=dict(color="#4FC3F7", size=10),
        showlegend=False,
        hoverinfo="text",
        hovertext=f"바람: {speed:.1f} m/s",
    )]


def _sector_overlay(sim: SimState) -> list[go.Scatter3d]:
    """관제 구역 경계선 + 밀도 색상 3D 오버레이"""
    traces = []
    with sim.lock:
        stats = sim.sector_mgr.sector_stats()
        sectors = sim.sector_mgr.sectors

    for sid, sector in sectors.items():
        x0, x1 = sector.x_range
        y0, y1 = sector.y_range
        n_drones = stats[sid]["drones"]
        density = stats[sid]["density"]

        # 밀도 기반 색상 (초록→노랑→빨강)
        if density > 4.0:
            color = "#FF1744"
        elif density > 2.0:
            color = "#FF9100"
        elif density > 1.0:
            color = "#FFEA00"
        else:
            color = "#00E676"

        # 구역 경계선
        traces.append(go.Scatter3d(
            x=[x0, x1, x1, x0, x0],
            y=[y0, y0, y1, y1, y0],
            z=[2, 2, 2, 2, 2],  # 지면 약간 위
            mode="lines+text",
            line=dict(color=color, width=3),
            opacity=0.6,
            text=[f"{sid} ({n_drones})", "", "", "", ""],
            textposition="top center",
            textfont=dict(color=color, size=9),
            showlegend=False, hoverinfo="text",
            hovertext=f"{sid}: {n_drones}기, 밀도 {density:.1f}/km²",
        ))

    return traces


def _threat_heatmap_overlay(sim: SimState) -> list:
    """위협 레벨에 따른 공역 히트맵 오버레이"""
    with sim.lock:
        matrix = sim.threat_matrix.copy() if sim.threat_matrix else {}

    overall = matrix.get("overall_level", ThreatLevel.LOW)
    if overall == ThreatLevel.LOW:
        return []

    # 위협 레벨 → 공역 전체 틴트 (경계 박스)
    level_colors = {
        ThreatLevel.MEDIUM: "rgba(255,234,0,0.03)",
        ThreatLevel.HIGH: "rgba(255,152,0,0.05)",
        ThreatLevel.CRITICAL: "rgba(244,67,54,0.07)",
    }
    color = level_colors.get(overall, "rgba(0,0,0,0)")

    b = BOUNDS_M
    vx = [-b, b, b, -b, -b, b, b, -b]
    vy = [-b, -b, b, b, -b, -b, b, b]
    vz = [0, 0, 0, 0, ALT_MAX, ALT_MAX, ALT_MAX, ALT_MAX]
    ii = [0, 0, 4, 4, 0, 0, 2, 2, 0, 0, 1, 1]
    jj = [1, 2, 5, 6, 1, 5, 3, 7, 3, 7, 2, 6]
    kk = [2, 3, 6, 7, 5, 4, 7, 6, 7, 4, 6, 5]

    return [go.Mesh3d(
        x=vx, y=vy, z=vz,
        i=ii, j=jj, k=kk,
        color=color.replace("rgba", "rgb").rsplit(",", 1)[0] + ")",
        opacity=float(color.split(",")[-1].rstrip(")")),
        flatshading=True,
        showlegend=False,
        hoverinfo="skip",
    )]


def build_figure(sim: SimState) -> go.Figure:
    """3D 시각화 Figure 빌드"""
    with sim.lock:
        drones = list(sim.drones.values())
        trails = {k: list(v) for k, v in sim.trails.items()}
        wind = sim.wind.copy()
        show_apf = sim.show_apf_field

    fig = go.Figure()

    # 지면 그리드
    fig.add_trace(_ground_grid())

    # NFZ
    fig.add_trace(_nfz_mesh())
    for t in _nfz_edges():
        fig.add_trace(t)

    # 회랑
    for t in _corridor_traces():
        fig.add_trace(t)

    # 착륙 패드
    fig.add_trace(_pad_trace())

    # 바람 화살표
    for t in _wind_arrow(wind):
        fig.add_trace(t)

    # APF 벡터 필드 (토글)
    if show_apf:
        for t in _apf_vector_field(drones, wind):
            fig.add_trace(t)

    # 관제 구역 오버레이
    for t in _sector_overlay(sim):
        fig.add_trace(t)

    # 위협 히트맵 오버레이
    for t in _threat_heatmap_overlay(sim):
        fig.add_trace(t)

    # 드론 트레일
    for drone in drones:
        trail = trails.get(drone.drone_id, [])
        if len(trail) < 2 or not drone.is_active:
            continue
        color = PHASE_COLORS[drone.flight_phase]
        fig.add_trace(go.Scatter3d(
            x=[p[0] for p in trail],
            y=[p[1] for p in trail],
            z=[p[2] for p in trail],
            mode="lines",
            line=dict(color=color, width=1.5),
            opacity=0.3,
            showlegend=False, hoverinfo="skip",
        ))

    # 드론 마커 — 비행 단계별로 묶어서 렌더
    phase_groups: dict[FlightPhase, list[DroneState]] = {p: [] for p in FlightPhase}
    for d in drones:
        phase_groups[d.flight_phase].append(d)

    for phase, grp in phase_groups.items():
        if not grp:
            continue
        size = 10 if phase == FlightPhase.EVADING else (
               7  if phase == FlightPhase.FAILED   else 6)
        hover = [
            f"<b>{d.drone_id}</b> [{PHASE_KO[d.flight_phase]}]<br>"
            f"프로파일: {d.profile_name}<br>"
            f"속도: {d.speed:.1f} m/s | 고도: {d.position[2]:.0f} m<br>"
            f"배터리: {d.battery_pct:.0f} %<br>"
            f"비행시간: {d.flight_time_s:.0f}s | 거리: {d.distance_flown_m:.0f}m<br>"
            f"위치: ({d.position[0]:.0f}, {d.position[1]:.0f})"
            + (f"<br>⚠ 고장: {d.failure_type.name}" if d.failure_type != FailureType.NONE else "")
            for d in grp
        ]
        fig.add_trace(go.Scatter3d(
            x=[d.position[0] for d in grp],
            y=[d.position[1] for d in grp],
            z=[d.position[2] for d in grp],
            mode="markers",
            marker=dict(
                size=size,
                color=PHASE_COLORS[phase],
                opacity=0.95,
                line=dict(color="white", width=0.5),
            ),
            name=PHASE_KO[phase],
            text=hover,
            hovertemplate="%{text}<extra></extra>",
        ))

    # NFZ 근접 경고 (NFZ 경계 200m 이내 활성 드론)
    nfz_warn = [d for d in drones if d.is_active and d.flight_phase not in
                (FlightPhase.GROUNDED, FlightPhase.LANDING)
                and NFZ_X[0] - 200 < d.position[0] < NFZ_X[1] + 200
                and NFZ_Y[0] - 200 < d.position[1] < NFZ_Y[1] + 200]
    if nfz_warn:
        fig.add_trace(go.Scatter3d(
            x=[d.position[0] for d in nfz_warn],
            y=[d.position[1] for d in nfz_warn],
            z=[d.position[2] for d in nfz_warn],
            mode="markers",
            marker=dict(
                size=18, color="rgba(0,0,0,0)",
                line=dict(color="#FF1744", width=3),
                symbol="circle",
            ),
            opacity=0.7,
            showlegend=False,
            hoverinfo="skip",
            name="NFZ 경고",
        ))

    # 속도 화살표 (활성 드론 최대 20기)
    active = [d for d in drones if d.is_active and d.speed > 0.5][:20]
    if active:
        arr_x, arr_y, arr_z = [], [], []
        for d in active:
            scale = 600.0 / max(d.speed, 0.1)
            ex = d.position[0] + d.velocity[0] * scale
            ey = d.position[1] + d.velocity[1] * scale
            ez = d.position[2] + d.velocity[2] * scale
            arr_x += [d.position[0], ex, None]
            arr_y += [d.position[1], ey, None]
            arr_z += [d.position[2], ez, None]
        fig.add_trace(go.Scatter3d(
            x=arr_x, y=arr_y, z=arr_z,
            mode="lines",
            line=dict(color="#80CBC4", width=1.5),
            opacity=0.5,
            showlegend=False, hoverinfo="skip",
            name="속도 벡터",
        ))

    fig.update_layout(
        paper_bgcolor="#0d1117",
        plot_bgcolor="#0d1117",
        scene=dict(
            xaxis=dict(
                range=[-BOUNDS_M, BOUNDS_M], title="East  (m)",
                backgroundcolor="#010409",
                gridcolor="#21262d", zerolinecolor="#30363d",
                showbackground=True, color="#6e7681",
            ),
            yaxis=dict(
                range=[-BOUNDS_M, BOUNDS_M], title="North  (m)",
                backgroundcolor="#010409",
                gridcolor="#21262d", zerolinecolor="#30363d",
                showbackground=True, color="#6e7681",
            ),
            zaxis=dict(
                range=[0, ALT_MAX + 20], title="고도  (m AGL)",
                backgroundcolor="#010409",
                gridcolor="#21262d", zerolinecolor="#30363d",
                showbackground=True, color="#6e7681",
            ),
            bgcolor="#010409",
            camera=dict(
                eye=dict(x=1.6, y=-1.9, z=1.1),
                up=dict(x=0, y=0, z=1),
            ),
            aspectmode="manual",
            aspectratio=dict(x=2.0, y=2.0, z=0.28),
            dragmode="orbit",
        ),
        legend=dict(
            font=dict(color="#c9d1d9", size=10),
            bgcolor="rgba(13,17,23,0.85)",
            bordercolor="#30363d",
            borderwidth=1,
            x=0.01, y=0.98,
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        uirevision="stable",  # 카메라 각도 유지
    )
    return fig


# ─────────────────────────────────────────────────────────────
# 전역 시뮬레이션 인스턴스
# ─────────────────────────────────────────────────────────────
SIM = SimState()
SIM.reset(30)  # 초기 드론 배치 (3D scene 즉시 렌더링용)


# ─────────────────────────────────────────────────────────────
# Dash 앱 레이아웃
# ─────────────────────────────────────────────────────────────
app = dash.Dash(
    __name__,
    title="군집드론 공역통제 3D 시뮬레이터",
    update_title=None,
)

app.layout = html.Div(
    style={
        "backgroundColor": "#010409",
        "height": "100vh",
        "display": "flex",
        "flexDirection": "column",
        "fontFamily": "'Segoe UI', 'Malgun Gothic', sans-serif",
        "overflow": "hidden",
    },
    children=[
        # ── 헤더
        html.Div(
            style={
                "backgroundColor": "#0d1117",
                "padding": "10px 20px",
                "borderBottom": "1px solid #21262d",
                "display": "flex",
                "justifyContent": "space-between",
                "alignItems": "center",
                "flexShrink": "0",
            },
            children=[
                html.Div([
                    html.Span("🛸 ", style={"fontSize": "20px"}),
                    html.Span("군집드론 공역통제 자동화 시스템",
                              style={"color": "#58a6ff", "fontSize": "16px",
                                     "fontWeight": "700"}),
                    html.Span(" — 3D 실시간 시뮬레이터",
                              style={"color": "#6e7681", "fontSize": "14px"}),
                ]),
                html.Div(id="hdr-time",
                         style={"color": "#8b949e", "fontSize": "13px",
                                "fontFamily": "monospace"}),
            ],
        ),

        # ── 본문
        html.Div(
            style={"display": "flex", "flex": "1", "overflow": "hidden"},
            children=[

                # ── 사이드 패널
                html.Div(
                    style={
                        "width": "240px",
                        "backgroundColor": "#0d1117",
                        "padding": "14px",
                        "borderRight": "1px solid #21262d",
                        "overflowY": "auto",
                        "flexShrink": "0",
                    },
                    children=[

                        # 제어 버튼
                        html.Div([
                            html.Button("▶ 시작",   id="btn-start", n_clicks=0,
                                        style=_btn("▶ 시작", "#238636")),
                            html.Button("⏸",        id="btn-pause", n_clicks=0,
                                        style=_btn("⏸", "#6e40c9",
                                                   marginLeft="6px", width="36px")),
                            html.Button("↺",         id="btn-reset", n_clicks=0,
                                        style=_btn("↺", "#b62324",
                                                   marginLeft="6px", width="36px")),
                        ], style={"marginBottom": "14px"}),

                        # 드론 수 슬라이더
                        html.Label("드론 수",
                                   style={"color": "#8b949e", "fontSize": "11px",
                                          "display": "block", "marginBottom": "4px"}),
                        dcc.Slider(
                            id="slider-drones", min=10, max=100, step=10, value=30,
                            marks={i: {"label": str(i),
                                       "style": {"color": "#6e7681", "fontSize": "10px"}}
                                   for i in [10, 30, 50, 80, 100]},
                            tooltip={"placement": "bottom", "always_visible": False},
                        ),

                        # 시나리오 선택
                        html.Label("시나리오",
                                   style={"color": "#8b949e", "fontSize": "11px",
                                          "display": "block", "marginTop": "12px",
                                          "marginBottom": "4px"}),
                        dcc.Dropdown(
                            id="dropdown-scenario",
                            options=[
                                {"label": "기본 (랜덤)",          "value": "default"},
                                {"label": "고밀도 교통",          "value": "high_density"},
                                {"label": "비상 장애",            "value": "emergency_failure"},
                                {"label": "동시 이착륙",          "value": "mass_takeoff"},
                                {"label": "경로 충돌",            "value": "route_conflict"},
                                {"label": "통신 두절",            "value": "comms_loss"},
                                {"label": "기상 교란",            "value": "weather_disturbance"},
                                {"label": "침입 드론",            "value": "adversarial_intrusion"},
                            ],
                            value="default",
                            clearable=False,
                            style={"backgroundColor": "#161b22", "color": "#c9d1d9",
                                   "fontSize": "11px", "border": "1px solid #30363d"},
                        ),

                        # 바람 토글
                        html.Div([
                            dcc.Checklist(
                                id="wind-check",
                                options=[{"label": " 🌬 바람 (2 m/s 동남풍)", "value": "on"}],
                                value=[],
                                style={"color": "#c9d1d9", "fontSize": "11px",
                                       "marginTop": "14px"},
                            ),
                        ]),

                        # APF 벡터 필드 토글
                        html.Div([
                            dcc.Checklist(
                                id="apf-field-check",
                                options=[{"label": " 🧲 APF 벡터 필드", "value": "on"}],
                                value=[],
                                style={"color": "#c9d1d9", "fontSize": "11px",
                                       "marginTop": "4px"},
                            ),
                        ]),

                        # 속도 조절
                        html.Div([
                            html.Div("⏩ 시뮬레이션 속도",
                                     style={"color": "#c9d1d9", "fontSize": "11px",
                                            "marginTop": "14px", "marginBottom": "4px"}),
                            dcc.Slider(
                                id="slider-speed",
                                min=0.25, max=5.0, step=0.25, value=1.0,
                                marks={0.25: "0.25x", 1: "1x", 2: "2x", 3: "3x", 5: "5x"},
                                tooltip={"placement": "bottom", "always_visible": False},
                            ),
                        ]),

                        html.Hr(style={"borderColor": "#21262d", "margin": "14px 0"}),

                        # 통계
                        html.Div("📊 실시간 통계",
                                 style={"color": "#58a6ff", "fontSize": "12px",
                                        "fontWeight": "600", "marginBottom": "8px"}),
                        html.Div(id="stats"),

                        html.Hr(style={"borderColor": "#21262d", "margin": "14px 0"}),

                        # 배터리 분포 차트
                        html.Div("🔋 배터리 분포",
                                 style={"color": "#58a6ff", "fontSize": "12px",
                                        "fontWeight": "600", "marginBottom": "8px"}),
                        dcc.Graph(
                            id="chart-battery-dist",
                            style={"height": "120px"},
                            config={"displayModeBar": False},
                        ),

                        html.Hr(style={"borderColor": "#21262d", "margin": "14px 0"}),

                        # 에너지 소모 시계열 차트
                        html.Div("⚡ 에너지 소모 (Wh)",
                                 style={"color": "#58a6ff", "fontSize": "12px",
                                        "fontWeight": "600", "marginBottom": "8px"}),
                        dcc.Graph(
                            id="chart-energy-ts",
                            style={"height": "120px"},
                            config={"displayModeBar": False},
                        ),

                        html.Hr(style={"borderColor": "#21262d", "margin": "14px 0"}),

                        # 충돌 해결률 시계열
                        html.Div("🛡 충돌 해결률 (%)",
                                 style={"color": "#58a6ff", "fontSize": "12px",
                                        "fontWeight": "600", "marginBottom": "8px"}),
                        dcc.Graph(
                            id="chart-cr-rate",
                            style={"height": "120px"},
                            config={"displayModeBar": False},
                        ),

                        html.Hr(style={"borderColor": "#21262d", "margin": "14px 0"}),

                        # 위협 레벨 패널
                        html.Div("⚠ 위협 레벨",
                                 style={"color": "#58a6ff", "fontSize": "12px",
                                        "fontWeight": "600", "marginBottom": "8px"}),
                        html.Div(id="threat-panel"),

                        html.Hr(style={"borderColor": "#21262d", "margin": "14px 0"}),

                        # SLA 상태 패널
                        html.Div("📋 SLA 상태",
                                 style={"color": "#58a6ff", "fontSize": "12px",
                                        "fontWeight": "600", "marginBottom": "8px"}),
                        html.Div(id="sla-panel"),

                        html.Hr(style={"borderColor": "#21262d", "margin": "14px 0"}),

                        # 구역별 현황
                        html.Div("🗺 관제 구역",
                                 style={"color": "#58a6ff", "fontSize": "12px",
                                        "fontWeight": "600", "marginBottom": "8px"}),
                        html.Div(id="sector-panel"),

                        html.Hr(style={"borderColor": "#21262d", "margin": "14px 0"}),

                        # 성능 모니터 차트
                        html.Div("⏱ 틱 처리시간 (ms)",
                                 style={"color": "#58a6ff", "fontSize": "12px",
                                        "fontWeight": "600", "marginBottom": "8px"}),
                        dcc.Graph(
                            id="chart-tick-perf",
                            style={"height": "100px"},
                            config={"displayModeBar": False},
                        ),

                        html.Hr(style={"borderColor": "#21262d", "margin": "14px 0"}),

                        # 범례
                        html.Div("🎨 비행 단계 범례",
                                 style={"color": "#58a6ff", "fontSize": "12px",
                                        "fontWeight": "600", "marginBottom": "8px"}),
                        html.Div([_legend_row(p) for p in FlightPhase]),
                    ],
                ),

                # ── 3D 뷰포트
                dcc.Graph(
                    id="graph-3d",
                    figure=build_figure(SIM),  # 초기 3D scene 즉시 렌더링
                    style={"flex": "1", "height": "100%"},
                    config={
                        "displayModeBar": True,
                        "scrollZoom": True,
                        "modeBarButtonsToRemove": ["toImage"],
                    },
                ),
            ],
        ),

        # ── 경보 로그 + 이벤트 타임라인 (하단 바 — 확장형)
        html.Div(
            style={
                "backgroundColor": "#0d1117",
                "borderTop": "1px solid #21262d",
                "flexShrink": "0",
                "height": "90px",
                "display": "flex",
            },
            children=[
                # 경보 로그 (왼쪽)
                html.Div(
                    style={
                        "flex": "1",
                        "padding": "6px 16px",
                        "overflowY": "auto",
                    },
                    children=[
                        html.Div("📜 경보 로그",
                                 style={"color": "#58a6ff", "fontSize": "10px",
                                        "fontWeight": "600", "marginBottom": "4px"}),
                        html.Div(
                            id="alert-log",
                            style={
                                "fontSize": "10px",
                                "fontFamily": "monospace",
                                "color": "#8b949e",
                                "lineHeight": "1.4",
                            },
                            children="경보 없음",
                        ),
                    ],
                ),
                # 이벤트 타임라인 미니 차트 (오른쪽)
                html.Div(
                    style={
                        "width": "350px",
                        "borderLeft": "1px solid #21262d",
                        "padding": "4px 8px",
                    },
                    children=[
                        html.Div("📅 이벤트 타임라인",
                                 style={"color": "#58a6ff", "fontSize": "10px",
                                        "fontWeight": "600", "marginBottom": "2px"}),
                        dcc.Graph(
                            id="chart-timeline",
                            style={"height": "65px"},
                            config={"displayModeBar": False},
                        ),
                    ],
                ),
            ],
        ),

        # 인터벌 & 상태 저장소
        dcc.Interval(id="interval", interval=200, n_intervals=0),
        dcc.Store(id="store-run", data=False),
        dcc.Store(id="store-alerts", data=[]),
        html.Div(id="_dummy-wind", style={"display": "none"}),
        html.Div(id="_dummy-apf", style={"display": "none"}),
        html.Div(id="_dummy-scenario", style={"display": "none"}),
    ],
)


# ─────────────────────────────────────────────────────────────
# 콜백
# ─────────────────────────────────────────────────────────────
@app.callback(
    Output("store-run", "data"),
    Input("btn-start", "n_clicks"),
    Input("btn-pause", "n_clicks"),
    Input("btn-reset", "n_clicks"),
    State("slider-drones", "value"),
    State("store-run", "data"),
    prevent_initial_call=True,
)
def _ctrl(start, pause, reset, n_drones, running):
    ctx = callback_context
    if not ctx.triggered:
        return running
    btn = ctx.triggered[0]["prop_id"].split(".")[0]
    if btn == "btn-start":
        SIM.running = True
        return True
    if btn == "btn-pause":
        SIM.running = False
        return False
    if btn == "btn-reset":
        SIM.running = False
        SIM.reset(int(n_drones or 30))
        return False
    return running


@app.callback(
    Output("_dummy-wind", "children"),
    Input("wind-check", "value"),
    prevent_initial_call=True,
)
def _wind(value):
    with SIM.lock:
        SIM.wind = np.array([2.0, -1.5, 0.0]) if (value and "on" in value) else np.zeros(3)
    return ""


@app.callback(
    Output("_dummy-apf", "children"),
    Input("apf-field-check", "value"),
    prevent_initial_call=True,
)
def _apf_toggle(value):
    with SIM.lock:
        SIM.show_apf_field = bool(value and "on" in value)
    return ""


@app.callback(
    Output("slider-speed", "className"),
    Input("slider-speed", "value"),
    prevent_initial_call=True,
)
def _speed(value):
    SIM.speed_multiplier = float(value or 1.0)
    return ""


@app.callback(
    Output("_dummy-scenario", "children"),
    Input("dropdown-scenario", "value"),
    prevent_initial_call=True,
)
def _apply_scenario(scenario: str):
    """시나리오 선택 시 드론 수 조정 및 시뮬레이션 리셋"""
    drone_counts = {
        "default":                30,
        "high_density":           80,
        "emergency_failure":      40,
        "mass_takeoff":           60,
        "route_conflict":         20,
        "comms_loss":             30,
        "weather_disturbance":    25,
        "adversarial_intrusion":  35,
    }
    n = drone_counts.get(scenario, 30)
    SIM.running = False
    SIM.reset(n)
    return ""


def _mini_chart_layout() -> dict:
    """소형 차트 공통 레이아웃"""
    return dict(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=30, r=8, t=4, b=20),
        xaxis=dict(color="#6e7681", gridcolor="#21262d", showgrid=True,
                   tickfont=dict(size=8)),
        yaxis=dict(color="#6e7681", gridcolor="#21262d", showgrid=True,
                   tickfont=dict(size=8)),
        showlegend=False,
        height=110,
    )


@app.callback(
    Output("graph-3d",           "figure"),
    Output("hdr-time",           "children"),
    Output("stats",              "children"),
    Output("alert-log",          "children"),
    Output("chart-battery-dist", "figure"),
    Output("chart-energy-ts",    "figure"),
    Output("chart-cr-rate",      "figure"),
    Output("threat-panel",       "children"),
    Output("sla-panel",          "children"),
    Output("sector-panel",       "children"),
    Output("chart-tick-perf",    "figure"),
    Output("chart-timeline",     "figure"),
    Input("interval",            "n_intervals"),
)
def _refresh(_n):
    fig = build_figure(SIM)

    with SIM.lock:
        t          = SIM.t
        drones     = list(SIM.drones.values())
        conflicts  = SIM.conflicts
        near_miss  = SIM.near_misses
        advisories = SIM.advisories
        collisions = SIM.collisions
        threat_mat = SIM.threat_matrix.copy() if SIM.threat_matrix else {}
        sla_viols  = list(SIM.sla_violations)
        sector_st  = SIM.sector_mgr.sector_stats()
        tick_times = list(SIM.tick_times_ms)
        timeline_events = SIM.timeline._events[-20:] if SIM.timeline._events else []

    active = sum(1 for d in drones if d.is_active)
    avg_bat = sum(d.battery_pct for d in drones) / max(len(drones), 1)
    evading = sum(1 for d in drones if d.flight_phase == FlightPhase.EVADING)

    phase_cnt: dict[str, int] = {}
    for d in drones:
        k = PHASE_KO[d.flight_phase]
        phase_cnt[k] = phase_cnt.get(k, 0) + 1

    mins, secs = divmod(int(t), 60)
    time_str = (
        f"T+{mins:02d}:{secs:02d}  |  "
        f"{'▶ 실행 중' if SIM.running else '⏸ 일시정지'}"
    )

    # 에너지 소모 표시
    latest = SIM.metrics.latest
    energy_wh = latest.total_energy_wh if latest else 0.0

    stats_div = html.Div([
        _stat("전체 드론",      f"{len(drones)}"),
        _stat("활성",           f"{active}"),
        _stat("회피 기동",      f"{evading}", warn=evading > 0),
        _stat("충돌 경보 누적", f"{conflicts}", warn=conflicts > 0),
        _stat("근접 경고 누적", f"{near_miss}", warn=near_miss > 0),
        _stat("실제 충돌",      f"{collisions}", warn=collisions > 0),
        _stat("어드바이저리",   f"{advisories}"),
        _stat("평균 배터리",    f"{avg_bat:.0f} %"),
        _stat("에너지 소모",    f"{energy_wh:.1f} Wh"),
        html.Hr(style={"borderColor": "#21262d", "margin": "8px 0"}),
        *[_stat(k, str(v)) for k, v in sorted(phase_cnt.items())],
    ])

    # ── 경보 로그 (최근 이벤트 기반)
    alert_items = []
    if collisions > 0:
        alert_items.append(
            html.Div(f"[T+{mins:02d}:{secs:02d}] 🔴 충돌 {collisions}건 발생",
                      style={"color": "#F44336"}))
    if near_miss > 0:
        alert_items.append(
            html.Div(f"[T+{mins:02d}:{secs:02d}] 🟠 근접경고 {near_miss}건",
                      style={"color": "#FF9800"}))
    if evading > 0:
        alert_items.append(
            html.Div(f"[T+{mins:02d}:{secs:02d}] 🟡 회피기동 {evading}기",
                      style={"color": "#FFEA00"}))
    if advisories > 0:
        alert_items.append(
            html.Div(f"[T+{mins:02d}:{secs:02d}] 🔵 어드바이저리 {advisories}건",
                      style={"color": "#42A5F5"}))
    # 위협 정보 추가
    overall_level = threat_mat.get("overall_level", ThreatLevel.LOW)
    if overall_level >= ThreatLevel.HIGH:
        level_name = overall_level.name if hasattr(overall_level, 'name') else str(overall_level)
        alert_items.append(
            html.Div(f"[T+{mins:02d}:{secs:02d}] ⚠ 위협 레벨: {level_name}",
                      style={"color": "#FF5722" if overall_level >= ThreatLevel.CRITICAL else "#FF9800"}))
    alert_div = html.Div(alert_items) if alert_items else "✅ 경보 없음"

    # ── 배터리 분포 바 차트
    bat_hist = SIM.metrics.battery_distribution()
    bat_labels = [f"{i*10}-{i*10+10}%" for i in range(10)]
    bat_colors = ["#F44336" if i < 2 else "#FF9800" if i < 4
                  else "#4CAF50" for i in range(10)]
    fig_bat = go.Figure(go.Bar(
        x=bat_labels, y=bat_hist,
        marker_color=bat_colors,
    ))
    fig_bat.update_layout(**_mini_chart_layout())

    # ── 에너지 소모 시계열
    ts_t, ts_e = SIM.metrics.time_series("total_energy_wh")
    fig_energy = go.Figure(go.Scatter(
        x=ts_t, y=ts_e,
        mode="lines",
        line=dict(color="#FFD700", width=1.5),
        fill="tozeroy",
        fillcolor="rgba(255,215,0,0.1)",
    ))
    fig_energy.update_layout(**_mini_chart_layout())
    fig_energy.update_xaxes(title_text="시간 (s)", title_font_size=8)

    # ── 충돌 해결률 시계열
    ts_t2, ts_cr = SIM.metrics.time_series("conflict_resolution_rate")
    fig_cr = go.Figure(go.Scatter(
        x=ts_t2, y=ts_cr,
        mode="lines",
        line=dict(color="#00E676", width=1.5),
        fill="tozeroy",
        fillcolor="rgba(0,230,118,0.1)",
    ))
    fig_cr.update_layout(**_mini_chart_layout())
    fig_cr.update_xaxes(title_text="시간 (s)", title_font_size=8)
    fig_cr.update_yaxes(range=[0, 105])

    # ── 위협 레벨 패널
    threat_color_map = {
        ThreatLevel.LOW: "#00E676",
        ThreatLevel.MEDIUM: "#FFEA00",
        ThreatLevel.HIGH: "#FF9800",
        ThreatLevel.CRITICAL: "#F44336",
    }
    threat_score = threat_mat.get("total_score", 0)
    threat_count = threat_mat.get("threat_count", 0)
    level_color = threat_color_map.get(overall_level, "#00E676")
    level_name = overall_level.name if hasattr(overall_level, 'name') else "LOW"

    threat_div = html.Div([
        html.Div([
            html.Span("●  ", style={"color": level_color, "fontSize": "16px"}),
            html.Span(level_name,
                      style={"color": level_color, "fontSize": "13px",
                             "fontWeight": "700"}),
        ]),
        _stat("위협 점수", f"{threat_score}"),
        _stat("위협 수", f"{threat_count}"),
        # 권장 조치 (최대 2개)
        *[html.Div(f"→ {action}",
                   style={"color": "#c9d1d9", "fontSize": "9px",
                          "marginTop": "2px", "lineHeight": "1.3"})
          for action in threat_mat.get("recommended_actions", [])[:2]],
    ])

    # ── SLA 상태 패널
    if sla_viols:
        sla_items = []
        for v in sla_viols[:3]:
            name = v.threshold_name if hasattr(v, 'threshold_name') else str(v)
            sla_items.append(
                html.Div(f"❌ {name}",
                         style={"color": "#F44336", "fontSize": "10px"}))
        sla_div = html.Div(sla_items)
    else:
        sla_div = html.Div("✅ 모든 SLA 충족",
                           style={"color": "#00E676", "fontSize": "10px"})

    # ── 구역별 현황 패널
    sector_items = []
    for sid, st in sorted(sector_st.items()):
        n_d = st["drones"]
        ho = st["handoffs_in"] + st["handoffs_out"]
        density = st["density"]
        d_color = "#F44336" if density > 4.0 else "#FF9800" if density > 2.0 else "#c9d1d9"
        sector_items.append(
            html.Div([
                html.Span(f"{sid}: ",
                          style={"color": "#8b949e", "fontSize": "10px"}),
                html.Span(f"{n_d}기",
                          style={"color": d_color, "fontSize": "10px",
                                 "fontWeight": "600"}),
                html.Span(f" ({density:.1f}/km²) H:{ho}",
                          style={"color": "#6e7681", "fontSize": "9px"}),
            ], style={"marginBottom": "2px"}))
    sector_div = html.Div(sector_items)

    # ── 틱 처리시간 차트
    fig_tick = go.Figure()
    if tick_times:
        fig_tick.add_trace(go.Scatter(
            y=tick_times[-100:],
            mode="lines",
            line=dict(color="#AB47BC", width=1.2),
            fill="tozeroy",
            fillcolor="rgba(171,71,188,0.1)",
        ))
        avg_ms = sum(tick_times[-100:]) / len(tick_times[-100:])
        fig_tick.add_hline(y=avg_ms, line_dash="dash",
                          line_color="#6e7681", line_width=1)
    fig_tick.update_layout(**_mini_chart_layout())
    fig_tick.update_layout(height=90)
    fig_tick.update_yaxes(title_text="ms", title_font_size=7)

    # ── 이벤트 타임라인 미니 차트
    fig_tl = go.Figure()
    if timeline_events:
        ev_times = [e.t for e in timeline_events]
        ev_types = [e.event_type for e in timeline_events]
        ev_colors_map = {
            "COLLISION": "#F44336",
            "EVADING": "#FF9800",
            "NFZ_VIOLATION": "#FF1744",
        }
        ev_colors = [ev_colors_map.get(et, "#42A5F5") for et in ev_types]
        fig_tl.add_trace(go.Scatter(
            x=ev_times,
            y=[1] * len(ev_times),
            mode="markers",
            marker=dict(size=8, color=ev_colors, symbol="diamond"),
            text=ev_types,
            hovertemplate="%{text} @ %{x:.1f}s<extra></extra>",
        ))
    fig_tl.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=8, t=2, b=15),
        xaxis=dict(color="#6e7681", gridcolor="#21262d",
                   tickfont=dict(size=7), title_text="시간(s)", title_font_size=7),
        yaxis=dict(visible=False),
        showlegend=False,
        height=60,
    )

    return (fig, time_str, stats_div, alert_div, fig_bat, fig_energy, fig_cr,
            threat_div, sla_div, sector_div, fig_tick, fig_tl)


# ─────────────────────────────────────────────────────────────
# 진입점
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    SIM.reset(30)

    bg = threading.Thread(target=_sim_loop, args=(SIM,), daemon=True)
    bg.start()

    print("=" * 60)
    print("  3D Simulator starting...")
    print("  Browser: http://localhost:8050")
    print("=" * 60)
    print("  Press [Start] button to begin simulation.")
    print("=" * 60)

    app.run(debug=False, host="0.0.0.0", port=8050)
