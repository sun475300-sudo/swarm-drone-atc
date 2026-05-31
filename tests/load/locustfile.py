"""P717 — SDACS 부하 테스트 (Locust).

목표: 100기 스웜 실시간 시각화 상황에서 API 처리량·지연·에러율 측정.

실행:
    pip install locust
    locust -f tests/load/locustfile.py --host http://localhost:8000 --headless \
        -u 100 -r 10 --run-time 60s --html results/load_report.html

성공 기준 (P717):
    - p95 latency < 200ms (snapshot/health)
    - error rate < 1%
    - throughput ≥ 50 req/s at 100 concurrent users
"""
from __future__ import annotations

import json
import random

try:
    from locust import HttpUser, between, events, task
    from locust.env import Environment
except ImportError as exc:
    raise SystemExit(
        "locust is required: pip install locust"
    ) from exc


# ---------------------------------------------------------------------------
# User behaviour classes
# ---------------------------------------------------------------------------


class ViewerUser(HttpUser):
    """공역 현황을 주기적으로 폴링하는 관찰자."""

    wait_time = between(0.5, 2.0)

    @task(3)
    def get_snapshot(self) -> None:
        self.client.get("/api/airspace/snapshot", name="/api/airspace/snapshot")

    @task(1)
    def get_health(self) -> None:
        self.client.get("/healthz", name="/healthz")

    @task(1)
    def list_scenarios(self) -> None:
        self.client.get("/api/scenarios", name="/api/scenarios")


class OperatorUser(HttpUser):
    """시나리오를 실행하는 운영자. 비율 낮게 유지."""

    wait_time = between(5.0, 15.0)

    @task(1)
    def run_scenario(self) -> None:
        scenario_id = random.choice([
            "01_corridor_crossing",
            "02_dense_intersection",
            "03_emergency_landing",
        ])
        payload = {"seed": random.randint(0, 9999), "method": "hybrid", "duration_s": 10}
        with self.client.post(
            f"/api/scenarios/{scenario_id}/run",
            json=payload,
            name="/api/scenarios/[id]/run",
            catch_response=True,
        ) as resp:
            if resp.status_code in (200, 201, 202):
                resp.success()
            elif resp.status_code == 404:
                resp.success()  # 시나리오 없음은 설정 문제, 서버 오류 아님
            else:
                resp.failure(f"unexpected {resp.status_code}")

    @task(2)
    def get_snapshot(self) -> None:
        self.client.get("/api/airspace/snapshot", name="/api/airspace/snapshot")


# ---------------------------------------------------------------------------
# Smoke runner — locust 없이도 requests 로 직접 실행 가능
# ---------------------------------------------------------------------------


def _smoke_run(host: str = "http://localhost:8000", n: int = 200) -> dict:
    """locust 없이 간단한 부하 지표를 반환한다."""
    import statistics
    import time

    try:
        import requests  # type: ignore
    except ImportError:
        return {"error": "requests not installed"}

    latencies: list[float] = []
    errors = 0
    for _ in range(n):
        t0 = time.perf_counter()
        try:
            r = requests.get(f"{host}/healthz", timeout=5)
            if r.status_code != 200:
                errors += 1
        except Exception:
            errors += 1
        latencies.append(time.perf_counter() - t0)

    valid = [x for x in latencies if x < 5]
    return {
        "n": n,
        "errors": errors,
        "error_rate": errors / n,
        "p50_ms": round(statistics.median(valid) * 1000, 1) if valid else None,
        "p95_ms": round(sorted(valid)[int(len(valid) * 0.95)] * 1000, 1) if valid else None,
        "mean_ms": round(statistics.mean(valid) * 1000, 1) if valid else None,
    }


if __name__ == "__main__":
    import sys

    host = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    print(f"Running smoke load against {host} …")
    result = _smoke_run(host)
    print(json.dumps(result, indent=2))
