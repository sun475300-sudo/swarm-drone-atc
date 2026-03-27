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
)
from src.airspace_control.agents.drone_state import (
    DroneState, FlightPhase, CommsStatus, FailureType,
)
from src.airspace_control.agents.drone_profiles import DRONE_PROFILES

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

        # 통계
        self.conflicts = 0
        self.near_misses = 0
        self.advisories = 0
        self.collisions = 0

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


def build_figure(sim: SimState) -> go.Figure:
    """3D 시각화 Figure 빌드"""
    with sim.lock:
        drones = list(sim.drones.values())
        trails = {k: list(v) for k, v in sim.trails.items()}

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
            f"<b>{d.drone_id}</b><br>"
            f"프로파일: {d.profile_name}<br>"
            f"속도: {d.speed:.1f} m/s<br>"
            f"고도: {d.position[2]:.0f} m<br>"
            f"배터리: {d.battery_pct:.0f} %"
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

        # ── 경보 로그 (하단 바)
        html.Div(
            id="alert-log",
            style={
                "backgroundColor": "#0d1117",
                "borderTop": "1px solid #21262d",
                "padding": "6px 16px",
                "fontSize": "11px",
                "fontFamily": "monospace",
                "color": "#8b949e",
                "flexShrink": "0",
                "height": "28px",
                "overflow": "hidden",
                "whiteSpace": "nowrap",
            },
            children="경보 없음",
        ),

        # 인터벌 & 상태 저장소
        dcc.Interval(id="interval", interval=200, n_intervals=0),
        dcc.Store(id="store-run", data=False),
        dcc.Store(id="store-alerts", data=[]),
        html.Div(id="_dummy-wind", style={"display": "none"}),
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


@app.callback(
    Output("graph-3d",  "figure"),
    Output("hdr-time",  "children"),
    Output("stats",     "children"),
    Output("alert-log", "children"),
    Input("interval",   "n_intervals"),
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

    stats_div = html.Div([
        _stat("전체 드론",      f"{len(drones)}"),
        _stat("활성",           f"{active}"),
        _stat("회피 기동",      f"{evading}", warn=evading > 0),
        _stat("충돌 경보 누적", f"{conflicts}", warn=conflicts > 0),
        _stat("근접 경고 누적", f"{near_miss}", warn=near_miss > 0),
        _stat("실제 충돌",      f"{collisions}", warn=collisions > 0),
        _stat("어드바이저리",   f"{advisories}"),
        _stat("평균 배터리",    f"{avg_bat:.0f} %"),
        html.Hr(style={"borderColor": "#21262d", "margin": "8px 0"}),
        *[_stat(k, str(v)) for k, v in sorted(phase_cnt.items())],
    ])

    # 경보 로그 텍스트 구성
    alerts = []
    if collisions > 0:
        alerts.append(f"🔴 충돌 {collisions}건")
    if near_miss > 0:
        alerts.append(f"🟠 근접경고 {near_miss}건")
    if evading > 0:
        alerts.append(f"🟡 회피기동 {evading}기")
    if advisories > 0:
        alerts.append(f"🔵 어드바이저리 {advisories}건")
    alert_str = "   |   ".join(alerts) if alerts else "✅ 경보 없음"

    return fig, time_str, stats_div, alert_str


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
