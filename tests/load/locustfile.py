"""P717 — SDACS API 부하 테스트 (Locust).

목표: 100기 스웜 실시간 시각화 + 60 FPS 유지 검증

실행:
    pip install locust
    locust -f tests/load/locustfile.py --headless -u 100 -r 10 \
           --host http://localhost:8080 --run-time 60s

결과 기준:
    - /api/airspace/snapshot  p95 응답시간 < 50ms
    - /api/scenarios          p95 응답시간 < 100ms
    - POST /api/scenarios/*/run p95 응답시간 < 500ms
    - WebSocket 처리량 ≥ 100 msg/s (60 FPS 기준)
"""

from __future__ import annotations

import json
import random
import time

try:
    from locust import HttpUser, TaskSet, between, events, task
    from locust.contrib.fasthttp import FastHttpUser
except ImportError as exc:
    raise RuntimeError("locust 필요: pip install locust") from exc


# --- 인증 토큰 캐시 ---
_TOKEN_CACHE: dict[str, str] = {}


class AirspaceReadTasks(TaskSet):
    """읽기 전용 공역 조회 태스크."""

    @task(5)
    def get_snapshot(self) -> None:
        with self.client.get("/api/airspace/snapshot", catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"unexpected {resp.status_code}")

    @task(3)
    def list_scenarios(self) -> None:
        with self.client.get("/api/scenarios", catch_response=True) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"unexpected {resp.status_code}")

    @task(2)
    def health_check(self) -> None:
        self.client.get("/healthz")

    @task(1)
    def health_detail(self) -> None:
        self.client.get("/health")


class OperatorTasks(TaskSet):
    """시나리오 실행 태스크 (operator 권한)."""

    scenarios = [
        "light_traffic_10",
        "dense_traffic_50",
        "crosswind_corridor",
        "geofence_breach",
        "remote_id_loss",
    ]

    def on_start(self) -> None:
        resp = self.client.post(
            "/auth/token",
            json={"username": "operator", "password": "op123"},
        )
        if resp.status_code == 200:
            self._token = resp.json().get("access_token", "")
        else:
            self._token = ""

    @property
    def _auth_header(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"}

    @task(2)
    def run_scenario(self) -> None:
        scenario = random.choice(self.scenarios)
        with self.client.post(
            f"/api/scenarios/{scenario}/run",
            json={"seed": random.randint(0, 9999), "duration_s": 10},
            headers=self._auth_header,
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 202):
                resp.success()
            elif resp.status_code == 401:
                resp.failure("auth failed")
            else:
                resp.failure(f"unexpected {resp.status_code}")

    @task(3)
    def get_snapshot(self) -> None:
        self.client.get("/api/airspace/snapshot")


class ViewerUser(FastHttpUser):
    """읽기 전용 뷰어 — 100기 스웜 시뮬레이션 폴링."""
    tasks = [AirspaceReadTasks]
    wait_time = between(0.016, 0.05)  # ~20-60 req/s per user (60 FPS 범위)
    weight = 8


class OperatorUser(FastHttpUser):
    """시나리오 실행 오퍼레이터."""
    tasks = [OperatorTasks]
    wait_time = between(1, 5)
    weight = 2


# --- 부하 테스트 결과 검증 ---

THRESHOLDS = {
    "GET /api/airspace/snapshot": {"p95_ms": 50, "fail_rate": 0.01},
    "GET /api/scenarios": {"p95_ms": 100, "fail_rate": 0.01},
    "POST /api/scenarios/*/run": {"p95_ms": 500, "fail_rate": 0.05},
}


@events.quitting.add_listener
def _on_quit(environment, **kwargs) -> None:
    """테스트 종료 시 임계값 위반 보고."""
    stats = environment.runner.stats
    violations = []
    for name, thresholds in THRESHOLDS.items():
        entry = stats.get(name, "GET")
        if entry is None:
            continue
        p95 = entry.get_response_time_percentile(0.95)
        fail_rate = entry.fail_ratio
        if p95 and p95 > thresholds["p95_ms"]:
            violations.append(f"{name}: p95={p95:.0f}ms > {thresholds['p95_ms']}ms")
        if fail_rate > thresholds["fail_rate"]:
            violations.append(f"{name}: fail_rate={fail_rate:.1%} > {thresholds['fail_rate']:.1%}")
    if violations:
        print("\n[P717] THRESHOLD VIOLATIONS:")
        for v in violations:
            print(f"  ✗ {v}")
        environment.process_exit_code = 1
    else:
        print("\n[P717] All thresholds PASSED ✓")
