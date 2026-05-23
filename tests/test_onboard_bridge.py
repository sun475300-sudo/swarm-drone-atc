from __future__ import annotations

import asyncio
import json
import sys
import types

import pytest

import src.hardware.onboard_bridge as _bridge_module
from src.hardware.onboard_bridge import (
    TELEMETRY_POLL_HZ,
    BridgeConfig,
    BridgeState,
    CallableRemoteIDTransport,
    GroundLink,
    LogRemoteIDTransport,
    MavlinkAdapter,
    OnboardBridge,
    RemoteIDTransport,
    TelemetrySnapshot,
    _load_remote_id_transport,
    parse_args,
)


def _snapshot(drone_id: int, seq: int = 0) -> TelemetrySnapshot:
    return TelemetrySnapshot(
        drone_id=drone_id,
        timestamp_ns=seq,
        lat_deg=37.5,
        lon_deg=127.0,
        alt_msl_m=120.0,
        alt_rel_m=30.0,
        vx_mps=1.0,
        vy_mps=0.0,
        vz_mps=-0.1,
        heading_deg=90.0,
        battery_pct=88.0,
        mode="GUIDED",
        armed=True,
        gps_fix_type=3,
    )


class FakeMav:
    def __init__(self, *, poll_failures: int = 0, send_failures: int = 0) -> None:
        self.poll_failures = poll_failures
        self.send_failures = send_failures
        self.connect_calls = 0
        self.close_calls = 0
        self.poll_calls = 0
        self.sent_commands: list[dict] = []

    async def connect(self) -> None:
        self.connect_calls += 1

    async def poll_telemetry(self, drone_id: int) -> TelemetrySnapshot:
        if self.poll_failures > 0:
            self.poll_failures -= 1
            raise RuntimeError("mavlink down")
        self.poll_calls += 1
        return _snapshot(drone_id, self.poll_calls)

    async def send_command(self, command_dict: dict) -> bool:
        if self.send_failures > 0:
            self.send_failures -= 1
            raise RuntimeError("command link down")
        self.sent_commands.append(command_dict)
        return True

    async def close(self) -> None:
        self.close_calls += 1


class FakeGround:
    def __init__(
        self,
        *,
        publish_failures: int = 0,
        command_errors: int = 0,
        commands: list[dict] | None = None,
    ) -> None:
        self.publish_failures = publish_failures
        self.command_errors = command_errors
        self.connect_calls = 0
        self.close_calls = 0
        self.published: list[TelemetrySnapshot] = []
        self.commands = list(commands or [])

    async def connect(self) -> None:
        self.connect_calls += 1

    async def publish(self, snapshot: TelemetrySnapshot) -> None:
        if self.publish_failures > 0:
            self.publish_failures -= 1
            raise RuntimeError("ground send failed")
        self.published.append(snapshot)

    async def next_command(self) -> dict | None:
        if self.command_errors > 0:
            self.command_errors -= 1
            raise RuntimeError("ground recv failed")
        if self.commands:
            return self.commands.pop(0)
        return None

    async def close(self) -> None:
        self.close_calls += 1


async def _run_bridge_for(bridge: OnboardBridge, duration_s: float = 0.12) -> int:
    task = asyncio.create_task(bridge.run())
    await asyncio.sleep(duration_s)
    await bridge.stop()
    return await task


@pytest.mark.asyncio
async def test_groundlink_next_command_raises_on_transport_error() -> None:
    class BrokenSocket:
        async def recv(self) -> str:
            raise RuntimeError("socket closed")

        async def close(self) -> None:
            return None

    link = GroundLink("ws://ground", 7)
    link._ws = BrokenSocket()

    with pytest.raises(RuntimeError, match="ground recv error: socket closed"):
        await link.next_command()


