"""P717 — SDACS 부하 테스트 스크립트.

Usage:
    # locust WebUI (8089)
    locust -f scripts/load_test.py --host http://localhost:8080

    # headless (100 동시 사용자, 10/s 생성, 60s)
    locust -f scripts/load_test.py --host http://localhost:8080 \
           --users 100 --spawn-rate 10 --run-time 60s --headless \
           --csv results/load_test
"""
from __future__ import annotations

import json
import os
import random

try:
    from locust import HttpUser, between, events, task
    from locust.env import Environment
except ImportError:
    raise SystemExit("locust not installed: pip install locust")

_API_TOKEN = os.environ.get("SDACS_LOAD_TEST_TOKEN", "")
_SCENARIOS = [
    "01_corridor_crossing",
    "02_dense_intersection",
    "03_mass_takeoff",
    "08_stress_high_density",
]


class SDACSDashboardUser(HttpUser):
    """ATC 대시보드 일반 사용자 — 읽기 위주."""
    wait_time = between(0.5, 2.0)

    def on_start(self):
        if _API_TOKEN:
            self.client.headers.update({"Authorization": f"Bearer {_API_TOKEN}"})

    @task(5)
    def get_snapshot(self):
        self.client.get("/api/airspace/snapshot", name="/api/airspace/snapshot")

    @task(3)
    def list_scenarios(self):
        self.client.get("/api/scenarios", name="/api/scenarios")

    @task(1)
    def health_check(self):
        self.client.get("/healthz", name="/healthz")

    @task(1)
    def get_metrics(self):
        self.client.get("/metrics", name="/metrics")


class SDACSOpsUser(HttpUser):
    """오퍼레이터 사용자 — 시뮬레이션 실행 포함."""
    wait_time = between(2.0, 5.0)

    def on_start(self):
        if _API_TOKEN:
            self.client.headers.update({"Authorization": f"Bearer {_API_TOKEN}"})

    @task(3)
    def get_snapshot(self):
        self.client.get("/api/airspace/snapshot")

    @task(1)
    def run_scenario(self):
        scenario = random.choice(_SCENARIOS)
        payload = {"seed": random.randint(0, 9999), "method": "hybrid", "duration_s": 10}
        with self.client.post(
            f"/api/scenarios/{scenario}/run",
            json=payload,
            name="/api/scenarios/{id}/run",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 202, 404):
                resp.success()
            else:
                resp.failure(f"unexpected status {resp.status_code}")


@events.quitting.add_listener
def _on_quit(environment: Environment, **_kw):
    stats = environment.runner.stats.total if environment.runner else None
    if stats:
        print(
            f"\n[load_test] total requests={stats.num_requests} "
            f"failures={stats.num_failures} "
            f"avg_ms={stats.avg_response_time:.1f}"
        )
    fail_pct = (
        stats.num_failures / max(stats.num_requests, 1) * 100
        if stats else 0
    )
    if fail_pct > 5:
        print(f"[load_test] WARN failure rate {fail_pct:.1f}% > 5%")
        environment.process_exit_code = 1
