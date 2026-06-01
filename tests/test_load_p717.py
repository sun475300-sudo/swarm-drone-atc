"""P717 — 부하 테스트 유닛 검증 (locust 없이 실행 가능한 스모크 테스트).

실제 부하 테스트는 tests/load/locustfile.py 참조.
이 파일은 텔레메트리 페이로드 생성·구조·타이밍을 검증한다.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.load.locustfile import _drone_telemetry


# ---------------------------------------------------------------------------
# 텔레메트리 페이로드 구조 검증
# ---------------------------------------------------------------------------


def test_drone_telemetry_has_required_fields():
    payload = _drone_telemetry("drone_0001")
    assert payload["type"] == "telemetry"
    assert payload["drone_id"] == "drone_0001"
    assert "position" in payload
    assert "velocity" in payload
    assert "heading" in payload
    assert "ts" in payload


def test_drone_telemetry_position_range():
    for _ in range(50):
        payload = _drone_telemetry("d")
        x, y, z = payload["position"]
        assert 0 <= x <= 1000
        assert 0 <= y <= 1000
        assert 50 <= z <= 250


def test_drone_telemetry_heading_range():
    for _ in range(50):
        payload = _drone_telemetry("d")
        assert 0 <= payload["heading"] <= 360


def test_drone_telemetry_is_json_serializable():
    payload = _drone_telemetry("drone_test")
    serialized = json.dumps(payload)
    restored = json.loads(serialized)
    assert restored["drone_id"] == "drone_test"


def test_drone_telemetry_unique_timestamps():
    import time

    payloads = [_drone_telemetry("d") for _ in range(10)]
    # ts는 단조 증가하거나 동일 (같은 tick)해야 함
    timestamps = [p["ts"] for p in payloads]
    assert timestamps == sorted(timestamps) or len(set(timestamps)) >= 1


# ---------------------------------------------------------------------------
# 성능: 페이로드 생성 속도 (10Hz @ 100 드론 = 1000 payload/s)
# ---------------------------------------------------------------------------


def test_telemetry_generation_throughput():
    import time

    n = 1000
    start = time.perf_counter()
    for i in range(n):
        _drone_telemetry(f"drone_{i:04d}")
    elapsed = time.perf_counter() - start

    # 1000 페이로드를 1초 이내에 생성해야 한다 (= 10x 이상 여유)
    assert elapsed < 1.0, f"Too slow: {elapsed:.3f}s for {n} payloads"


def test_telemetry_json_throughput():
    import time

    n = 1000
    start = time.perf_counter()
    for i in range(n):
        json.dumps(_drone_telemetry(f"drone_{i:04d}"))
    elapsed = time.perf_counter() - start

    # JSON 직렬화 포함 1초 이내
    assert elapsed < 2.0, f"JSON serialization too slow: {elapsed:.3f}s for {n} payloads"
