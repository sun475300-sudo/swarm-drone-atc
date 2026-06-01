"""P717 — 부하 테스트 (locust).

목표: 100기 드론 텔레메트리 스트리밍을 시뮬레이션하며 60 FPS를 유지하는지 검증.

실행 방법:
    # headless 모드 (CI/CD):
    locust -f tests/load/locustfile.py \
        --headless -u 100 -r 10 --run-time 60s \
        --host http://localhost:8080

    # 대화형 웹 UI:
    locust -f tests/load/locustfile.py --host http://localhost:8080

지표:
    - REST 엔드포인트 p95 응답시간 < 200ms
    - WebSocket 텔레메트리 수신률 ≥ 95%
    - 에러율 < 1%
"""
from __future__ import annotations

import json
import random
import time

from locust import HttpUser, between, events, tag, task
from locust.contrib.fasthttp import FastHttpUser


# ---------------------------------------------------------------------------
# 공통 헬퍼
# ---------------------------------------------------------------------------


def _drone_telemetry(drone_id: str) -> dict:
    """랜덤 드론 텔레메트리 페이로드를 생성한다."""
    return {
        "type": "telemetry",
        "drone_id": drone_id,
        "position": [
            random.uniform(0, 1000),
            random.uniform(0, 1000),
            random.uniform(50, 250),
        ],
        "velocity": [
            random.uniform(-15, 15),
            random.uniform(-15, 15),
            random.uniform(-2, 2),
        ],
        "heading": random.uniform(0, 360),
        "ts": time.time(),
    }


def _get_token(client, username: str = "atc_operator", password: str = "operator") -> str | None:
    """로그인 후 JWT 토큰을 반환한다."""
    resp = client.post(
        "/auth/token",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if resp.status_code == 200:
        return resp.json().get("access_token")
    return None


# ---------------------------------------------------------------------------
# REST API 부하 테스트 유저
# ---------------------------------------------------------------------------


class RestApiUser(FastHttpUser):
    """REST 엔드포인트 부하 테스트.

    시나리오: ATC 운영자가 주기적으로 공역 스냅샷·시나리오 목록을 조회한다.
    """

    wait_time = between(0.5, 2.0)
    weight = 3  # 전체 유저의 30%

    def on_start(self) -> None:
        """세션 시작 시 토큰을 발급받는다."""
        self._token = _get_token(self.client) or ""

    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}"}

    @tag("health")
    @task(1)
    def health_check(self) -> None:
        """상태 확인 엔드포인트 (인증 불필요)."""
        self.client.get("/healthz")

    @tag("airspace")
    @task(5)
    def get_snapshot(self) -> None:
        """공역 스냅샷 조회 (고빈도 폴링)."""
        self.client.get("/api/airspace/snapshot")

    @tag("scenarios")
    @task(2)
    def list_scenarios(self) -> None:
        """시나리오 목록 조회."""
        self.client.get("/api/scenarios")

    @tag("auth")
    @task(1)
    def get_me(self) -> None:
        """인증된 사용자 정보 조회."""
        self.client.get("/auth/me", headers=self._auth_headers())


# ---------------------------------------------------------------------------
# WebSocket 텔레메트리 부하 테스트 유저
# ---------------------------------------------------------------------------


class TelemetryStreamUser(HttpUser):
    """WebSocket 텔레메트리 스트리밍 부하 테스트.

    시나리오: 드론 1기 당 유저 1명이 10Hz로 텔레메트리를 전송한다.
    목표: 100명 동시 연결 시 60 FPS 유지.
    """

    wait_time = between(0.08, 0.12)  # 10Hz ≈ 100ms
    weight = 7  # 전체 유저의 70%

    def on_start(self) -> None:
        """드론 ID와 WebSocket 클라이언트를 초기화한다."""
        self._drone_id = f"drone_{random.randint(1, 9999):04d}"
        self._ws = None
        self._send_count = 0
        self._error_count = 0
        self._connect_ws()

    def _connect_ws(self) -> None:
        """WebSocket에 연결한다."""
        import websocket as ws_lib

        host = self.host.replace("http://", "ws://").replace("https://", "wss://")
        try:
            self._ws = ws_lib.create_connection(
                f"{host}/ws/telemetry",
                timeout=5,
            )
        except Exception:
            self._ws = None

    def on_stop(self) -> None:
        """연결을 닫는다."""
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass

    @tag("ws_telemetry")
    @task
    def send_telemetry(self) -> None:
        """10Hz로 텔레메트리 프레임을 전송한다."""
        if self._ws is None:
            self._connect_ws()
            if self._ws is None:
                return

        payload = _drone_telemetry(self._drone_id)
        start = time.perf_counter()
        try:
            self._ws.send(json.dumps(payload))
            elapsed_ms = (time.perf_counter() - start) * 1000
            events.request.fire(
                request_type="WS",
                name="send_telemetry",
                response_time=elapsed_ms,
                response_length=len(json.dumps(payload)),
                exception=None,
            )
            self._send_count += 1
        except Exception as exc:
            self._error_count += 1
            events.request.fire(
                request_type="WS",
                name="send_telemetry",
                response_time=0,
                response_length=0,
                exception=exc,
            )
            self._ws = None  # 재연결 유도


# ---------------------------------------------------------------------------
# 시나리오 실행 부하 (인증 필요)
# ---------------------------------------------------------------------------


class ScenarioRunUser(FastHttpUser):
    """시나리오 실행 엔드포인트 부하 테스트.

    시나리오: 운영자가 드물게 시뮬레이션을 트리거한다.
    """

    wait_time = between(5.0, 15.0)
    weight = 1  # 전체 유저의 10% 미만 (고부하 작업)

    _SCENARIOS = [
        "light_traffic_10",
        "dense_traffic_50",
        "crosswind_corridor",
    ]

    def on_start(self) -> None:
        """관리자 토큰을 발급받는다."""
        self._token = _get_token(self.client, "atc_operator", "operator") or ""

    def _auth_headers(self) -> dict:
        return {"Authorization": f"Bearer {self._token}"}

    @tag("scenario_run")
    @task
    def run_scenario(self) -> None:
        """시나리오 실행을 트리거한다."""
        scenario = random.choice(self._SCENARIOS)
        self.client.post(
            f"/api/scenarios/{scenario}/run",
            json={"seed": random.randint(0, 999), "method": "hybrid", "duration_s": 30},
            headers=self._auth_headers(),
        )
