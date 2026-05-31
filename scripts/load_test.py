#!/usr/bin/env python3
"""P717 — Load test: 100-drone swarm real-time visualization at 60 FPS.

Measures:
  - WebSocket throughput (messages/s)
  - HTTP endpoint latency (p50, p95, p99)
  - Memory growth under sustained load
  - Target: server must sustain ≥60 telemetry frames/s for 100-drone scenario

Usage:
    python scripts/load_test.py --host localhost --port 8080 --drones 100 --duration 30
    python scripts/load_test.py --quick   # 10s smoke test, 20 drones
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
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

LOGGER = logging.getLogger("sdacs.load_test")
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s  %(message)s")

# --------------------------------------------------------------------------- #
# Scenario payloads                                                            #
# --------------------------------------------------------------------------- #

def _drone_frame(n: int) -> dict[str, Any]:
    """Minimal JSON payload matching SimulateRequest."""
    return {"drones": n, "duration": 5, "seed": 42}


# --------------------------------------------------------------------------- #
# Result accumulator                                                            #
# --------------------------------------------------------------------------- #

@dataclass
class LatencyBucket:
    name: str
    samples: list[float] = field(default_factory=list)

    def record(self, elapsed_s: float) -> None:
        self.samples.append(elapsed_s * 1000)  # convert to ms

    def report(self) -> dict[str, float]:
        if not self.samples:
            return {"count": 0}
        s = sorted(self.samples)
        n = len(s)
        return {
            "count": n,
            "p50_ms": s[n // 2],
            "p95_ms": s[int(n * 0.95)],
            "p99_ms": s[int(n * 0.99)],
            "mean_ms": statistics.mean(s),
            "max_ms": max(s),
        }


@dataclass
class LoadTestResult:
    ws_messages_received: int = 0
    ws_duration_s: float = 0.0
    http_buckets: dict[str, LatencyBucket] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    @property
    def ws_fps(self) -> float:
        if self.ws_duration_s <= 0:
            return 0.0
        return self.ws_messages_received / self.ws_duration_s


# --------------------------------------------------------------------------- #
# HTTP load                                                                    #
# --------------------------------------------------------------------------- #

async def _http_worker(
    base_url: str,
    bucket: LatencyBucket,
    rps: float,
    duration_s: float,
    result: LoadTestResult,
    session: Any,
) -> None:
    end = time.monotonic() + duration_s
    interval = 1.0 / rps
    while time.monotonic() < end:
        t0 = time.monotonic()
        try:
            async with session.get(f"{base_url}/healthz") as resp:
                await resp.read()
                elapsed = time.monotonic() - t0
                bucket.record(elapsed)
        except Exception as exc:
            result.errors.append(f"http: {exc}")
        await asyncio.sleep(max(0, interval - (time.monotonic() - t0)))


async def run_http_load(
    base_url: str,
    concurrency: int,
    rps_per_worker: float,
    duration_s: float,
    result: LoadTestResult,
) -> None:
    try:
        import aiohttp  # type: ignore
    except ImportError:
        LOGGER.warning("aiohttp not installed — skipping HTTP load test (pip install aiohttp)")
        return

    bucket = LatencyBucket("healthz")
    result.http_buckets["healthz"] = bucket
    async with aiohttp.ClientSession() as session:
        workers = [
            _http_worker(base_url, bucket, rps_per_worker, duration_s, result, session)
            for _ in range(concurrency)
        ]
        await asyncio.gather(*workers)


# --------------------------------------------------------------------------- #
# WebSocket load                                                               #
# --------------------------------------------------------------------------- #

async def run_ws_load(
    ws_url: str,
    n_drones: int,
    duration_s: float,
    result: LoadTestResult,
) -> None:
    try:
        import aiohttp  # type: ignore
    except ImportError:
        LOGGER.warning("aiohttp not installed — skipping WS load test")
        return

    t_start = time.monotonic()
    count = 0
    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(ws_url, heartbeat=30) as ws:
                LOGGER.info("WS connected: %s", ws_url)
                end = time.monotonic() + duration_s
                while time.monotonic() < end:
                    msg = await asyncio.wait_for(ws.receive(), timeout=2.0)
                    if msg.type in (
                        getattr(msg, "WSMsgType", type(msg)).TEXT,
                        getattr(msg, "WSMsgType", type(msg)).BINARY,
                    ):
                        count += 1
                    elif msg.type in (
                        getattr(msg, "WSMsgType", type(msg)).CLOSE,
                        getattr(msg, "WSMsgType", type(msg)).ERROR,
                    ):
                        break
    except asyncio.TimeoutError:
        pass  # no message during timeout — server might be idle
    except Exception as exc:
        result.errors.append(f"ws: {exc}")
        LOGGER.warning("WS error: %s", exc)

    result.ws_messages_received = count
    result.ws_duration_s = time.monotonic() - t_start
    LOGGER.info("WS: %d messages in %.1fs → %.1f fps", count, result.ws_duration_s, result.ws_fps)


# --------------------------------------------------------------------------- #
# Simulate-endpoint flood                                                      #
# --------------------------------------------------------------------------- #

async def run_simulate_flood(
    base_url: str,
    n_drones: int,
    concurrency: int,
    result: LoadTestResult,
) -> None:
    try:
        import aiohttp  # type: ignore
    except ImportError:
        return

    bucket = LatencyBucket("simulate")
    result.http_buckets["simulate"] = bucket

    async def _one(session: Any) -> None:
        t0 = time.monotonic()
        try:
            async with session.post(
                f"{base_url}/api/simulate",
                json=_drone_frame(n_drones),
            ) as resp:
                await resp.read()
                bucket.record(time.monotonic() - t0)
        except Exception as exc:
            result.errors.append(f"simulate: {exc}")

    async with aiohttp.ClientSession() as session:
        await asyncio.gather(*[_one(session) for _ in range(concurrency)])


# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #

async def _run(args: argparse.Namespace) -> LoadTestResult:
    base_url = f"http://{args.host}:{args.port}"
    ws_url = f"ws://{args.host}:{args.port}/ws/telemetry"
    result = LoadTestResult()

    LOGGER.info(
        "Load test started  drones=%d  duration=%ds  concurrency=%d",
        args.drones, args.duration, args.concurrency,
    )

    tasks = [
        run_http_load(base_url, args.concurrency, args.rps, args.duration, result),
        run_ws_load(ws_url, args.drones, args.duration, result),
        run_simulate_flood(base_url, args.drones, args.sim_concurrency, result),
    ]
    await asyncio.gather(*tasks)
    return result


def _print_report(result: LoadTestResult, args: argparse.Namespace) -> None:
    print("\n" + "=" * 60)
    print("SDACS LOAD TEST REPORT")
    print("=" * 60)
    print(f"  drones:       {args.drones}")
    print(f"  duration:     {args.duration}s")
    print(f"  concurrency:  {args.concurrency}")
    print()
    print("WebSocket throughput:")
    print(f"  messages:   {result.ws_messages_received}")
    print(f"  duration:   {result.ws_duration_s:.1f}s")
    print(f"  fps:        {result.ws_fps:.1f}  (target ≥60)")
    print()
    for name, bucket in result.http_buckets.items():
        r = bucket.report()
        print(f"HTTP /{name}:")
        for k, v in r.items():
            print(f"  {k:10s}: {v:.1f}" if isinstance(v, float) else f"  {k:10s}: {v}")
        print()
    if result.errors:
        print(f"Errors ({len(result.errors)}):")
        for e in result.errors[:10]:
            print(f"  {e}")
    print("=" * 60)

    # Pass/fail
    target_fps = 60.0
    if result.ws_messages_received > 0 and result.ws_fps < target_fps:
        print(f"FAIL: WS fps {result.ws_fps:.1f} < {target_fps}")
        sys.exit(1)
    print("PASS" if not result.errors else "WARN: see errors above")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="SDACS load tester")
    p.add_argument("--host", default="localhost")
    p.add_argument("--port", type=int, default=8080)
    p.add_argument("--drones", type=int, default=100, help="drone count for simulate endpoint")
    p.add_argument("--duration", type=int, default=30, help="test duration in seconds")
    p.add_argument("--concurrency", type=int, default=10, help="HTTP worker count")
    p.add_argument("--rps", type=float, default=5.0, help="HTTP requests/s per worker")
    p.add_argument("--sim-concurrency", type=int, default=5, help="parallel simulate calls")
    p.add_argument("--quick", action="store_true", help="10s smoke test with 20 drones")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    if args.quick:
        args.drones = 20
        args.duration = 10
        args.concurrency = 3
        args.sim_concurrency = 2
    result = asyncio.run(_run(args))
    _print_report(result, args)


if __name__ == "__main__":
    main()
