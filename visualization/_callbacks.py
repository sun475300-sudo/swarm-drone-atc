"""
Dash 콜백 등록.

register_callbacks(app, sim) 을 호출하면 모든 콜백이 app에 등록된다.
SIM 전역을 직접 참조하지 않고 sim 파라미터를 클로저로 캡처한다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import plotly.graph_objects as go
from dash import Input, Output, State, callback_context, html

from simulation.threat_assessment import ThreatLevel
from src.airspace_control.agents.drone_state import FlightPhase
from visualization._layout import _gpu_progress_bar, _stat
from visualization._scene_traces import CAMERA_PRESETS, PHASE_KO, build_figure

if TYPE_CHECKING:
    import dash

    from visualization._domain import SimState


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


def register_callbacks(app: dash.Dash, sim: SimState) -> None:
    """모든 Dash 콜백을 app에 등록한다."""

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
            sim.running = True
            return True
        if btn == "btn-pause":
            sim.running = False
            return False
        if btn == "btn-reset":
            sim.running = False
            sim.reset(int(n_drones or 30))
            return False
        return running

    @app.callback(
        Output("_dummy-wind", "children"),
        Input("wind-check", "value"),
        prevent_initial_call=True,
    )
    def _wind(value):
        with sim.lock:
            sim.wind = np.array([2.0, -1.5, 0.0]) if (value and "on" in value) else np.zeros(3)
        return ""

    @app.callback(
        Output("_dummy-apf", "children"),
        Input("apf-field-check", "value"),
        prevent_initial_call=True,
    )
    def _apf_toggle(value):
        with sim.lock:
            sim.show_apf_field = bool(value and "on" in value)
        return ""

    @app.callback(
        Output("slider-speed", "className"),
        Input("slider-speed", "value"),
        prevent_initial_call=True,
    )
    def _speed(value):
        sim.speed_multiplier = float(value or 1.0)
        return ""

    @app.callback(
        Output("store-camera", "data"),
        Input("dropdown-camera", "value"),
        prevent_initial_call=True,
    )
    def _camera_preset(value: str):
        return value or "기본 3D"

    @app.callback(
        Output("_dummy-scenario", "children"),
        Input("dropdown-scenario", "value"),
        prevent_initial_call=True,
    )
    def _apply_scenario(scenario: str):
        drone_counts = {
            "default":                      30,
            "high_density":                 80,
            "emergency_failure":            40,
            "mass_takeoff":                 60,
            "route_conflict":               20,
            "comms_loss":                   30,
            "weather_disturbance":          25,
            "adversarial_intrusion":        35,
            "swarm_autonomous_no_preplan":  50,
            "multi_city":                   70,
        }
        n = drone_counts.get(scenario, 30)
        sim.running = False
        sim.reset(n)
        return ""

    @app.callback(
        Output("graph-3d",           "figure"),
        Output("hdr-time",           "children"),
        Output("hdr-fps",            "children"),
        Output("gpu-stats",          "children"),
        Output("gpu-utilization",    "children"),
        Output("drone-count-panel",  "children"),
        Output("stats",              "children"),
        Output("alert-log",          "children"),
        Output("chart-battery-dist", "figure"),
        Output("chart-alt-dist",     "figure"),
        Output("chart-speed-dist",   "figure"),
        Output("chart-energy-ts",    "figure"),
        Output("chart-cr-rate",      "figure"),
        Output("threat-panel",       "children"),
        Output("sla-panel",          "children"),
        Output("sector-panel",       "children"),
        Output("chart-tick-perf",    "figure"),
        Output("chart-timeline",     "figure"),
        Input("interval",            "n_intervals"),
        State("store-camera",        "data"),
    )
    def _refresh(_n, camera_preset):
        fig = build_figure(sim)

        # 카메라 프리셋 적용
        cam = CAMERA_PRESETS.get(camera_preset or "기본 3D",
                                CAMERA_PRESETS["기본 3D"])
        fig.update_layout(scene_camera=cam)

        with sim.lock:
            t          = sim.t
            drones     = list(sim.drones.values())
            conflicts  = sim.conflicts
            near_miss  = sim.near_misses
            advisories = sim.advisories
            collisions = sim.collisions
            threat_mat = sim.threat_matrix.copy() if sim.threat_matrix else {}
            sla_viols  = list(sim.sla_violations)
            sector_st  = sim.sector_mgr.sector_stats()
            tick_times = list(sim.tick_times_ms)
            timeline_events = sim.timeline._events[-20:] if sim.timeline._events else []

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
            f"{'▶ 실행 중' if sim.running else '⏸ 일시정지'}"
        )

        latest = sim.metrics.latest
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

        # ── 경보 로그
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
        overall_level = threat_mat.get("overall_level", ThreatLevel.LOW)
        if overall_level >= ThreatLevel.HIGH:
            level_name = overall_level.name if hasattr(overall_level, 'name') else str(overall_level)
            alert_items.append(
                html.Div(f"[T+{mins:02d}:{secs:02d}] ⚠ 위협 레벨: {level_name}",
                          style={"color": "#FF5722" if overall_level >= ThreatLevel.CRITICAL else "#FF9800"}))
        alert_div = html.Div(alert_items) if alert_items else "✅ 경보 없음"

        # ── 배터리 분포 바 차트
        bat_hist = sim.metrics.battery_distribution()
        bat_labels = [f"{i*10}-{i*10+10}%" for i in range(10)]
        bat_colors = ["#F44336" if i < 2 else "#FF9800" if i < 4
                      else "#4CAF50" for i in range(10)]
        fig_bat = go.Figure(go.Bar(x=bat_labels, y=bat_hist, marker_color=bat_colors))
        fig_bat.update_layout(**_mini_chart_layout())

        # ── 고도 분포 히스토그램
        alts = [d.position[2] for d in drones if d.is_active and d.position[2] > 1]
        fig_alt = go.Figure()
        if alts:
            fig_alt.add_trace(go.Histogram(
                x=alts, nbinsx=12,
                marker_color="#29B6F6",
                opacity=0.8,
            ))
            # 순항 고도 기준선
            fig_alt.add_vline(x=60, line_dash="dash", line_color="#FFD700",
                              line_width=1, annotation_text="순항",
                              annotation_font_size=8, annotation_font_color="#FFD700")
        fig_alt.update_layout(**_mini_chart_layout())
        fig_alt.update_xaxes(title_text="고도 (m)", title_font_size=8)

        # ── 속도 분포 히스토그램
        speeds = [d.speed for d in drones if d.is_active and d.speed > 0.1]
        fig_spd = go.Figure()
        if speeds:
            fig_spd.add_trace(go.Histogram(
                x=speeds, nbinsx=10,
                marker_color="#69F0AE",
                opacity=0.8,
            ))
            avg_spd = sum(speeds) / len(speeds)
            fig_spd.add_vline(x=avg_spd, line_dash="dash", line_color="#FFEA00",
                              line_width=1, annotation_text=f"평균 {avg_spd:.1f}",
                              annotation_font_size=8, annotation_font_color="#FFEA00")
        fig_spd.update_layout(**_mini_chart_layout())
        fig_spd.update_xaxes(title_text="속도 (m/s)", title_font_size=8)

        # ── 에너지 소모 시계열
        ts_t, ts_e = sim.metrics.time_series("total_energy_wh")
        fig_energy = go.Figure(go.Scatter(
            x=ts_t, y=ts_e, mode="lines",
            line=dict(color="#FFD700", width=1.5),
            fill="tozeroy", fillcolor="rgba(255,215,0,0.1)",
        ))
        fig_energy.update_layout(**_mini_chart_layout())
        fig_energy.update_xaxes(title_text="시간 (s)", title_font_size=8)

        # ── 충돌 해결률 시계열
        ts_t2, ts_cr = sim.metrics.time_series("conflict_resolution_rate")
        fig_cr = go.Figure(go.Scatter(
            x=ts_t2, y=ts_cr, mode="lines",
            line=dict(color="#00E676", width=1.5),
            fill="tozeroy", fillcolor="rgba(0,230,118,0.1)",
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
            *[html.Div(f"→ {action}",
                       style={"color": "#c9d1d9", "fontSize": "9px",
                              "marginTop": "2px", "lineHeight": "1.3"})
              for action in threat_mat.get("recommended_actions", [])[:2]],
        ])

        # ── SLA 패널
        if sla_viols:
            sla_items = []
            for v in sla_viols[:3]:
                name = v.threshold_name if hasattr(v, 'threshold_name') else str(v)
                sla_items.append(html.Div(f"❌ {name}", style={"color": "#F44336", "fontSize": "10px"}))
            sla_div = html.Div(sla_items)
        else:
            sla_div = html.Div("✅ 모든 SLA 충족", style={"color": "#00E676", "fontSize": "10px"})

        # ── 구역별 현황 패널
        sector_items = []
        for sid, st in sorted(sector_st.items()):
            n_d = st["drones"]
            ho = st["handoffs_in"] + st["handoffs_out"]
            density = st["density"]
            d_color = "#F44336" if density > 4.0 else "#FF9800" if density > 2.0 else "#c9d1d9"
            sector_items.append(html.Div([
                html.Span(f"{sid}: ", style={"color": "#8b949e", "fontSize": "10px"}),
                html.Span(f"{n_d}기", style={"color": d_color, "fontSize": "10px", "fontWeight": "600"}),
                html.Span(f" ({density:.1f}/km²) H:{ho}", style={"color": "#6e7681", "fontSize": "9px"}),
            ], style={"marginBottom": "2px"}))
        sector_div = html.Div(sector_items)

        # ── 틱 처리시간 차트
        fig_tick = go.Figure()
        if tick_times:
            fig_tick.add_trace(go.Scatter(
                y=tick_times[-100:], mode="lines",
                line=dict(color="#AB47BC", width=1.2),
                fill="tozeroy", fillcolor="rgba(171,71,188,0.1)",
            ))
            avg_ms = sum(tick_times[-100:]) / len(tick_times[-100:])
            fig_tick.add_hline(y=avg_ms, line_dash="dash", line_color="#6e7681", line_width=1)
        fig_tick.update_layout(**_mini_chart_layout())
        fig_tick.update_layout(height=90)
        fig_tick.update_yaxes(title_text="ms", title_font_size=7)

        # ── 이벤트 타임라인 미니 차트
        fig_tl = go.Figure()
        if timeline_events:
            ev_times = [e.t for e in timeline_events]
            ev_types = [e.event_type for e in timeline_events]
            ev_colors_map = {"COLLISION": "#F44336", "EVADING": "#FF9800", "NFZ_VIOLATION": "#FF1744"}
            ev_colors = [ev_colors_map.get(et, "#42A5F5") for et in ev_types]
            fig_tl.add_trace(go.Scatter(
                x=ev_times, y=[1] * len(ev_times), mode="markers",
                marker=dict(size=8, color=ev_colors, symbol="diamond"),
                text=ev_types,
                hovertemplate="%{text} @ %{x:.1f}s<extra></extra>",
            ))
        fig_tl.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=20, r=8, t=2, b=15),
            xaxis=dict(color="#6e7681", gridcolor="#21262d",
                       tickfont=dict(size=7), title_text="시간(s)", title_font_size=7),
            yaxis=dict(visible=False),
            showlegend=False, height=60,
        )

        # ── GPU 메트릭 패널
        try:
            from simulation.apf_engine import get_apf_backend_info
            gpu_info = get_apf_backend_info()
            gpu_name = gpu_info.get("gpu", "N/A") or "CPU"
            gpu_backend = gpu_info.get("backend", "numpy")
            gpu_vram = gpu_info.get("vram_gb", "")
            is_gpu = gpu_info.get("device", "cpu") != "cpu" and gpu_name != "CPU"
            mode_label = "GPU" if is_gpu else "CPU"
            mode_color = "#00ff88" if is_gpu else "#FF9800"
            gpu_children = [
                _stat("연산 모드", mode_label),
                _stat("백엔드", gpu_backend),
                _stat("디바이스", gpu_name),
            ]
            if gpu_vram:
                gpu_children.append(_stat("VRAM", f"{gpu_vram} GB"))
            if gpu_info.get("n_gpus", 0) > 1:
                gpu_children.append(_stat("GPU 수", str(gpu_info["n_gpus"])))
            if gpu_info.get("multi_gpu"):
                gpu_children.append(_stat("멀티GPU", "활성"))
        except Exception:
            gpu_children = [_stat("연산 모드", "CPU"), _stat("백엔드", "numpy-cpu")]
            mode_color = "#FF9800"
        gpu_div = html.Div(gpu_children)

        # ── GPU 사용률 (타이밍 기반)
        gpu_util_children = []
        if tick_times:
            recent = tick_times[-20:]
            avg_tick = sum(recent) / len(recent)
            max_tick = max(recent)
            gpu_util_children.append(_stat("평균 틱", f"{avg_tick:.1f} ms"))
            gpu_util_children.append(_stat("최대 틱", f"{max_tick:.1f} ms"))
            load_pct = min(avg_tick / 100.0 * 100, 100)
            gpu_util_children.append(
                _gpu_progress_bar("연산 부하", load_pct, 100.0, color=mode_color))
        gpu_util_div = html.Div(gpu_util_children)

        # ── FPS / 틱 레이트
        if tick_times and len(tick_times) >= 2:
            recent_ticks = tick_times[-10:]
            avg_ms = sum(recent_ticks) / len(recent_ticks)
            tps = 1000.0 / max(avg_ms, 0.1)
            fps_str = f"{tps:.1f} tps | {avg_ms:.1f} ms/tick"
        else:
            fps_str = "— tps"

        # ── 드론 현황 패널
        drone_count_children = []
        for phase_label, count in sorted(phase_cnt.items()):
            drone_count_children.append(_stat(phase_label, str(count)))
        drone_count_div = html.Div(drone_count_children)

        return (fig, time_str, fps_str, gpu_div, gpu_util_div, drone_count_div,
                stats_div, alert_div, fig_bat, fig_alt, fig_spd,
                fig_energy, fig_cr,
                threat_div, sla_div, sector_div, fig_tick, fig_tl)
