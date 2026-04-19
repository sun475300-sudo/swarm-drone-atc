"""
Phase 481: Adversarial Defense System
적대적 공격 탐지, GPS 스푸핑 방어, 안티재밍.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional


class AttackType(Enum):
    GPS_SPOOFING = "gps_spoofing"
    SIGNAL_JAMMING = "signal_jamming"
    REPLAY_ATTACK = "replay_attack"
    DEAUTH = "deauth"
    SENSOR_INJECTION = "sensor_injection"
    MAN_IN_THE_MIDDLE = "mitm"


class DefenseAction(Enum):
    SWITCH_IMU = "switch_imu"
    FREQ_HOP = "frequency_hop"
    INCREASE_POWER = "increase_power"
    AUTHENTICATE = "authenticate"
    ISOLATE = "isolate"
    ALERT = "alert"


@dataclass
class ThreatSignature:
    attack_type: AttackType
    confidence: float
    source_bearing: Optional[float] = None
    signal_strength: float = 0.0
    timestamp: float = 0.0


@dataclass
class DefenseEvent:
    threat: ThreatSignature
    action: DefenseAction
    success: bool
    response_time_ms: float


class AdversarialDefense:
    """Multi-layered adversarial defense for drone swarms."""

    def __init__(self, n_drones: int = 20, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_drones = n_drones
        self.threats_detected: List[ThreatSignature] = []
        self.defense_log: List[DefenseEvent] = []
        self.drone_trust: Dict[int, float] = {i: 1.0 for i in range(n_drones)}
        self.gps_baseline: Dict[int, np.ndarray] = {}
        self.time = 0.0

        for i in range(n_drones):
            self.gps_baseline[i] = self.rng.uniform(-100, 100, 3)

    def detect_gps_spoofing(self, drone_id: int, reported_pos: np.ndarray,
                            imu_pos: np.ndarray) -> Optional[ThreatSignature]:
        diff = np.linalg.norm(reported_pos - imu_pos)
        if diff > 5.0:
            confidence = min(1.0, diff / 20.0)
            threat = ThreatSignature(
                AttackType.GPS_SPOOFING, confidence,
                signal_strength=diff, timestamp=self.time)
            self.threats_detected.append(threat)
            self.drone_trust[drone_id] = max(0, self.drone_trust[drone_id] - 0.2)
            return threat
        return None

    def detect_jamming(self, drone_id: int, snr_db: float,
                       noise_floor_db: float = -90) -> Optional[ThreatSignature]:
        if snr_db < 5.0:
            confidence = min(1.0, (10.0 - snr_db) / 15.0)
            threat = ThreatSignature(
                AttackType.SIGNAL_JAMMING, confidence,
                signal_strength=noise_floor_db + 30, timestamp=self.time)
            self.threats_detected.append(threat)
            return threat
        return None

    def detect_replay(self, packet_timestamps: List[float],
                      window_s: float = 2.0) -> Optional[ThreatSignature]:
        if len(packet_timestamps) < 4:
            return None
        diffs = np.diff(sorted(packet_timestamps[-20:]))
        if len(diffs) > 2:
            std = np.std(diffs)
            if std < 0.001:
                threat = ThreatSignature(
                    AttackType.REPLAY_ATTACK, 0.8, timestamp=self.time)
                self.threats_detected.append(threat)
                return threat
        return None

    def respond_to_threat(self, threat: ThreatSignature) -> DefenseEvent:
        action_map = {
            AttackType.GPS_SPOOFING: DefenseAction.SWITCH_IMU,
            AttackType.SIGNAL_JAMMING: DefenseAction.FREQ_HOP,
            AttackType.REPLAY_ATTACK: DefenseAction.AUTHENTICATE,
            AttackType.DEAUTH: DefenseAction.INCREASE_POWER,
            AttackType.SENSOR_INJECTION: DefenseAction.ISOLATE,
            AttackType.MAN_IN_THE_MIDDLE: DefenseAction.AUTHENTICATE,
        }
        action = action_map.get(threat.attack_type, DefenseAction.ALERT)
        success_rate = 0.85 - threat.confidence * 0.2
        success = self.rng.random() < max(0.4, success_rate)
        response_time = self.rng.exponential(50) + 10

        event = DefenseEvent(threat, action, success, round(response_time, 1))
        self.defense_log.append(event)
        return event

    def run_scan(self) -> List[ThreatSignature]:
        """Scan all drones for potential threats."""
        self.time += 1.0
        threats = []
        for i in range(self.n_drones):
            reported = self.gps_baseline[i] + self.rng.standard_normal(3) * 0.5
            imu = self.gps_baseline[i] + self.rng.standard_normal(3) * 0.3
            if self.rng.random() < 0.05:
                reported += self.rng.uniform(5, 20, 3)
            t = self.detect_gps_spoofing(i, reported, imu)
            if t:
                threats.append(t)

            snr = self.rng.normal(20, 5)
            if self.rng.random() < 0.03:
                snr = self.rng.uniform(-5, 5)
            t = self.detect_jamming(i, snr)
            if t:
                threats.append(t)
        return threats

    def run_defense_cycle(self, n_cycles: int = 10) -> Dict:
        total_threats = 0
        total_defended = 0
        for _ in range(n_cycles):
            threats = self.run_scan()
            total_threats += len(threats)
            for t in threats:
                event = self.respond_to_threat(t)
                if event.success:
                    total_defended += 1
        return {
            "cycles": n_cycles,
            "threats_detected": total_threats,
            "successfully_defended": total_defended,
            "defense_rate": round(total_defended / max(total_threats, 1), 4),
        }

    def summary(self) -> Dict:
        return {
            "drones_monitored": self.n_drones,
            "total_threats": len(self.threats_detected),
            "defense_events": len(self.defense_log),
            "success_rate": round(
                sum(1 for e in self.defense_log if e.success) / max(len(self.defense_log), 1), 4),
            "avg_trust": round(float(np.mean(list(self.drone_trust.values()))), 4),
        }
