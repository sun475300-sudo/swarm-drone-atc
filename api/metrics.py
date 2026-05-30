"""P718: Prometheus 메트릭 — 운영 가시성 (Observability).

메트릭 목록:
    sdacs_active_drones          — 현재 활성 드론 수 (게이지)
    sdacs_active_conflicts       — 현재 충돌 감지 수 (게이지)
    sdacs_advisories_total       — 누적 어드바이저리 발행 수 (카운터)
    sdacs_ws_subscribers         — WebSocket 구독자 수 (게이지)
    sdacs_run_duration_seconds   — 시뮬레이션 실행 시간 히스토그램

Prometheus 스크레이프 엔드포인트: GET /metrics
"""

from __future__ import annotations

try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )
    _PROMETHEUS_AVAILABLE = True
except ImportError:
    _PROMETHEUS_AVAILABLE = False

from fastapi import Response

# ── 메트릭 정의 ──────────────────────────────────────────────────────

if _PROMETHEUS_AVAILABLE:
    ACTIVE_DRONES = Gauge("sdacs_active_drones", "현재 활성 드론 수")
    ACTIVE_CONFLICTS = Gauge("sdacs_active_conflicts", "현재 감지된 충돌 수")
    ADVISORIES_TOTAL = Counter(
        "sdacs_advisories_total",
        "누적 어드바이저리 발행 수",
        ["advisory_type"],
    )
    WS_SUBSCRIBERS = Gauge("sdacs_ws_subscribers", "WebSocket 구독자 수")
    RUN_DURATION = Histogram(
        "sdacs_run_duration_seconds",
        "시뮬레이션 실행 시간",
        buckets=[1, 5, 10, 30, 60, 120, 300, 600],
    )
    HTTP_REQUESTS_TOTAL = Counter(
        "sdacs_http_requests_total",
        "HTTP 요청 수",
        ["method", "endpoint", "status"],
    )
else:
    # prometheus_client 미설치 시 no-op 스텁
    class _Noop:
        def inc(self, *a, **kw): pass
        def dec(self, *a, **kw): pass
        def set(self, *a, **kw): pass
        def observe(self, *a, **kw): pass
        def labels(self, *a, **kw): return self
        def time(self): return self
        def __enter__(self): return self
        def __exit__(self, *a): pass

    ACTIVE_DRONES = _Noop()  # type: ignore[assignment]
    ACTIVE_CONFLICTS = _Noop()  # type: ignore[assignment]
    ADVISORIES_TOTAL = _Noop()  # type: ignore[assignment]
    WS_SUBSCRIBERS = _Noop()  # type: ignore[assignment]
    RUN_DURATION = _Noop()  # type: ignore[assignment]
    HTTP_REQUESTS_TOTAL = _Noop()  # type: ignore[assignment]


def update_from_snapshot(drones: list, conflicts: list) -> None:
    """AppState 스냅샷에서 게이지 값을 갱신한다."""
    ACTIVE_DRONES.set(len(drones))
    ACTIVE_CONFLICTS.set(len(conflicts))


def record_advisory(advisory_type: str) -> None:
    """어드바이저리 발행 시 카운터를 증가시킨다."""
    ADVISORIES_TOTAL.labels(advisory_type=advisory_type).inc()


def set_ws_subscribers(count: int) -> None:
    """WebSocket 구독자 수를 갱신한다."""
    WS_SUBSCRIBERS.set(count)


async def metrics_endpoint() -> Response:
    """GET /metrics — Prometheus 스크레이프 엔드포인트."""
    if not _PROMETHEUS_AVAILABLE:
        return Response(
            content="# prometheus_client not installed\n",
            media_type="text/plain",
        )
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