@pytest.mark.asyncio
async def test_onboard_bridge_reconnects_after_mavlink_poll_failure() -> None:
    config = BridgeConfig(
        drone_id=7,
        mavlink_uri="udp://unused",
        ground_uri="ws://unused",
        heartbeat_interval_s=0.01,
        telemetry_poll_hz=100,
        enable_remote_id=False,
    )
    mav = FakeMav(poll_failures=1)
    ground = FakeGround()
    bridge = OnboardBridge(config=config, mav=mav, ground=ground)

    rc = await _run_bridge_for(bridge)

    assert rc == 0
    assert bridge.state.mavlink_reconnects == 1
    assert mav.connect_calls >= 2
    assert ground.connect_calls >= 2
    assert bridge.state.frames_out >= 1
    assert len(ground.published) >= 1


@pytest.mark.asyncio
async def test_onboard_bridge_reconnects_after_ground_publish_failure() -> None:
    config = BridgeConfig(
        drone_id=9,
        mavlink_uri="udp://unused",
        ground_uri="ws://unused",
        heartbeat_interval_s=0.01,
        telemetry_poll_hz=100,
        enable_remote_id=False,
    )
    mav = FakeMav()
    ground = FakeGround(publish_failures=1)
    bridge = OnboardBridge(config=config, mav=mav, ground=ground)

    rc = await _run_bridge_for(bridge)

    assert rc == 0
    assert bridge.state.ground_reconnects == 1
    assert mav.connect_calls >= 2
    assert ground.connect_calls >= 2
    assert bridge.state.frames_out >= 1
    assert len(ground.published) >= 1


def test_load_remote_id_transport_wraps_callable_from_module_attribute(monkeypatch: pytest.MonkeyPatch) -> None:
    emitted: list[int] = []

    def _emitter(snapshot: TelemetrySnapshot) -> None:
        emitted.append(snapshot.drone_id)

    monkeypatch.setattr("src.hardware.onboard_bridge._test_remote_id_emitter", _emitter, raising=False)
    transport = _load_remote_id_transport("src.hardware.onboard_bridge:_test_remote_id_emitter")

    transport.emit(_snapshot(42))
    assert emitted == [42]


@pytest.mark.asyncio
async def test_onboard_bridge_uses_injected_remote_id_transport() -> None:
    emitted: list[int] = []
    config = BridgeConfig(
        drone_id=13,
        mavlink_uri="udp://unused",
        ground_uri="ws://unused",
        heartbeat_interval_s=0.01,
        telemetry_poll_hz=100,
        enable_remote_id=True,
    )
    mav = FakeMav()
    ground = FakeGround()
    transport = CallableRemoteIDTransport(lambda snapshot: emitted.append(snapshot.drone_id))
    bridge = OnboardBridge(
        config=config,
        mav=mav,
        ground=ground,
        remote_id_transport=transport,
    )

    rc = await _run_bridge_for(bridge)

    assert rc == 0
    assert emitted
    assert set(emitted) == {13}


# --- TelemetrySnapshot ---


def test_telemetry_snapshot_to_json() -> None:
    snap = _snapshot(5, seq=1000)
    result = json.loads(snap.to_json())
    assert result["drone_id"] == 5
    assert result["pos"]["lat"] == pytest.approx(37.5)
    assert result["pos"]["lon"] == pytest.approx(127.0)
    assert result["armed"] is True
    assert result["mode"] == "GUIDED"
    assert result["fix"] == 3


# --- MavlinkAdapter ---


def test_mav_adapter_init_attributes() -> None:
    adapter = MavlinkAdapter("udp:localhost:14550")
    assert adapter.uri == "udp:localhost:14550"
    assert adapter._connection is None
    assert adapter._last_heartbeat_mode == "UNKNOWN"


@pytest.mark.asyncio
async def test_mav_adapter_close_noop_when_not_connected() -> None:
    adapter = MavlinkAdapter("udp:localhost:14550")
    await adapter.close()
    assert adapter._connection is None


def test_mav_decode_mode_armed_and_guided() -> None:
    mode = MavlinkAdapter._decode_mode(0x80 | 0x08, 0)
    assert "SAFETY_ARMED" in mode
    assert "GUIDED_ENABLED" in mode


