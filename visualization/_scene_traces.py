"""
3D scene trace builders for the SDACS Dash visualizer.

All functions are pure (side-effect-free) except those that read from a
SimState instance (build_figure, _sector_overlay, _threat_heatmap_overlay).
This module intentionally owns the airspace constants so that
visualization/simulator_3d.py can import them from here — avoiding a circular
dependency during the PR#B refactor (constants will migrate to _domain.py in
PR#C).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import plotly.graph_objects as go

from simulation.apf_engine.apf import (
    APFState,
    compute_total_force,
)
from simulation.threat_assessment import ThreatLevel
from src.airspace_control.agents.drone_state import (
    DroneState,
    FailureType,
    FlightPhase,
)

if TYPE_CHECKING:
    from visualization._domain import SimState


# ─────────────────────────────────────────────────────────────
# 공역 상수  (will be moved to _domain.py in PR#C)
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

# 카메라 프리셋 (뷰포트 선택용)
CAMERA_PRESETS: dict[str, dict] = {
    "기본 3D": dict(eye=dict(x=1.6, y=-1.9, z=1.1), up=dict(x=0, y=0, z=1)),
    "탑다운": dict(eye=dict(x=0.0, y=0.0, z=3.5), up=dict(x=0, y=1, z=0)),
    "측면": dict(eye=dict(x=2.5, y=0.0, z=0.4), up=dict(x=0, y=0, z=1)),
    "대각선": dict(eye=dict(x=1.8, y=-1.8, z=0.6), up=dict(x=0, y=0, z=1)),
    "NFZ 클로즈업": dict(eye=dict(x=0.4, y=-0.5, z=0.3), up=dict(x=0, y=0, z=1)),
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
    ii = [0, 0,  4, 4,  0, 0,  2, 2,  0, 0,  1, 1]
    jj = [1, 2,  5, 6,  1, 5,  3, 7,  3, 7,  2, 6]
    kk = [2, 3,  6, 7,  5, 4,  7, 6,  7, 4,  6, 5]
    return go.Mesh3d(
        x=vx, y=vy, z=vz,
        i=ii, j=jj, k=kk,
        color="#FF1744",
        opacity=0.25,
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
            line=dict(color="#FF5252", width=4, dash="dot"),
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
            line=dict(color=color, width=8),
            opacity=0.75,
            name=name,
        )
    return [
        make(CORRIDOR_EW, "#448AFF", "동서 회랑 (60 m)"),
        make(CORRIDOR_NS, "#69F0AE", "남북 회랑 (80 m)"),
    ]


def _pad_trace() -> list:
    """착륙 패드 — 헬리패드 링 + 중심 마커 + H 라벨"""
    traces = []
    pad_names = list(LANDING_PADS.keys())
    pads = list(LANDING_PADS.values())

    # 각 패드에 원형 링
    n_pts = 24
    radius = 150.0
    for _name, pad in LANDING_PADS.items():
        ring_x, ring_y, ring_z = [], [], []
        for i in range(n_pts + 1):
            angle = 2 * np.pi * i / n_pts
            ring_x.append(pad[0] + radius * np.cos(angle))
            ring_y.append(pad[1] + radius * np.sin(angle))
            ring_z.append(1.0)
        traces.append(go.Scatter3d(
            x=ring_x, y=ring_y, z=ring_z,
            mode="lines",
            line=dict(color="#FFD600", width=3),
            opacity=0.7,
            showlegend=False, hoverinfo="skip",
        ))
        # 내부 십자 (H 표시)
        cr = radius * 0.5
        traces.append(go.Scatter3d(
            x=[pad[0] - cr, pad[0] + cr, None,
               pad[0], pad[0], None,
               pad[0] - cr, pad[0] + cr],
            y=[pad[1], pad[1], None,
               pad[1] - cr, pad[1] + cr, None,
               pad[1], pad[1]],
            z=[1.5] * 8,
            mode="lines",
            line=dict(color="#FFD600", width=2),
            opacity=0.5,
            showlegend=False, hoverinfo="skip",
        ))

    # 중심 마커 + 라벨
    traces.append(go.Scatter3d(
        x=[p[0] for p in pads],
        y=[p[1] for p in pads],
        z=[p[2] + 2 for p in pads],
        mode="markers+text",
        marker=dict(
            size=10, color="#FFD600", symbol="circle",
            opacity=1.0, line=dict(color="#ffffff", width=2),
        ),
        text=pad_names,
        textposition="top center",
        textfont=dict(color="#FFD600", size=9),
        name="착륙 패드",
        hovertemplate="%{text}<extra>착륙 패드</extra>",
    ))
    return traces


def _ground_grid() -> list[go.Scatter3d]:
    """지면 그리드 (z=0 평면) + 공역 경계 + 순항 고도 + 거리 라벨"""
    traces = []
    b = BOUNDS_M

    # 지면 그리드 — 1km 간격, 밝은 색
    lines_x, lines_y, lines_z = [], [], []
    step = 1000.0
    for v in np.arange(-b, b + step, step):
        lines_x += [v, v, None, -b, b, None]
        lines_y += [-b, b, None, v, v, None]
        lines_z += [0, 0, None, 0, 0, None]
    traces.append(go.Scatter3d(
        x=lines_x, y=lines_y, z=lines_z,
        mode="lines",
        line=dict(color="#3d4663", width=1.5),
        showlegend=False, hoverinfo="skip",
        opacity=0.5,
    ))

    # 지면 채움 (반투명 면으로 바닥을 시각화)
    traces.append(go.Mesh3d(
        x=[-b, b, b, -b], y=[-b, -b, b, b], z=[0, 0, 0, 0],
        i=[0, 0], j=[1, 2], k=[2, 3],
        color="#1a2233", opacity=0.4,
        flatshading=True, showlegend=False, hoverinfo="skip",
    ))

    # 공역 경계 강조 (굵은 외곽선)
    traces.append(go.Scatter3d(
        x=[-b, b, b, -b, -b], y=[-b, -b, b, b, -b],
        z=[0, 0, 0, 0, 0],
        mode="lines",
        line=dict(color="#5a6a8a", width=4),
        opacity=0.9,
        showlegend=False, hoverinfo="skip",
    ))

    # 거리 라벨 (모서리에 km 표시)
    dist_x, dist_y, dist_z, dist_text = [], [], [], []
    for km in range(-4, 5, 2):
        if km == 0:
            continue
        dist_x.append(km * 1000)
        dist_y.append(-b - 200)
        dist_z.append(0)
        dist_text.append(f"{km}km")
    traces.append(go.Scatter3d(
        x=dist_x, y=dist_y, z=dist_z,
        mode="text",
        text=dist_text,
        textfont=dict(color="#7a8aaa", size=10),
        showlegend=False, hoverinfo="skip",
    ))

    # 순항 고도 기준면 (60m — 밝은 점선 + 라벨)
    traces.append(go.Scatter3d(
        x=[-b, b, b, -b, -b], y=[-b, -b, b, b, -b],
        z=[CRUISE_ALT] * 5,
        mode="lines",
        line=dict(color="#2d5a8a", width=2, dash="dash"),
        opacity=0.35,
        showlegend=False, hoverinfo="skip",
    ))
    traces.append(go.Scatter3d(
        x=[b], y=[b], z=[CRUISE_ALT],
        mode="text",
        text=[f"순항고도 {CRUISE_ALT:.0f}m"],
        textfont=dict(color="#5a8abb", size=9),
        showlegend=False, hoverinfo="skip",
    ))

    return traces


def _apf_vector_field(drones: list[DroneState], wind: np.ndarray) -> list:
    """APF 벡터 필드를 그리드 포인트에서 Cone3d 트레이스로 렌더링"""
    active = [d for d in drones if d.is_active and d.flight_phase not in
              (FlightPhase.GROUNDED, FlightPhase.LANDING)]
    if not active:
        return []

    grid_step = 1000.0
    xs = np.arange(-BOUNDS_M + 500, BOUNDS_M, grid_step)
    ys = np.arange(-BOUNDS_M + 500, BOUNDS_M, grid_step)
    z_sample = CRUISE_ALT

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
            probe = APFState(pos, np.zeros(3), "__probe__")
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
    """공역 좌측 상단에 바람 방향 화살표 표시"""
    speed = float(np.linalg.norm(wind[:2]))
    if speed < 0.1:
        return []

    origin = np.array([-BOUNDS_M * 0.85, BOUNDS_M * 0.85, CRUISE_ALT])
    direction = wind[:3].copy()
    direction[2] = 0.0
    scale = BOUNDS_M * 0.15 / max(speed, 0.1)
    end = origin + direction * scale

    label = f"바람 {speed:.1f} m/s"
    return [
        go.Scatter3d(
            x=[origin[0], end[0]],
            y=[origin[1], end[1]],
            z=[origin[2], end[2]],
            mode="lines+text",
            line=dict(color="#80DEEA", width=4),
            text=["", label],
            textposition="top center",
            textfont=dict(color="#80DEEA", size=10),
            showlegend=False,
            hovertext=label,
            hoverinfo="text",
        )
    ]


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

        if density > 4.0:
            color = "#FF1744"
        elif density > 2.0:
            color = "#FF9100"
        elif density > 1.0:
            color = "#FFEA00"
        else:
            color = "#00E676"

        traces.append(go.Scatter3d(
            x=[x0, x1, x1, x0, x0],
            y=[y0, y0, y1, y1, y0],
            z=[2, 2, 2, 2, 2],
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
    """위협 레벨에 따른 공역 전체 틴트 오버레이"""
    with sim.lock:
        matrix = sim.threat_matrix.copy() if sim.threat_matrix else {}

    overall = matrix.get("overall_level", ThreatLevel.LOW)
    if overall == ThreatLevel.LOW:
        return []

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

    # 지면 그리드 + 공역 경계 + 순항 고도 기준면
    for t in _ground_grid():
        fig.add_trace(t)

    # NFZ
    fig.add_trace(_nfz_mesh())
    for t in _nfz_edges():
        fig.add_trace(t)

    # 회랑
    for t in _corridor_traces():
        fig.add_trace(t)

    # 착륙 패드 (헬리패드 링)
    for t in _pad_trace():
        fig.add_trace(t)

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

    # 드론 트레일 — 그라데이션 페이드 (최신→과거 투명도 감소)
    for drone in drones:
        trail = trails.get(drone.drone_id, [])
        if len(trail) < 2 or not drone.is_active:
            continue
        color = PHASE_COLORS[drone.flight_phase]
        n = len(trail)
        seg_count = min(4, n - 1)
        seg_size = max(n // seg_count, 2)
        for si in range(seg_count):
            start = si * seg_size
            end = min(start + seg_size + 1, n)
            if end - start < 2:
                continue
            opacity = 0.15 + 0.55 * (si / max(seg_count - 1, 1))
            width = 2.0 + 3.0 * (si / max(seg_count - 1, 1))
            fig.add_trace(go.Scatter3d(
                x=[trail[j][0] for j in range(start, end)],
                y=[trail[j][1] for j in range(start, end)],
                z=[trail[j][2] for j in range(start, end)],
                mode="lines",
                line=dict(color=color, width=width),
                opacity=opacity,
                showlegend=False, hoverinfo="skip",
            ))

    # 드론 마커 — 비행 단계별로 묶어서 렌더
    phase_groups: dict[FlightPhase, list[DroneState]] = {p: [] for p in FlightPhase}
    for d in drones:
        phase_groups[d.flight_phase].append(d)

    for phase, grp in phase_groups.items():
        if not grp:
            continue
        # 단계별 마커 크기 및 심볼 분화 (가독성 위해 대형화)
        if phase == FlightPhase.EVADING:
            size, symbol = 22, "diamond"
        elif phase == FlightPhase.FAILED:
            size, symbol = 18, "x"
        elif phase == FlightPhase.GROUNDED:
            size, symbol = 10, "square"
        elif phase == FlightPhase.RTL:
            size, symbol = 16, "diamond"
        else:
            size, symbol = 14, "circle"

        # 배터리 기반 색상 변조 (저배터리 드론 강조)
        colors = []
        for d in grp:
            if d.battery_pct < 15:
                colors.append("#FF1744")
            elif d.battery_pct < 30:
                colors.append("#FF9100")
            else:
                colors.append(PHASE_COLORS[phase])

        hover = [
            (f"<b>{d.drone_id}</b> [{PHASE_KO[d.flight_phase]}]<br>"
             f"프로파일: {d.profile_name}<br>"
             f"속도: {d.speed:.1f} m/s | 고도: {d.position[2]:.0f} m<br>"
             f"배터리: {d.battery_pct:.0f} %<br>"
             f"비행시간: {d.flight_time_s:.0f}s | 거리: {d.distance_flown_m:.0f}m<br>"
             f"위치: ({d.position[0]:.0f}, {d.position[1]:.0f})"
             + (f"<br>⚠ 고장: {d.failure_type.name}"
                if d.failure_type != FailureType.NONE else ""))
            for d in grp
        ]
        fig.add_trace(go.Scatter3d(
            x=[d.position[0] for d in grp],
            y=[d.position[1] for d in grp],
            z=[d.position[2] for d in grp],
            mode="markers",
            marker=dict(
                size=size,
                color=colors,
                symbol=symbol,
                opacity=0.95,
                line=dict(color="white", width=0.5),
            ),
            name=PHASE_KO[phase],
            text=hover,
            hovertemplate="%{text}<extra></extra>",
        ))

    # 고도 참조선 — 활성 드론에서 지면까지 수직 점선 (최대 30기)
    alt_drones = [d for d in drones if d.is_active
                  and d.flight_phase != FlightPhase.GROUNDED
                  and d.position[2] > 5][:30]
    if alt_drones:
        alt_x, alt_y, alt_z = [], [], []
        for d in alt_drones:
            alt_x += [d.position[0], d.position[0], None]
            alt_y += [d.position[1], d.position[1], None]
            alt_z += [0, d.position[2], None]
        fig.add_trace(go.Scatter3d(
            x=alt_x, y=alt_y, z=alt_z,
            mode="lines",
            line=dict(color="#30363d", width=0.8, dash="dot"),
            opacity=0.25,
            showlegend=False, hoverinfo="skip",
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

    # 속도 벡터 — Cone 3D (활성 드론 최대 30기)
    active = [d for d in drones if d.is_active and d.speed > 0.5][:30]
    if active:
        cx, cy, cz, cu, cv, cw = [], [], [], [], [], []
        for d in active:
            cx.append(d.position[0])
            cy.append(d.position[1])
            cz.append(d.position[2])
            cu.append(float(d.velocity[0]))
            cv.append(float(d.velocity[1]))
            cw.append(float(d.velocity[2]))
        max_spd = max(d.speed for d in active)
        fig.add_trace(go.Cone(
            x=cx, y=cy, z=cz,
            u=cu, v=cv, w=cw,
            sizemode="scaled",
            sizeref=max_spd * 1.2,
            anchor="tail",
            colorscale=[[0, "#26C6DA"], [0.5, "#80CBC4"], [1, "#FFD54F"]],
            cmin=0, cmax=max_spd,
            opacity=0.7,
            showscale=False,
            name="속도 벡터",
            hovertemplate="속도: %{u:.1f}, %{v:.1f}, %{w:.1f}<extra></extra>",
        ))

    fig.update_layout(
        paper_bgcolor="#0f1318",
        plot_bgcolor="#0f1318",
        scene=dict(
            xaxis=dict(
                range=[-BOUNDS_M, BOUNDS_M], title="East (m)",
                backgroundcolor="#141d2b",
                gridcolor="#2a3a55", zerolinecolor="#4a6080",
                showbackground=True, color="#a0b0c8",
                tickfont=dict(size=11, color="#8899aa"),
            ),
            yaxis=dict(
                range=[-BOUNDS_M, BOUNDS_M], title="North (m)",
                backgroundcolor="#141d2b",
                gridcolor="#2a3a55", zerolinecolor="#4a6080",
                showbackground=True, color="#a0b0c8",
                tickfont=dict(size=11, color="#8899aa"),
            ),
            zaxis=dict(
                range=[0, ALT_MAX + 20], title="고도 (m)",
                backgroundcolor="#141d2b",
                gridcolor="#2a3a55", zerolinecolor="#4a6080",
                showbackground=True, color="#a0b0c8",
                tickfont=dict(size=11, color="#8899aa"),
            ),
            bgcolor="#0a1020",
            camera=dict(
                eye=dict(x=1.5, y=-1.7, z=1.3),
                up=dict(x=0, y=0, z=1),
            ),
            aspectmode="manual",
            aspectratio=dict(x=2.0, y=2.0, z=0.55),
            dragmode="orbit",
        ),
        legend=dict(
            font=dict(color="#d0d8e0", size=11),
            bgcolor="rgba(15,19,24,0.9)",
            bordercolor="#3a4a60",
            borderwidth=1,
            x=0.01, y=0.98,
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        uirevision="stable",
    )
    return fig
