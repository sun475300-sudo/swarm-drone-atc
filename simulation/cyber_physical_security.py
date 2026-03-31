"""
Phase 505: Cyber-Physical Security
CPS 보안 모니터링, 물리-사이버 공격 벡터 탐지, 무결성 검증.
"""

import numpy as np
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional


class AttackSurface(Enum):
    FIRMWARE = "firmware"
    SENSOR = "sensor"
    ACTUATOR = "actuator"
    COMMUNICATION = "communication"
    GNSS = "gnss"
    SUPPLY_CHAIN = "supply_chain"


class ThreatLevel(Enum):
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class IntegrityCheck:
    component: str
    expected_hash: str
    actual_hash: str
    passed: bool
    timestamp: float


@dataclass
class CPSAlert:
    alert_id: str
    surface: AttackSurface
    level: ThreatLevel
    description: str
    timestamp: float
    mitigated: bool = False


@dataclass
class SensorReading:
    sensor_id: str
    value: float
    expected_range: tuple
    anomaly_score: float = 0.0


class FirmwareVerifier:
    """Firmware integrity verification using hash chains."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.firmware_hashes: Dict[str, str] = {}
        self.verification_log: List[IntegrityCheck] = []

    def register(self, component: str, firmware_data: str):
        h = hashlib.sha256(firmware_data.encode()).hexdigest()
        self.firmware_hashes[component] = h

    def verify(self, component: str, current_data: str, timestamp: float = 0) -> IntegrityCheck:
        expected = self.firmware_hashes.get(component, "")
        actual = hashlib.sha256(current_data.encode()).hexdigest()
        check = IntegrityCheck(component, expected[:16], actual[:16],
                              expected == actual, timestamp)
        self.verification_log.append(check)
        return check


class SensorAnomalyDetector:
    """Physics-based anomaly detection for CPS sensors."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.history: Dict[str, List[float]] = {}
        self.window_size = 20

    def check(self, reading: SensorReading) -> float:
        if reading.sensor_id not in self.history:
            self.history[reading.sensor_id] = []
        hist = self.history[reading.sensor_id]
        hist.append(reading.value)
        if len(hist) > self.window_size:
            hist.pop(0)

        score = 0.0
        lo, hi = reading.expected_range
        if reading.value < lo or reading.value > hi:
            score += 0.5

        if len(hist) >= 5:
            mean = np.mean(hist)
            std = np.std(hist) + 1e-8
            z = abs(reading.value - mean) / std
            if z > 3:
                score += 0.3
            diffs = np.diff(hist[-5:])
            if np.std(diffs) < 1e-6 and len(set(hist[-5:])) == 1:
                score += 0.2  # stuck sensor

        reading.anomaly_score = min(1.0, score)
        return reading.anomaly_score


class CyberPhysicalSecurity:
    """Integrated CPS security monitoring for drone swarms."""

    def __init__(self, n_drones: int = 20, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_drones = n_drones
        self.firmware = FirmwareVerifier(seed)
        self.anomaly_detector = SensorAnomalyDetector(seed)
        self.alerts: List[CPSAlert] = []
        self.time = 0.0
        self._alert_counter = 0

        for i in range(n_drones):
            self.firmware.register(f"drone_{i}", f"firmware_v1.0_drone_{i}")

    def _emit_alert(self, surface: AttackSurface, level: ThreatLevel,
                    desc: str) -> CPSAlert:
        self._alert_counter += 1
        alert = CPSAlert(f"CPS-{self._alert_counter:05d}", surface, level,
                        desc, self.time)
        self.alerts.append(alert)
        return alert

    def check_firmware(self, drone_id: int, current_data: str = None) -> IntegrityCheck:
        comp = f"drone_{drone_id}"
        data = current_data or f"firmware_v1.0_drone_{drone_id}"
        check = self.firmware.verify(comp, data, self.time)
        if not check.passed:
            self._emit_alert(AttackSurface.FIRMWARE, ThreatLevel.CRITICAL,
                           f"Firmware integrity failure: {comp}")
        return check

    def check_sensor(self, drone_id: int, sensor_name: str,
                     value: float, expected_range: tuple) -> float:
        reading = SensorReading(f"d{drone_id}_{sensor_name}", value, expected_range)
        score = self.anomaly_detector.check(reading)
        if score > 0.5:
            level = ThreatLevel.HIGH if score > 0.7 else ThreatLevel.MEDIUM
            self._emit_alert(AttackSurface.SENSOR, level,
                           f"Sensor anomaly d{drone_id}/{sensor_name}: score={score:.2f}")
        return score

    def run_scan(self) -> Dict:
        self.time += 1.0
        firmware_ok = 0
        sensor_alerts = 0
        for i in range(self.n_drones):
            tampered = self.rng.random() < 0.02
            data = f"firmware_TAMPERED_{i}" if tampered else f"firmware_v1.0_drone_{i}"
            check = self.check_firmware(i, data)
            if check.passed:
                firmware_ok += 1

            alt = self.rng.normal(50, 5)
            score = self.check_sensor(i, "altimeter", alt, (10, 150))
            if score > 0.5:
                sensor_alerts += 1

        return {"firmware_ok": firmware_ok, "sensor_alerts": sensor_alerts,
                "total_alerts": len(self.alerts)}

    def summary(self) -> Dict:
        return {
            "drones": self.n_drones,
            "total_alerts": len(self.alerts),
            "critical": sum(1 for a in self.alerts if a.level == ThreatLevel.CRITICAL),
            "firmware_checks": len(self.firmware.verification_log),
            "integrity_rate": round(
                sum(1 for c in self.firmware.verification_log if c.passed) /
                max(len(self.firmware.verification_log), 1), 4),
        }
