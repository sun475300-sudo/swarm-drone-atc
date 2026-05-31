"""P718 — Prometheus 관측성 메트릭.

FastAPI 미들웨어에서 HTTP 요청 지표를 수집하고,
/metrics 엔드포인트로 Prometheus scrape 형식을 반환한다.

사용:
    from api.metrics import instrument_app, metrics_endpoint
    instrument_app(app)
    app.add_api_route("/metrics", metrics_endpoint, include_in_schema=False)
"""

from __future__ import annotations

import time
from typing import Callable

try:
    import prometheus_client as prom
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
except ImportError as exc:
    raise RuntimeError(
        "prometheus-client required: pip install prometheus-client"
    ) from exc

try:
    from fastapi import Request, Response
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.routing import Match
except ImportError as exc:
    raise RuntimeError("fastapi / starlette required") from exc

# ---------- 메트릭 정의 ----------

REQUEST_COUNT = prom.Counter(
    "sdacs_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

REQUEST_LATENCY = prom.Histogram(
    "sdacs_http_request_duration_seconds",
    "HTTP request duration",
    ["method", "path"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

WS_CONNECTIONS = prom.Gauge(
    "sdacs_ws_active_connections",
    "Active WebSocket telemetry subscribers",
)

RUN_TOTAL = prom.Counter(
    "sdacs_scenario_runs_total",
    "Scenario runs started",
    ["scenario", "status"],
)

DRONE_COUNT = prom.Gauge(
    "sdacs_airspace_drones",
    "Drones currently tracked in airspace snapshot",
)

CONFLICT_TOTAL = prom.Counter(
    "sdacs_conflicts_detected_total",
    "Conflict detection events",
)


# ---------- 미들웨어 ----------


class PrometheusMiddleware(BaseHTTPMiddleware):
    """모든 HTTP 요청의 카운터·지연시간을 기록한다."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = _matched_route(request)
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start
        REQUEST_COUNT.labels(
            method=request.method,
            path=path,
            status=response.status_code,
        ).inc()
        REQUEST_LATENCY.labels(method=request.method, path=path).observe(duration)
        return response


def _matched_route(request: Request) -> str:
    """라우트 파라미터를 제거한 패턴 경로를 반환한다 (예: /api/runs/{run_id})."""
    for route in request.app.routes:
        match, _ = route.matches(request.scope)
        if match == Match.FULL:
            return getattr(route, "path", request.url.path)
    return request.url.path


# ---------- 엔드포인트 ----------


async def metrics_endpoint() -> Response:
    """Prometheus scrape 형식 데이터를 반환한다."""
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


# ---------- 앱 계측 ----------


def instrument_app(app) -> None:  # type: ignore[type-arg]
    """FastAPI 앱에 Prometheus 미들웨어와 /metrics 엔드포인트를 등록한다."""
    app.add_middleware(PrometheusMiddleware)
    app.add_api_route("/metrics", metrics_endpoint, include_in_schema=False)
