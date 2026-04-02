"""
시각 자산 관리 — 차트/이미지/SVG 자산의 인벤토리 관리 및 동기화 리포트
"""
from __future__ import annotations

import os

_ASSET_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "images")

_EXPECTED_ASSETS = [
    "throughput_vs_drones.png",
    "advisory_latency.png",
    "scenario_kpi_radar.png",
    "conflict_resolution_heatmap.png",
    "architecture.svg",
    "algorithm_flow.svg",
    "detection_pipeline.svg",
    "flight_phase_fsm.svg",
]


def load_asset_index() -> dict:
    index: dict[str, bool] = {}
    for name in _EXPECTED_ASSETS:
        path = os.path.join(_ASSET_DIR, name)
        index[name] = os.path.isfile(path)
    return index


def check_missing_assets() -> list[str]:
    index = load_asset_index()
    return [name for name, exists in index.items() if not exists]


def generate_sync_report() -> dict:
    index = load_asset_index()
    missing = [k for k, v in index.items() if not v]
    return {
        "total_assets": len(index),
        "present_assets": sum(1 for v in index.values() if v),
        "missing_assets": len(missing),
        "missing_list": missing,
    }
