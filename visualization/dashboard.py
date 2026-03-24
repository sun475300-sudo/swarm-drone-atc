"""
Plotly Dash 3D 대시보드
드론 궤적 시각화 + 공역 경계 + NFZ + 재생 슬라이더
"""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import yaml

logger = logging.getLogger("sdacs.dashboard")

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def _load_airspace_zones() -> dict:
    with open(CONFIG_DIR / "airspace_zones.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _build_zone_traces(zones_cfg: dict) -> list[go.Scatter3d]:
    """공역 구역 경계선 트레이스"""
    traces = []

    for zone in zones_cfg.get("zones", []):
        bx = zone["bounds"]["x"]
        by = zone["bounds"]["y"]
        alt = zone.get("altitude_band", {}).get("max_m", 120)
        color = "rgba(255,0,0,0.3)" if zone["type"] == "NO_FLY" else "rgba(100,200,255,0.15)"
        name = zone["name"]

        # 바닥 사각형
        xs = [bx[0]*1000, bx[1]*1000, bx[1]*1000, bx[0]*1000, bx[0]*1000]
        ys = [by[0]*1000, by[0]*1000, by[1]*1000, by[1]*1000, by[0]*1000]
        zs = [alt] * 5
        traces.append(go.Scatter3d(
            x=xs, y=ys, z=zs,
            mode="lines",
            line=dict(color=color, width=3),
            name=name,
            showlegend=True,
        ))

    return traces


def _build_corridor_traces(zones_cfg: dict) -> list[go.Scatter3d]:
    traces = []
    for cor in zones_cfg.get("corridors", []):
        wps = cor["waypoints"]
        xs = [w[0]*1000 for w in wps]
        ys = [w[1]*1000 for w in wps]
        zs = [w[2] for w in wps]
        traces.append(go.Scatter3d(
            x=xs, y=ys, z=zs,
            mode="lines+markers",
            line=dict(color="rgba(255,200,0,0.7)", width=4),
            marker=dict(size=3, color="gold"),
            name=cor["name"],
        ))
    return traces


def create_trajectory_figure(trajectory_log: list[dict]) -> go.Figure:
    """궤적 로그 → 3D Plotly 피규어"""
    zones_cfg = _load_airspace_zones()
    fig = go.Figure()

    # 공역 경계
    for tr in _build_zone_traces(zones_cfg):
        fig.add_trace(tr)
    for tr in _build_corridor_traces(zones_cfg):
        fig.add_trace(tr)

    if not trajectory_log:
        fig.update_layout(title="시뮬레이션 데이터 없음", template="plotly_dark")
        return fig

    # 드론별 궤적
    import pandas as pd
    df = pd.DataFrame(trajectory_log)
    drone_ids = df["drone_id"].unique()

    # 색상 팔레트
    colors = [
        f"hsl({int(i * 360 / max(len(drone_ids), 1))}, 80%, 60%)"
        for i in range(len(drone_ids))
    ]

    # 최대 20기만 개별 궤적 표시 (성능)
    show_ids = drone_ids[:20]
    for idx, did in enumerate(show_ids):
        ddf = df[df["drone_id"] == did]
        fig.add_trace(go.Scatter3d(
            x=ddf["x"], y=ddf["y"], z=ddf["z"],
            mode="lines",
            line=dict(color=colors[idx], width=2),
            name=did,
            opacity=0.6,
        ))

    # 최종 위치 (모든 드론)
    last_t = df["t"].max()
    last = df[df["t"] == last_t]
    fig.add_trace(go.Scatter3d(
        x=last["x"], y=last["y"], z=last["z"],
        mode="markers",
        marker=dict(
            size=4, color=last["battery_pct"],
            colorscale="RdYlGn", cmin=0, cmax=100,
            colorbar=dict(title="배터리 %"),
        ),
        name="최종 위치",
        text=last["drone_id"],
    ))

    fig.update_layout(
        title="군집드론 공역통제 3D 궤적",
        template="plotly_dark",
        scene=dict(
            xaxis_title="동 (m)",
            yaxis_title="북 (m)",
            zaxis_title="고도 (m)",
            aspectmode="data",
        ),
        width=1200, height=800,
        legend=dict(font=dict(size=9)),
    )
    return fig


def launch_dashboard(trajectory_log: list[dict], port: int = 8050):
    """Dash 앱 기동"""
    try:
        from dash import Dash, dcc, html
        from dash.dependencies import Input, Output
    except ImportError:
        logger.error("dash 패키지가 필요합니다: pip install dash")
        return

    app = Dash(__name__)

    fig = create_trajectory_figure(trajectory_log)

    # 시간 슬라이더용 데이터
    import pandas as pd
    if trajectory_log:
        df = pd.DataFrame(trajectory_log)
        times = sorted(df["t"].unique())
        max_t = times[-1] if times else 0
    else:
        times = [0]
        max_t = 0

    app.layout = html.Div(
        style={"backgroundColor": "#111", "color": "#eee", "padding": "20px"},
        children=[
            html.H1(
                "🛸 군집드론 공역통제 시스템 — 3D 대시보드",
                style={"textAlign": "center", "color": "#4fc3f7"},
            ),
            html.Div([
                html.Label("시뮬레이션 시간 (초)", style={"color": "#aaa"}),
                dcc.Slider(
                    id="time-slider",
                    min=0, max=max_t,
                    step=max(1, max_t / 100),
                    value=max_t,
                    marks={int(t): f"{int(t)}s" for t in times[::max(1, len(times)//10)]},
                    tooltip={"placement": "bottom"},
                ),
            ], style={"margin": "20px 0"}),
            dcc.Graph(id="3d-plot", figure=fig, style={"height": "80vh"}),
            html.Div(
                id="stats-panel",
                style={"marginTop": "20px", "fontFamily": "monospace", "fontSize": "14px"},
            ),
        ],
    )

    @app.callback(
        Output("3d-plot", "figure"),
        Output("stats-panel", "children"),
        Input("time-slider", "value"),
    )
    def update_figure(selected_time):
        if not trajectory_log:
            return fig, "데이터 없음"
        filtered = [r for r in trajectory_log if r["t"] <= selected_time]
        new_fig = create_trajectory_figure(filtered)
        n_drones = len(set(r["drone_id"] for r in filtered))
        stats = f"t={selected_time:.0f}s | 활성 드론: {n_drones}기"
        return new_fig, stats

    logger.info("대시보드 시작: http://127.0.0.1:%d", port)
    print(f"\n  🌐  http://127.0.0.1:{port}\n")
    app.run(debug=False, port=port)
