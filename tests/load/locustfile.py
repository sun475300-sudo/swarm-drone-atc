"""P717 — Locust 부하 테스트 (100기 드론 스웜 텔레메트리 처리량)

실행 방법:
    pip install locust
    locust -f tests/load/locustfile.py --host http://localhost:8000
"""

import random

from locust import HttpUser, between, task

# 부하 테스트에서 사용할 시나리오 ID 범위
_SCENARIO_IDS = ["high_density", "low_density", "storm", "night_ops", "urban"]
_RUN_ID_RANGE = 1000


class ViewerUser(HttpUser):
    """뷰어 역할 — 실시간 공역 스냅샷을 30~60 FPS로 폴링."""

    weight = 3
    wait_time = between(1 / 60, 1 / 30)  # 30~60 FPS 폴링 간격

    @task
    def poll_snapshot(self):
        """실시간 공역 상태 스냅샷 조회."""
        self.client.get("/api/airspace/snapshot", name="/api/airspace/snapshot")

    @task
    def check_runs(self):
        """최근 실행 결과 조회."""
        run_id = random.randint(1, _RUN_ID_RANGE)
        self.client.get(f"/api/runs/{run_id}", name="/api/runs/{run_id}")


class OperatorUser(HttpUser):
    """오퍼레이터 역할 — 시나리오 실행 후 완료까지 상태 폴링."""

    weight = 1
    wait_time = between(5, 15)

    @task
    def run_scenario(self):
        """시나리오 시작 → 완료 상태 폴링."""
        scenario_id = random.choice(_SCENARIO_IDS)
        with self.client.post(
            f"/api/scenarios/{scenario_id}/run",
            name="/api/scenarios/{id}/run",
            json={"drone_count": 100},
            catch_response=True,
        ) as resp:
            if resp.status_code not in (200, 202):
                resp.failure(f"Unexpected status {resp.status_code}")
                return
            try:
                data = resp.json()
                run_id = data.get("run_id") or data.get("id")
            except Exception:
                run_id = None

        if run_id:
            # 최대 3회 완료 상태 폴링
            for _ in range(3):
                self.client.get(
                    f"/api/runs/{run_id}",
                    name="/api/runs/{run_id}",
                )

    @task
    def check_health(self):
        """헬스체크 엔드포인트 확인."""
        self.client.get("/healthz", name="/healthz")
