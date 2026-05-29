"""P717 — WebSocket load test for 100-drone swarm real-time visualisation.

Spawns N concurrent WebSocket clients against /ws/telemetry and measures
throughput (messages/s) and round-trip latency. Target: ≥60 msg/s average
with 100 concurrent connections.

Usage:
    python scripts/load_test.py                          # 100 clients, 5 s
    python scripts/load_test.py --clients 10 --dur 3    # quick smoke
    python scripts/load_test.py --url ws://host:8080/ws/telemetry --fps 30
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from dataclasses import dataclass, field


try:
    import websockets
    import websockets.exceptions
except ImportError as exc:
    raise SystemExit("websockets required: pip install 'websockets>=12'") from exc


@dataclass
class ClientResult:
    client_id: int
    messages: int = 0
    latencies_ms: list[float] = field(default_factory=list)
    error: str = ""
    duration_s: float = 0.0

    @property
    def rate(self) -> float:
        return self.messages / self.duration_s if self.duration_s > 0 else 0.0


async def _run_client(client_id: int, url: str, duration_s: float) -> ClientResult:
    result = ClientResult(client_id=client_id)
    t_start = time.monotonic()
    try:
        async with websockets.connect(url, ping_interval=None, close_timeout=2) as ws:
            deadline = t_start + duration_s
            while time.monotonic() < deadline:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=0.05)
                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        result.messages += 1
                        continue
                    server_ts_ns = msg.get("t", 0)
                    if server_ts_ns:
                        latency_ms = (time.time_ns() - server_ts_ns) / 1e6
                        if 0 < latency_ms < 5000:
                            result.latencies_ms.append(latency_ms)
                    result.messages += 1
                except asyncio.TimeoutError:
                    continue
    except websockets.exceptions.WebSocketException as exc:
        result.error = str(exc)
    except OSError as exc:
        result.error = str(exc)
    result.duration_s = time.monotonic() - t_start
    return result


def _print_report(results: list[ClientResult], target_fps: float) -> int:
    ok = [r for r in results if not r.error]
    failed = [r for r in results if r.error]
    total = len(results)

    print("=" * 64)
    print("SDACS P717 WebSocket Load Test Report")
    print("=" * 64)

    if not ok:
        print(f"FAIL — all {total} clients failed to connect")
        if failed:
            print(f"  first error: {failed[0].error}")
        return 1

    rates = [r.rate for r in ok]
    avg_rate = statistics.mean(rates)
    p50_rate = statistics.median(rates)
    min_rate = min(rates)
    max_rate = max(rates)

    all_latencies = sorted(lat for r in ok for lat in r.latencies_ms)
    p50_lat = all_latencies[len(all_latencies) // 2] if all_latencies else float("nan")
    p99_lat = all_latencies[int(len(all_latencies) * 0.99)] if all_latencies else float("nan")

    print(f"Clients connected : {len(ok):>4} / {total}")
    print(f"Clients failed    : {len(failed):>4}")
    print(f"Total messages    : {sum(r.messages for r in ok):>8}")
    print()
    print(f"Throughput (msg/s per client)")
    print(f"  avg : {avg_rate:>8.1f}    target: {target_fps:.0f}")
    print(f"  P50 : {p50_rate:>8.1f}")
    print(f"  min : {min_rate:>8.1f}")
    print(f"  max : {max_rate:>8.1f}")
    print()
    print(f"Latency (server timestamp → client recv)")
    print(f"  P50 : {p50_lat:>8.1f} ms")
    print(f"  P99 : {p99_lat:>8.1f} ms")

    if failed:
        print(f"\nFailed clients (first {min(5, len(failed))}):")
        for r in failed[:5]:
            print(f"  client-{r.client_id}: {r.error}")

    passed = avg_rate >= target_fps and len(failed) == 0
    verdict = "PASS" if passed else "FAIL"
    cmp = ">=" if passed else "<"
    print(f"\n{verdict} — avg {avg_rate:.1f} msg/s {cmp} {target_fps:.0f} FPS target")
    return 0 if passed else 1


async def _main(url: str, n_clients: int, duration_s: float, target_fps: float) -> int:
    print(f"Spawning {n_clients} WebSocket clients → {url} for {duration_s:.1f}s …")
    tasks = [_run_client(i, url, duration_s) for i in range(n_clients)]
    results = await asyncio.gather(*tasks)
    return _print_report(list(results), target_fps)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="P717 WebSocket load test")
    parser.add_argument("--url", default="ws://localhost:8080/ws/telemetry",
                        help="WebSocket URL to test (default: ws://localhost:8080/ws/telemetry)")
    parser.add_argument("--clients", type=int, default=100,
                        help="number of concurrent clients (default: 100)")
    parser.add_argument("--dur", type=float, default=5.0,
                        help="test duration in seconds (default: 5.0)")
    parser.add_argument("--fps", type=float, default=60.0,
                        help="target messages/sec per client (default: 60)")
    args = parser.parse_args(argv)
    code = asyncio.run(_main(args.url, args.clients, args.dur, args.fps))
    sys.exit(code)


if __name__ == "__main__":
    main()
