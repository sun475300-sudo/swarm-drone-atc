"""
Cyber-Physical System Monitor
Phase 356 - State Estimation, Anomaly Detection, Fault Diagnosis
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Callable
from collections import deque
import random


@dataclass
class CPSState:
    timestamp: float
    position: np.ndarray
    velocity: np.ndarray
    acceleration: np.ndarray
    battery: float
    temperature: float
    sensor_readings: Dict[str, float] = field(default_factory=dict)


@dataclass
class AnomalyAlert:
    timestamp: float
    anomaly_type: str
    severity: str
    description: str
    affected_component: str


class KalmanFilterCPS:
    def __init__(self, state_dim: int = 9, measurement_dim: int = 6):
        self.state_dim = state_dim
        self.measurement_dim = measurement_dim

        self.x = np.zeros(state_dim)
        self.P = np.eye(state_dim) * 1000

        self.F = np.eye(state_dim)
        dt = 0.01
        self.F[0:3, 3:6] = np.eye(3) * dt
        self.F[0:3, 6:9] = np.eye(3) * dt**2 / 2
        self.F[3:6, 6:9] = np.eye(3) * dt

        self.H = np.zeros((measurement_dim, state_dim))
        self.H[0:3, 0:3] = np.eye(3)
        self.H[3:6, 3:6] = np.eye(3)

        self.Q = np.eye(state_dim) * 0.01
        self.R = np.eye(measurement_dim) * 0.1

    def predict(self) -> np.ndarray:
        self.x = self.F @ self.x
        self.P = self.F @ self.P @ self.F.T + self.Q
        return self.x

    def update(self, z: np.ndarray) -> np.ndarray:
        y = z - self.H @ self.x
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)

        self.x = self.x + K @ y
        self.P = (np.eye(self.state_dim) - K @ self.H) @ self.P

        return self.x

    def get_state(self) -> Dict:
        return {
            "position": self.x[0:3],
            "velocity": self.x[3:6],
            "acceleration": self.x[6:9],
        }


class AnomalyDetector:
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.position_history = deque(maxlen=window_size)
        self.velocity_history = deque(maxlen=window_size)
        self.battery_history = deque(maxlen=window_size)

        self.position_threshold = 50.0
        self.velocity_threshold = 30.0
        self.battery_threshold = 15.0
        self.temperature_threshold = 70.0

    def add_observation(self, state: CPSState):
        self.position_history.append(state.position.copy())
        self.velocity_history.append(state.velocity.copy())
        self.battery_history.append(state.battery)

    def detect(self, state: CPSState) -> List[AnomalyAlert]:
        alerts = []

        if len(self.position_history) >= 10:
            recent_positions = np.array(list(self.position_history)[-10:])
            position_std = np.std(recent_positions, axis=0)

            if np.any(position_std > self.position_threshold):
                alerts.append(
                    AnomalyAlert(
                        timestamp=state.timestamp,
                        anomaly_type="position_jump",
                        severity="high",
                        description=f"Unexpected position change: std={position_std}",
                        affected_component="gps_sensor",
                    )
                )

        velocity_mag = np.linalg.norm(state.velocity)
        if velocity_mag > self.velocity_threshold:
            alerts.append(
                AnomalyAlert(
                    timestamp=state.timestamp,
                    anomaly_type="velocity_exceeded",
                    severity="critical",
                    description=f"Velocity {velocity_mag:.1f} m/s exceeds limit",
                    affected_component="flight_controller",
                )
            )

        if state.battery < self.battery_threshold:
            alerts.append(
                AnomalyAlert(
                    timestamp=state.timestamp,
                    anomaly_type="low_battery",
                    severity="critical",
                    description=f"Battery at {state.battery:.1f}%",
                    affected_component="power_system",
                )
            )

        if state.temperature > self.temperature_threshold:
            alerts.append(
                AnomalyAlert(
                    timestamp=state.timestamp,
                    anomaly_type="overheating",
                    severity="high",
                    description=f"Temperature {state.temperature:.1f}°C exceeds limit",
                    affected_component="motor",
                )
            )

        return alerts


class FaultDiagnosis:
    def __init__(self):
        self.fault_models = {
            "motor_failure": self._detect_motor_failure,
            "sensor_bias": self._detect_sensor_bias,
            "communication_loss": self._detect_comm_loss,
            "structural_damage": self._detect_structural,
        }
        self.diagnosis_history: List[Dict] = []

    def _detect_motor_failure(self, state: CPSState, history: List[CPSState]) -> float:
        if len(history) < 10:
            return 0.0

        recent_accel = np.array([s.acceleration for s in history[-10:]])
        accel_variance = np.var(recent_accel, axis=0)

        if np.mean(accel_variance) > 10.0:
            return 0.9

        return 0.0

    def _detect_sensor_bias(self, state: CPSState, history: List[CPSState]) -> float:
        if len(history) < 20:
            return 0.0

        positions = np.array([s.position for s in history[-20:]])

        velocity_from_pos = np.diff(positions, axis=0)
        reported_velocity = np.array([s.velocity for s in history[-19:]])

        bias = np.mean(velocity_from_pos - reported_velocity[:-1], axis=0)

        if np.linalg.norm(bias) > 2.0:
            return 0.8

        return 0.0

    def _detect_comm_loss(self, state: CPSState, history: List[CPSState]) -> float:
        if len(history) < 5:
            return 0.0

        time_gaps = [
            history[i].timestamp - history[i - 1].timestamp
            for i in range(1, len(history))
        ]

        max_gap = max(time_gaps)

        if max_gap > 1.0:
            return min(1.0, max_gap / 5.0)

        return 0.0

    def _detect_structural(self, state: CPSState, history: List[CPSState]) -> float:
        if len(history) < 30:
            return 0.0

        positions = np.array([s.position for s in history[-30:]])

        vibrations = np.diff(positions, axis=0)
        vibration_energy = np.mean(np.linalg.norm(vibrations, axis=1))

        if vibration_energy > 5.0:
            return 0.7

        return 0.0

    def diagnose(self, state: CPSState, history: List[CPSState]) -> Dict:
        faults = {}

        for fault_name, detect_fn in self.fault_models.items():
            probability = detect_fn(state, history)
            if probability > 0.5:
                faults[fault_name] = probability

        diagnosis = {
            "timestamp": state.timestamp,
            "faults": faults,
            "health_score": 1.0 - max(faults.values()) if faults else 1.0,
            "recommendation": self._get_recommendation(faults),
        }

        self.diagnosis_history.append(diagnosis)

        return diagnosis

    def _get_recommendation(self, faults: Dict) -> str:
        if not faults:
            return "Continue normal operation"

        max_fault = max(faults, key=faults.get)

        recommendations = {
            "motor_failure": "Immediate landing recommended - check motor status",
            "sensor_bias": "Recalibrate sensors - use redundant sensors",
            "communication_loss": "Switch to backup communication channel",
            "structural_damage": "Return to base for inspection",
        }

        return recommendations.get(max_fault, "Monitor closely")


class CPSMonitor:
    def __init__(self, drone_id: str):
        self.drone_id = drone_id
        self.kalman_filter = KalmanFilterCPS()
        self.anomaly_detector = AnomalyDetector()
        self.fault_diagnosis = FaultDiagnosis()

        self.state_history: List[CPSState] = []
        self.alerts: List[AnomalyAlert] = []
        self.diagnoses: List[Dict] = []

    def update(self, timestamp: float, sensor_data: Dict) -> Dict:
        position = np.array(
            [
                sensor_data.get("gps_x", 0),
                sensor_data.get("gps_y", 0),
                sensor_data.get("gps_z", 50),
            ]
        )

        velocity = np.array(
            [
                sensor_data.get("vel_x", 0),
                sensor_data.get("vel_y", 0),
                sensor_data.get("vel_z", 0),
            ]
        )

        measurement = np.concatenate([position, velocity])

        self.kalman_filter.predict()
        self.kalman_filter.update(measurement)

        estimated_state = self.kalman_filter.get_state()

        state = CPSState(
            timestamp=timestamp,
            position=estimated_state["position"],
            velocity=estimated_state["velocity"],
            acceleration=estimated_state["acceleration"],
            battery=sensor_data.get("battery", 100),
            temperature=sensor_data.get("temperature", 25),
            sensor_readings=sensor_data,
        )

        self.state_history.append(state)
        self.anomaly_detector.add_observation(state)

        alerts = self.anomaly_detector.detect(state)
        self.alerts.extend(alerts)

        diagnosis = self.fault_diagnosis.diagnose(state, self.state_history)
        self.diagnoses.append(diagnosis)

        return {
            "estimated_state": estimated_state,
            "alerts": alerts,
            "diagnosis": diagnosis,
        }

    def get_health_status(self) -> Dict:
        if not self.diagnoses:
            return {"health_score": 1.0, "status": "unknown"}

        latest = self.diagnoses[-1]

        return {
            "health_score": latest["health_score"],
            "status": "healthy" if latest["health_score"] > 0.8 else "degraded",
            "active_faults": latest["faults"],
            "recommendation": latest["recommendation"],
            "alert_count": len(self.alerts),
        }


def simulate_cps_monitoring(duration: float = 10.0):
    monitor = CPSMonitor("drone_001")

    print(f"=== Cyber-Physical System Monitoring ({duration}s) ===")

    time_step = 0.1
    t = 0

    while t < duration:
        sensor_data = {
            "gps_x": 100 + t * 0.5 + np.random.randn() * 0.5,
            "gps_y": 100 + t * 0.3 + np.random.randn() * 0.5,
            "gps_z": 50 + np.sin(t * 0.5) * 5 + np.random.randn() * 0.5,
            "vel_x": 0.5 + np.random.randn() * 0.1,
            "vel_y": 0.3 + np.random.randn() * 0.1,
            "vel_z": np.sin(t * 0.5) * 0.5 + np.random.randn() * 0.1,
            "battery": max(0, 80 - t * 0.5),
            "temperature": 25 + t * 0.2 + np.random.randn() * 1,
        }

        if t > 5 and t < 5.5:
            sensor_data["vel_x"] += 50
            sensor_data["temperature"] += 30

        result = monitor.update(t, sensor_data)

        if result["alerts"]:
            for alert in result["alerts"]:
                print(f"[{t:.1f}s] ALERT: {alert.anomaly_type} - {alert.description}")

        if int(t / 2) > int((t - time_step) / 2):
            health = monitor.get_health_status()
            print(
                f"[{t:.1f}s] Health: {health['health_score']:.2f}, Status: {health['status']}"
            )

        t += time_step

    final_health = monitor.get_health_status()
    print(f"\n=== Final Status ===")
    print(f"Health Score: {final_health['health_score']:.2f}")
    print(f"Total Alerts: {final_health['alert_count']}")
    print(f"Recommendation: {final_health['recommendation']}")

    return final_health


if __name__ == "__main__":
    simulate_cps_monitoring(duration=10)
