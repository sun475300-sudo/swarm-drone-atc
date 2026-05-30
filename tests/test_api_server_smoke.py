"""Module: tests/test_api_server_smoke.py."""

from __future__ import annotations

import importlib
import json

import pytest

pytest.importorskip("fastapi")


@pytest.mark.asyncio
async def test_legacy_api_simulate_uses_constructor_override(monkeypatch: pytest.MonkeyPatch):
    api_server = importlib.import_module("api.server")

    captured: dict[str, object] = {}

    class FakeResult:
        def to_dict(self) -> dict[str, object]:
            return {"ok": True}

    class FakeSimulator:
        def __init__(self, config_path: str, scenario_cfg: dict | None = None, seed: int = 42):
            captured["config_path"] = config_path
            captured["scenario_cfg"] = scenario_cfg
            captured["seed"] = seed

        def run(self, duration_s: float) -> FakeResult:
            captured["duration_s"] = duration_s
            return FakeResult()

    monkeypatch.setattr(api_server, "SwarmSimulator", FakeSimulator)

    req = api_server.SimulateRequest(drones=12, duration=33.0, seed=7)
    result = await api_server.simulate(req)

    assert result == {"ok": True}
    assert captured["config_path"] == "config/default_simulation.yaml"
    assert captured["scenario_cfg"] == {"drones": {"default_count": 12}}
    assert captured["seed"] == 7
    assert captured["duration_s"] == 33.0


def test_fastapi_backend_module_imports_when_dependency_available():
    mod = importlib.import_module("api.fastapi_server")
    assert mod is not None


@pytest.mark.asyncio
async def test_compatibility_wrapper_exports_primary_app():
    wrapper = importlib.import_module("api.server")
    backend = importlib.import_module("api.fastapi_server")

    assert wrapper.app is backend.app


@pytest.mark.asyncio
async def test_api_run_scenario_accepts_unknown_ids_as_live_airspace(monkeypatch: pytest.MonkeyPatch):
    backend = importlib.import_module("api.fastapi_server")

    monkeypatch.setattr(
        backend,
        "_build_scenario_catalog",
        lambda: {"known_scenario": {"name": "Known Scenario"}},
    )

    scheduled: dict[str, object] = {}

    def fake_create_task(coro):
        scheduled["coro"] = coro
        coro.close()
        return object()

    monkeypatch.setattr(backend.asyncio, "create_task", fake_create_task)

    from api.auth import Role, TokenPayload
    from unittest.mock import MagicMock

    fake_request = MagicMock()
    fake_request.client.host = "127.0.0.1"
    operator_user = TokenPayload(sub="test-op", role=Role.OPERATOR, exp=9999999999, iat=0)

    body = backend.RunScenarioBody(seed=11, method="hybrid", duration_s=45)
    result = await backend.run_scenario("corridor-alpha", body, request=fake_request, user=operator_user)

    assert result["success"] is True
    assert result["data"]["status"] == "queued"
    assert result["data"]["mode"] == "live_airspace"
    run_id = result["data"]["run_id"]
    assert backend.STATE.runs[run_id].scenario_id == "corridor-alpha"
    assert "coro" in scheduled


@pytest.mark.asyncio
async def test_execute_run_uses_live_airspace_stats_for_unknown_ids(monkeypatch: pytest.MonkeyPatch):
    backend = importlib.import_module("api.fastapi_server")

    monkeypatch.setattr(backend, "_load_repo_scenarios", lambda: ["known_scenario"])
    monkeypatch.setattr(
        backend,
        "_live_airspace_stats",
        lambda corridor_label: {
            "corridor_label": corridor_label,
            "grid_utilization": 0.25,
            "active_corridors": 1,
        },
    )

    run_id = "live-run"
    backend.STATE.runs[run_id] = backend.RunRecord(
        run_id=run_id,
        scenario_id="corridor-beta",
        status="queued",
        started_at_ns=123,
    )

    await backend._execute_run(
        run_id,
        backend.RunScenarioBody(seed=3, method="hybrid", duration_s=30),
    )

    record = backend.STATE.runs[run_id]
    assert record.status == "completed"
    assert record.metrics["corridor_label"] == "corridor-beta"
    assert record.metrics["grid_utilization"] == 0.25
    assert record.finished_at_ns is not None


