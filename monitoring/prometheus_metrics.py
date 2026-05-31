"""P718 — Prometheus 메트릭 정의.

prometheus_client가 없으면 간이 텍스트 출력으로 폴백한다.
"""
from __future__ import annotations

import time
from typing import Any

_REGISTRY: dict[str, dict[str, Any]] = {}


def _get_or_create(name: str, metric_type: str, help_text: str) -> dict[str, Any]:
    if name not in _REGISTRY:
        _REGISTRY[name] = {"type": metric_type, "help": help_text, "value": 0.0, "labels": {}}
    return _REGISTRY[name]


# --- Gauge 클래스 ---

class _Gauge:
    def __init__(self, name: str, documentation: str, labelnames: list[str] | None = None) -> None:
        self.name = name
        self._meta = _get_or_create(name, "gauge", documentation)
        self._labelnames = labelnames or []

    def set(self, value: float) -> None:
        self._meta["value"] = float(value)

    def labels(self, **kw: str) -> "_LabeledGauge":
        return _LabeledGauge(self, kw)


class _LabeledGauge:
    def __init__(self, parent: _Gauge, labels: dict[str, str]) -> None:
        self._parent = parent
        self._labels = labels

    def _key(self) -> str:
        return ",".join(f'{k}="{v}"' for k, v in sorted(self._labels.items()))

    def set(self, value: float) -> None:
        self._parent._meta["labels"][self._key()] = {"labels": self._labels, "value": float(value)}


class _Counter:
    def __init__(self, name: str, documentation: str) -> None:
        self.name = name
        self._meta = _get_or_create(name, "counter", documentation)

    def inc(self, amount: float = 1.0) -> None:
        self._meta["value"] += float(amount)


class _Histogram:
    _BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

    def __init__(self, name: str, documentation: str) -> None:
        self.name = name
        self._meta = _get_or_create(name, "histogram", documentation)
        self._sum = 0.0
        self._count = 0
        self._buckets: dict[float, int] = {b: 0 for b in self._BUCKETS}

    def observe(self, value: float) -> None:
        self._sum += value
        self._count += 1
        for b in self._BUCKETS:
            if value <= b:
                self._buckets[b] += 1


# --- SDACS 메트릭 정의 ---

drones_active = _Gauge("sdacs_drones_active", "현재 활성 드론 수")
conflicts_active = _Gauge("sdacs_conflicts_active", "현재 활성 충돌 수")
ws_subscribers = _Gauge("sdacs_ws_subscribers", "WebSocket 구독자 수")
scenario_runs_total = _Counter("sdacs_scenario_runs_total", "총 시나리오 실행 횟수")
scenario_runs_failed = _Counter("sdacs_scenario_runs_failed", "실패한 시나리오 실행 수")
api_request_duration = _Histogram("sdacs_api_request_duration_seconds", "API 요청 처리 시간(초)")
collision_resolution_rate = _Gauge("sdacs_collision_resolution_rate", "충돌 해결률 (0~1)")
drone_latency_ms = _Gauge("sdacs_drone_telemetry_latency_ms", "드론 텔레메트리 지연(ms)")
auth_failures = _Counter("sdacs_auth_failures_total", "인증 실패 횟수")
audit_events_total = _Counter("sdacs_audit_events_total", "감사 이벤트 총 수")

_server_start_time = time.time()
server_uptime = _Gauge("sdacs_server_uptime_seconds", "서버 가동 시간(초)")


def update_runtime_metrics(state: Any) -> None:
    """AppState에서 실시간 메트릭을 갱신한다."""
    drones_active.set(len(state.snapshot.drones))
    conflicts_active.set(len(state.snapshot.conflicts))
    ws_subscribers.set(len(state.telemetry_subscribers))
    scenario_runs_total._meta["value"] = len(state.runs)
    scenario_runs_failed.inc(0)  # 유지
    server_uptime.set(time.time() - _server_start_time)


def generate_metrics_text(state: Any | None = None) -> str:
    """Prometheus exposition 포맷 텍스트를 생성한다."""
    if state is not None:
        update_runtime_metrics(state)

    lines: list[str] = []
    for name, meta in _REGISTRY.items():
        lines.append(f"# HELP {name} {meta['help']}")
        lines.append(f"# TYPE {name} {meta['type']}")
        if meta["labels"]:
            for key_data in meta["labels"].values():
                label_str = ",".join(f'{k}="{v}"' for k, v in key_data["labels"].items())
                lines.append(f"{name}{{{label_str}}} {key_data['value']}")
        else:
            lines.append(f"{name} {meta['value']}")
    return "\n".join(lines) + "\n"
