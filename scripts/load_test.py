#!/usr/bin/env python3
"""P717 — Load test for SDACS FastAPI backend.

Simulates concurrent users hitting key endpoints, measures throughput and
latency, and asserts that p95 latency stays under SLA thresholds.

Requires: httpx, asyncio (stdlib)
Optional: rich (pretty tables)

Usage:
    # Start the server first:
    uvicorn api.fastapi_server:app --port 8080

    # Run load test:
    python scripts/load_test.py
    python scripts/load_test.py --url http://localhost:8080 --users 20 --duration 30
    python scripts/load_test.py --users 100 --duration 60 --sla-p95-ms 500

Exit codes:
    0 — all SLA assertions passed
    1 — SLA breach or server unreachable
"""
from __future__ import annotations

import argparse
import asyncio
import statistics
import sys
import time
from dataclasses import dataclass, field
from typing import Any

try:
    import httpx
except ImportError:
    print("httpx is required: pip install httpx", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# SLA defaults (milliseconds)
# ---------------------------------------------------------------------------
SLA_P50_MS = 100
SLA_P95_MS = 500
SLA_P99_MS = 1000
SLA_ERROR_RATE = 0.05  # max 5% error rate


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class RequestResult:
    endpoint: str
    status_code: int
    latency_ms: float
    error: str | None = None


@dataclass
class EndpointStats:
    endpoint: str
    count: int = 0
    errors: int = 0
    latencies: list[float] = field(default_factory=list)

    @property
    def error_rate(self) -> float:
        return self.errors / self.count if self.count else 0.0

    def percentile(self, p: float) -> float:
        if not self.latencies:
            return 0.0
        sorted_lat = sorted(self.latencies)
        # Nearest-rank formula: ceil(N * p/100) - 1, clamped to valid range.
        idx = max(0, int(len(sorted_lat) * p / 100) - 1)
        return sorted_lat[idx]


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------

async def _get_token(client: httpx.AsyncClient, base_url: str) -> str | None:
    try:
        resp = await client.post(
            f"{base_url}/auth/token",
            data={"username": "operator", "password": "operator"},
            timeout=5.0,
        )
        if resp.status_code == 200:
            return resp.json()["access_token"]
    except Exception:
        pass
    return None


async def _worker(
    client: httpx.AsyncClient,
    base_url: str,
    token: str | None,
    results: list[RequestResult],
    stop_event: asyncio.Event,
) -> None:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    endpoints = [
        ("GET", "/healthz", None),
        ("GET", "/health", None),
        ("GET", "/api/scenarios", None),
        ("GET", "/metrics", None),
        ("GET", "/auth/me", None),
    ]
    idx = 0
    while not stop_event.is_set():
        method, path, body = endpoints[idx % len(endpoints)]
        idx += 1
        url = f"{base_url}{path}"
        t0 = time.perf_counter()
        try:
            if method == "GET":
                resp = await client.get(url, headers=headers, timeout=5.0)
            else:
                resp = await client.post(url, json=body, headers=headers, timeout=5.0)
            latency_ms = (time.perf_counter() - t0) * 1000
            # Treat any non-2xx/3xx response as an error — 401/403/404 indicate
            # misconfiguration or auth failures under load, not acceptable outcomes.
            is_error = resp.status_code >= 400
            results.append(
                RequestResult(
                    endpoint=path,
                    status_code=resp.status_code,
                    latency_ms=latency_ms,
                    error=f"HTTP {resp.status_code}" if is_error else None,
                )
            )
        except Exception as exc:
            latency_ms = (time.perf_counter() - t0) * 1000
            results.append(
                RequestResult(
                    endpoint=path,
                    status_code=0,
                    latency_ms=latency_ms,
                    error=str(exc),
                )
            )
        await asyncio.sleep(0.01)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

async def run_load_test(
    base_url: str,
    n_users: int,
    duration_s: float,
    sla_p95_ms: float,
) -> bool:
    results: list[RequestResult] = []
    stop_event = asyncio.Event()

    async with httpx.AsyncClient() as client:
        # Verify server is up
        try:
            resp = await client.get(f"{base_url}/healthz", timeout=5.0)
            if resp.status_code != 200:
                print(f"ERROR: server at {base_url} returned {resp.status_code}", file=sys.stderr)
                return False
        except Exception as exc:
            print(f"ERROR: cannot reach {base_url}: {exc}", file=sys.stderr)
            return False

        print(f"Server OK — starting {n_users} users for {duration_s}s …")

        token = await _get_token(client, base_url)
        if token:
            print("Auth: JWT token obtained (operator role)")
        else:
            print("Auth: no token — unauthenticated endpoints only")

        workers = [
            asyncio.create_task(_worker(client, base_url, token, results, stop_event))
            for _ in range(n_users)
        ]
        await asyncio.sleep(duration_s)
        stop_event.set()
        await asyncio.gather(*workers, return_exceptions=True)

    # ---------------------------------------------------------------------------
    # Aggregate stats
    # ---------------------------------------------------------------------------
    by_endpoint: dict[str, EndpointStats] = {}
    for r in results:
        stats = by_endpoint.setdefault(r.endpoint, EndpointStats(r.endpoint))
        stats.count += 1
        stats.latencies.append(r.latency_ms)
        if r.error is not None:
            stats.errors += 1

    total = len(results)
    total_errors = sum(r.error is not None for r in results)
    all_latencies = [r.latency_ms for r in results]
    rps = total / duration_s if duration_s > 0 else 0

    print(f"\n{'='*60}")
    print(f"  Load test results — {base_url}")
    print(f"{'='*60}")
    print(f"  Users:        {n_users}")
    print(f"  Duration:     {duration_s}s")
    print(f"  Total reqs:   {total}")
    print(f"  RPS:          {rps:.1f}")
    print(f"  Errors:       {total_errors} ({100*total_errors/max(total,1):.1f}%)")
    _all_stats = EndpointStats("__all__", latencies=list(all_latencies))
    if all_latencies:
        print(f"  Latency p50:  {_all_stats.percentile(50):.1f} ms")
        print(f"  Latency p95:  {_all_stats.percentile(95):.1f} ms")
        print(f"  Latency p99:  {_all_stats.percentile(99):.1f} ms")
        print(f"  Latency max:  {max(all_latencies):.1f} ms")
    print(f"\n  {'Endpoint':<30} {'Reqs':>6} {'Err%':>6} {'p50':>8} {'p95':>8}")
    print(f"  {'-'*30} {'-'*6} {'-'*6} {'-'*8} {'-'*8}")
    for ep, stats in sorted(by_endpoint.items()):
        print(
            f"  {ep:<30} {stats.count:>6} {100*stats.error_rate:>5.1f}%"
            f" {stats.percentile(50):>7.1f}ms {stats.percentile(95):>7.1f}ms"
        )

    # ---------------------------------------------------------------------------
    # SLA assertions
    # ---------------------------------------------------------------------------
    passed = True
    p95 = _all_stats.percentile(95)
    error_rate = total_errors / max(total, 1)

    print(f"\n  SLA checks (p95 ≤ {sla_p95_ms}ms, error rate ≤ {100*SLA_ERROR_RATE}%):")
    if p95 <= sla_p95_ms:
        print(f"  ✓ p95 latency {p95:.1f}ms ≤ {sla_p95_ms}ms")
    else:
        print(f"  ✗ p95 latency {p95:.1f}ms > {sla_p95_ms}ms  [FAIL]")
        passed = False

    if error_rate <= SLA_ERROR_RATE:
        print(f"  ✓ error rate {100*error_rate:.1f}% ≤ {100*SLA_ERROR_RATE}%")
    else:
        print(f"  ✗ error rate {100*error_rate:.1f}% > {100*SLA_ERROR_RATE}%  [FAIL]")
        passed = False

    print(f"\n  Result: {'PASS' if passed else 'FAIL'}")
    return passed


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="SDACS load tester (P717)")
    parser.add_argument("--url", default="http://localhost:8080", help="Base URL of the FastAPI server")
    parser.add_argument("--users", type=int, default=10, help="Concurrent users")
    parser.add_argument("--duration", type=float, default=15.0, help="Test duration in seconds")
    parser.add_argument("--sla-p95-ms", type=float, default=SLA_P95_MS, help="p95 latency SLA in ms")
    args = parser.parse_args()

    passed = asyncio.run(
        run_load_test(
            base_url=args.url,
            n_users=args.users,
            duration_s=args.duration,
            sla_p95_ms=args.sla_p95_ms,
        )
    )
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
