"""P717 — 부하 테스트 스크립트 단위 테스트."""

from __future__ import annotations

import pytest

from scripts.load_test import (
    HttpStats,
    WsStats,
    TARGET_FPS,
    TARGET_FRAME_MS,
    _percentile,
)


class TestPercentile:
    def test_median_even(self):
        data = [1.0, 2.0, 3.0, 4.0]
        assert _percentile(data, 50) == pytest.approx(2.5)

    def test_p100_is_max(self):
        data = [1.0, 5.0, 10.0]
        assert _percentile(data, 100) == pytest.approx(10.0)

    def test_p0_is_min(self):
        data = [3.0, 1.0, 2.0]
        assert _percentile(data, 0) == pytest.approx(1.0)

    def test_empty_returns_nan(self):
        import math
        assert math.isnan(_percentile([], 50))

    def test_single_element(self):
        assert _percentile([42.0], 95) == pytest.approx(42.0)


class TestTargetConstants:
    def test_fps_is_60(self):
        assert TARGET_FPS == 60.0

    def test_frame_ms_is_approx_16_67(self):
        assert TARGET_FRAME_MS == pytest.approx(1000.0 / 60.0)


class TestStatsDataclasses:
    def test_http_stats_defaults(self):
        s = HttpStats()
        assert s.latencies_ms == []
        assert s.errors == 0
        assert s.requests == 0

    def test_ws_stats_defaults(self):
        s = WsStats()
        assert s.frame_intervals_ms == []
        assert s.frames == 0
        assert s.errors == 0


class TestPassCriteria:
    """부하 테스트 PASS/FAIL 기준 검증."""

    def test_pass_when_p95_within_target(self):
        # p95 <= 33.3ms (30fps 최저선)면 PASS
        intervals = [16.0] * 100  # 정확히 60fps
        p95 = _percentile(intervals, 95)
        assert p95 <= TARGET_FRAME_MS * 2

    def test_fail_when_p95_exceeds_target(self):
        intervals = [50.0] * 100  # 20fps — 목표 미달
        p95 = _percentile(intervals, 95)
        assert p95 > TARGET_FRAME_MS * 2
