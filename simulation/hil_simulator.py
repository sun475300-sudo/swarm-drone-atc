"""Phase 300: Hardware-in-the-Loop (HIL) Simulator — 하드웨어 인 더 루프 시뮬레이터.

실제 비행 컨트롤러 펌웨어와 연동 가능한 시뮬레이션 프레임워크.
센서 에뮬레이션, 액추에이터 모델링, 실시간 클럭 동기화.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Callable
import time


class HILMode(Enum):
    SOFTWARE_ONLY = "software_only"
    PROCESSOR_IN_LOOP = "pil"
    HARDWARE_IN_LOOP = "hil"
    FULL_VEHICLE = "full_vehicle"


class SensorType(Enum):
    IMU = "imu"
    GPS = "gps"
    BAROMETER = "barometer"
    MAGNETOMETER = "magnetometer"
    LIDAR = "lidar"
    OPTICAL_FLOW = "optical_flow"
    ULTRASONIC = "ultrasonic"


@dataclass
class SensorReading:
    sensor_type: SensorType
    timestamp: float
    data: np.ndarray
    noise_std: float = 0.0
    bias: float = 0.0
    latency_ms: float = 0.0


@dataclass
class ActuatorCommand:
    motor_speeds: np.ndarray  # RPM for each motor
    servo_angles: np.ndarray  # degrees
    timestamp: float = 0.0


@dataclass
class VehicleState:
    position: np.ndarray = field(default_factory=lambda: np.zeros(3))
    velocity: np.ndarray = field(default_factory=lambda: np.zeros(3))
    acceleration: np.ndarray = field(default_factory=lambda: np.zeros(3))
    attitude: np.ndarray = field(default_factory=lambda: np.zeros(3))  # roll, pitch, yaw
    angular_velocity: np.ndarray = field(default_factory=lambda: np.zeros(3))
    battery_voltage: float = 16.8
    motor_rpms: np.ndarray = field(default_factory=lambda: np.zeros(4))


class SensorEmulator:
    """센서 에뮬레이터 — 실제 센서 출력 시뮬레이션."""

    def __init__(self, rng_seed: int = 42):
        self._rng = np.random.default_rng(rng_seed)
        self._sensor_configs: Dict[SensorType, dict] = {
            SensorType.IMU: {"noise_std": 0.01, "bias": 0.001, "rate_hz": 400, "latency_ms": 0.5},
            SensorType.GPS: {"noise_std": 1.5, "bias": 0.0, "rate_hz": 10, "latency_ms": 100},
            SensorType.BAROMETER: {"noise_std": 0.5, "bias": 0.1, "rate_hz": 50, "latency_ms": 5},
            SensorType.MAGNETOMETER: {"noise_std": 0.02, "bias": 0.005, "rate_hz": 100, "latency_ms": 2},
            SensorType.LIDAR: {"noise_std": 0.05, "bias": 0.0, "rate_hz": 20, "latency_ms": 10},
        }

    def read_sensor(self, sensor_type: SensorType, true_state: VehicleState, timestamp: float) -> SensorReading:
        config = self._sensor_configs.get(sensor_type, {})
        noise_std = config.get("noise_std", 0.01)
        bias = config.get("bias", 0.0)
        latency = config.get("latency_ms", 1.0)

        if sensor_type == SensorType.IMU:
            data = np.concatenate([true_state.acceleration, true_state.angular_velocity])
        elif sensor_type == SensorType.GPS:
            data = true_state.position.copy()
        elif sensor_type == SensorType.BAROMETER:
            data = np.array([true_state.position[2]])  # altitude
        elif sensor_type == SensorType.MAGNETOMETER:
            heading = true_state.attitude[2]
            data = np.array([np.cos(heading), np.sin(heading), 0.0])
        else:
            data = true_state.position.copy()

        noise = self._rng.normal(0, noise_std, data.shape)
        data = data + noise + bias

        return SensorReading(
            sensor_type=sensor_type, timestamp=timestamp - latency / 1000.0,
            data=data, noise_std=noise_std, bias=bias, latency_ms=latency,
        )


class PhysicsEngine:
    """간이 쿼드콥터 물리 엔진."""

    GRAVITY = 9.81
    MASS_KG = 2.0
    ARM_LENGTH_M = 0.25
    THRUST_COEFF = 1e-5  # N per RPM²

    def __init__(self):
        self.drag_coeff = 0.1

    def step(self, state: VehicleState, command: ActuatorCommand, dt: float = 0.001) -> VehicleState:
        # Total thrust from motors
        total_thrust = sum(self.THRUST_COEFF * rpm ** 2 for rpm in command.motor_speeds)
        # Thrust direction based on attitude
        cy, sy = np.cos(state.attitude[2]), np.sin(state.attitude[2])
        cp, sp = np.cos(state.attitude[0]), np.sin(state.attitude[0])
        cr, sr = np.cos(state.attitude[1]), np.sin(state.attitude[1])

        thrust_vec = np.array([
            total_thrust * (cy * sp * cr + sy * sr),
            total_thrust * (sy * sp * cr - cy * sr),
            total_thrust * cp * cr,
        ])

        # Gravity
        gravity_vec = np.array([0, 0, -self.GRAVITY * self.MASS_KG])
        # Drag
        drag = -self.drag_coeff * state.velocity * np.abs(state.velocity)

        # Net force
        net_force = thrust_vec + gravity_vec + drag
        state.acceleration = net_force / self.MASS_KG
        state.velocity = state.velocity + state.acceleration * dt
        state.position = state.position + state.velocity * dt
        state.motor_rpms = command.motor_speeds.copy()

        # Simple attitude dynamics
        if len(command.motor_speeds) >= 4:
            torque_roll = (command.motor_speeds[1] - command.motor_speeds[3]) * self.ARM_LENGTH_M * self.THRUST_COEFF
            torque_pitch = (command.motor_speeds[0] - command.motor_speeds[2]) * self.ARM_LENGTH_M * self.THRUST_COEFF
            state.angular_velocity[0] += torque_roll * dt
            state.angular_velocity[1] += torque_pitch * dt
            state.attitude += state.angular_velocity * dt

        return state


class HILSimulator:
    """Hardware-in-the-Loop 시뮬레이터.

    - 실시간/가속 시뮬레이션 클럭
    - 센서 에뮬레이션 + 물리 엔진
    - 액추에이터 커맨드 처리
    - 다중 차량 HIL 지원
    """

    def __init__(self, mode: HILMode = HILMode.SOFTWARE_ONLY, rng_seed: int = 42):
        self.mode = mode
        self._rng = np.random.default_rng(rng_seed)
        self._vehicles: Dict[str, VehicleState] = {}
        self._sensor_emu = SensorEmulator(rng_seed)
        self._physics = PhysicsEngine()
        self._clock = 0.0
        self._dt = 0.001  # 1kHz physics
        self._callbacks: Dict[str, List[Callable]] = {}
        self._history: List[dict] = []
        self._step_count = 0

    def add_vehicle(self, vehicle_id: str, initial_pos: Optional[np.ndarray] = None) -> VehicleState:
        state = VehicleState()
        if initial_pos is not None:
            state.position = initial_pos.copy()
        self._vehicles[vehicle_id] = state
        return state

    def get_sensor(self, vehicle_id: str, sensor_type: SensorType) -> Optional[SensorReading]:
        state = self._vehicles.get(vehicle_id)
        if not state:
            return None
        return self._sensor_emu.read_sensor(sensor_type, state, self._clock)

    def send_command(self, vehicle_id: str, command: ActuatorCommand):
        state = self._vehicles.get(vehicle_id)
        if state:
            command.timestamp = self._clock
            self._physics.step(state, command, self._dt)

    def step(self, dt: Optional[float] = None):
        if dt is None:
            dt = self._dt
        self._clock += dt
        self._step_count += 1

    def run_for(self, duration_sec: float, command_fn: Optional[Callable] = None):
        steps = int(duration_sec / self._dt)
        for _ in range(steps):
            if command_fn:
                for vid in self._vehicles:
                    cmd = command_fn(vid, self._vehicles[vid], self._clock)
                    if cmd:
                        self.send_command(vid, cmd)
            self.step()

    def get_state(self, vehicle_id: str) -> Optional[VehicleState]:
        return self._vehicles.get(vehicle_id)

    @property
    def clock(self) -> float:
        return self._clock

    def reset(self):
        self._clock = 0.0
        self._step_count = 0
        self._vehicles.clear()

    def summary(self) -> dict:
        return {
            "mode": self.mode.value,
            "vehicles": len(self._vehicles),
            "clock_sec": round(self._clock, 4),
            "step_count": self._step_count,
            "physics_dt": self._dt,
        }
