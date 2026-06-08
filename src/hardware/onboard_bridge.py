"""Onboard bridge - Jetson companion computer <-> Pixhawk (MAVLink) <-> AirspaceController.

Phase: P692
Role: the piece of code that runs on the drone itself. Subscribes to Pixhawk
telemetry, forwards it to the SDACS ground controller over a reliable link,
and translates controller commands back into MAVLink.

Design principles (from .claude/rules/coding-style.md):
- Immutable telemetry snapshots (dataclass with frozen=True).
- Small, focused functions.
- Explicit error handling.
- No hardcoded secrets - connection details come from config.

Runtime deps (add to requirements-hardware.txt):
    pymavlink >= 2.4.42
    pyserial >= 3.5

Quickstart:
    python -m src.hardware.onboard_bridge \
        --mavlink-uri udp:0.0.0.0:14550 \
        --ground-uri tcp://ground.example:5555 \
        --drone-id 7

Exit codes:
    0 - clean shutdown
    1 - config error
    2 - MAVLink link lost beyond retry budget
    3 - ground link lost beyond retry budget
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import importlib
import json
import logging
import math
import os
import signal
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass

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
    # Optional attitude (radians, from MAVLink ATTITUDE msg). NaN when no
    # ATTITUDE frame has been received yet.
    roll_rad: float = float("nan")
    pitch_rad: float = float("nan")
    yaw_rad: float = float("nan")
    attitude_ts_ns: int = 0

    def to_json(self) -> str:
        """``to_json`` 동작을 수행한다."""
        payload = {
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
        if self.attitude_ts_ns > 0 and not math.isnan(self.roll_rad):
            payload["att"] = {
                "roll": self.roll_rad,
                "pitch": self.pitch_rad,
                "yaw": self.yaw_rad,
                "t_ns": self.attitude_ts_ns,
            }
        return json.dumps(payload)


@dataclass(frozen=True)
class BridgeConfig:
    """``BridgeConfig`` 데이터를 표현한다."""
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
    - RealAdapter - calls into pymavlink.
    - FakeAdapter - for unit tests, yields scripted frames.
    """

    def __init__(self, uri: str) -> None:
        """인스턴스를 초기화한다."""
        self.uri = uri
        self._connection = None
        # Per-instance aggregated state - not class-level so each adapter tracks
        # its own drone independently.
        self._last_sys_status_battery_pct: float = -1.0
        self._last_heartbeat_mode: str = "UNKNOWN"
        self._last_heartbeat_armed: bool = False
        self._last_gps_fix_type: int = 0
        self._last_attitude_roll: float = float("nan")
        self._last_attitude_pitch: float = float("nan")
        self._last_attitude_yaw: float = float("nan")
        self._last_attitude_ts_ns: int = 0
        self._last_heartbeat_monotonic_s: float = 0.0

    async def connect(self) -> None:
        # Deferred import so tests can import this module without pymavlink installed.
        """``connect`` 동작을 수행한다."""
        try:
            from pymavlink import mavutil  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "pymavlink is required for MavlinkAdapter. "
                "pip install pymavlink"
            ) from exc

        LOGGER.info("connecting to MAVLink at %s", self.uri)
        self._connection = mavutil.mavlink_connection(self.uri)
        self._connection.wait_heartbeat(timeout=10)  # type: ignore[attr-defined]
        LOGGER.info(
            "heartbeat received from system %d component %d",
            self._connection.target_system,  # type: ignore[attr-defined]
            self._connection.target_component,  # type: ignore[attr-defined]
        )

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

    async def poll_telemetry(self, drone_id: int) -> TelemetrySnapshot | None:
        """``poll_telemetry`` 동작을 수행한다."""
        if self._connection is None:
            raise RuntimeError("not connected")

        # Drain all available messages this tick so SYS_STATUS / HEARTBEAT
        # state stays fresh between GLOBAL_POSITION_INT updates.
        position_msg = None
        for _ in range(64):
            msg = self._connection.recv_match(
                type=["GLOBAL_POSITION_INT", "HEARTBEAT", "SYS_STATUS", "GPS_RAW_INT", "ATTITUDE"],
                blocking=False,
            )
            if msg is None:
                break
            mtype = msg.get_type()
            if mtype == "GLOBAL_POSITION_INT":
                position_msg = msg
            elif mtype == "SYS_STATUS":
                br = getattr(msg, "battery_remaining", -1)
                self._last_sys_status_battery_pct = float(br) if br >= 0 else -1.0
            elif mtype == "HEARTBEAT":
                self._last_heartbeat_mode = self._decode_mode(
                    getattr(msg, "base_mode", 0),
                    getattr(msg, "custom_mode", 0),
                )
                self._last_heartbeat_armed = bool(getattr(msg, "base_mode", 0) & 0x80)
                self._last_heartbeat_monotonic_s = time.monotonic()
            elif mtype == "GPS_RAW_INT":
                self._last_gps_fix_type = int(getattr(msg, "fix_type", 0))
            elif mtype == "ATTITUDE":
                self._last_attitude_roll = float(getattr(msg, "roll", float("nan")))
                self._last_attitude_pitch = float(getattr(msg, "pitch", float("nan")))
                self._last_attitude_yaw = float(getattr(msg, "yaw", float("nan")))
                self._last_attitude_ts_ns = time.time_ns()

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
            roll_rad=self._last_attitude_roll,
            pitch_rad=self._last_attitude_pitch,
            yaw_rad=self._last_attitude_yaw,
            attitude_ts_ns=self._last_attitude_ts_ns,
        )

    def heartbeat_age_s(self, now_monotonic_s: float | None = None) -> float:
        """Return seconds since the last HEARTBEAT (math.inf if never seen)."""
        if self._last_heartbeat_monotonic_s <= 0.0:
            return float("inf")
        now = now_monotonic_s if now_monotonic_s is not None else time.monotonic()
        return max(0.0, now - self._last_heartbeat_monotonic_s)

    async def send_position_target_local_ned(
        self,
        north_m: float,
        east_m: float,
        down_m: float,
        yaw_rad: float | None = None,
        vx_mps: float = 0.0,
        vy_mps: float = 0.0,
        vz_mps: float = 0.0,
    ) -> bool:
        """Send SET_POSITION_TARGET_LOCAL_NED (advisory -> position cmd)."""
        if self._connection is None:
            raise RuntimeError("not connected")
        try:
            from pymavlink import mavutil  # type: ignore
        except ImportError:
            LOGGER.error("pymavlink unavailable; cannot send position target")
            return False
        use_yaw = yaw_rad is not None
        type_mask = 0b101111000000 if not use_yaw else 0b100111000000
        send_fn = getattr(
            self._connection.mav, "set_position_target_local_ned_send", None
        )
        if send_fn is None:
            LOGGER.error("MAVLink dialect missing set_position_target_local_ned")
            return False
        try:
            send_fn(
                int(time.monotonic() * 1000) & 0xFFFFFFFF,
                self._connection.target_system,
                self._connection.target_component,
                mavutil.mavlink.MAV_FRAME_LOCAL_NED,
                type_mask,
                float(north_m),
                float(east_m),
                float(down_m),
                float(vx_mps),
                float(vy_mps),
                float(vz_mps),
                0.0, 0.0, 0.0,
                float(yaw_rad) if use_yaw else 0.0,
                0.0,
            )
        except Exception as exc:  # noqa: BLE001
            LOGGER.error("set_position_target_local_ned wire error: %s", exc)
            return False
        return True

    async def set_mode_message(self, custom_mode: int) -> bool:
        """Send dedicated SET_MODE message (ArduPilot canonical path)."""
        if self._connection is None:
            raise RuntimeError("not connected")
        try:
            from pymavlink import mavutil  # type: ignore
        except ImportError:
            LOGGER.error("pymavlink unavailable; cannot set_mode")
            return False
        base_mode = mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
        send_fn = getattr(self._connection.mav, "set_mode_send", None)
        if send_fn is None:
            LOGGER.error("MAVLink dialect missing set_mode_send")
            return False
        send_fn(self._connection.target_system, base_mode, int(custom_mode))
        deadline = time.monotonic() + COMMAND_ACK_TIMEOUT_S
        while time.monotonic() < deadline:
            msg = self._connection.recv_match(type="HEARTBEAT", blocking=False)
            if msg is not None and int(getattr(msg, "custom_mode", -1)) == int(custom_mode):
                self._last_heartbeat_mode = self._decode_mode(
                    getattr(msg, "base_mode", 0),
                    getattr(msg, "custom_mode", 0),
                )
                return True
            await asyncio.sleep(0.05)
        LOGGER.warning("set_mode_message no HEARTBEAT echo within %ss", COMMAND_ACK_TIMEOUT_S)
        return False

    _COMMAND_MAP: dict = {
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
                0,
                0,
                float("nan"),
                int(float(d["lat_deg"]) * 1e7),
                int(float(d["lon_deg"]) * 1e7),
                float(d["alt_m"]),
            ),
        ),
        "SET_MODE": (
            "MAV_CMD_DO_SET_MODE",
            lambda d: (
                float(d.get("base_mode", 1)),
                float(d.get("custom_mode", 0)),
                0,
                0,
                0,
                0,
                0,
            ),
        ),
    }

    async def send_command(
        self,
        command_dict: dict,
        ack_timeout_s: float = 3.0,
    ) -> bool:
        """Translate a high-level command into MAVLink and await ACK."""
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
        except (KeyError, ValueError) as exc:
            LOGGER.error("send_command bad params for %s: %s", name, exc)
            return False

        self._connection.mav.command_long_send(
            self._connection.target_system,
            self._connection.target_component,
            cmd_const,
            0,
            *params,
        )

        deadline = time.monotonic() + ack_timeout_s
        while time.monotonic() < deadline:
            ack = self._connection.recv_match(type="COMMAND_ACK", blocking=False)
            if ack is not None and getattr(ack, "command", None) == cmd_const:
                accepted = (
                    getattr(ack, "result", -1) == mavutil.mavlink.MAV_RESULT_ACCEPTED
                )
                if not accepted:
                    LOGGER.warning(
                        "command %s rejected (result=%s)",
                        name,
                        getattr(ack, "result", "?"),
                    )
                return accepted
            await asyncio.sleep(0.05)

        LOGGER.warning("command %s ACK timeout after %ss", name, ack_timeout_s)
        return False

    async def close(self) -> None:
        """``close`` 동작을 수행한다."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None


# --- Lost-Link state machine (MAVLINK_SPEC.md §6) ---

LOST_LINK_HOLD_TIMEOUT_S = 3.0
LOST_LINK_RTL_AFTER_S = 30.0
LOST_LINK_LAND_RADIUS_M = 50.0
ARDUPILOT_MODE_LOITER = 5
ARDUPILOT_MODE_RTL = 6
ARDUPILOT_MODE_LAND = 9


class LostLinkPhase:
    """Phase name marker."""

    NORMAL = "NORMAL"
    HOLDING = "HOLDING"
    RTL = "RTL"
    LANDING = "LANDING"


@dataclass
class LostLinkConfig:
    """``LostLinkConfig`` parameters."""

    hold_timeout_s: float = LOST_LINK_HOLD_TIMEOUT_S
    rtl_after_s: float = LOST_LINK_RTL_AFTER_S
    land_radius_m: float = LOST_LINK_LAND_RADIUS_M
    rtl_altitude_m: float = 80.0


class LostLinkStateMachine:
    """Track heartbeat freshness and emit 3-phase Lost-Link transitions."""

    def __init__(
        self,
        config: LostLinkConfig | None = None,
        *,
        home_position: tuple[float, float, float] | None = None,
    ) -> None:
        """Initialize."""
        self.config = config or LostLinkConfig()
        self.phase: str = LostLinkPhase.NORMAL
        self._silence_started_s: float | None = None
        self._home = home_position

    def set_home(self, lat_deg: float, lon_deg: float, alt_m: float) -> None:
        """Set home (used for LANDING radius)."""
        self._home = (lat_deg, lon_deg, alt_m)

    def update(
        self,
        heartbeat_age_s: float,
        snapshot: TelemetrySnapshot | None,
        now_s: float | None = None,
    ) -> str | None:
        """Advance machine; return new phase on transition else None."""
        now = now_s if now_s is not None else time.monotonic()

        if heartbeat_age_s <= self.config.hold_timeout_s:
            if self.phase != LostLinkPhase.NORMAL:
                self.phase = LostLinkPhase.NORMAL
                self._silence_started_s = None
                return LostLinkPhase.NORMAL
            return None

        if self._silence_started_s is None:
            self._silence_started_s = now - heartbeat_age_s

        silence_age = now - self._silence_started_s

        if (
            self.phase in (LostLinkPhase.HOLDING, LostLinkPhase.RTL)
            and snapshot is not None
            and self._home is not None
            and self._distance_to_home_m(snapshot) <= self.config.land_radius_m
        ):
            self.phase = LostLinkPhase.LANDING
            return LostLinkPhase.LANDING

        if silence_age >= self.config.rtl_after_s and self.phase != LostLinkPhase.RTL:
            if self.phase != LostLinkPhase.LANDING:
                self.phase = LostLinkPhase.RTL
                return LostLinkPhase.RTL
            return None

        if (
            heartbeat_age_s > self.config.hold_timeout_s
            and self.phase == LostLinkPhase.NORMAL
        ):
            self.phase = LostLinkPhase.HOLDING
            return LostLinkPhase.HOLDING

        return None

    def _distance_to_home_m(self, snapshot: TelemetrySnapshot) -> float:
        """Equirectangular distance from home (m)."""
        if self._home is None:
            return float("inf")
        h_lat, h_lon, h_alt = self._home
        d_lat_m = (snapshot.lat_deg - h_lat) * 111_320.0
        d_lon_m = (
            (snapshot.lon_deg - h_lon)
            * 111_320.0
            * math.cos(math.radians((snapshot.lat_deg + h_lat) / 2.0))
        )
        d_alt_m = snapshot.alt_msl_m - h_alt
        return math.sqrt(d_lat_m * d_lat_m + d_lon_m * d_lon_m + d_alt_m * d_alt_m)

    @staticmethod
    def mode_for_phase(phase: str) -> int | None:
        """Map phase -> ArduPilot custom_mode int."""
        return {
            LostLinkPhase.HOLDING: ARDUPILOT_MODE_LOITER,
            LostLinkPhase.RTL: ARDUPILOT_MODE_RTL,
            LostLinkPhase.LANDING: ARDUPILOT_MODE_LAND,
        }.get(phase)


# --- Ground-link adapter (replaceable) ---


class GroundLink:
    """Reliable ground-control channel.

    Reference implementation: JSON over WebSocket. Swap with DDS or ROS2 as needed.
    """

    def __init__(self, uri: str, drone_id: int) -> None:
        """인스턴스를 초기화한다."""
        self.uri = uri
        self.drone_id = drone_id
        self._ws = None

    async def connect(self) -> None:
        """``connect`` 동작을 수행한다."""
        try:
            import websockets  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "websockets is required for GroundLink. pip install websockets"
            ) from exc

        LOGGER.info("connecting to ground at %s", self.uri)
        self._ws = await websockets.connect(self.uri, max_size=2**20)  # type: ignore[assignment]
        await self._ws.send(json.dumps({"type": "hello", "drone_id": self.drone_id}))  # type: ignore[attr-defined]

    async def publish(self, snapshot: TelemetrySnapshot) -> None:
        """``publish`` 동작을 수행한다."""
        if self._ws is None:
            raise RuntimeError("ground link not connected")
        await self._ws.send(snapshot.to_json())

    async def next_command(self) -> dict | None:
        """Non-blocking poll for commands from the ground."""
        if self._ws is None:
            return None
        try:
            raw = await asyncio.wait_for(self._ws.recv(), timeout=0.01)
            return json.loads(raw)
        except asyncio.TimeoutError:
            return None
        except Exception as exc:
            raise RuntimeError(f"ground recv error: {exc}") from exc

    async def close(self) -> None:
        """``close`` 동작을 수행한다."""
        if self._ws is not None:
            await self._ws.close()
            self._ws = None


# --- Remote-ID transport ---


class RemoteIDTransport:
    """Minimal transport interface for ASTM F3411 broadcast backends."""

    def emit(self, snapshot: TelemetrySnapshot) -> None:
        """``emit`` 동작을 수행한다."""
        raise NotImplementedError


class LogRemoteIDTransport(RemoteIDTransport):
    """Fallback transport that logs the broadcast frame."""

    def emit(self, snapshot: TelemetrySnapshot) -> None:
        """``emit`` 동작을 수행한다."""
        LOGGER.debug(
            "remote_id frame drone=%d lat=%.6f lon=%.6f alt=%.1fm",
            snapshot.drone_id,
            snapshot.lat_deg,
            snapshot.lon_deg,
            snapshot.alt_msl_m,
        )


class CallableRemoteIDTransport(RemoteIDTransport):
    """Adapter for externally supplied transport callables."""

    def __init__(self, emitter: Callable[[TelemetrySnapshot], None]) -> None:
        """인스턴스를 초기화한다."""
        self._emitter = emitter

    def emit(self, snapshot: TelemetrySnapshot) -> None:
        """``emit`` 동작을 수행한다."""
        self._emitter(snapshot)


def _load_remote_id_transport(spec: str | None = None) -> RemoteIDTransport:
    """Load a Remote ID transport from env/config.

    Supported forms:
    - ``log`` or empty: built-in log-only fallback
    - ``pkg.module:factory_or_object``: imported object. If it is a class it
      will be instantiated with no args. If it is callable it will be wrapped
      as a transport emitter.
    """
    raw_spec = spec if spec is not None else os.getenv("SDACS_REMOTE_ID_TRANSPORT", "log")
    resolved = (raw_spec or "log").strip()
    if resolved in {"", "log"}:
        return LogRemoteIDTransport()

    if ":" not in resolved:
        raise RuntimeError(
            "remote ID transport spec must be 'log' or 'module:attribute'"
        )

    module_name, attr_name = resolved.split(":", 1)
    module = importlib.import_module(module_name)
    transport_obj = getattr(module, attr_name)
    if isinstance(transport_obj, type):
        transport_obj = transport_obj()
    if isinstance(transport_obj, RemoteIDTransport):
        return transport_obj
    if hasattr(transport_obj, "emit") and callable(transport_obj.emit):
        return transport_obj
    if callable(transport_obj):
        return CallableRemoteIDTransport(transport_obj)
    raise RuntimeError(
        f"remote ID transport '{resolved}' must be a RemoteIDTransport or callable"
    )


# --- Remote-ID broadcast helper ---


def _broadcast_remote_id(
    snapshot: TelemetrySnapshot,
    transport: RemoteIDTransport | None = None,
) -> None:
    """Emit a Remote-ID (ASTM F3411-22a) compatible broadcast for one frame."""
    (transport or _load_remote_id_transport()).emit(snapshot)


# --- Bridge main loop ---


@dataclass
class BridgeState:
    """Mutable runtime state, kept in one place for inspectability."""

    frames_in: int = 0
    frames_out: int = 0
    commands_in: int = 0
    commands_ok: int = 0
    last_heartbeat_ns: int = 0
    mavlink_reconnects: int = 0
    ground_reconnects: int = 0


class OnboardBridge:
    """``OnboardBridge`` 역할을 담당한다."""
    def __init__(
        self,
        config: BridgeConfig,
        mav: MavlinkAdapter,
        ground: GroundLink,
        remote_id_transport: RemoteIDTransport | None = None,
    ) -> None:
        """인스턴스를 초기화한다."""
        self.config = config
        self.mav = mav
        self.ground = ground
        self.remote_id_transport = remote_id_transport
        self.state = BridgeState()
        self._stop_event = asyncio.Event()
        self._reconnect_lock = asyncio.Lock()
        self._connection_generation = 0

    async def run(self) -> int:
        """메인 실행 루프를 수행한다."""
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
        """`대상` 실행 상태를 제어한다."""
        self._stop_event.set()

    async def _connect_with_retry(self) -> None:
        for attempt in range(MAX_RECONNECT_ATTEMPTS):
            try:
                await self.mav.connect()
                await self.ground.connect()
                self._connection_generation += 1
                return
            except Exception as exc:
                backoff = RECONNECT_BACKOFF_S[min(attempt, len(RECONNECT_BACKOFF_S) - 1)]
                LOGGER.warning(
                    "connect attempt %d failed: %s (sleep %.1fs)",
                    attempt,
                    exc,
                    backoff,
                )
                await asyncio.sleep(backoff)

        raise RuntimeError("max reconnect attempts exhausted")

    async def _reconnect_runtime(
        self,
        *,
        reason: str,
        generation: int,
        mav_failed: bool = False,
        ground_failed: bool = False,
    ) -> bool:
        async with self._reconnect_lock:
            if generation != self._connection_generation:
                return True

            LOGGER.warning("runtime reconnect requested: %s", reason)
            await self._close_links()

            for attempt in range(MAX_RECONNECT_ATTEMPTS):
                try:
                    await self.mav.connect()
                    await self.ground.connect()
                    self._connection_generation += 1
                    if mav_failed:
                        self.state.mavlink_reconnects += 1
                    if ground_failed:
                        self.state.ground_reconnects += 1
                    LOGGER.info("runtime reconnect succeeded")
                    return True
                except Exception as exc:
                    backoff = RECONNECT_BACKOFF_S[min(attempt, len(RECONNECT_BACKOFF_S) - 1)]
                    LOGGER.warning(
                        "runtime reconnect attempt %d failed: %s (sleep %.1fs)",
                        attempt,
                        exc,
                        backoff,
                    )
                    await asyncio.sleep(backoff)

            LOGGER.error("runtime reconnect exhausted; stopping bridge")
            await self.stop()
            return False

    async def _telemetry_loop(self) -> None:
        period = 1.0 / max(1, self.config.telemetry_poll_hz)
        while not self._stop_event.is_set():
            generation = self._connection_generation
            try:
                snapshot = await self.mav.poll_telemetry(self.config.drone_id)
            except Exception as exc:
                LOGGER.warning("telemetry poll error: %s", exc)
                recovered = await self._reconnect_runtime(
                    reason=f"telemetry poll failed: {exc}",
                    generation=generation,
                    mav_failed=True,
                )
                if not recovered:
                    break
                continue

            if snapshot is not None:
                self.state.frames_in += 1
                try:
                    await self.ground.publish(snapshot)
                    self.state.frames_out += 1
                except Exception as exc:
                    LOGGER.warning("ground publish failed: %s", exc)
                    recovered = await self._reconnect_runtime(
                        reason=f"ground publish failed: {exc}",
                        generation=self._connection_generation,
                        ground_failed=True,
                    )
                    if not recovered:
                        break
                if self.config.enable_remote_id:
                    _broadcast_remote_id(snapshot, transport=self.remote_id_transport)
            await asyncio.sleep(period)

    async def _command_loop(self) -> None:
        while not self._stop_event.is_set():
            generation = self._connection_generation
            try:
                cmd = await self.ground.next_command()
            except Exception as exc:
                LOGGER.warning("ground command poll failed: %s", exc)
                recovered = await self._reconnect_runtime(
                    reason=f"ground command poll failed: {exc}",
                    generation=generation,
                    ground_failed=True,
                )
                if not recovered:
                    break
                continue

            if cmd is not None:
                self.state.commands_in += 1
                try:
                    ok = await self.mav.send_command(cmd)
                except Exception as exc:
                    LOGGER.warning("command send failed: %s", exc)
                    recovered = await self._reconnect_runtime(
                        reason=f"command send failed: {exc}",
                        generation=self._connection_generation,
                        mav_failed=True,
                    )
                    if not recovered:
                        break
                    await asyncio.sleep(0.01)
                    continue
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
        await self._close_links()

    async def _close_links(self) -> None:
        await self.mav.close()
        await self.ground.close()


# --- CLI ---


def parse_args(argv: list[str]) -> BridgeConfig:
    """`args` 입력을 해석한다."""
    parser = argparse.ArgumentParser(prog="onboard_bridge")
    parser.add_argument("--drone-id", type=int, required=True)
    parser.add_argument("--mavlink-uri", required=True, help="e.g. udp:0.0.0.0:14550")
    parser.add_argument("--ground-uri", required=True, help="e.g. ws://ground:5555")
    parser.add_argument("--heartbeat-interval-s", type=float, default=HEARTBEAT_INTERVAL_S)
    parser.add_argument("--telemetry-hz", type=int, default=TELEMETRY_POLL_HZ)
    parser.add_argument("--no-remote-id", action="store_true")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

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
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(getattr(signal, sig_name), _on_signal, sig_name)

    return await bridge.run()


def main(argv: list[str] | None = None) -> int:
    """``main`` 동작을 수행한다."""
    config = parse_args(argv if argv is not None else sys.argv[1:])
    return asyncio.run(_async_main(config))


if __name__ == "__main__":
    raise SystemExit(main())
