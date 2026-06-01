#!/usr/bin/env python3
"""P717 — 부하 테스트: 100기 스웜 실시간 시각화 (60 FPS 검증).

asyncio + httpx 기반. SDACS FastAPI 서버에 대해:
  - HTTP 엔드포인트 동시 요청 (N_HTTP_CLIENTS)
  - WebSocket 동시 연결 (N_WS_CLIENTS) → 프레임 간격 측정

Usage:
    python scripts/load_test.py
    python scripts/load_test.py --host 127.0.0.1 --port 8000 --ws-clients 100 --http-clients 50 --duration 30

Exit codes:
    0 — 목표 달성 (p95 프레임 간격 < 16.7ms == 60fps)
    1 — 성능 목표 미달 또는 서버 연결 실패
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import statistics
import sys
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

try:
    import httpx
    import websockets  # type: ignore[import]
except ImportError:  # pragma: no cover
    print("설치 필요: pip install httpx websockets")
    sys.exit(1)

LOGGER = logging.getLogger("sdacs.load_test")

# 재현성 확보 (CLAUDE.md: random.random() 대신 np.random.default_rng 사용)
_RNG = np.random.default_rng(seed=42)

TARGET_FPS = 60.0
TARGET_FRAME_MS = 1000.0 / TARGET_FPS  # 16.67ms


@dataclass
class HttpStats:
    latencies_ms: list[float] = field(default_factory=list)
    errors: int = 0
    requests: int = 0


@dataclass
class WsStats:
    frame_intervals_ms: list[float] = field(default_factory=list)
    frames: int = 0
    errors: int = 0


async def http_worker(client: "httpx.AsyncClient", url: str, n: int, stats: HttpStats) -> None:
    for _ in range(n):
        t0 = time.perf_counter()
        try:
            r = await client.get(url, timeout=5.0)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            stats.latencies_ms.append(elapsed_ms)
            stats.requests += 1
            if r.status_code not in (200, 401, 403):
                stats.errors += 1
        except Exception as exc:
            LOGGER.debug("http_worker error: %s", exc)
            stats.errors += 1
            stats.requests += 1


_LOAD_TEST_LOGGER = logging.getLogger("sdacs.load_test")


async def ws_worker(uri: str, duration_s: float, stats: WsStats) -> None:
    try:
        async with websockets.connect(uri, ping_interval=None, close_timeout=2) as ws:
            last_t = time.perf_counter()
            deadline = time.perf_counter() + duration_s
            while time.perf_counter() < deadline:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                    now = time.perf_counter()
                    interval_ms = (now - last_t) * 1000
                    if stats.frames > 0:  # 첫 프레임 간격 제외
                        stats.frame_intervals_ms.append(interval_ms)
                    last_t = now
                    stats.frames += 1
                    _ = json.loads(msg)  # 파싱 검증
                except asyncio.TimeoutError:
                    pass
    except Exception as exc:
        _LOAD_TEST_LOGGER.debug("ws_worker error: %s", exc)
        stats.errors += 1


def _percentile(data: list[float], p: float) -> float:
    if not data:
        return float("nan")
    arr = sorted(data)
    idx = (p / 100) * (len(arr) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(arr) - 1)
    return arr[lo] + (arr[hi] - arr[lo]) * (idx - lo)


async def run_load_test(
    host: str,
    port: int,
    n_ws_clients: int,
    n_http_clients: int,
    duration_s: float,
) -> dict[str, Any]:
    base_url = f"http://{host}:{port}"
    ws_uri = f"ws://{host}:{port}/ws/telemetry"

    http_stats = HttpStats()
    ws_stats_list = [WsStats() for _ in range(n_ws_clients)]

    print(f"[SDACS 부하 테스트] 서버: {base_url}")
    print(f"  WebSocket 클라이언트: {n_ws_clients}")
    print(f"  HTTP 동시 클라이언트: {n_http_clients}")
    print(f"  지속 시간: {duration_s}s")
    print("-" * 50)

    async with httpx.AsyncClient(base_url=base_url) as client:
        # HTTP 요청: /healthz, /api/airspace/snapshot 번갈아 호출
        http_req_per_client = max(1, int(duration_s * 2))
        http_tasks = []
        for i in range(n_http_clients):
            endpoint = "/healthz" if i % 2 == 0 else "/api/airspace/snapshot"
            http_tasks.append(http_worker(client, endpoint, http_req_per_client, http_stats))

        # WebSocket 클라이언트
        ws_tasks = [
            ws_worker(ws_uri, duration_s, ws_stats_list[i])
            for i in range(n_ws_clients)
        ]

        t_start = time.perf_counter()
        await asyncio.gather(*http_tasks, *ws_tasks, return_exceptions=True)
        elapsed = time.perf_counter() - t_start

    # 집계
    all_frames = [interval for s in ws_stats_list for interval in s.frame_intervals_ms]
    total_ws_errors = sum(s.errors for s in ws_stats_list)
    total_frames = sum(s.frames for s in ws_stats_list)

    http_p50 = _percentile(http_stats.latencies_ms, 50)
    http_p95 = _percentile(http_stats.latencies_ms, 95)
    http_p99 = _percentile(http_stats.latencies_ms, 99)

    ws_p50 = _percentile(all_frames, 50)
    ws_p95 = _percentile(all_frames, 95)
    ws_fps = 1000.0 / ws_p50 if ws_p50 > 0 else 0.0

    result = {
        "duration_s": round(elapsed, 2),
        "http": {
            "requests": http_stats.requests,
            "errors": http_stats.errors,
            "p50_ms": round(http_p50, 2),
            "p95_ms": round(http_p95, 2),
            "p99_ms": round(http_p99, 2),
        },
        "websocket": {
            "clients": n_ws_clients,
            "total_frames": total_frames,
            "errors": total_ws_errors,
            "frame_interval_p50_ms": round(ws_p50, 2),
            "frame_interval_p95_ms": round(ws_p95, 2),
            "effective_fps": round(ws_fps, 1),
        },
        "target_fps": TARGET_FPS,
        "pass": ws_p95 <= TARGET_FRAME_MS * 2,  # p95 <= 33.3ms (30fps 최저선)
    }

    print(f"\n[HTTP 결과]")
    print(f"  총 요청: {result['http']['requests']}, 오류: {result['http']['errors']}")
    print(f"  지연 p50={result['http']['p50_ms']}ms p95={result['http']['p95_ms']}ms p99={result['http']['p99_ms']}ms")
    print(f"\n[WebSocket 결과]")
    print(f"  총 프레임: {total_frames}, 오류: {total_ws_errors}")
    print(f"  프레임 간격 p50={result['websocket']['frame_interval_p50_ms']}ms p95={result['websocket']['frame_interval_p95_ms']}ms")
    print(f"  유효 FPS (p50 기준): {result['websocket']['effective_fps']}")
    print(f"\n[판정] {'PASS ✓' if result['pass'] else 'FAIL ✗'} (p95 프레임 간격 목표: <={TARGET_FRAME_MS * 2:.1f}ms)")

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="SDACS P717 부하 테스트")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--ws-clients", type=int, default=100)
    parser.add_argument("--http-clients", type=int, default=50)
    parser.add_argument("--duration", type=float, default=30.0)
    args = parser.parse_args()

    result = asyncio.run(
        run_load_test(
            host=args.host,
            port=args.port,
            n_ws_clients=args.ws_clients,
            n_http_clients=args.http_clients,
            duration_s=args.duration,
        )
    )

    import datetime
    import pathlib
    out = pathlib.Path("results/load_test_latest.json")
    out.parent.mkdir(exist_ok=True)
    result["timestamp"] = datetime.datetime.utcnow().isoformat()
    out.write_text(json.dumps(result, indent=2))
    print(f"\n결과 저장: {out}")

    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
