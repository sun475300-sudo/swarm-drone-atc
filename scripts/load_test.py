#!/usr/bin/env python3
"""P717 — SDACS 부하 테스트.

100기 드론 실시간 시각화 + REST API 동시 요청을 시뮬레이션한다.
외부 의존성 없이 asyncio + urllib + threading으로 구현.

사용:
    python scripts/load_test.py                     # 기본: 100드론, 30초
    python scripts/load_test.py --drones 200 --duration 60
    python scripts/load_test.py --host localhost --port 8000

종료 코드:
    0 — 테스트 통과 (p99 < 200ms, 에러율 < 1%)
    1 — 기준 미충족
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import random
import statistics
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any


# --- 설정 ---

@dataclass
class LoadTestConfig:
    host: str = "localhost"
    port: int = 8000
    n_drones: int = 100
    duration_s: float = 30.0
    telemetry_hz: float = 2.0
    concurrent_http: int = 10
    target_p99_ms: float = 200.0
    target_error_rate: float = 0.01  # 1%


# --- 결과 ---

@dataclass
class RequestResult:
    url: str
    status: int
    latency_ms: float
    error: str | None = None


@dataclass
class LoadTestReport:
    config: LoadTestConfig
    results: list[RequestResult] = field(default_factory=list)
    ws_frames_sent: int = 0
    ws_frames_received: int = 0
    start_time: float = field(default_factory=time.time)
    end_time: float = 0.0

    @property
    def duration_s(self) -> float:
        return self.end_time - self.start_time

    @property
    def total_requests(self) -> int:
        return len(self.results)

    @property
    def error_count(self) -> int:
        return sum(1 for r in self.results if r.error or r.status >= 500)

    @property
    def error_rate(self) -> float:
        if not self.results:
            return 0.0
        return self.error_count / len(self.results)

    @property
    def latencies_ms(self) -> list[float]:
        return [r.latency_ms for r in self.results if not r.error]

    def percentile(self, p: float) -> float:
        lat = sorted(self.latencies_ms)
        if not lat:
            return 0.0
        idx = max(0, int(len(lat) * p / 100) - 1)
        return lat[idx]

    def print_summary(self) -> None:
        lat = self.latencies_ms
        print("\n" + "=" * 60)
        print("SDACS Load Test Report")
        print("=" * 60)
        print(f"Duration          : {self.duration_s:.1f}s")
        print(f"Total requests    : {self.total_requests}")
        print(f"Errors            : {self.error_count} ({self.error_rate * 100:.1f}%)")
        print(f"WS frames sent    : {self.ws_frames_sent}")
        print(f"WS frames received: {self.ws_frames_received}")
        if lat:
            print(f"Latency p50       : {statistics.median(lat):.1f} ms")
            print(f"Latency p95       : {self.percentile(95):.1f} ms")
            print(f"Latency p99       : {self.percentile(99):.1f} ms")
            print(f"Latency max       : {max(lat):.1f} ms")
        print("=" * 60)


# --- HTTP 헬퍼 ---

def http_get(url: str, timeout: float = 5.0) -> RequestResult:
    t0 = time.perf_counter()
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read()
            return RequestResult(
                url=url,
                status=resp.status,
                latency_ms=(time.perf_counter() - t0) * 1000,
            )
    except urllib.error.HTTPError as exc:
        return RequestResult(url=url, status=exc.code, latency_ms=(time.perf_counter() - t0) * 1000)
    except Exception as exc:
        return RequestResult(url=url, status=0, latency_ms=(time.perf_counter() - t0) * 1000, error=str(exc))


# --- 비동기 부하 생성기 ---

async def http_load_worker(
    base_url: str,
    endpoints: list[str],
    duration_s: float,
    report: LoadTestReport,
    worker_id: int,
) -> None:
    deadline = time.monotonic() + duration_s
    rng = random.Random(worker_id)
    while time.monotonic() < deadline:
        url = base_url + rng.choice(endpoints)
        result = await asyncio.to_thread(http_get, url)
        report.results.append(result)
        await asyncio.sleep(rng.uniform(0.05, 0.2))


async def telemetry_ws_worker(
    host: str,
    port: int,
    n_drones: int,
    duration_s: float,
    hz: float,
    report: LoadTestReport,
) -> None:
    """WebSocket 텔레메트리 스트림 부하 생성."""
    try:
        import websockets  # type: ignore
    except ImportError:
        print("[WS] websockets 패키지 없음 — WebSocket 부하 테스트 건너뜀")
        return

    uri = f"ws://{host}:{port}/ws/telemetry"
    t0 = time.monotonic()
    interval = 1.0 / hz

    try:
        async with websockets.connect(uri, open_timeout=5, close_timeout=2) as ws:
            while time.monotonic() - t0 < duration_s:
                frame_start = time.monotonic()
                t_sim = time.monotonic() - t0

                for i in range(n_drones):
                    payload = {
                        "type": "telemetry",
                        "drone_id": f"load-drone-{i:04d}",
                        "timestamp_ns": time.time_ns(),
                        "lat": 34.93 + 0.001 * math.cos(t_sim * 0.1 + i * 0.05),
                        "lon": 126.45 + 0.001 * math.sin(t_sim * 0.1 + i * 0.05),
                        "alt": 60.0 + 10.0 * math.sin(t_sim * 0.2 + i * 0.1),
                        "vx": 3.0 * math.cos(t_sim * 0.1 + i),
                        "vy": 3.0 * math.sin(t_sim * 0.1 + i),
                        "vz": 0.0,
                    }
                    await ws.send(json.dumps(payload))
                    report.ws_frames_sent += 1

                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=0.05)
                    if msg:
                        report.ws_frames_received += 1
                except asyncio.TimeoutError:
                    pass

                elapsed = time.monotonic() - frame_start
                sleep_time = max(0.0, interval - elapsed)
                await asyncio.sleep(sleep_time)
    except Exception as exc:
        print(f"[WS] 연결 오류 (서버 미구동?): {exc}")


# --- 메인 ---

async def run_load_test(cfg: LoadTestConfig) -> LoadTestReport:
    base_url = f"http://{cfg.host}:{cfg.port}"
    report = LoadTestReport(config=cfg, start_time=time.time())

    http_endpoints = [
        "/healthz",
        "/health",
        "/api/airspace/snapshot",
        "/api/scenarios",
        "/metrics",
    ]

    print(f"[LOAD TEST] 시작: {cfg.n_drones}드론, {cfg.duration_s}초, {cfg.concurrent_http}워커")
    print(f"            대상: {base_url}")

    http_workers = [
        http_load_worker(base_url, http_endpoints, cfg.duration_s, report, i)
        for i in range(cfg.concurrent_http)
    ]

    ws_worker = telemetry_ws_worker(
        cfg.host, cfg.port, cfg.n_drones, cfg.duration_s, cfg.telemetry_hz, report
    )

    await asyncio.gather(*http_workers, ws_worker)
    report.end_time = time.time()
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="SDACS P717 부하 테스트")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--drones", type=int, default=100)
    parser.add_argument("--duration", type=float, default=30.0)
    parser.add_argument("--hz", type=float, default=2.0, help="텔레메트리 전송 주파수")
    parser.add_argument("--workers", type=int, default=10, help="HTTP 동시 워커 수")
    parser.add_argument("--p99-limit", type=float, default=200.0, help="p99 레이턴시 한계(ms)")
    args = parser.parse_args()

    cfg = LoadTestConfig(
        host=args.host,
        port=args.port,
        n_drones=args.drones,
        duration_s=args.duration,
        telemetry_hz=args.hz,
        concurrent_http=args.workers,
        target_p99_ms=args.p99_limit,
    )

    report = asyncio.run(run_load_test(cfg))
    report.print_summary()

    p99 = report.percentile(99)
    passed = p99 <= cfg.target_p99_ms and report.error_rate <= cfg.target_error_rate
    if passed:
        print(f"\n[PASS] p99={p99:.1f}ms <= {cfg.target_p99_ms}ms, "
              f"에러율={report.error_rate * 100:.2f}% <= {cfg.target_error_rate * 100:.0f}%")
        return 0
    else:
        print(f"\n[FAIL] p99={p99:.1f}ms (한계 {cfg.target_p99_ms}ms), "
              f"에러율={report.error_rate * 100:.2f}% (한계 {cfg.target_error_rate * 100:.0f}%)")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