def test_mav_decode_mode_custom_mode() -> None:
    mode = MavlinkAdapter._decode_mode(0, 4)
    assert "custom=4" in mode


def test_mav_decode_mode_unknown_when_zero() -> None:
    assert MavlinkAdapter._decode_mode(0, 0) == "UNKNOWN"


# --- BridgeState ---


def test_bridge_state_default_values() -> None:
    state = BridgeState()
    assert state.frames_in == 0
    assert state.frames_out == 0
    assert state.commands_in == 0
    assert state.commands_ok == 0
    assert state.mavlink_reconnects == 0
    assert state.ground_reconnects == 0


# --- GroundLink ---


@pytest.mark.asyncio
async def test_ground_link_next_command_returns_none_when_not_connected() -> None:
    link = GroundLink("ws://ground", 1)
    result = await link.next_command()
    assert result is None


@pytest.mark.asyncio
async def test_ground_link_close_noop_when_not_connected() -> None:
    link = GroundLink("ws://ground", 1)
    await link.close()
    assert link._ws is None


@pytest.mark.asyncio
async def test_ground_link_close_closes_ws_when_connected() -> None:
    class FakeWS:
        closed = False

        async def close(self) -> None:
            self.closed = True

    link = GroundLink("ws://ground", 1)
    fake_ws = FakeWS()
    link._ws = fake_ws
    await link.close()
    assert fake_ws.closed
    assert link._ws is None


# --- RemoteIDTransport ---


def test_remote_id_transport_base_raises_not_implemented() -> None:
    transport = RemoteIDTransport()
    with pytest.raises(NotImplementedError):
        transport.emit(_snapshot(1))


def test_log_remote_id_transport_emit_does_not_raise() -> None:
    transport = LogRemoteIDTransport()
    transport.emit(_snapshot(3))


# --- _load_remote_id_transport ---


def test_load_remote_id_transport_log_explicit() -> None:
    assert isinstance(_load_remote_id_transport("log"), LogRemoteIDTransport)


def test_load_remote_id_transport_empty_string() -> None:
    assert isinstance(_load_remote_id_transport(""), LogRemoteIDTransport)


