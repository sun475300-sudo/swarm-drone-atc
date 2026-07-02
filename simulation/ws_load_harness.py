"""TRANSCENDENCE Phase 246 — WebSocket 부하 테스트 하니스 (100 동시 사용자).

결정적 부하 *계획* (LoadPlan) 과 실측 *실행기* (run_load_test) 를 분리한다:
- 계획: 클라이언트 수·램프업·메시지 수를 결정적으로 산출 — 단위 테스트 가능
- 실행: asyncio + websockets 로 실 서버에 접속 (서버 주소는 호출자가 제공,
  기본 loopback — ws_bridge 보안 기본값과 정합)

정직성: 본 하니스의 실측은 *로컬 loopback 조건* 이며 실 네트워크·실 배포
(K8s Phase 247) 성능을 대변하지 않는다. 가치는 (1) 서버가 100 동시 접속에서
크래시·데드락 없이 응답하는가 (2) 동일 계획 재실행 시 회귀 비교 기준선.

사용:
    python -m simulation.ws_load_harness --url ws://127.0.0.1:8765 --clients 100
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from dataclasses import dataclass, field

__all__ = ["ClientPlan", "LoadPlan", "LoadReport", "build_plan", "run_load_test", "summarize"]

DEFAULT_CLIENTS = 100
DEFAULT_MESSAGES_PER_CLIENT = 10
DEFAULT_RAMP_UP_S = 5.0


@dataclass(frozen=True)
class ClientPlan:
    """클라이언트 1개의 결정적 실행 계획."""

    client_id: str
    start_offset_s: float  # 램프업 내 시작 시점 (결정적 균등 분배)
    messages: int


@dataclass(frozen=True)
class LoadPlan:
    """부하 테스트 전체 계획 — 동일 인자 → 동일 계획 (무작위성 0)."""

    url: str
    clients: tuple[ClientPlan, ...]
    messages_per_client: int
    ramp_up_s: float

    @property
    def total_messages(self) -> int:
        return sum(c.messages for c in self.clients)


@dataclass
class LoadReport:
    """실행 결과 집계."""

    connected: int = 0
    connect_failures: int = 0
    messages_sent: int = 0
    messages_recv: int = 0
    errors: int = 0
    latencies_ms: list[float] = field(default_factory=list)
    duration_s: float = 0.0

    def latency_summary(self) -> dict:
        if not self.latencies_ms:
            return {"count": 0}
        xs = sorted(self.latencies_ms)
        return {
            "count": len(xs),
            "p50_ms": round(statistics.median(xs), 2),
            "p95_ms": round(xs[min(len(xs) - 1, int(len(xs) * 0.95))], 2),
            "max_ms": round(xs[-1], 2),
        }


def build_plan(
    url: str,
    n_clients: int = DEFAULT_CLIENTS,
    messages_per_client: int = DEFAULT_MESSAGES_PER_CLIENT,
    ramp_up_s: float = DEFAULT_RAMP_UP_S,
) -> LoadPlan:
    """결정적 부하 계획 생성 — 시작 시점은 램프업 구간 균등 분배."""
    if n_clients < 1:
        raise ValueError("n_clients >= 1")
    if messages_per_client < 0:
        raise ValueError("messages_per_client >= 0")
    if ramp_up_s < 0:
        raise ValueError("ramp_up_s >= 0")
    step = ramp_up_s / n_clients if n_clients > 0 else 0.0
    clients = tuple(
        ClientPlan(client_id=f"load-{i:04d}", start_offset_s=round(i * step, 6), messages=messages_per_client)
        for i in range(n_clients)
    )
    return LoadPlan(url=url, clients=clients, messages_per_client=messages_per_client, ramp_up_s=ramp_up_s)


async def _run_client(plan: ClientPlan, url: str, report: LoadReport, recv_timeout_s: float) -> None:
    import websockets  # 지역 import — 하니스 실행 시에만 필요

    await asyncio.sleep(plan.start_offset_s)
    try:
        async with websockets.connect(url, open_timeout=10) as ws:
            report.connected += 1
            for seq in range(1, plan.messages + 1):
                t0 = time.monotonic()
                await ws.send(json.dumps({
                    "type": "load_probe", "client_id": plan.client_id, "seq": seq,
                }))
                report.messages_sent += 1
                try:
                    await asyncio.wait_for(ws.recv(), timeout=recv_timeout_s)
                    report.messages_recv += 1
                    report.latencies_ms.append((time.monotonic() - t0) * 1000.0)
                except asyncio.TimeoutError:
                    # 서버가 probe 에 응답하지 않는 프로토콜이면 수신 통계만 0 —
                    # 접속 유지·송신 성공 자체가 1차 검증 대상
                    pass
    except Exception:  # noqa: BLE001 — 접속 실패는 집계 대상
        report.connect_failures += 1


async def run_load_test(plan: LoadPlan, recv_timeout_s: float = 2.0) -> LoadReport:
    """계획 실행 — 모든 클라이언트 동시 기동 (램프업 오프셋 적용)."""
    report = LoadReport()
    t0 = time.monotonic()
    await asyncio.gather(*(_run_client(c, plan.url, report, recv_timeout_s) for c in plan.clients))
    report.duration_s = round(time.monotonic() - t0, 3)
    return report


def summarize(plan: LoadPlan, report: LoadReport) -> dict:
    """결과 요약 — CI/회귀 비교용 JSON."""
    return {
        "url": plan.url,
        "planned_clients": len(plan.clients),
        "planned_messages": plan.total_messages,
        "connected": report.connected,
        "connect_failures": report.connect_failures,
        "messages_sent": report.messages_sent,
        "messages_recv": report.messages_recv,
        "duration_s": report.duration_s,
        "latency": report.latency_summary(),
        "pass": report.connect_failures == 0 and report.connected == len(plan.clients),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="ws://127.0.0.1:8765", help="대상 WS 서버 (기본 loopback)")
    parser.add_argument("--clients", type=int, default=DEFAULT_CLIENTS)
    parser.add_argument("--messages", type=int, default=DEFAULT_MESSAGES_PER_CLIENT)
    parser.add_argument("--ramp-up", type=float, default=DEFAULT_RAMP_UP_S)
    args = parser.parse_args(argv)

    plan = build_plan(args.url, args.clients, args.messages, args.ramp_up)
    report = asyncio.run(run_load_test(plan))
    out = summarize(plan, report)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
