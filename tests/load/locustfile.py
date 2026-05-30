"""P717: SDACS API 부하 테스트 — Locust.

목표:
    - 100기 스웜 실시간 시각화, 60 FPS 유지 검증
    - /api/airspace/snapshot 폴링 처리량
    - /ws/telemetry WebSocket 부하
    - /api/scenarios/{id}/run 동시 실행

실행 방법:
    pip install locust
    locust -f tests/load/locustfile.py --host http://localhost:8080

    # 헤드리스 (CI 용):
    locust -f tests/load/locustfile.py --host http://localhost:8080 \
        --headless -u 50 -r 10 --run-time 60s \
        --csv results/load_test
"""

from __future__ import annotations

import json
import os
import time

from locust import HttpUser, between, events, task
from locust.env import Environment

_API_HOST = os.environ.get("SDACS_API_HOST", "http://localhost:8080")

# 개발 환경 기본 토큰 (OPERATOR 권한)
_DEV_OPERATOR_CREDS = {"username": "operator", "password": "op-secret"}


def _get_operator_token(client) -> str:
    """POST /auth/token 으로 토큰을 획득한다."""
    resp = client.post("/auth/token", json=_DEV_OPERATOR_CREDS, name="/auth/token")
    if resp.status_code == 200:
        return resp.json().get("access_token", "")
    return ""


class ViewerUser(HttpUser):
    """읽기 전용 폴링 — 대시보드 뷰어 시뮬레이션."""

    wait_time = between(0.016, 0.033)  # 30~60 FPS 폴링 간격

    def on_start(self) -> None:
        self.token = _get_operator_token(self.client)
        self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(10)
    def poll_snapshot(self) -> None:
        """공역 스냅샷 폴링 (최고 빈도)."""
        self.client.get("/api/airspace/snapshot", name="/api/airspace/snapshot")

    @task(3)
    def list_scenarios(self) -> None:
        """시나리오 목록 조회."""
        self.client.get("/api/scenarios", name="/api/scenarios")

    @task(1)
    def health_check(self) -> None:
        """헬스 체크."""
        self.client.get("/healthz", name="/healthz")


class OperatorUser(HttpUser):
    """시나리오 실행 사용자 — 관제 운영자 시뮬레이션."""

    wait_time = between(5, 15)

    def on_start(self) -> None:
        self.token = _get_operator_token(self.client)
        self.headers = {"Authorization": f"Bearer {self.token}"}
        self.active_run_id: str | None = None

    @task(3)
    def run_scenario(self) -> None:
        """시나리오 실행 요청."""
        resp = self.client.post(
            "/api/scenarios/light_traffic_10/run",
            json={"seed": int(time.time()) % 1000, "method": "hybrid", "duration_s": 10},
            headers=self.headers,
            name="/api/scenarios/{id}/run",
        )
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            self.active_run_id = data.get("run_id")

    @task(5)
    def poll_run_status(self) -> None:
        """실행 상태 폴링."""
        if self.active_run_id is None:
            return
        self.client.get(
            f"/api/runs/{self.active_run_id}",
            name="/api/runs/{run_id}",
        )


class TelemetryProducer(HttpUser):
    """WebSocket 텔레메트리 생성자 — 드론 상태 스트림 시뮬레이션.

    주의: Locust 기본 HttpUser는 WS를 직접 지원하지 않으므로
    REST 폴백(/api/airspace/snapshot 폴링)으로 부하를 대체 측정한다.
    실제 WS 부하는 `locust-websocket` 플러그인 또는 별도 k6 스크립트를 사용하라.
    """

    wait_time = between(0.1, 0.5)

    @task
    def simulate_telemetry_rate(self) -> None:
        """100기 드론 텔레메트리 처리량 검증용 스냅샷 폴링."""
        self.client.get("/api/airspace/snapshot", name="/api/airspace/snapshot[telemetry-rate]")


@events.test_start.add_listener
def on_test_start(environment: Environment, **kwargs) -> None:
    print(f"[SDACS Load Test] 시작 — host={environment.host}")


@events.test_stop.add_listener
def on_test_stop(environment: Environment, **kwargs) -> None:
    stats = environment.runner.stats.total if environment.runner else None
    if stats:
        print(
            f"[SDACS Load Test] 완료 — "
            f"RPS={stats.current_rps:.1f} "
            f"P50={stats.get_response_time_percentile(0.5):.0f}ms "
            f"P99={stats.get_response_time_percentile(0.99):.0f}ms "
            f"Failures={stats.num_failures}"
        )
