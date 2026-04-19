"""
WebSocket 브릿지 — SwarmSimulator ↔ 3D 시뮬레이터 실시간 연동

asyncio WebSocket 서버 (port 8765)로 시뮬레이션 스냅샷을 스트리밍.
swarm_3d_simulator.html에서 ws://localhost:8765로 연결하여 실시간 데이터 수신.

실행: python simulation/ws_bridge.py [--drones 50] [--port 8765]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import os
import time

import numpy as np

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


async def _run_simulation(drones: int, seed: int, port: int):
    """시뮬레이션을 실행하면서 WebSocket으로 스냅샷 스트리밍."""
    try:
        import websockets
    except ImportError:
        print("websockets 패키지가 필요합니다: pip install websockets")
        return

    from simulation.simulator import SwarmSimulator
    from simulation.apf_engine import get_apf_backend_info

    backend = get_apf_backend_info()
    gpu_name = backend.get("gpu", "CPU") or "CPU"
    print(f"🛸 WebSocket 브릿지 시작: {drones}기, port={port} [{gpu_name}]")

    clients: set = set()

    async def handler(websocket):
        clients.add(websocket)
        try:
            await websocket.wait_closed()
        finally:
            clients.discard(websocket)

    server = await websockets.serve(handler, "0.0.0.0", port)
    print(f"📡 ws://localhost:{port} 대기 중...")

    cfg = {"drones": {"default_count": drones}}
    sim = SwarmSimulator(seed=seed, scenario_cfg=cfg)

    # SimPy 환경을 0.1초씩 진행하면서 스냅샷 전송
    dt = 0.1
    tick = 0
    while True:
        sim.env.run(until=sim.env.now + dt)
        tick += 1

        # 10Hz → 2Hz 다운샘플 (5틱마다 전송)
        if tick % 5 != 0:
            await asyncio.sleep(0.01)
            continue

        # 드론 스냅샷 구성
        snapshot = {
            "t": round(float(sim.env.now), 1),
            "drones": [],
            "stats": {
                "collisions": sim.metrics.collision_count,
                "near_misses": sim.metrics.near_miss_count,
                "conflicts": sim.metrics.conflicts_total,
                "advisories": sim.metrics.advisories_issued,
                "resolution_rate": round(sim.metrics.conflict_resolution_rate_pct, 1),
            },
            "backend": backend.get("device", "cpu"),
        }

        for did, drone in sim._drones.items():
            snapshot["drones"].append({
                "id": did,
                "pos": [round(float(x), 1) for x in drone.state.position],
                "vel": [round(float(x), 1) for x in drone.state.velocity],
                "phase": drone.state.flight_phase.name,
                "battery": round(float(drone.state.battery_pct), 1),
            })

        msg = json.dumps(snapshot, ensure_ascii=False)

        # 연결된 모든 클라이언트에 전송
        if clients:
            await asyncio.gather(
                *[c.send(msg) for c in clients],
                return_exceptions=True,
            )

        await asyncio.sleep(0.05)


def main():
    parser = argparse.ArgumentParser(description="WebSocket 시뮬레이션 브릿지")
    parser.add_argument("--drones", type=int, default=50)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    asyncio.run(_run_simulation(args.drones, args.seed, args.port))


if __name__ == "__main__":
    main()