def test_process_live_telemetry_generates_conflict_and_advisory(monkeypatch: pytest.MonkeyPatch):
    backend = importlib.import_module("api.fastapi_server")
    monkeypatch.setattr(backend, "_build_scenario_catalog", lambda: {})

    state = backend.AppState()
    first = backend._process_live_telemetry(
        state,
        {
            "type": "telemetry",
            "drone_id": "drone-a",
            "position": [0.0, 0.0, 120.0],
            "velocity": [4.0, 0.0, 0.0],
            "battery_pct": 95.0,
            "timestamp_ns": 1_000_000_000,
        },
    )
    second = backend._process_live_telemetry(
        state,
        {
            "type": "telemetry",
            "drone_id": "drone-b",
            "position": [5.0, 0.0, 121.0],
            "velocity": [-4.0, 0.0, 0.0],
            "battery_pct": 91.0,
            "timestamp_ns": 1_100_000_000,
        },
    )

    assert first["type"] == "live_airspace_update"
    assert len(second["drones"]) == 2
    assert len(second["conflicts"]) >= 1
    assert len(second["advisories"]) >= 1
    assert second["advisories"][0]["target_drone_id"] == "drone-b"
    assert second["stats"]["active_corridors"] >= 2
    assert state.snapshot.conflicts


def test_process_live_telemetry_replaces_previous_corridor_for_same_drone(monkeypatch: pytest.MonkeyPatch):
    backend = importlib.import_module("api.fastapi_server")
    monkeypatch.setattr(backend, "_build_scenario_catalog", lambda: {})

    state = backend.AppState()
    backend._process_live_telemetry(
        state,
        {
            "drone_id": "drone-a",
            "position": [0.0, 0.0, 100.0],
            "velocity": [1.0, 0.0, 0.0],
            "timestamp_ns": 1_000_000_000,
        },
    )
    first_corridor_id = state.live_corridors["drone-a"]

    result = backend._process_live_telemetry(
        state,
        {
            "drone_id": "drone-a",
            "position": [50.0, 0.0, 100.0],
            "velocity": [1.0, 0.0, 0.0],
            "timestamp_ns": 2_000_000_000,
        },
    )

    second_corridor_id = state.live_corridors["drone-a"]
    assert second_corridor_id != first_corridor_id
    assert result["stats"]["total_corridors"] == 1
    assert first_corridor_id not in state.live_grid.corridors


@pytest.mark.asyncio
async def test_ws_telemetry_broadcasts_live_airspace_update(monkeypatch: pytest.MonkeyPatch):
    backend = importlib.import_module("api.fastapi_server")

    state = backend.AppState()
    monkeypatch.setattr(backend, "STATE", state)

    class FakeWebSocket:
        def __init__(self, incoming: list[str]) -> None:
            self._incoming = iter(incoming)
            self.outgoing: list[dict] = []
            self.accepted = False

        async def accept(self) -> None:
            self.accepted = True

        async def receive_text(self) -> str:
            try:
                return next(self._incoming)
            except StopIteration as exc:
                raise backend.WebSocketDisconnect() from exc

        async def send_text(self, text: str) -> None:
            self.outgoing.append(json.loads(text))

    ws = FakeWebSocket(
        [
            json.dumps(
                {
                    "type": "telemetry",
                    "drone_id": "drone-a",
                    "position": [0.0, 0.0, 120.0],
                    "velocity": [4.0, 0.0, 0.0],
                    "timestamp_ns": 1_000_000_000,
                }
            ),
            json.dumps(
                {
                    "type": "telemetry",
                    "drone_id": "drone-b",
                    "position": [5.0, 0.0, 121.0],
                    "velocity": [-4.0, 0.0, 0.0],
                    "timestamp_ns": 1_100_000_000,
                }
            ),
        ]
    )

    await backend.ws_telemetry(ws)
    first, second = ws.outgoing

    assert first["type"] == "live_airspace_update"
    assert len(first["drones"]) == 1
    assert second["type"] == "live_airspace_update"
    assert len(second["drones"]) == 2
    assert second["conflicts"]
    assert second["advisories"]
