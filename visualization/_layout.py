"""
Dash 앱 레이아웃 빌더.

make_layout(sim) → app.layout 에 할당할 컴포넌트 트리를 반환.
UI 헬퍼(_btn, _legend_row, _stat)도 여기서 소유.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import dash
from dash import dcc, html

from src.airspace_control.agents.drone_state import FlightPhase
from visualization._scene_traces import PHASE_COLORS, PHASE_KO, build_figure

if TYPE_CHECKING:
    from visualization._domain import SimState


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
# 레이아웃 빌더
# ─────────────────────────────────────────────────────────────

def make_layout(sim: SimState) -> html.Div:
    """Dash app.layout 에 할당할 전체 UI 컴포넌트 트리를 반환."""
    return html.Div(
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

                            # GPU 메트릭
                            html.Div("🟢 GPU 가속",
                                     style={"color": "#00ff88", "fontSize": "12px",
                                            "fontWeight": "600", "marginBottom": "8px"}),
                            html.Div(id="gpu-stats"),

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
                        figure=build_figure(sim),
                        style={"flex": "1", "height": "100%"},
                        config={
                            "displayModeBar": True,
                            "scrollZoom": True,
                            "modeBarButtonsToRemove": ["toImage"],
                        },
                    ),
                ],
            ),

            # ── 경보 로그 + 이벤트 타임라인 (하단 바)
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
