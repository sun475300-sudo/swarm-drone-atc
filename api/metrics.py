"""P718 — Prometheus 메트릭 수집 모듈 (prometheus_client 기반)."""
from __future__ import annotations

try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )
    _HAS_PROMETHEUS = True
except ImportError:
    _HAS_PROMETHEUS = False

from fastapi import Response

# ─── 메트릭 정의 ─────────────────────────────────────────────────────────────
if _HAS_PROMETHEUS:
    sim_runs_total = Counter(
        "sdacs_sim_runs_total", "Total simulation runs started", ["scenario", "method"]
    )
    sim_run_duration_s = Histogram(
        "sdacs_sim_run_duration_seconds",
        "Simulation wall-clock duration",
        buckets=[1, 5, 10, 30, 60, 120, 300],
    )
    active_drones = Gauge("sdacs_active_drones", "Currently tracked drones in airspace")
    conflict_resolution_rate = Gauge(
        "sdacs_conflict_resolution_rate", "Last run conflict resolution rate (0-1)"
    )
    ws_connections = Gauge("sdacs_ws_connections_active", "Active WebSocket connections")
    api_requests_total = Counter(
        "sdacs_api_requests_total", "API request count", ["method", "endpoint", "status"]
    )
    api_latency_s = Histogram(
        "sdacs_api_latency_seconds",
        "API response latency",
        ["endpoint"],
        buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
    )
else:
    # no-op stubs so the rest of the code imports cleanly
    class _Noop:
        def labels(self, **_): return self
        def inc(self, *_): pass
        def set(self, *_): pass
        def observe(self, *_): pass
        def time(self): return self
        def __enter__(self): return self
        def __exit__(self, *_): pass

    sim_runs_total = _Noop()  # type: ignore
    sim_run_duration_s = _Noop()  # type: ignore
    active_drones = _Noop()  # type: ignore
    conflict_resolution_rate = _Noop()  # type: ignore
    ws_connections = _Noop()  # type: ignore
    api_requests_total = _Noop()  # type: ignore
    api_latency_s = _Noop()  # type: ignore


def metrics_endpoint() -> Response:
    """FastAPI GET /metrics 핸들러."""
    if not _HAS_PROMETHEUS:
        return Response("prometheus_client not installed", media_type="text/plain", status_code=501)
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
