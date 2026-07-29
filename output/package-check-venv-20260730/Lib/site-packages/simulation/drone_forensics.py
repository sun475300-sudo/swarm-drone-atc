"""
Phase 506: Drone Forensics
비행 기록 분석, 사고 재구성, 디지털 포렌식 체인.
"""

import hashlib
from dataclasses import dataclass, field
from enum import Enum

import numpy as np


class IncidentType(Enum):
    """``IncidentType`` 관련 기능을 제공한다."""
    CRASH = "crash"
    NEAR_MISS = "near_miss"
    GEOFENCE_BREACH = "geofence_breach"
    COMM_LOSS = "comm_loss"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    SENSOR_FAILURE = "sensor_failure"


class EvidenceType(Enum):
    """``EvidenceType`` 관련 기능을 제공한다."""
    FLIGHT_LOG = "flight_log"
    TELEMETRY = "telemetry"
    VIDEO = "video"
    SENSOR_DATA = "sensor_data"
    COMM_LOG = "comm_log"
    FIRMWARE_DUMP = "firmware_dump"


@dataclass
class FlightRecord:
    """``FlightRecord`` 데이터를 표현한다."""
    timestamp: float
    position: np.ndarray
    velocity: np.ndarray
    battery: float
    status: str
    sensors: dict[str, float] = field(default_factory=dict)


@dataclass
class Evidence:
    """``Evidence`` 관련 기능을 제공한다."""
    evidence_id: str
    etype: EvidenceType
    drone_id: str
    timestamp: float
    data_hash: str
    chain_hash: str = ""
    tamper_proof: bool = True


@dataclass
class ForensicReport:
    """``ForensicReport`` 관련 기능을 제공한다."""
    incident_id: str
    incident_type: IncidentType
    drone_id: str
    timeline: list[FlightRecord]
    evidence_chain: list[Evidence]
    root_cause: str
    confidence: float


class EvidenceChain:
    """Tamper-proof evidence chain using hash linking."""

    def __init__(self):
        """인스턴스를 초기화한다."""
        self.chain: list[Evidence] = []
        self._counter = 0

    def add(self, etype: EvidenceType, drone_id: str,
            data: str, timestamp: float) -> Evidence:
        """`대상` 항목을 추가한다."""
        self._counter += 1
        data_hash = hashlib.sha256(data.encode()).hexdigest()[:16]
        prev_hash = self.chain[-1].chain_hash if self.chain else "GENESIS"
        chain_hash = hashlib.sha256(f"{prev_hash}:{data_hash}".encode()).hexdigest()[:16]
        evidence = Evidence(f"EV-{self._counter:05d}", etype, drone_id,
                          timestamp, data_hash, chain_hash)
        self.chain.append(evidence)
        return evidence

    def verify(self) -> bool:
        """`대상` 결과를 계산하거나 판정한다."""
        prev_hash = "GENESIS"
        for ev in self.chain:
            expected = hashlib.sha256(f"{prev_hash}:{ev.data_hash}".encode()).hexdigest()[:16]
            if ev.chain_hash != expected:
                return False
            prev_hash = ev.chain_hash
        return True


class DroneForensics:
    """Digital forensics system for drone incident investigation."""

    def __init__(self, seed: int = 42):
        """인스턴스를 초기화한다."""
        self.rng = np.random.default_rng(seed)
        self.flight_logs: dict[str, list[FlightRecord]] = {}
        self.evidence_chains: dict[str, EvidenceChain] = {}
        self.reports: list[ForensicReport] = []
        self._incident_counter = 0

    def record_flight(self, drone_id: str, record: FlightRecord):
        """`flight` 정보를 기록한다."""
        if drone_id not in self.flight_logs:
            self.flight_logs[drone_id] = []
        self.flight_logs[drone_id].append(record)

    def simulate_flight(self, drone_id: str, duration: float = 60,
                        dt: float = 1.0) -> list[FlightRecord]:
        """``simulate_flight`` 동작을 수행한다."""
        records = []
        pos = self.rng.uniform(-100, 100, 3)
        pos[2] = 50
        vel = self.rng.standard_normal(3) * 2
        battery = 95.0

        for t in np.arange(0, duration, dt):
            vel += self.rng.standard_normal(3) * 0.5
            pos = pos + vel * dt
            battery -= self.rng.uniform(0.01, 0.05)
            record = FlightRecord(t, pos.copy(), vel.copy(), round(battery, 1), "nominal",
                                {"altitude": pos[2], "speed": np.linalg.norm(vel)})
            records.append(record)
            self.record_flight(drone_id, record)
        return records

    def investigate(self, drone_id: str, incident_type: IncidentType,
                    incident_time: float = None) -> ForensicReport:
        """``investigate`` 동작을 수행한다."""
        self._incident_counter += 1
        logs = self.flight_logs.get(drone_id, [])

        chain = EvidenceChain()
        self.evidence_chains[drone_id] = chain
        chain.add(EvidenceType.FLIGHT_LOG, drone_id,
                 f"flight_log_{len(logs)}_records", incident_time or 0)
        chain.add(EvidenceType.TELEMETRY, drone_id,
                 "telemetry_snapshot", incident_time or 0)
        chain.add(EvidenceType.SENSOR_DATA, drone_id,
                 "sensor_dump", incident_time or 0)

        root_cause = self._determine_root_cause(logs, incident_type)
        confidence = self.rng.uniform(0.6, 0.95)

        report = ForensicReport(
            f"INC-{self._incident_counter:04d}", incident_type, drone_id,
            logs[-10:] if logs else [], chain.chain, root_cause, round(confidence, 3))
        self.reports.append(report)
        return report

    def _determine_root_cause(self, logs: list[FlightRecord],
                              incident_type: IncidentType) -> str:
        causes = {
            IncidentType.CRASH: ["Motor failure", "Battery depletion", "Control system error",
                                "Wind gust exceeded limits", "Structural failure"],
            IncidentType.NEAR_MISS: ["Late conflict detection", "Inadequate separation",
                                    "Communication delay", "Path planning error"],
            IncidentType.GEOFENCE_BREACH: ["GPS drift", "Geofence misconfiguration",
                                          "Wind displacement", "Operator error"],
            IncidentType.COMM_LOSS: ["Signal interference", "Antenna failure",
                                    "Range exceeded", "Jamming detected"],
            IncidentType.SENSOR_FAILURE: ["Calibration drift", "Hardware degradation",
                                         "EMI interference", "Firmware bug"],
        }
        options = causes.get(incident_type, ["Unknown cause"])
        return self.rng.choice(options)

    def summary(self) -> dict:
        """현재 상태 요약을 반환한다."""
        return {
            "drones_recorded": len(self.flight_logs),
            "total_records": sum(len(v) for v in self.flight_logs.values()),
            "investigations": len(self.reports),
            "evidence_chains": len(self.evidence_chains),
            "chain_integrity": all(c.verify() for c in self.evidence_chains.values()),
        }
