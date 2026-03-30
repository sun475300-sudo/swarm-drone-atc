"""
Hardware-in-the-Loop Simulator v2
Phase 362 - Real-time HIL with physics engine, sensor simulation
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
import time


@dataclass
class DronePhysicsState:
    position: np.ndarray
    velocity: np.ndarray
    attitude: np.ndarray
    angular_velocity: np.ndarray
    acceleration: np.ndarray


@dataclass
class SensorData:
    imu_accel: np.ndarray
    imu_gyro: np.ndarray
    magnetometer: np.ndarray
    gps_position: np.ndarray
    gps_velocity: np.ndarray
    barometer_altitude: float
    ultrasonic_distance: float
    camera_image: Optional[np.ndarray] = None


@dataclass
class MotorCommand:
    motor_id: int
    pwm: float
    rpm: int


class PhysicsEngine:
    def __init__(self):
        self.g = 9.81
        self.air_density = 1.225
        self.dt = 0.001

    def update(
        self, state: DronePhysicsState, commands: List[MotorCommand]
    ) -> DronePhysicsState:
        thrust = self._calculate_thrust(commands)
        torque = self._calculate_torque(commands)
        drag = self._calculate_drag(state.velocity)
        gravity = np.array([0, 0, -self.g])

        total_force = thrust + drag + gravity * 1.0
        acceleration = total_force / 1.0

        new_velocity = state.velocity + acceleration * self.dt
        new_position = state.position + new_velocity * self.dt

        inertia = np.array([0.1, 0.1, 0.05])
        angular_acceleration = torque / inertia - state.angular_velocity * 0.1

        new_angular_velocity = state.angular_velocity + angular_acceleration * self.dt
        new_attitude = state.attitude + new_angular_velocity * self.dt

        return DronePhysicsState(
            position=new_position,
            velocity=new_velocity,
            attitude=new_attitude,
            angular_velocity=new_angular_velocity,
            acceleration=acceleration,
        )

    def _calculate_thrust(self, commands: List[MotorCommand]) -> np.ndarray:
        total_thrust = sum(c.pwm / 255.0 * 10.0 for c in commands)
        return np.array([0, 0, total_thrust])

    def _calculate_torque(self, commands: List[MotorCommand]) -> np.ndarray:
        if len(commands) < 4:
            return np.zeros(3)

        dx = np.array([1, -1, -1, 1]) * 0.1
        dy = np.array([1, 1, -1, -1]) * 0.1

        torque = np.zeros(3)
        for i, cmd in enumerate(commands):
            torque[0] += dy[i] * cmd.pwm / 255.0
            torque[1] += dx[i] * cmd.pwm / 255.0
            torque[2] += (-1) ** i * cmd.pwm / 255.0 * 0.01

        return torque

    def _calculate_drag(self, velocity: np.ndarray) -> np.ndarray:
        drag_coefficient = 0.05
        return -drag_coefficient * np.linalg.norm(velocity) * velocity


class SensorSimulator:
    def __init__(self, noise_level: float = 0.1):
        self.noise_level = noise_level

    def generate_imu(
        self, true_accel: np.ndarray, true_gyro: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        accel_noise = np.random.normal(0, self.noise_level * 0.1, 3)
        gyro_noise = np.random.normal(0, self.noise_level * 0.05, 3)

        accel = true_accel + accel_noise + np.array([0, 0, self.g])
        gyro = true_gyro + gyro_noise

        return accel, gyro

    def generate_magnetometer(self, attitude: np.ndarray) -> np.ndarray:
        base = np.array([1, 0, 0])
        noise = np.random.normal(0, 0.01, 3)

        roll, pitch, yaw = attitude
        rotation = self._euler_to_rotation(roll, pitch, yaw)

        return rotation @ base + noise

    def generate_gps(
        self, position: np.ndarray, velocity: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        pos_noise = np.random.normal(0, self.noise_level * 0.5, 3)
        vel_noise = np.random.normal(0, self.noise_level * 0.2, 3)

        return position + pos_noise, velocity + vel_noise

    def generate_barometer(self, altitude: float) -> float:
        noise = np.random.normal(0, 0.5)
        return altitude + noise

    def generate_ultrasonic(self, distance: float) -> float:
        noise = np.random.normal(0, 0.02)
        return max(0, distance + noise)

    def _euler_to_rotation(self, roll: float, pitch: float, yaw: float) -> np.ndarray:
        R_roll = np.array(
            [
                [1, 0, 0],
                [0, np.cos(roll), -np.sin(roll)],
                [0, np.sin(roll), np.cos(roll)],
            ]
        )
        R_pitch = np.array(
            [
                [np.cos(pitch), 0, np.sin(pitch)],
                [0, 1, 0],
                [-np.sin(pitch), 0, np.cos(pitch)],
            ]
        )
        R_yaw = np.array(
            [[np.cos(yaw), -np.sin(yaw), 0], [np.sin(yaw), np.cos(yaw), 0], [0, 0, 1]]
        )
        return R_roll @ R_pitch @ R_yaw


class HILController:
    def __init__(self):
        self.physics = PhysicsEngine()
        self.sensors = SensorSimulator()

        self.state = DronePhysicsState(
            position=np.array([0.0, 0.0, 0.0]),
            velocity=np.array([0.0, 0.0, 0.0]),
            attitude=np.array([0.0, 0.0, 0.0]),
            angular_velocity=np.array([0.0, 0.0, 0.0]),
            acceleration=np.array([0.0, 0.0, -9.81]),
        )

        self.motors = [MotorCommand(i, 0, 0) for i in range(4)]
        self.sensor_data: Optional[SensorData] = None
        self.time = 0.0

    def set_motor(self, motor_id: int, pwm: float):
        if 0 <= motor_id < len(self.motors):
            self.motors[motor_id].pwm = np.clip(pwm, 0, 255)
            self.motors[motor_id].rpm = int(pwm / 255.0 * 10000)

    def step(self, dt: float = 0.001) -> SensorData:
        self.state = self.physics.update(self.state, self.motors)
        self.time += dt

        accel, gyro = self.sensors.generate_imu(
            self.state.acceleration, self.state.angular_velocity
        )
        magnetometer = self.sensors.generate_magnetometer(self.state.attitude)
        gps_pos, gps_vel = self.sensors.generate_gps(
            self.state.position, self.state.velocity
        )
        baro_alt = self.sensors.generate_barometer(self.state.position[2])

        ground_distance = max(0, self.state.position[2])
        ultrasonic = self.sensors.generate_ultrasonic(ground_distance)

        self.sensor_data = SensorData(
            imu_accel=accel,
            imu_gyro=gyro,
            magnetometer=magnetometer,
            gps_position=gps_pos,
            gps_velocity=gps_vel,
            barometer_altitude=baro_alt,
            ultrasonic_distance=ultrasonic,
        )

        return self.sensor_data

    def get_state_estimate(self) -> Dict:
        return {
            "position": self.state.position.tolist(),
            "velocity": self.state.velocity.tolist(),
            "attitude": self.state.attitude.tolist(),
            "altitude": self.state.position[2],
        }


class FlightController:
    def __init__(self, hil: HILController):
        self.hil = hil
        self.target_altitude = 0.0
        self.pid_altitude = PIDController(1.0, 0.1, 0.05)
        self.pid_roll = PIDController(1.0, 0.01, 0.0)
        self.pid_pitch = PIDController(1.0, 0.01, 0.0)
        self.pid_yaw = PIDController(1.0, 0.01, 0.0)

    def compute_control(self) -> List[MotorCommand]:
        sensors = self.hil.sensor_data
        if not sensors:
            return self.hil.motors

        current_alt = sensors.barometer_altitude
        alt_error = self.target_altitude - current_alt

        thrust_cmd = self.pid_altitude.compute(alt_error, 0.01)

        for i in range(4):
            self.hil.set_motor(i, thrust_cmd)

        return self.hil.motors


class PIDController:
    def __init__(self, kp: float, ki: float, kd: float):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.integral = 0.0
        self.prev_error = 0.0

    def compute(self, error: float, dt: float) -> float:
        self.integral += error * dt
        derivative = (error - self.prev_error) / dt if dt > 0 else 0

        output = self.kp * error + self.ki * self.integral + self.kd * derivative

        self.prev_error = error

        return np.clip(output + 128, 0, 255)


def simulate_hil():
    print("=== Hardware-in-the-Loop Simulator v2 ===")

    hil = HILController()
    fc = FlightController(hil)

    fc.target_altitude = 10.0

    print("\n--- Takeoff Sequence ---")
    for step in range(500):
        fc.compute_control()
        sensors = hil.step(0.01)

        if step % 50 == 0:
            state = hil.get_state_estimate()
            print(
                f"t={hil.time:.2f}s: Alt={state['altitude']:.2f}m, "
                f"Vel={np.linalg.norm(state['velocity']):.2f}m/s"
            )

    print("\n--- Hover Test ---")
    for step in range(500):
        fc.compute_control()
        sensors = hil.step(0.01)

        if step % 100 == 0:
            state = hil.get_state_estimate()
            print(f"t={hil.time:.2f}s: Alt={state['altitude']:.2f}m")

    print("\n--- Sensor Data Sample ---")
    print(f"IMU Accel: {sensors.imu_accel}")
    print(f"GPS: {sensors.gps_position}")
    print(f"Barometer: {sensors.barometer_altitude:.2f}m")
    print(f"Ultrasonic: {sensors.ultrasonic_distance:.2f}m")

    return hil.get_state_estimate()


if __name__ == "__main__":
    simulate_hil()
