"""
pytest 공통 픽스처
"""
from __future__ import annotations

import asyncio
import os
import sys

import numpy as np
import pytest

# 프로젝트 루트를 sys.path에 추가
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


# ── 이벤트 루프 복구 픽스처 ───────────────────────────────────────────────
# pytest-xdist parallel mode에서 같은 worker가 여러 파일을 처리할 때,
# 이전 async 테스트가 event loop를 닫아두면 다음 sync 테스트의
# asyncio.get_event_loop().run_until_complete()가 RuntimeError를 일으킨다.
# async 테스트는 pytest-asyncio가 루프를 직접 관리하므로 건드리지 않는다.

@pytest.fixture(autouse=True)
def _ensure_open_event_loop(request):
    """sync 테스트에서 닫힌 event loop를 새로운 루프로 교체한다."""
    if asyncio.iscoroutinefunction(request.function):
        yield
        return

    try:
        loop = asyncio.get_event_loop_policy().get_event_loop()
        if loop is None or loop.is_closed():
            raise RuntimeError("closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    yield


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
        "drones": {"default_count": 4, "count": 4, "profiles": ["COMMERCIAL_DELIVERY"]},
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
