from __future__ import annotations

import asyncio

import pytest

from src.hardware.onboard_bridge import (
    BridgeConfig,
    CallableRemoteIDTransport,
    GroundLink,
    OnboardBridge,
    TelemetrySnapshot,
    _load_remote_id_transport,
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
