# Phase 550: Drone Digital Twin — State Synchronization & Prediction
"""
디지털 트윈: 물리 드론 ↔ 가상 모델 실시간 동기화,
상태 예측, 이상 탐지, 예지 정비.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class DronePhysicalState:
    drone_id: str
    position: np.ndarray  # [x, y, z]
    velocity: np.ndarray
    battery_pct: float
    motor_rpm: np.ndarray  # 4 motors
    temperature_c: float
    timestamp: float


@dataclass
class TwinState:
    predicted_position: np.ndarray
    predicted_battery: float
    divergence: float  # physical vs twin 차이
    anomaly_score: float
    maintenance_needed: bool


class PhysicsModel:
    """간이 드론 물리 모델."""

    def __init__(self, mass=1.5, drag=0.1):
        self.mass = mass
        self.drag = drag

    def predict_next(self, state: DronePhysicalState, dt=0.1) -> DronePhysicalState:
        accel = -self.drag * state.velocity / self.mass
        new_vel = state.velocity + accel * dt
        new_pos = state.position + new_vel * dt
        # 배터리 소모 모델
        power = float(np.sum(state.motor_rpm) * 0.0001)
        new_batt = max(0, state.battery_pct - power * dt)
        # 온도 모델
        new_temp = state.temperature_c + power * 0.1 * dt - 0.05 * dt * (state.temperature_c - 25)
        return DronePhysicalState(
            state.drone_id, new_pos, new_vel, new_batt,
            state.motor_rpm.copy(), new_temp, state.timestamp + dt
        )


class AnomalyPredictor:
    """상태 이상 예측."""

    def __init__(self, threshold=5.0):
        self.threshold = threshold
        self.history: list[float] = []

    def score(self, physical: DronePhysicalState, predicted: DronePhysicalState) -> float:
        pos_diff = float(np.linalg.norm(physical.position - predicted.predicted_position
                                         if hasattr(predicted, 'predicted_position')
                                         else physical.position - predicted.position))
        batt_diff = abs(physical.battery_pct - predicted.battery_pct)
        temp_anomaly = max(0, physical.temperature_c - 60) * 0.5
        score = pos_diff + batt_diff * 0.1 + temp_anomaly
        self.history.append(score)
        return score

    def needs_maintenance(self, state: DronePhysicalState) -> bool:
        return (state.battery_pct < 20 or
                state.temperature_c > 55 or
                float(np.min(state.motor_rpm)) < 100)


class DigitalTwin:
    """단일 드론 디지털 트윈."""

    def __init__(self, drone_id: str, seed=42):
        self.drone_id = drone_id
        self.physics = PhysicsModel()
        self.anomaly = AnomalyPredictor()
        self.rng = np.random.default_rng(seed)
        self.sync_count = 0
        self.predicted: DronePhysicalState | None = None

    def sync(self, physical_state: DronePhysicalState) -> TwinState:
        """물리 상태와 동기화 + 예측."""
        self.sync_count += 1
        predicted = self.physics.predict_next(physical_state)
        self.predicted = predicted

        divergence = float(np.linalg.norm(physical_state.position - predicted.position))
        anomaly_score = self.anomaly.score(physical_state, predicted)
        maint = self.anomaly.needs_maintenance(physical_state)

        return TwinState(predicted.position, predicted.battery_pct,
                         divergence, anomaly_score, maint)


class DroneDigitalTwinSystem:
    """다중 드론 디지털 트윈 시스템."""

    def __init__(self, n_drones=15, seed=42):
        self.rng = np.random.default_rng(seed)
        self.n_drones = n_drones
        self.twins: dict[str, DigitalTwin] = {}
        self.states: dict[str, DronePhysicalState] = {}
        self.twin_results: list[TwinState] = []

        for i in range(n_drones):
            did = f"drone_{i}"
            self.twins[did] = DigitalTwin(did, seed + i)
            pos = self.rng.uniform(-100, 100, 3)
            pos[2] = 30 + self.rng.uniform(0, 70)
            self.states[did] = DronePhysicalState(
                did, pos, self.rng.uniform(-5, 5, 3),
                80 + self.rng.uniform(0, 20),
                3000 + self.rng.uniform(-500, 500, 4),
                25 + self.rng.uniform(0, 15),
                0.0
            )

    def step(self, dt=0.1):
        """한 스텝: 물리 업데이트 + 트윈 동기화."""
        for did in self.states:
            state = self.states[did]
            # 물리 시뮬레이션 (노이즈 포함)
            noise = self.rng.normal(0, 0.1, 3)
            state.position = state.position + state.velocity * dt + noise
            state.velocity += self.rng.normal(0, 0.05, 3)
            state.battery_pct = max(0, state.battery_pct - 0.01 * dt)
            state.motor_rpm += self.rng.normal(0, 10, 4)
            state.temperature_c += self.rng.normal(0, 0.1)
            state.timestamp += dt

            # 트윈 동기화
            result = self.twins[did].sync(state)
            self.twin_results.append(result)

    def run(self, steps=50, dt=0.1):
        for _ in range(steps):
            self.step(dt)

    def summary(self):
        maint_needed = sum(1 for r in self.twin_results[-self.n_drones:]
                           if r.maintenance_needed)
        avg_div = float(np.mean([r.divergence for r in self.twin_results[-self.n_drones:]]))
        avg_anom = float(np.mean([r.anomaly_score for r in self.twin_results[-self.n_drones:]]))
        return {
            "drones": self.n_drones,
            "sync_steps": len(self.twin_results) // self.n_drones,
            "avg_divergence": round(avg_div, 4),
            "avg_anomaly_score": round(avg_anom, 4),
            "maintenance_needed": maint_needed,
        }


if __name__ == "__main__":
    dts = DroneDigitalTwinSystem(15, 42)
    dts.run(50)
    for k, v in dts.summary().items():
        print(f"  {k}: {v}")
