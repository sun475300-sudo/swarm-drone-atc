"""
군집드론 공역통제 자동화 시스템 — 3D 실시간 시각화 시뮬레이터
=============================================================
실행:  python visualization/simulator_3d.py
브라우저: http://localhost:8050

이 파일은 서브모듈에서 모든 심볼을 re-export하는 파사드입니다.
실제 구현은 아래 서브모듈에 위치합니다:
  - _domain.py        : SimState
  - _embedded_sim.py  : _in_nfz, _assign_goal, _step, _update, _sim_loop
  - _scene_traces.py  : 3D trace builders, build_figure, 공역 상수
  - _callbacks.py     : register_callbacks
  - _layout.py        : make_layout
"""

from __future__ import annotations

import os
import sys
import threading

# 프로젝트 루트를 Python 경로에 추가
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import dash
from dash import html

# -- 레이아웃 & 콜백 --
from visualization._callbacks import _mini_chart_layout, register_callbacks

# -- 도메인 --
from visualization._domain import SimState

# -- 시뮬레이션 엔진 --
from visualization._embedded_sim import (
    _assign_goal,
    _in_nfz,
    _sim_loop,
    _step,
    _update,
)
from visualization._layout import make_layout

# -- 공역 상수 & 3D trace builders --
from visualization._scene_traces import (
    _NFZ_OBSTACLES,
    _PAD_LIST,
    ALT_MAX,
    ALT_MIN,
    BOUNDS_M,
    CORRIDOR_EW,
    CORRIDOR_NS,
    CRUISE_ALT,
    LANDING_PADS,
    NFZ_X,
    NFZ_Y,
    NFZ_Z,
    PHASE_COLORS,
    PHASE_KO,
    _apf_vector_field,
    _corridor_traces,
    _ground_grid,
    _nfz_edges,
    _nfz_mesh,
    _pad_trace,
    _sector_overlay,
    _threat_heatmap_overlay,
    _wind_arrow,
    build_figure,
)

# -- 전역 시뮬레이션 인스턴스 --
SIM = SimState()
SIM.reset(30)

# -- Dash 앱 생성 --
app = dash.Dash(
    __name__,
    title="군집드론 공역통제 3D 시뮬레이터",
    update_title=None,
)
app.layout = make_layout(SIM)
register_callbacks(app, SIM)

# -- 진입점 --
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
