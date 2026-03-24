"""
pytest 공통 픽스처
"""
from __future__ import annotations
import os
import sys

import numpy as np
import pytest

# 프로젝트 루트를 sys.path에 추가
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


# ── 공통 픽스처 ──────────────────────────────────────────────────────────

@pytest.fixture
def rng():
    return np.random.default_rng(42)


@pytest.fixture
def airspace_bounds():
    return {"x": [-2000, 2000], "y": [-2000, 2000], "z": [0, 200]}


@pytest.fixture
def no_fly_zones():
    return [{"center": np.array([0.0, 0.0, 0.0]), "radius_m": 200.0}]


@pytest.fixture
def sim_config(tmp_path):
    """최소한의 시뮬레이션 설정 YAML 경로"""
    import yaml

    cfg = {
        "simulation": {"hz": 10, "realtime": False},
        "drones": {"count": 4, "profiles": ["COMMERCIAL_DELIVERY"]},
        "airspace": {
            "bounds_km": {"x": [-2, 2], "y": [-2, 2], "z": [0, 0.15]},
            "no_fly_zones": [
                {"center": [0, 0, 0], "radius_m": 200, "label": "TEST_NFZ"}
            ],
        },
        "separation_standards": {
            "lateral_min_m": 50.0,
            "vertical_min_m": 15.0,
            "near_miss_lateral_m": 10.0,
            "conflict_lookahead_s": 90.0,
        },
        "controller": {"max_concurrent_clearances": 50},
        "logging": {"save_trajectory": False},
    }
    p = tmp_path / "test_sim.yaml"
    with open(p, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f)
    return str(p)
