"""Tests for simulation/ws_bridge.py — argparse, import-guard, and async loop."""
from __future__ import annotations

import asyncio
import sys
import types
from unittest.mock import patch

import pytest

import simulation.ws_bridge as ws_bridge
from simulation.ws_bridge import _run_simulation, main

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_coro_in_new_loop(coro):
    """asyncio.run 대체용: 새 이벤트 루프에서 코루틴 실행.

    Python 3.10에선 현재 이벤트 루프가 없을 때 asyncio.get_event_loop()가
    RuntimeError를 던지므로(3.12에서 폐기) 명시적으로 새 루프를 만들어 호환.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _make_fake_sim_modules():
    """Return fake simulation.apf_engine and simulation.simulator modules."""

    class FakeFlightPhase:
        name = "CRUISE"

    class FakeDrone:
        # SwarmSimulator._drones[id] = DroneState (직접 속성, state 래퍼 없음)
        position = [0.0, 0.0, 100.0]
        velocity = [1.0, 0.0, 0.0]
        flight_phase = FakeFlightPhase()
        battery_pct = 95.0

    class FakeController:
        # 컨트롤러 내부 통계 카운터 (ws_bridge가 _safe_int로 안전 접근)
        _collision_count = 0
        _near_miss_count = 0
        _conflicts_total = 0
        _advisories_issued = 0
        _cbs_attempts = 0
        _cbs_successes = 0

        def run(self):
            if False:
                yield  # generator 형태 유지

    class FakeEnv:
        now = 0.0

        def run(self, until: float) -> None:
            self.now = until

        def process(self, _coro) -> None:
            # SimPy.env.process 모킹 — 등록만 하고 실행은 무시
            return None

    class FakeSwarmSimulator:
        def __init__(self, **kwargs):
            self.env = FakeEnv()
            self._drones = {1: FakeDrone()}
            self.controller = FakeController()

        def _spawn_drones(self) -> None:
            return None

        def _apf_batch_loop(self):
            if False:
                yield  # generator 형태 유지

    fake_sim = types.SimpleNamespace(SwarmSimulator=FakeSwarmSimulator)
    fake_apf = types.SimpleNamespace(
        get_apf_backend_info=lambda: {"gpu": "FakeGPU", "device": "cuda:0"}
    )
    return fake_sim, fake_apf


def _make_fake_websockets():
    """Return a fake websockets module that tracks serve calls."""
    serve_calls: list[dict] = []

    async def fake_serve(handler, host, port):
        serve_calls.append({"host": host, "port": port})
        return types.SimpleNamespace()

    fake_ws = types.SimpleNamespace(serve=fake_serve)
    return fake_ws, serve_calls


# ---------------------------------------------------------------------------
# main() — argument parsing
# ---------------------------------------------------------------------------


def test_main_parses_default_args(monkeypatch: pytest.MonkeyPatch) -> None:
    """main() should use default drones=50 seed=42 port=8765."""
    captured: list[tuple] = []

    async def fake_run(drones, seed, port):
        captured.append((drones, seed, port))

    monkeypatch.setattr(ws_bridge, "_run_simulation", fake_run)
    monkeypatch.setattr(sys, "argv", ["ws_bridge"])

    with patch("asyncio.run", _run_coro_in_new_loop):
        main()

    assert captured == [(50, 42, 8765)]


def test_main_parses_custom_args(monkeypatch: pytest.MonkeyPatch) -> None:
    """main() should forward custom CLI args to _run_simulation."""
    captured: list[tuple] = []

    async def fake_run(drones, seed, port):
        captured.append((drones, seed, port))

    monkeypatch.setattr(ws_bridge, "_run_simulation", fake_run)
    monkeypatch.setattr(sys, "argv", ["ws_bridge", "--drones", "100", "--seed", "7", "--port", "9000"])

    with patch("asyncio.run", _run_coro_in_new_loop):
        main()

    assert captured == [(100, 7, 9000)]


# ---------------------------------------------------------------------------
# _run_simulation() — import-guard path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_simulation_returns_early_when_websockets_missing(
    monkeypatch: pytest.MonkeyPatch,
    capsys,
) -> None:
    """_run_simulation should print a helpful message and return when websockets is absent."""
    monkeypatch.setitem(sys.modules, "websockets", None)

    await _run_simulation(5, 42, 19765)

    out = capsys.readouterr().out
    assert "websockets" in out or "pip" in out


# ---------------------------------------------------------------------------
# _run_simulation() — happy path (mocked deps, task cancellation)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_simulation_starts_server_and_loops(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """_run_simulation should start a WebSocket server and begin the SimPy tick loop."""
    fake_sim_mod, fake_apf_mod = _make_fake_sim_modules()
    fake_ws, serve_calls = _make_fake_websockets()

    monkeypatch.setitem(sys.modules, "websockets", fake_ws)
    monkeypatch.setitem(sys.modules, "simulation.simulator", fake_sim_mod)
    monkeypatch.setitem(sys.modules, "simulation.apf_engine", fake_apf_mod)

    task = asyncio.create_task(_run_simulation(5, 42, 19766))
    await asyncio.sleep(0.15)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert serve_calls, "websockets.serve should have been called"
    assert serve_calls[0]["port"] == 19766


@pytest.mark.asyncio
async def test_run_simulation_broadcasts_to_connected_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Snapshots should be sent to connected WebSocket clients."""
    fake_sim_mod, fake_apf_mod = _make_fake_sim_modules()

    messages: list[str] = []

    class FakeClient:
        async def send(self, msg: str) -> None:
            messages.append(msg)

        async def wait_closed(self) -> None:
            await asyncio.sleep(1000)

    client = FakeClient()

    async def fake_serve(handler, host, port):
        asyncio.create_task(handler(client))
        return types.SimpleNamespace()

    fake_ws = types.SimpleNamespace(serve=fake_serve)
    monkeypatch.setitem(sys.modules, "websockets", fake_ws)
    monkeypatch.setitem(sys.modules, "simulation.simulator", fake_sim_mod)
    monkeypatch.setitem(sys.modules, "simulation.apf_engine", fake_apf_mod)

    task = asyncio.create_task(_run_simulation(5, 42, 19767))
    # 5 ticks @ 0.01s each + 1 broadcast tick @ 0.05s ~= 0.09s; wait 0.3s to be safe
    await asyncio.sleep(0.30)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert messages, "at least one snapshot should have been sent to the client"
