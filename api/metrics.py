"""P718 — Prometheus 메트릭 엔드포인트 (prometheus_client 선택적)"""

try:
    from prometheus_client import (
        CollectorRegistry,
        Counter,
        Gauge,
        Histogram,
        generate_latest as _prom_generate_latest,
        CONTENT_TYPE_LATEST,
    )
    _PROMETHEUS_AVAILABLE = True
except ImportError:
    _PROMETHEUS_AVAILABLE = False


_RUN_DURATION_BUCKETS = [1, 5, 10, 30, 60, 120, 300]


class _StubMetric:
    """Minimal stub when prometheus_client is not installed."""
    def __init__(self):
        self._value = 0.0
        self._counts: dict[str, float] = {}
        self._observations: list[float] = []

    def set(self, value: float) -> None:
        self._value = value

    def inc(self, amount: float = 1.0, labels: dict | None = None) -> None:
        key = str(labels)
        self._counts[key] = self._counts.get(key, 0.0) + amount

    def observe(self, value: float) -> None:
        self._observations.append(value)


class SDACSTelemetryMetrics:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        if _PROMETHEUS_AVAILABLE:
            self._registry = CollectorRegistry()
            self._active_drones = Gauge(
                "sdacs_active_drones",
                "현재 활성 드론 수",
                registry=self._registry,
            )
            self._active_conflicts = Gauge(
                "sdacs_active_conflicts",
                "현재 감지된 충돌 위험 수",
                registry=self._registry,
            )
            self._advisories_total = Counter(
                "sdacs_advisories_total",
                "발행된 해결 권고 총계",
                ["advisory_type"],
                registry=self._registry,
            )
            self._ws_subscribers = Gauge(
                "sdacs_ws_subscribers",
                "현재 WebSocket 구독자 수",
                registry=self._registry,
            )
            self._run_duration = Histogram(
                "sdacs_run_duration_seconds",
                "시뮬레이션 실행 소요 시간 (초)",
                buckets=_RUN_DURATION_BUCKETS,
                registry=self._registry,
            )
        else:
            self._active_drones = _StubMetric()
            self._active_conflicts = _StubMetric()
            self._advisories_total = _StubMetric()
            self._ws_subscribers = _StubMetric()
            self._run_duration = _StubMetric()
            self._registry = None
        self._initialized = True

    def update_drones(self, n: int) -> None:
        self._active_drones.set(n)

    def update_conflicts(self, n: int) -> None:
        self._active_conflicts.set(n)

    def inc_advisory(self, advisory_type: str) -> None:
        if _PROMETHEUS_AVAILABLE:
            self._advisories_total.labels(advisory_type=advisory_type).inc()
        else:
            self._advisories_total.inc(labels={"advisory_type": advisory_type})

    def update_ws_subscribers(self, n: int) -> None:
        self._ws_subscribers.set(n)

    def observe_run_duration(self, seconds: float) -> None:
        self._run_duration.observe(seconds)

    def generate_latest(self) -> str:
        if _PROMETHEUS_AVAILABLE:
            return _prom_generate_latest(self._registry).decode()
        return (
            "# HELP sdacs_active_drones 현재 활성 드론 수\n"
            "# TYPE sdacs_active_drones gauge\n"
            f"sdacs_active_drones {self._active_drones._value}\n"
            "# HELP sdacs_active_conflicts 현재 감지된 충돌 위험 수\n"
            "# TYPE sdacs_active_conflicts gauge\n"
            f"sdacs_active_conflicts {self._active_conflicts._value}\n"
            "# HELP sdacs_advisories_total 발행된 해결 권고 총계\n"
            "# TYPE sdacs_advisories_total counter\n"
            "# HELP sdacs_ws_subscribers 현재 WebSocket 구독자 수\n"
            "# TYPE sdacs_ws_subscribers gauge\n"
            f"sdacs_ws_subscribers {self._ws_subscribers._value}\n"
            "# HELP sdacs_run_duration_seconds 시뮬레이션 실행 소요 시간 (초)\n"
            "# TYPE sdacs_run_duration_seconds histogram\n"
            "# (prometheus_client not installed — stub output)\n"
        )
