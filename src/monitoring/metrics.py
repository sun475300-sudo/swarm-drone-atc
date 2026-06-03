"""P718 — SDACS Prometheus 메트릭 정의 및 FastAPI 미들웨어.

사용법:
    from src.monitoring.metrics import get_metrics_router, instrument_app

    app = FastAPI()
    instrument_app(app)           # 미들웨어 + /metrics 엔드포인트 등록
    app.include_router(get_metrics_router())
"""

from __future__ import annotations

import time
from typing import Callable

try:
    from prometheus_client import (
        Counter,
        Gauge,
        Histogram,
        REGISTRY,
        CollectorRegistry,
        generate_latest,
        CONTENT_TYPE_LATEST,
    )
    from fastapi import APIRouter, Request, Response
    from fastapi.routing import APIRoute
    _PROMETHEUS_AVAILABLE = True
except ImportError:  # prometheus_client 없을 때 graceful degradation
    _PROMETHEUS_AVAILABLE = False

# ---------------------------------------------------------------------------
# 메트릭 인스턴스 정의
# ---------------------------------------------------------------------------

if _PROMETHEUS_AVAILABLE:
    # API 요청 총 횟수 — method, endpoint, status 레이블로 집계
    api_requests_total = Counter(
        "api_requests_total",
        "FastAPI 엔드포인트별 총 요청 수",
        labelnames=["method", "endpoint", "status"],
    )

    # 공역 충돌 감지 총 횟수 — resolution_type 레이블
    conflict_detected_total = Counter(
        "conflict_detected_total",
        "드론 간 공역 충돌 감지 총 횟수",
        labelnames=["resolution_type"],
    )

    # 요청 처리 소요 시간 히스토그램 — SLO 100ms 기준으로 버킷 설계
    request_duration_seconds = Histogram(
        "request_duration_seconds",
        "API 요청 처리 소요 시간 (초)",
        labelnames=["method", "endpoint"],
        buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    )

    # 현재 활성 드론 수 — 실시간 게이지
    active_drones = Gauge(
        "active_drones",
        "현재 시뮬레이션에서 활성 상태인 드론 수",
    )

    # 시뮬레이션 실시간 배율 (Real-Time Factor)
    simulation_rtf = Gauge(
        "simulation_rtf",
        "시뮬레이션 실시간 배율 (1.0 = 실시간, >1 = 가속)",
    )
else:
    # prometheus_client 미설치 시 더미 객체 — 운영 외 환경 대응
    class _DummyMetric:  # noqa: D101
        def labels(self, **_: object) -> "_DummyMetric":
            return self

        def inc(self, *_: object) -> None: ...
        def observe(self, *_: object) -> None: ...
        def set(self, *_: object) -> None: ...

    api_requests_total = _DummyMetric()       # type: ignore[assignment]
    conflict_detected_total = _DummyMetric()  # type: ignore[assignment]
    request_duration_seconds = _DummyMetric() # type: ignore[assignment]
    active_drones = _DummyMetric()            # type: ignore[assignment]
    simulation_rtf = _DummyMetric()           # type: ignore[assignment]


# ---------------------------------------------------------------------------
# FastAPI 미들웨어 — 모든 요청에 자동 계측
# ---------------------------------------------------------------------------

def _make_middleware(app_instance: object) -> Callable:
    """요청 수 + 응답 시간을 자동으로 기록하는 ASGI 미들웨어 팩토리."""

    async def prometheus_middleware(request: "Request", call_next: Callable) -> "Response":
        start_time = time.perf_counter()

        # 요청 처리
        response = await call_next(request)

        # 경로 정규화 — path parameter를 {param} 형태로 치환하여 카디널리티 폭발 방지
        endpoint = _normalize_path(request)
        method = request.method
        status = str(response.status_code)
        elapsed = time.perf_counter() - start_time

        api_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
        request_duration_seconds.labels(method=method, endpoint=endpoint).observe(elapsed)

        return response

    return prometheus_middleware


def _normalize_path(request: "Request") -> str:
    """라우트 템플릿 경로 반환 (예: /api/runs/{run_id}). 없으면 원본 경로."""
    if not _PROMETHEUS_AVAILABLE:
        return request.url.path

    # FastAPI Request.scope에서 matched route 정보 추출
    route: APIRoute | None = request.scope.get("route")
    if route is not None:
        return getattr(route, "path", request.url.path)
    return request.url.path


def instrument_app(app: object) -> None:
    """FastAPI app에 Prometheus 미들웨어를 등록합니다.

    Args:
        app: FastAPI 애플리케이션 인스턴스.
    """
    if not _PROMETHEUS_AVAILABLE:
        return

    from starlette.middleware.base import BaseHTTPMiddleware  # type: ignore[import]

    middleware = _make_middleware(app)
    app.add_middleware(BaseHTTPMiddleware, dispatch=middleware)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# /metrics 엔드포인트 라우터
# ---------------------------------------------------------------------------

def get_metrics_router() -> "APIRouter":
    """prometheus 스크레이프용 /metrics 엔드포인트 라우터를 반환합니다.

    FastAPI app에 include_router()로 등록하세요:

        app.include_router(get_metrics_router())
    """
    if not _PROMETHEUS_AVAILABLE:
        # prometheus_client 없을 때 빈 라우터 반환
        try:
            from fastapi import APIRouter as _APIRouter
            return _APIRouter()
        except ImportError:
            raise RuntimeError("FastAPI가 설치되어 있지 않습니다.")

    router = APIRouter(tags=["observability"])

    @router.get(
        "/metrics",
        summary="Prometheus 메트릭 스크레이프 엔드포인트",
        response_class=Response,
        include_in_schema=False,  # Swagger UI에서 숨김
    )
    async def metrics_endpoint() -> Response:
        """Prometheus 형식의 메트릭 데이터를 반환합니다."""
        data = generate_latest(REGISTRY)
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)

    return router


# ---------------------------------------------------------------------------
# 헬퍼 함수 — 시뮬레이션 레이어에서 직접 호출
# ---------------------------------------------------------------------------

def record_conflict(resolution_type: str = "apf") -> None:
    """충돌 감지 이벤트를 기록합니다.

    Args:
        resolution_type: 해결 방식 ("apf", "cbs", "reroute" 등).
    """
    conflict_detected_total.labels(resolution_type=resolution_type).inc()


def update_active_drones(count: int) -> None:
    """활성 드론 수 게이지를 업데이트합니다.

    Args:
        count: 현재 활성 드론 수.
    """
    active_drones.set(count)


def update_simulation_rtf(rtf: float) -> None:
    """시뮬레이션 RTF 게이지를 업데이트합니다.

    Args:
        rtf: 실시간 배율 값 (예: 2.0 = 2배속).
    """
    simulation_rtf.set(rtf)
