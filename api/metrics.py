"""P718 — Prometheus 메트릭 수집 모듈.

FastAPI /metrics 엔드포인트에서 스크랩 가능한 메트릭을 노출한다.
prometheus_client 라이브러리가 없는 환경에서는 간략한 텍스트 포맷을 직접 생성한다.

수집 메트릭:
    sdacs_active_drones         — 현재 추적 중인 드론 수
    sdacs_conflicts_total       — 누적 충돌 감지 횟수
    sdacs_ws_subscribers        — WebSocket 연결 수
    sdacs_api_requests_total    — HTTP 요청 수 (endpoint, method, status 레이블)
    sdacs_api_latency_seconds   — HTTP 응답 시간 히스토그램
    sdacs_runs_total            — 시뮬레이션 실행 수 (status 레이블)
    sdacs_uptime_seconds        — 서버 가동 시간
"""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Any

_start_time = time.time()

# ---------------------------------------------------------------------------
# 카운터 / 게이지 (in-process, 단순 dict 기반)
# ---------------------------------------------------------------------------

_counters: dict[str, float] = defaultdict(float)
_gauges: dict[str, float] = defaultdict(float)
# latency 버킷: (endpoint, method) → [latency_ms, ...]
_latencies: dict[tuple[str, str], list[float]] = defaultdict(list)


def inc(metric: str, labels: dict[str, str] | None = None, value: float = 1.0) -> None:
    """카운터를 증가시킨다."""
    key = _key(metric, labels)
    _counters[key] += value


def set_gauge(metric: str, value: float, labels: dict[str, str] | None = None) -> None:
    """게이지 값을 설정한다."""
    key = _key(metric, labels)
    _gauges[key] = value


def observe_latency(endpoint: str, method: str, latency_ms: float) -> None:
    """응답 시간을 히스토그램 버킷에 기록한다."""
    _latencies[(endpoint, method)].append(latency_ms)
    # 최근 10,000개만 유지
    bucket = _latencies[(endpoint, method)]
    if len(bucket) > 10_000:
        _latencies[(endpoint, method)] = bucket[-10_000:]


def _key(metric: str, labels: dict[str, str] | None) -> str:
    if not labels:
        return metric
    label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
    return f"{metric}{{{label_str}}}"


# ---------------------------------------------------------------------------
# 텍스트 포맷 생성
# ---------------------------------------------------------------------------

_HELP: dict[str, str] = {
    "sdacs_active_drones": "현재 추적 중인 드론 수",
    "sdacs_conflicts_total": "누적 충돌 감지 횟수",
    "sdacs_ws_subscribers": "WebSocket 연결 수",
    "sdacs_api_requests_total": "HTTP 요청 수",
    "sdacs_api_latency_ms_sum": "HTTP 응답 시간 합계 (ms)",
    "sdacs_api_latency_ms_count": "HTTP 응답 시간 샘플 수",
    "sdacs_runs_total": "시뮬레이션 실행 수",
    "sdacs_uptime_seconds": "서버 가동 시간 (초)",
}

_TYPE: dict[str, str] = {
    "sdacs_active_drones": "gauge",
    "sdacs_conflicts_total": "counter",
    "sdacs_ws_subscribers": "gauge",
    "sdacs_api_requests_total": "counter",
    "sdacs_api_latency_ms_sum": "counter",
    "sdacs_api_latency_ms_count": "counter",
    "sdacs_runs_total": "counter",
    "sdacs_uptime_seconds": "gauge",
}


def generate_text(state: Any) -> str:
    """Prometheus 텍스트 포맷으로 모든 메트릭을 직렬화한다.

    Args:
        state: AppState 인스턴스 (fastapi_server.AppState)
    """
    lines: list[str] = []

    # 실시간 게이지 업데이트
    set_gauge("sdacs_active_drones", len(state.live_tracks))
    set_gauge("sdacs_ws_subscribers", len(state.telemetry_subscribers))
    set_gauge("sdacs_uptime_seconds", time.time() - _start_time)
    set_gauge("sdacs_conflicts_total", _counters.get("sdacs_conflicts_total", 0))
    set_gauge("sdacs_runs_total", _counters.get("sdacs_runs_total", 0))

    emitted: set[str] = set()

    def _emit(metric: str) -> None:
        if metric in emitted:
            return
        emitted.add(metric)
        help_text = _HELP.get(metric, metric)
        type_text = _TYPE.get(metric, "untyped")
        lines.append(f"# HELP {metric} {help_text}")
        lines.append(f"# TYPE {metric} {type_text}")

    # 게이지
    for key, value in _gauges.items():
        base = key.split("{")[0]
        _emit(base)
        lines.append(f"{key} {value:.6g}")

    # 카운터
    for key, value in _counters.items():
        base = key.split("{")[0]
        _emit(base)
        lines.append(f"{key} {value:.6g}")

    # 히스토그램 합산
    for (endpoint, method), samples in _latencies.items():
        if not samples:
            continue
        labels = f'endpoint="{endpoint}",method="{method}"'
        total = sum(samples)
        count = len(samples)
        _emit("sdacs_api_latency_ms_sum")
        _emit("sdacs_api_latency_ms_count")
        lines.append(f"sdacs_api_latency_ms_sum{{{labels}}} {total:.6g}")
        lines.append(f"sdacs_api_latency_ms_count{{{labels}}} {count}")

    return "\n".join(lines) + "\n"


__all__ = ["inc", "set_gauge", "observe_latency", "generate_text"]
