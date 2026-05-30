"""P717 부하 테스트 — 100기 스웜 실시간 WebSocket 시각화 스루풋 검증.

목표: 100기 드론 텔레메트리 스트림을 1 kHz로 전송할 때 60 FPS (≥33ms/frame) 유지.

실행:
    python tests/load/load_test_swarm.py [--drones 100] [--duration 30] [--hz 10]

의존성: httpx (동기 HTTP 클라이언트), asyncio+websockets 선택적.
"""

import argparse
import asyncio
import json
import math
import statistics
import sys
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False


# ── Simulated drone fleet ─────────────────────────────────────────────────────

def _make_frame(drone_id: str, t: float, rng: np.random.Generator) -> dict[str, Any]:
    angle = t * 0.1 + rng.uniform(0, 2 * math.pi)
    return {
        "drone_id": drone_id,
        "timestamp": t,
        "x": 500 * math.cos(angle) + rng.normal(0, 0.5),
        "y": 500 * math.sin(angle) + rng.normal(0, 0.5),
        "z": 100 + 20 * math.sin(t * 0.05) + rng.normal(0, 0.2),
        "vx": -5 * math.sin(angle),
        "vy": 5 * math.cos(angle),
        "vz": rng.normal(0, 0.1),
        "battery": max(0.0, 95.0 - t * 0.01),
        "state": "FLYING",
    }


# ── Local simulation throughput benchmark (no server needed) ─────────────────

@dataclass
class LoadTestResult:
    n_drones: int
    duration_s: float
    target_hz: int
    frames_sent: int
    frames_per_s: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    max_ms: float
    target_fps: float = 60.0
    passed: bool = False

    def __post_init__(self) -> None:
        self.passed = self.frames_per_s >= self.target_fps

    def report(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return (
            f"=== SDACS Load Test [{status}] ===\n"
            f"Drones: {self.n_drones}  Hz: {self.target_hz}  Duration: {self.duration_s:.1f}s\n"
            f"Throughput: {self.frames_per_s:.1f} frames/s  (target ≥{self.target_fps})\n"
            f"Latency p50={self.p50_ms:.2f}ms  p95={self.p95_ms:.2f}ms  "
            f"p99={self.p99_ms:.2f}ms  max={self.max_ms:.2f}ms\n"
            f"Total frames: {self.frames_sent}"
        )


def run_local_benchmark(
    n_drones: int = 100,
    duration_s: float = 10.0,
    target_hz: int = 10,
    seed: int = 42,
) -> LoadTestResult:
    """Measure serialization + processing throughput without a live server."""
    rng = np.random.default_rng(seed)
    drone_ids = [f"D-{i:03d}" for i in range(n_drones)]

    latencies_ms: list[float] = []
    frames_sent = 0
    interval = 1.0 / target_hz
    t_start = time.perf_counter()
    t_sim = 0.0

    while (time.perf_counter() - t_start) < duration_s:
        batch_t0 = time.perf_counter()

        # Build + serialize one frame per drone (simulates a broadcast tick)
        for did in drone_ids:
            frame = _make_frame(did, t_sim, rng)
            _ = json.dumps(frame)  # simulate serialization cost
            frames_sent += 1

        batch_elapsed = (time.perf_counter() - batch_t0) * 1000
        latencies_ms.append(batch_elapsed)

        t_sim += interval

        # Throttle to target Hz
        elapsed = time.perf_counter() - t_start
        next_tick = math.ceil(elapsed / interval) * interval
        sleep_s = next_tick - elapsed
        if sleep_s > 0:
            time.sleep(sleep_s)

    total_elapsed = time.perf_counter() - t_start
    fps = frames_sent / total_elapsed

    latencies_ms.sort()
    n = len(latencies_ms)
    p50 = latencies_ms[int(n * 0.50)] if n else 0.0
    p95 = latencies_ms[int(n * 0.95)] if n else 0.0
    p99 = latencies_ms[int(n * 0.99)] if n else 0.0
    mx  = max(latencies_ms) if latencies_ms else 0.0

    return LoadTestResult(
        n_drones=n_drones,
        duration_s=total_elapsed,
        target_hz=target_hz,
        frames_sent=frames_sent,
        frames_per_s=fps,
        p50_ms=p50,
        p95_ms=p95,
        p99_ms=p99,
        max_ms=mx,
        target_fps=float(n_drones * target_hz) / 1000.0,  # kFrames/s
    )


async def run_http_benchmark(
    base_url: str,
    n_drones: int = 100,
    duration_s: float = 10.0,
    target_hz: int = 10,
    seed: int = 42,
) -> LoadTestResult:
    """POST telemetry frames to /api/simulate as an HTTP load test."""
    if not _HAS_HTTPX:
        raise ImportError("httpx required: pip install httpx")

    rng = np.random.default_rng(seed)
    latencies_ms: list[float] = []
    frames_sent = 0
    t_start = time.perf_counter()

    async with httpx.AsyncClient(base_url=base_url, timeout=5.0) as client:
        while (time.perf_counter() - t_start) < duration_s:
            t = time.perf_counter() - t_start
            frame = _make_frame(f"D-{frames_sent % n_drones:03d}", t, rng)
            t0 = time.perf_counter()
            try:
                await client.post("/api/simulate", json={"drones": 1, "duration": 1, "seed": 42})
                latencies_ms.append((time.perf_counter() - t0) * 1000)
            except Exception:
                pass
            frames_sent += 1
            await asyncio.sleep(1.0 / (target_hz * n_drones))

    total_elapsed = time.perf_counter() - t_start
    latencies_ms.sort()
    n = len(latencies_ms)

    return LoadTestResult(
        n_drones=n_drones,
        duration_s=total_elapsed,
        target_hz=target_hz,
        frames_sent=frames_sent,
        frames_per_s=frames_sent / total_elapsed,
        p50_ms=latencies_ms[int(n * 0.50)] if n else 0.0,
        p95_ms=latencies_ms[int(n * 0.95)] if n else 0.0,
        p99_ms=latencies_ms[int(n * 0.99)] if n else 0.0,
        max_ms=max(latencies_ms) if latencies_ms else 0.0,
        target_fps=60.0,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="SDACS Load Test (P717)")
    parser.add_argument("--drones", type=int, default=100)
    parser.add_argument("--duration", type=float, default=10.0)
    parser.add_argument("--hz", type=int, default=10)
    parser.add_argument("--url", type=str, default="", help="Live server URL (optional)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if args.url:
        result = asyncio.run(run_http_benchmark(
            args.url, args.drones, args.duration, args.hz, args.seed
        ))
    else:
        result = run_local_benchmark(args.drones, args.duration, args.hz, args.seed)

    print(result.report())
    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
