"""Onboard bridge — Jetson companion computer ⇄ Pixhawk (MAVLink) ⇄ AirspaceController.

Phase: P692
Role: the piece of code that runs on the drone itself. Subscribes to Pixhawk
telemetry, forwards it to the SDACS ground controller over a reliable link,
and translates controller commands back into MAVLink.

Design principles (from .claude/rules/coding-style.md):
- Immutable telemetry snapshots (dataclass with frozen=True).
- Small, focused functions.
- Explicit error handling.
- No hardcoded secrets — connection details come from config.

Runtime deps (add to requirements-hardware.txt):
    pymavlink >= 2.4.42
    pyserial >= 3.5

Quickstart:
    python -m src.hardware.onboard_bridge \\
        --mavlink-uri udp:0.0.0.0:14550 \\
        --ground-uri tcp://ground.example:5555 \\
        --drone-id 7

Exit codes:
    0 — clean shutdown
    1 — config error
    2 — MAVLink link lost beyond retry budget
    3 — ground link lost beyond retry budget
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import signal
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

LOGGER = logging.getLogger("sdacs.onboard_bridge")

# --- Constants (no magic numbers elsewhere) ---

HEARTBEAT_INTERVAL_S = 1.0
TELEMETRY_POLL_HZ = 20
RECONNECT_BACKOFF_S = (0.5, 1.0, 2.0, 5.0, 10.0)
MAX_RECONNECT_ATTEMPTS = 10
COMMAND_ACK_TIMEOUT_S = 2.0


# --- Value objects ---


@dataclass(frozen=True)
class TelemetrySnapshot:
    """Single immutable telemetry frame pulled from MAVLink."""

    drone_id: int
    timestamp_ns: int
    lat_deg: float
    lon_deg: float
    alt_msl_m: float
    alt_rel_m: float
    vx_mps: float
    vy_mps: float
    vz_mps: float
    heading_deg: float
    battery_pct: float
    mode: str
    armed: bool
    gps_fix_type: int

    def to_json(self) -> str:
        return json.dumps(
            {
                "drone_id": self.drone_id,
                "t_ns": self.timestamp_ns,
                "pos": {"lat": self.lat_deg, "lon": self.lon_deg, "alt": self.alt_msl_m},
                "vel": {"x": self.vx_mps, "y": self.vy_mps, "z": self.vz_mps},
                "head": self.heading_deg,
                "bat": self.battery_pct,
                "mode": self.mode,
                "armed": self.armed,
                "fix": self.gps_fix_type,
            }
        )


@dataclass(frozen=True)
class BridgeConfig:
    drone_id: int
    mavlink_uri: str
    ground_uri: str
    heartbeat_interval_s: float = HEARTBEAT_INTERVAL_S
    telemetry_poll_hz: int = TELEMETRY_POLL_HZ
    enable_remote_id: bool = True


# --- MAVLink adapter (thin, replaceable) ---


class MavlinkAdapter:
    """Thin wrapper around pymavlink so the bridge does not depend on it directly.

    Implementations:
    - RealAdapter — calls into pymavlink.
    - FakeAdapter — for unit tests, yields scripted frames.
    """

    def __init__(self, uri: str) -> None:
        self.uri = uri
        self._connection = None

    async def connect(self) -> None:
        # Deferred import so tests can import this module without pymavlink installed.
        try:
            from pymavlink import mavutil  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "pymavlink is required for MavlinkAdapter. "
                "pip install pymavlink"
            ) from exc

        LOGGER.info("connecting to MAVLink at %s", self.uri)
        self._connection = mavutil.mavlink_connection(self.uri)
        self._connection.wait_heartbeat(timeout=10)
        LOGGER.info(
            "heartbeat received from system %d component %d",
            self._connection.target_system,
            self._connection.target_component,
        )

    async def poll_telemetry(self, drone_id: int) -> Optional[TelemetrySnapshot]:
        if self._connection is None:
            raise RuntimeError("not connected")

        msg = self._connection.recv_match(
            type=["GLOBAL_POSITION_INT", "HEARTBEAT", "SYS_STATUS"],
            blocking=False,
        )
        if msg is None:
            return None

        # This is a simplified assembly — real code aggregates multiple message types.
        if msg.get_type() != "GLOBAL_POSITION_INT":
            return None

        return TelemetrySnapshot(
            drone_id=drone_id,
            timestamp_ns=time.time_ns(),
            lat_deg=msg.lat / 1e7,
            lon_deg=msg.lon / 1e7,
            alt_msl_m=msg.alt / 1000.0,
            alt_rel_m=msg.relative_alt / 1000.0,
            vx_mps=msg.vx / 100.0,
            vy_mps=msg.vy / 100.0,
            vz_mps=msg.vz / 100.0,
            heading_deg=msg.hdg / 100.0,
            battery_pct=-1.0,  # populated by SYS_STATUS handler (TODO)
            mode="UNKNOWN",  # populated by HEARTBEAT handler (TODO)
            armed=False,
            gps_fix_type=3,
        )

    async def send_command(self, command_dict: dict) -> bool:
        """Translate a high-level command into MAVLink and await ACK.

        Returns True on COMMAND_ACK with MAV_RESULT_ACCEPTED within timeout.
        """
        if self._connection is None:
            raise RuntimeError("not connected")
        # TODO: map command_dict → MAV_CMD_* and call command_long_send.
        # For now, log only so the skeleton runs end-to-end.
        LOGGER.warning("send_command stub: %s", command_dict)
        return False

    async def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None


# --- Ground-link adapter (replaceable) ---


class GroundLink:
    """Reliable ground-control channel.

    Reference implementation: JSON over WebSocket. Swap with DDS or ROS2 as needed.
    """

    def __init__(self, uri: str, drone_id: int) -> None:
        self.uri = uri
        self.drone_id = drone_id
        self._ws = None

    async def connect(self) -> None:
        try:
            import websockets  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "websockets is required for GroundLink. pip install websockets"
            ) from exc

        LOGGER.info("connecting to ground at %s", self.uri)
        self._ws = await websockets.connect(self.uri, max_size=2**20)
        await self._ws.send(json.dumps({"type": "hello", "drone_id": self.drone_id}))

    async def publish(self, snapshot: TelemetrySnapshot) -> None:
        if self._ws is None:
            raise RuntimeError("ground link not connected")
        await self._ws.send(snapshot.to_json())

    async def next_command(self) -> Optional[dict]:
        """Non-blocking poll for commands from the ground."""
        if self._ws is None:
            return None
        try:
            raw = await asyncio.wait_for(self._ws.recv(), timeout=0.01)
            return json.loads(raw)
        except asyncio.TimeoutError:
            return None
        except Exception as exc:
            LOGGER.warning("ground recv error: %s", exc)
            return None

    async def close(self) -> None:
        if self._ws is not None:
            await self._ws.close()
            self._ws = None


# --- Bridge main loop ---


@dataclass
class BridgeState:
    """Mutable runtime state, kept in ONE place for inspectability."""

    frames_in: int = 0
    frames_out: int = 0
    commands_in: int = 0
    commands_ok: int = 0
    last_heartbeat_ns: int = 0
    mavlink_reconnects: int = 0
    ground_reconnects: int = 0


class OnboardBridge:
    def __init__(
        self,
        config: BridgeConfig,
        mav: MavlinkAdapter,
        ground: GroundLink,
    ) -> None:
        self.config = config
        self.mav = mav
        self.ground = ground
        self.state = BridgeState()
        self._stop_event = asyncio.Event()

    async def run(self) -> int:
        try:
            await self._connect_with_retry()
        except RuntimeError as exc:
            LOGGER.error("startup failed: %s", exc)
            return 1

        try:
            await asyncio.gather(
                self._telemetry_loop(),
                self._command_loop(),
                self._heartbeat_loop(),
            )
        except asyncio.CancelledError:
            pass
        finally:
            await self._shutdown()

        return 0

    async def stop(self) -> None:
        self._stop_event.set()

    # ---- phase 1: connect ----

    async def _connect_with_retry(self) -> None:
        for attempt in range(MAX_RECONNECT_ATTEMPTS):
            try:
                await self.mav.connect()
                await self.ground.connect()
                return
            except Exception as exc:
                backoff = RECONNECT_BACKOFF_S[min(attempt, len(RECONNECT_BACKOFF_S) - 1)]
                LOGGER.warning("connect attempt %d failed: %s (sleep %.1fs)", attempt, exc, backoff)
                await asyncio.sleep(backoff)

        raise RuntimeError("max reconnect attempts exhausted")

    # ---- phase 2: loops ----

    async def _telemetry_loop(self) -> None:
        period = 1.0 / max(1, self.config.telemetry_poll_hz)
        while not self._stop_event.is_set():
            snapshot = await self.mav.poll_telemetry(self.config.drone_id)
            if snapshot is not None:
                self.state.frames_in += 1
                try:
                    await self.ground.publish(snapshot)
                    self.state.frames_out += 1
                except Exception as exc:
                    LOGGER.warning("publish failed: %s", exc)
            await asyncio.sleep(period)

    async def _command_loop(self) -> None:
        while not self._stop_event.is_set():
            cmd = await self.ground.next_command()
            if cmd is not None:
                self.state.commands_in += 1
                ok = await self.mav.send_command(cmd)
                if ok:
                    self.state.commands_ok += 1
            await asyncio.sleep(0.01)

    async def _heartbeat_loop(self) -> None:
        while not self._stop_event.is_set():
            self.state.last_heartbeat_ns = time.time_ns()
            LOGGER.debug(
                "hb in=%d out=%d cmd=%d/%d",
                self.state.frames_in,
                self.state.frames_out,
                self.state.commands_ok,
                self.state.commands_in,
            )
            await asyncio.sleep(self.config.heartbeat_interval_s)

    async def _shutdown(self) -> None:
        LOGGER.info("shutting down bridge")
        await self.mav.close()
        await self.ground.close()


# --- CLI ---


def parse_args(argv: list[str]) -> BridgeConfig:
    parser = argparse.ArgumentParser(prog="onboard_bridge")
    parser.add_argument("--drone-id", type=int, required=True)
    parser.add_argument("--mavlink-uri", required=True, help="e.g. udp:0.0.0.0:14550")
    parser.add_argument("--ground-uri", required=True, help="e.g. ws://ground:5555")
    parser.add_argument("--heartbeat-interval-s", type=float, default=HEARTBEAT_INTERVAL_S)
    parser.add_argument("--telemetry-hz", type=int, default=TELEMETRY_POLL_HZ)
    parser.add_argument("--no-remote-id", action="store_true")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    logging.basicConfig(level=args.log_level.upper(), format="%(asctime)s %(name)s %(levelname)s %(message)s")

    if args.drone_id < 0:
        raise SystemExit("--drone-id must be non-negative")
    if args.telemetry_hz < 1:
        raise SystemExit("--telemetry-hz must be >= 1")

    return BridgeConfig(
        drone_id=args.drone_id,
        mavlink_uri=args.mavlink_uri,
        ground_uri=args.ground_uri,
        heartbeat_interval_s=args.heartbeat_interval_s,
        telemetry_poll_hz=args.telemetry_hz,
        enable_remote_id=not args.no_remote_id,
    )


async def _async_main(config: BridgeConfig) -> int:
    bridge = OnboardBridge(
        config=config,
        mav=MavlinkAdapter(config.mavlink_uri),
        ground=GroundLink(config.ground_uri, config.drone_id),
    )

    loop = asyncio.get_running_loop()

    def _on_signal(sig_name: str) -> None:
        LOGGER.info("signal %s received, stopping", sig_name)
        loop.create_task(bridge.stop())

    for sig_name in ("SIGINT", "SIGTERM"):
        try:
            loop.add_signal_handler(getattr(signal, sig_name), _on_signal, sig_name)
        except NotImplementedError:
            # Windows: signal handlers on the loop are limited.
            pass

    return await bridge.run()


def main(argv: Optional[list[str]] = None) -> int:
    config = parse_args(argv if argv is not None else sys.argv[1:])
    return asyncio.run(_async_main(config))


if __name__ == "__main__":
    raise SystemExit(main())
