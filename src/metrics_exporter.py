"""Prometheus 메트릭 익스포터 — P718."""
from __future__ import annotations

try:
    from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
    _HAS_PROMETHEUS = True
except ImportError:
    _HAS_PROMETHEUS = False

if _HAS_PROMETHEUS:
    DRONE_COUNT = Gauge("sdacs_drone_count", "현재 활성 드론 수")
    CONFLICT_TOTAL = Counter("sdacs_conflict_total", "누적 충돌 감지 건수")
    RESOLUTION_TOTAL = Counter("sdacs_resolution_total", "누적 충돌 해결 건수", ["method"])
    WS_CONNECTIONS = Gauge("sdacs_ws_connections", "현재 WebSocket 연결 수")
    SIM_STEP_DURATION = Histogram(
        "sdacs_sim_step_seconds",
        "시뮬레이션 스텝 처리 시간",
        buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5],
    )


def get_metrics_response() -> tuple[bytes, str]:
    """Prometheus 스크레이프용 메트릭 바이트 반환."""
    if not _HAS_PROMETHEUS:
        return b"# prometheus_client not installed\n", "text/plain"
    return generate_latest(), CONTENT_TYPE_LATEST