def test_load_remote_id_transport_none_defaults_to_log(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SDACS_REMOTE_ID_TRANSPORT", raising=False)
    assert isinstance(_load_remote_id_transport(None), LogRemoteIDTransport)


def test_load_remote_id_transport_invalid_no_colon() -> None:
    with pytest.raises(RuntimeError, match="module:attribute"):
        _load_remote_id_transport("some_module_without_colon")


def test_load_remote_id_transport_class_instantiation() -> None:
    transport = _load_remote_id_transport("src.hardware.onboard_bridge:LogRemoteIDTransport")
    assert isinstance(transport, LogRemoteIDTransport)


def test_load_remote_id_transport_callable_wrapped(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[int] = []

    def _my_emitter(snap: TelemetrySnapshot) -> None:
        called.append(snap.drone_id)

    monkeypatch.setattr("src.hardware.onboard_bridge._test_emitter_new", _my_emitter, raising=False)
    transport = _load_remote_id_transport("src.hardware.onboard_bridge:_test_emitter_new")
    assert isinstance(transport, CallableRemoteIDTransport)
    transport.emit(_snapshot(99))
    assert called == [99]


def test_load_remote_id_transport_non_callable_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.hardware.onboard_bridge._bad_transport_obj", 42, raising=False)
    with pytest.raises(RuntimeError, match="must be a RemoteIDTransport or callable"):
        _load_remote_id_transport("src.hardware.onboard_bridge:_bad_transport_obj")


# --- parse_args ---


def test_parse_args_basic() -> None:
    cfg = parse_args(["--drone-id", "5", "--mavlink-uri", "udp:0.0.0.0:14550", "--ground-uri", "ws://ground:5555"])
    assert cfg.drone_id == 5
    assert cfg.mavlink_uri == "udp:0.0.0.0:14550"
    assert cfg.ground_uri == "ws://ground:5555"
    assert cfg.enable_remote_id is True
    assert cfg.telemetry_poll_hz == TELEMETRY_POLL_HZ


def test_parse_args_no_remote_id() -> None:
    cfg = parse_args(["--drone-id", "1", "--mavlink-uri", "udp:0:14550", "--ground-uri", "ws://g", "--no-remote-id"])
    assert cfg.enable_remote_id is False


def test_parse_args_custom_heartbeat() -> None:
    cfg = parse_args(["--drone-id", "2", "--mavlink-uri", "udp:x", "--ground-uri", "ws://g", "--heartbeat-interval-s", "0.5"])
    assert cfg.heartbeat_interval_s == pytest.approx(0.5)


# --- OnboardBridge startup failure ---


@pytest.mark.asyncio
async def test_bridge_startup_failure_returns_1(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_bridge_module, "MAX_RECONNECT_ATTEMPTS", 1)
    monkeypatch.setattr(_bridge_module, "RECONNECT_BACKOFF_S", (0.0,))

    class AlwaysFailMav:
        async def connect(self) -> None:
            raise RuntimeError("cannot connect")

        async def close(self) -> None:
            pass

        async def poll_telemetry(self, drone_id: int) -> None:
            return None

        async def send_command(self, cmd: dict) -> bool:
            return False

    config = BridgeConfig(
        drone_id=1,
        mavlink_uri="udp://x",
        ground_uri="ws://x",
        enable_remote_id=False,
        heartbeat_interval_s=0.01,
    )
    bridge = OnboardBridge(config=config, mav=AlwaysFailMav(), ground=FakeGround())
    rc = await bridge.run()
    assert rc == 1


# --- _reconnect_runtime stale generation ---


@pytest.mark.asyncio
async def test_reconnect_runtime_stale_generation_returns_true() -> None:
    config = BridgeConfig(drone_id=1, mavlink_uri="udp://x", ground_uri="ws://x", enable_remote_id=False)
    mav = FakeMav()
    bridge = OnboardBridge(config=config, mav=mav, ground=FakeGround())
    bridge._connection_generation = 5
    result = await bridge._reconnect_runtime(reason="test", generation=3)
    assert result is True
    assert mav.connect_calls == 0


# --- Command received and forwarded ---


@pytest.mark.asyncio
async def test_bridge_command_received_and_forwarded() -> None:
    cmd = {"name": "LAND"}
    config = BridgeConfig(
        drone_id=2,
        mavlink_uri="udp://unused",
        ground_uri="ws://unused",
        heartbeat_interval_s=0.01,
        telemetry_poll_hz=100,
        enable_remote_id=False,
    )
    mav = FakeMav()
    ground = FakeGround(commands=[cmd])
    bridge = OnboardBridge(config=config, mav=mav, ground=ground)

    await _run_bridge_for(bridge, duration_s=0.15)

    assert mav.sent_commands == [cmd]
    assert bridge.state.commands_in >= 1
    assert bridge.state.commands_ok >= 1


@pytest.mark.asyncio
async def test_bridge_command_poll_failure_reconnects() -> None:
    config = BridgeConfig(
        drone_id=3,
        mavlink_uri="udp://unused",
        ground_uri="ws://unused",
        heartbeat_interval_s=0.01,
        telemetry_poll_hz=100,
        enable_remote_id=False,
    )
    mav = FakeMav()
    ground = FakeGround(command_errors=1)
    bridge = OnboardBridge(config=config, mav=mav, ground=ground)

    await _run_bridge_for(bridge, duration_s=0.18)

    assert bridge.state.ground_reconnects == 1


@pytest.mark.asyncio
async def test_bridge_command_send_failure_reconnects() -> None:
    """mav.send_command() raises → _reconnect_runtime is called (lines 613-623)."""
    cmd = {"name": "LAND"}
    config = BridgeConfig(
        drone_id=4,
        mavlink_uri="udp://unused",
        ground_uri="ws://unused",
        heartbeat_interval_s=0.01,
        telemetry_poll_hz=100,
        enable_remote_id=False,
    )
    mav = FakeMav(send_failures=1)
    ground = FakeGround(commands=[cmd])
    bridge = OnboardBridge(config=config, mav=mav, ground=ground)

    await _run_bridge_for(bridge, duration_s=0.18)

    assert bridge.state.mavlink_reconnects == 1


# --- MavlinkAdapter close when connected ---


@pytest.mark.asyncio
async def test_mav_adapter_close_when_connection_set() -> None:
    """MavlinkAdapter.close() calls _connection.close() when not None (lines 310-312)."""

    class FakeConnection:
        closed = False

        def close(self) -> None:
            self.closed = True

    adapter = MavlinkAdapter("udp:localhost:14550")
    fake_conn = FakeConnection()
    adapter._connection = fake_conn
    await adapter.close()
    assert fake_conn.closed
    assert adapter._connection is None


# --- GroundLink with mock WebSocket ---


@pytest.mark.asyncio
async def test_ground_link_publish_raises_when_not_connected() -> None:
    """GroundLink.publish() raises RuntimeError when _ws is None (line 343)."""
    link = GroundLink("ws://ground", 1)
    with pytest.raises(RuntimeError, match="not connected"):
        await link.publish(_snapshot(1))


@pytest.mark.asyncio
async def test_ground_link_connect_raises_when_websockets_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GroundLink.connect() raises RuntimeError when websockets is not installed."""
    monkeypatch.setitem(sys.modules, "websockets", None)
    link = GroundLink("ws://ground", 1)
    with pytest.raises(RuntimeError, match="websockets is required"):
        await link.connect()


@pytest.mark.asyncio
async def test_ground_link_publish_with_mock_ws() -> None:
    """GroundLink.publish() sends snapshot JSON over _ws (lines 342-344)."""
    sent: list[str] = []

    class FakeWS:
        async def send(self, msg: str) -> None:
            sent.append(msg)

        async def close(self) -> None:
            pass

    link = GroundLink("ws://ground", 1)
    link._ws = FakeWS()
    snap = _snapshot(1)
    await link.publish(snap)
    assert len(sent) == 1
    assert '"drone_id": 1' in sent[0]


@pytest.mark.asyncio
async def test_ground_link_next_command_success_path() -> None:
    """GroundLink.next_command() returns parsed JSON when ws delivers a message (line 352)."""

    class FakeWS:
        async def recv(self) -> str:
            return '{"name": "RTL"}'

        async def close(self) -> None:
            pass

    link = GroundLink("ws://ground", 1)
    link._ws = FakeWS()
    cmd = await link.next_command()
    assert cmd == {"name": "RTL"}


@pytest.mark.asyncio
async def test_ground_link_next_command_timeout_returns_none() -> None:
    """GroundLink.next_command() returns None when recv times out (line 354)."""

    class SlowWS:
        async def recv(self) -> str:
            await asyncio.sleep(10)
            return "{}"

        async def close(self) -> None:
            pass

    link = GroundLink("ws://ground", 1)
    link._ws = SlowWS()
    result = await link.next_command()
    assert result is None


# --- _load_remote_id_transport: object with .emit callable (line 424) ---


def test_load_remote_id_transport_object_with_emit_attribute(monkeypatch: pytest.MonkeyPatch) -> None:
    """An object that has a callable .emit but is not a RemoteIDTransport is returned as-is."""

    class EmitableNonTransport:
        def emit(self, snap: TelemetrySnapshot) -> None:
            pass

    obj = EmitableNonTransport()
    monkeypatch.setattr("src.hardware.onboard_bridge._emit_obj_test", obj, raising=False)
    transport = _load_remote_id_transport("src.hardware.onboard_bridge:_emit_obj_test")
    assert transport is obj


# --- main() (lines 706-707) ---


def test_main_function_calls_asyncio_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """main() should parse CLI args and call asyncio.run (lines 706-707)."""
    run_calls: list = []
    monkeypatch.setattr(_bridge_module.asyncio, "run", lambda coro: run_calls.append(coro))
    monkeypatch.setattr(
        _bridge_module.sys,
        "argv",
        ["onboard_bridge", "--drone-id", "1", "--mavlink-uri", "udp:x", "--ground-uri", "ws://g"],
    )
    from src.hardware.onboard_bridge import main as bridge_main

    bridge_main()
    assert len(run_calls) == 1


# --- Runtime reconnect exhaustion — stop the bridge loop (lines 544-556, 572) ---


@pytest.mark.asyncio
async def test_bridge_stops_when_runtime_reconnect_exhausted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When runtime reconnect exhausts all attempts, the bridge should stop cleanly."""
    monkeypatch.setattr(_bridge_module, "MAX_RECONNECT_ATTEMPTS", 1)
    monkeypatch.setattr(_bridge_module, "RECONNECT_BACKOFF_S", (0.0,))

    connect_calls = [0]

    class FailAfterFirstMav:
        async def connect(self) -> None:
            connect_calls[0] += 1
            if connect_calls[0] > 1:
                raise RuntimeError("reconnect refused")

        async def poll_telemetry(self, drone_id: int) -> None:
            if connect_calls[0] == 1:
                raise RuntimeError("telemetry gone")
            return None

        async def send_command(self, cmd: dict) -> bool:
            return True

        async def close(self) -> None:
            pass

    config = BridgeConfig(
        drone_id=5,
        mavlink_uri="udp://x",
        ground_uri="ws://x",
        heartbeat_interval_s=1.0,
        telemetry_poll_hz=100,
        enable_remote_id=False,
    )
    bridge = OnboardBridge(config=config, mav=FailAfterFirstMav(), ground=FakeGround())
    rc = await asyncio.wait_for(bridge.run(), timeout=2.0)
    assert rc == 0  # run() returns 0 after loop breaks


# --- MavlinkAdapter.connect() with mocked pymavlink (lines 127-138) ---


@pytest.mark.asyncio
async def test_mav_adapter_connect_with_mock_pymavlink(monkeypatch: pytest.MonkeyPatch) -> None:
    """MavlinkAdapter.connect() initializes the connection via mocked pymavlink."""

    class FakeConnection:
        target_system = 1
        target_component = 1

        def wait_heartbeat(self, timeout: float = 10.0) -> None:
            pass

        def close(self) -> None:
            pass

    def fake_mavlink_connection(uri: str) -> FakeConnection:
        return FakeConnection()

    fake_mavutil = types.SimpleNamespace(mavlink_connection=fake_mavlink_connection)
    fake_pymavlink = types.SimpleNamespace(mavutil=fake_mavutil)
    monkeypatch.setitem(sys.modules, "pymavlink", fake_pymavlink)
    monkeypatch.setitem(sys.modules, "pymavlink.mavutil", fake_mavutil)

    adapter = MavlinkAdapter("udp:0.0.0.0:14550")
    await adapter.connect()
    assert adapter._connection is not None

    await adapter.close()
    assert adapter._connection is None


# --- GroundLink.connect() with mocked websockets (lines 330-339) ---


@pytest.mark.asyncio
async def test_ground_link_connect_with_mock_websockets(monkeypatch: pytest.MonkeyPatch) -> None:
    """GroundLink.connect() establishes a ws connection and sends the hello message."""
    sent_messages: list[str] = []

    class FakeWS:
        async def send(self, msg: str) -> None:
            sent_messages.append(msg)

        async def recv(self) -> str:
            return "{}"

        async def close(self) -> None:
            pass

    async def fake_connect(uri: str, **kwargs) -> FakeWS:
        return FakeWS()

    fake_websockets = types.SimpleNamespace(connect=fake_connect)
    monkeypatch.setitem(sys.modules, "websockets", fake_websockets)

    link = GroundLink("ws://ground", 99)
    await link.connect()

    assert link._ws is not None
    assert len(sent_messages) == 1
    hello = json.loads(sent_messages[0])
    assert hello["drone_id"] == 99
    assert hello["type"] == "hello"

    await link.close()
