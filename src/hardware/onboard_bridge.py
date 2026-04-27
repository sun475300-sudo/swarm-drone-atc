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

    # Aggregated state across multiple MAVLink message types.
    # GLOBAL_POSITION_INT carries the position; SYS_STATUS carries battery;
    # HEARTBEAT carries mode + armed flag. We keep the most-recent of each.
    _last_sys_status_battery_pct: float = -1.0
    _last_heartbeat_mode: str = "UNKNOWN"
    _last_heartbeat_armed: bool = False
    _last_gps_fix_type: int = 0

    # Best-effort string for known PX4 base_mode flags. Vendor-specific
    # custom_mode interpretation is left to the consumer.
    _MAV_MODE_FLAGS = {
        0x80: "SAFETY_ARMED",
        0x40: "MANUAL_INPUT_ENABLED",
        0x20: "HIL_ENABLED",
        0x10: "STABILIZE_ENABLED",
        0x08: "GUIDED_ENABLED",
        0x04: "AUTO_ENABLED",
        0x02: "TEST_ENABLED",
        0x01: "CUSTOM_MODE_ENABLED",
    }

    @classmethod
    def _decode_mode(cls, base_mode: int, custom_mode: int) -> str:
        flags = [name for bit, name in cls._MAV_MODE_FLAGS.items() if base_mode & bit]
        if custom_mode:
            flags.append(f"custom={custom_mode}")
        return "|".join(flags) if flags else "UNKNOWN"

    async def poll_telemetry(self, drone_id: int) -> Optional[TelemetrySnapshot]:
        if self._connection is None:
            raise RuntimeError("not connected")

        # Drain all available messages this tick so SYS_STATUS / HEARTBEAT
        # state stays fresh between GLOBAL_POSITION_INT updates.
        position_msg = None
        for _ in range(64):  # cap drain to avoid starving the loop
            msg = self._connection.recv_match(
                type=["GLOBAL_POSITION_INT", "HEARTBEAT", "SYS_STATUS", "GPS_RAW_INT"],
                blocking=False,
            )
            if msg is None:
                break
            mtype = msg.get_type()
            if mtype == "GLOBAL_POSITION_INT":
                position_msg = msg
            elif mtype == "SYS_STATUS":
                # battery_remaining is 0..100 % (or -1 if unknown)
                br = getattr(msg, "battery_remaining", -1)
                self._last_sys_status_battery_pct = float(br) if br >= 0 else -1.0
            elif mtype == "HEARTBEAT":
                self._last_heartbeat_mode = self._decode_mode(
                    getattr(msg, "base_mode", 0),
                    getattr(msg, "custom_mode", 0),
                )
                self._last_heartbeat_armed = bool(
                    getattr(msg, "base_mode", 0) & 0x80
                )
            elif mtype == "GPS_RAW_INT":
                self._last_gps_fix_type = int(getattr(msg, "fix_type", 0))

        if position_msg is None:
            return None

        return TelemetrySnapshot(
            drone_id=drone_id,
            timestamp_ns=time.time_ns(),
            lat_deg=position_msg.lat / 1e7,
            lon_deg=position_msg.lon / 1e7,
            alt_msl_m=position_msg.alt / 1000.0,
            alt_rel_m=position_msg.relative_alt / 1000.0,
            vx_mps=position_msg.vx / 100.0,
            vy_mps=position_msg.vy / 100.0,
            vz_mps=position_msg.vz / 100.0,
            heading_deg=position_msg.hdg / 100.0,
            battery_pct=self._last_sys_status_battery_pct,
            mode=self._last_heartbeat_mode,
            armed=self._last_heartbeat_armed,
            gps_fix_type=self._last_gps_fix_type,
        )

    # Mapping table: high-level SDACS commands → (MAV_CMD_*, param tuple builder).
    # The builder takes the command_dict and returns a 7-tuple of param1..param7
    # exactly as MAV_CMD expects. Add entries here as the controller grows.
    _COMMAND_MAP: dict = {
        # name : (MAV_CMD constant string, builder)
        "TAKEOFF": (
            "MAV_CMD_NAV_TAKEOFF",
            lambda d: (0, 0, 0, float("nan"), 0, 0, float(d.get("alt_m", 10.0))),
        ),
        "LAND": (
            "MAV_CMD_NAV_LAND",
            lambda d: (0, 0, 0, float("nan"), 0, 0, 0),
        ),
        "RTL": (
            "MAV_CMD_NAV_RETURN_TO_LAUNCH",
            lambda d: (0, 0, 0, 0, 0, 0, 0),
        ),
        "GOTO": (
            "MAV_CMD_DO_REPOSITION",
            lambda d: (
                float(d.get("speed_mps", -1.0)),
                0, 0, float("nan"),
                int(float(d["lat_deg"]) * 1e7),
                int(float(d["lon_deg"]) * 1e7),
                float(d["alt_m"]),
            ),
        ),
        "SET_MODE": (
            "MAV_CMD_DO_SET_MODE",
            lambda d: (
                float(d.get("base_mode", 1)),  # MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
                float(d.get("custom_mode", 0)),
                0, 0, 0, 0, 0,
            ),
        ),
    }

    async def send_command(
        self,
        command_dict: dict,
        ack_timeout_s: float = 3.0,
    ) -> bool:
        """Translate a high-level command into MAVLink and await ACK.

        ``command_dict`` shape::

            {"name": "GOTO", "lat_deg": 36.5, "lon_deg": 126.4, "alt_m": 50}

        Returns True on COMMAND_ACK with MAV_RESULT_ACCEPTED within
        ``ack_timeout_s`` seconds. Returns False otherwise (logged).
        """
        if self._connection is None:
            raise RuntimeError("not connected")

        name = command_dict.get("name", "").upper()
        if name not in self._COMMAND_MAP:
            LOGGER.warning("send_command unknown command: %s", name)
            return False

        cmd_const_name, builder = self._COMMAND_MAP[name]
        try:
            from pymavlink import mavutil  # type: ignore
        except ImportError:
            LOGGER.error("pymavlink unavailable; cannot send_command")
            return False

        cmd_const = getattr(mavutil.mavlink, cmd_const_name, None)
        if cmd_const is None:
            LOGGER.error("MAVLink dialect missing %s", cmd_const_name)
            return False

        try:
            params = builder(command_dict)
        except (KeyError, ValueError) as e:
            LOGGER.error("send_command bad params for %s: %s", name, e)
            return False

        self._connection.mav.command_long_send(
            self._connection.target_system,
            self._connection.target_component,
            cmd_const,
            0,  # confirmation
            *params,
        )

        # Wait for the matching COMMAND_ACK
        deadline = time.monotonic() + ack_timeout_s
        while time.monotonic() < deadline:
            ack = self._connection.recv_match(type="COMMAND_ACK", blocking=False)
            if ack is not None and getattr(ack, "command", None) == cmd_const:
                accepted = getattr(ack, "result", -1) == mavutil.mavlink.MAV_RESULT_ACCEPTED
                if not accepted:
                    LOGGER.warning(
                        "command %s rejected (result=%s)",
                        name, getattr(ack, "result", "?"),
                    )
                return accepted
            await asyncio.sleep(0.05)

        LOGGER.warning("command %s ACK timeout after %ss", name, ack_timeout_s)
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
