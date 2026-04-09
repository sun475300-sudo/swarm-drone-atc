"""
Phase 340: Predictive Maintenance v2
RUL(Remaining Useful Life) 추정 + Weibull 분석 + 이상 징후 탐지.
센서 데이터 기반 부품 수명 예측.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple


class ComponentType(Enum):
    MOTOR = "motor"
    ESC = "esc"
    BATTERY = "battery"
    PROPELLER = "propeller"
    FRAME = "frame"
    SENSOR_IMU = "sensor_imu"
    SENSOR_GPS = "sensor_gps"
    FLIGHT_CONTROLLER = "flight_controller"


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    WARNING = "warning"
    CRITICAL = "critical"
    FAILED = "failed"


class AlertSeverity(Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SensorReading:
    timestamp: float
    component_id: str
    vibration: float  # g
    temperature: float  # celsius
    current_draw: float  # amps
    voltage: float  # volts
    rpm: float = 0.0
    noise_db: float = 0.0


@dataclass
class ComponentHealth:
    component_id: str
    component_type: ComponentType
    health_score: float  # 0-100
    status: HealthStatus
    rul_hours: float  # remaining useful life
    failure_probability: float  # 0-1
    trend: str  # improving, stable, degrading


@dataclass
class MaintenanceAlert:
    alert_id: str
    component_id: str
    severity: AlertSeverity
    description: str
    recommended_action: str
    estimated_rul: float
    timestamp: float


@dataclass
class WeibullParams:
    shape: float  # beta
    scale: float  # eta
    location: float = 0.0


class WeibullAnalyzer:
    """Weibull distribution for reliability analysis."""

    def __init__(self):
        self.params: Dict[ComponentType, WeibullParams] = {
            ComponentType.MOTOR: WeibullParams(2.5, 800),
            ComponentType.ESC: WeibullParams(2.0, 1200),
            ComponentType.BATTERY: WeibullParams(3.0, 500),
            ComponentType.PROPELLER: WeibullParams(1.8, 300),
            ComponentType.FRAME: WeibullParams(4.0, 5000),
            ComponentType.SENSOR_IMU: WeibullParams(2.2, 2000),
            ComponentType.SENSOR_GPS: WeibullParams(2.0, 3000),
            ComponentType.FLIGHT_CONTROLLER: WeibullParams(3.5, 4000),
        }

    def reliability(self, comp_type: ComponentType, hours: float) -> float:
        p = self.params.get(comp_type, WeibullParams(2.0, 1000))
        t = max(hours - p.location, 0)
        return float(np.exp(-(t / p.scale) ** p.shape))

    def failure_rate(self, comp_type: ComponentType, hours: float) -> float:
        p = self.params.get(comp_type, WeibullParams(2.0, 1000))
        t = max(hours - p.location, 1e-10)
        return float((p.shape / p.scale) * (t / p.scale) ** (p.shape - 1))

    def rul_estimate(self, comp_type: ComponentType, current_hours: float,
                     target_reliability: float = 0.5) -> float:
        p = self.params.get(comp_type, WeibullParams(2.0, 1000))
        target_time = p.scale * (-np.log(target_reliability)) ** (1.0 / p.shape) + p.location
        return max(0, target_time - current_hours)

    def mtbf(self, comp_type: ComponentType) -> float:
        p = self.params.get(comp_type, WeibullParams(2.0, 1000))
        from math import gamma
        return p.scale * gamma(1 + 1.0 / p.shape) + p.location


class AnomalyDetector:
    """Sensor-based anomaly detection for predictive maintenance."""

    def __init__(self, window_size: int = 50, threshold_sigma: float = 3.0):
        self.window_size = window_size
        self.threshold_sigma = threshold_sigma
        self.history: Dict[str, List[float]] = {}

    def add_reading(self, component_id: str, value: float) -> Optional[float]:
        if component_id not in self.history:
            self.history[component_id] = []
        self.history[component_id].append(value)

        hist = self.history[component_id]
        if len(hist) < self.window_size:
            return None

        window = hist[-self.window_size:]
        mean = np.mean(window)
        std = np.std(window)
        if std < 1e-10:
            return 0.0

        z_score = abs(value - mean) / std
        return float(z_score)

    def is_anomalous(self, component_id: str, value: float) -> bool:
        z = self.add_reading(component_id, value)
        return z is not None and z > self.threshold_sigma


class PredictiveMaintenanceV2:
    """Advanced predictive maintenance engine."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.weibull = WeibullAnalyzer()
        self.anomaly_detector = AnomalyDetector()
        self.components: Dict[str, Tuple[ComponentType, float]] = {}  # id -> (type, hours)
        self.health_records: Dict[str, ComponentHealth] = {}
        self.alerts: List[MaintenanceAlert] = []
        self.readings: List[SensorReading] = []
        self._alert_counter = 0

    def register_component(self, component_id: str,
                           component_type: ComponentType,
                           initial_hours: float = 0.0) -> None:
        self.components[component_id] = (component_type, initial_hours)

    def process_reading(self, reading: SensorReading) -> ComponentHealth:
        self.readings.append(reading)
        comp_type, hours = self.components.get(
            reading.component_id, (ComponentType.MOTOR, 0))

        # Update flight hours (assume 1 reading ≈ 0.01 hours)
        hours += 0.01
        self.components[reading.component_id] = (comp_type, hours)

        # Weibull-based reliability
        reliability = self.weibull.reliability(comp_type, hours)
        rul = self.weibull.rul_estimate(comp_type, hours)
        fail_prob = 1.0 - reliability

        # Anomaly scoring
        vib_anomaly = self.anomaly_detector.is_anomalous(
            f"{reading.component_id}_vib", reading.vibration)
        temp_anomaly = self.anomaly_detector.is_anomalous(
            f"{reading.component_id}_temp", reading.temperature)

        # Health score
        health_score = reliability * 100
        if vib_anomaly:
            health_score *= 0.7
        if temp_anomaly:
            health_score *= 0.8
        if reading.temperature > 80:
            health_score *= 0.6
        health_score = max(0, min(100, health_score))

        # Determine status
        if health_score > 80:
            status = HealthStatus.HEALTHY
        elif health_score > 60:
            status = HealthStatus.DEGRADED
        elif health_score > 40:
            status = HealthStatus.WARNING
        elif health_score > 20:
            status = HealthStatus.CRITICAL
        else:
            status = HealthStatus.FAILED

        # Trend detection
        prev = self.health_records.get(reading.component_id)
        if prev:
            if health_score > prev.health_score + 2:
                trend = "improving"
            elif health_score < prev.health_score - 2:
                trend = "degrading"
            else:
                trend = "stable"
        else:
            trend = "stable"

        health = ComponentHealth(
            component_id=reading.component_id,
            component_type=comp_type,
            health_score=round(health_score, 1),
            status=status,
            rul_hours=round(rul, 1),
            failure_probability=round(fail_prob, 4),
            trend=trend
        )
        self.health_records[reading.component_id] = health

        # Generate alerts
        if status in (HealthStatus.WARNING, HealthStatus.CRITICAL, HealthStatus.FAILED):
            self._generate_alert(health, reading.timestamp)

        return health

    def _generate_alert(self, health: ComponentHealth, timestamp: float) -> None:
        self._alert_counter += 1
        severity_map = {
            HealthStatus.WARNING: AlertSeverity.MEDIUM,
            HealthStatus.CRITICAL: AlertSeverity.HIGH,
            HealthStatus.FAILED: AlertSeverity.CRITICAL,
        }
        action_map = {
            HealthStatus.WARNING: "Schedule inspection",
            HealthStatus.CRITICAL: "Immediate maintenance required",
            HealthStatus.FAILED: "Ground drone and replace component",
        }
        self.alerts.append(MaintenanceAlert(
            alert_id=f"MA-{self._alert_counter:06d}",
            component_id=health.component_id,
            severity=severity_map.get(health.status, AlertSeverity.INFO),
            description=f"{health.component_type.value} health={health.health_score}%, "
                        f"RUL={health.rul_hours}h",
            recommended_action=action_map.get(health.status, "Monitor"),
            estimated_rul=health.rul_hours,
            timestamp=timestamp
        ))

    def fleet_health_report(self) -> Dict:
        if not self.health_records:
            return {"total_components": 0}

        scores = [h.health_score for h in self.health_records.values()]
        statuses: Dict[str, int] = {}
        for h in self.health_records.values():
            statuses[h.status.value] = statuses.get(h.status.value, 0) + 1

        return {
            "total_components": len(self.components),
            "avg_health": round(float(np.mean(scores)), 1),
            "min_health": round(float(np.min(scores)), 1),
            "status_distribution": statuses,
            "total_alerts": len(self.alerts),
            "critical_alerts": sum(1 for a in self.alerts
                                   if a.severity == AlertSeverity.CRITICAL),
        }

    def summary(self) -> Dict:
        return {
            **self.fleet_health_report(),
            "total_readings": len(self.readings),
        }


if __name__ == "__main__":
    pm = PredictiveMaintenanceV2(seed=42)
    rng = np.random.default_rng(42)

    for i in range(4):
        pm.register_component(f"motor_{i}", ComponentType.MOTOR, initial_hours=i * 100)
    pm.register_component("battery_0", ComponentType.BATTERY, initial_hours=200)

    for t in range(100):
        for comp_id in list(pm.components.keys()):
            reading = SensorReading(
                timestamp=float(t),
                component_id=comp_id,
                vibration=0.5 + rng.standard_normal() * 0.1 + t * 0.002,
                temperature=40 + rng.standard_normal() * 2 + t * 0.1,
                current_draw=5.0 + rng.standard_normal() * 0.5,
                voltage=11.1 - t * 0.005,
                rpm=5000 + rng.standard_normal() * 100,
            )
            pm.process_reading(reading)

    print(f"Summary: {pm.summary()}")
