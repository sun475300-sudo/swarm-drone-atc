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


def _make_fake_sim_modules():
    """Return fake simulation.apf_engine and simulation.simulator modules."""

    class FakeDroneState:
        position = [0.0, 0.0, 100.0]
        velocity = [1.0, 0.0, 0.0]

        class flight_phase:
            name = "CRUISE"

        battery_pct = 95.0

    class FakeDrone:
        state = FakeDroneState()

    class FakeMetrics:
        collision_count = 0
        near_miss_count = 0
        conflicts_total = 0
        advisories_issued = 0
        conflict_resolution_rate_pct = 100.0

    class FakeEnv:
        now = 0.0

        def run(self, until):
            self.now = until

    class FakeSwarmSimulator:
        def __init__(self, **kwargs):
            self.env = FakeEnv()
            self._drones = {1: FakeDrone()}
            self.metrics = FakeMetrics()

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

    def _run(coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    with patch("asyncio.run", _run):
        main()

    assert captured == [(50, 42, 8765)]


def test_main_parses_custom_args(monkeypatch: pytest.MonkeyPatch) -> None:
    """main() should forward custom CLI args to _run_simulation."""
    captured: list[tuple] = []

    async def fake_run(drones, seed, port):
        captured.append((drones, seed, port))

    monkeypatch.setattr(ws_bridge, "_run_simulation", fake_run)
    monkeypatch.setattr(sys, "argv", ["ws_bridge", "--drones", "100", "--seed", "7", "--port", "9000"])

    def _run(coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    with patch("asyncio.run", _run):
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
