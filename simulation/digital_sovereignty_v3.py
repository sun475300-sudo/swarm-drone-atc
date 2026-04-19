"""
Phase 501: Digital Sovereignty V3
제로 트러스트 데이터 라우팅, 국가별 암호화 정책, 실시간 컴플라이언스 감사.
"""

import numpy as np
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Set


class DataClassification(Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    TOP_SECRET = "top_secret"


class Region(Enum):
    KR = "korea"
    US = "usa"
    EU = "eu"
    JP = "japan"
    CN = "china"
    NEUTRAL = "neutral"


class EncryptionStandard(Enum):
    AES256 = "aes_256"
    ARIA256 = "aria_256"       # 한국 국가 표준
    SM4 = "sm4"                # 중국 표준
    CAMELLIA = "camellia_256"  # 일본 선호
    QUANTUM_SAFE = "quantum_safe"


@dataclass
class DataPacket:
    packet_id: str
    classification: DataClassification
    origin_region: Region
    payload_hash: str
    size_bytes: int
    encryption: EncryptionStandard = EncryptionStandard.AES256
    route_log: List[str] = field(default_factory=list)
    compliant: bool = True


@dataclass
class SovereigntyPolicy:
    region: Region
    allowed_destinations: Set[Region]
    required_encryption: EncryptionStandard
    data_residency_required: bool = True
    audit_required: bool = True
    max_hop_count: int = 3


@dataclass
class AuditEntry:
    timestamp: float
    packet_id: str
    action: str
    region: Region
    compliant: bool
    details: str = ""


class ZeroTrustGateway:
    """Zero-trust data gateway with per-packet verification."""

    def __init__(self, region: Region, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.region = region
        self.trust_scores: Dict[str, float] = {}
        self.verified_sessions: Set[str] = set()

    def authenticate(self, entity_id: str, credential_hash: str) -> bool:
        expected = hashlib.sha256(f"{entity_id}:secret".encode()).hexdigest()[:16]
        verified = credential_hash[:8] == expected[:8] or self.rng.random() > 0.1
        if verified:
            self.verified_sessions.add(entity_id)
            self.trust_scores[entity_id] = min(1.0, self.trust_scores.get(entity_id, 0.5) + 0.1)
        else:
            self.trust_scores[entity_id] = max(0, self.trust_scores.get(entity_id, 0.5) - 0.2)
        return verified

    def authorize(self, entity_id: str, action: str) -> bool:
        if entity_id not in self.verified_sessions:
            return False
        trust = self.trust_scores.get(entity_id, 0)
        if action in ("read_public", "write_telemetry"):
            return trust > 0.2
        elif action in ("read_confidential", "write_control"):
            return trust > 0.6
        elif action == "admin":
            return trust > 0.9
        return trust > 0.5


class DigitalSovereigntyV3:
    """Advanced digital sovereignty with zero-trust architecture."""

    def __init__(self, home_region: Region = Region.KR, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.home_region = home_region
        self.gateway = ZeroTrustGateway(home_region, seed)
        self.policies: Dict[Region, SovereigntyPolicy] = {}
        self.audit_log: List[AuditEntry] = []
        self.packets_processed = 0
        self.violations = 0
        self.time = 0.0
        self._init_default_policies()

    def _init_default_policies(self):
        self.policies[Region.KR] = SovereigntyPolicy(
            Region.KR, {Region.KR, Region.US, Region.JP, Region.EU},
            EncryptionStandard.ARIA256, True, True)
        self.policies[Region.US] = SovereigntyPolicy(
            Region.US, {Region.US, Region.KR, Region.EU, Region.JP},
            EncryptionStandard.AES256, True, True)
        self.policies[Region.EU] = SovereigntyPolicy(
            Region.EU, {Region.EU, Region.KR, Region.US},
            EncryptionStandard.AES256, True, True, max_hop_count=2)
        self.policies[Region.CN] = SovereigntyPolicy(
            Region.CN, {Region.CN, Region.NEUTRAL},
            EncryptionStandard.SM4, True, True, max_hop_count=1)
        self.policies[Region.JP] = SovereigntyPolicy(
            Region.JP, {Region.JP, Region.KR, Region.US, Region.EU},
            EncryptionStandard.CAMELLIA, False, True)

    def route_data(self, packet: DataPacket, destination: Region) -> Dict:
        self.time += 0.01
        self.packets_processed += 1
        origin_policy = self.policies.get(packet.origin_region)
        compliant = True
        issues = []

        if origin_policy:
            if destination not in origin_policy.allowed_destinations:
                compliant = False
                issues.append(f"Destination {destination.value} not allowed from {packet.origin_region.value}")
            if packet.encryption != origin_policy.required_encryption:
                if packet.classification.value in ("confidential", "top_secret"):
                    compliant = False
                    issues.append(f"Encryption mismatch: {packet.encryption.value} vs {origin_policy.required_encryption.value}")
            if len(packet.route_log) >= origin_policy.max_hop_count:
                compliant = False
                issues.append(f"Max hops exceeded: {len(packet.route_log)} >= {origin_policy.max_hop_count}")

        packet.route_log.append(f"{self.home_region.value}->{destination.value}")
        packet.compliant = compliant

        if not compliant:
            self.violations += 1

        self.audit_log.append(AuditEntry(
            self.time, packet.packet_id,
            "route" if compliant else "block",
            destination, compliant,
            "; ".join(issues) if issues else "OK"))

        return {
            "packet_id": packet.packet_id,
            "routed": compliant,
            "destination": destination.value,
            "issues": issues,
            "hops": len(packet.route_log),
        }

    def create_packet(self, classification: DataClassification,
                      origin: Region, data: str) -> DataPacket:
        self.packets_processed += 1
        return DataPacket(
            f"PKT-{self.packets_processed:06d}",
            classification, origin,
            hashlib.sha256(data.encode()).hexdigest()[:16],
            len(data),
            self.policies.get(origin, SovereigntyPolicy(
                origin, set(), EncryptionStandard.AES256)).required_encryption)

    def compliance_score(self) -> float:
        if self.packets_processed == 0:
            return 1.0
        return round(1.0 - self.violations / self.packets_processed, 4)

    def summary(self) -> Dict:
        return {
            "home_region": self.home_region.value,
            "packets_processed": self.packets_processed,
            "violations": self.violations,
            "compliance_score": self.compliance_score(),
            "audit_entries": len(self.audit_log),
            "policies": len(self.policies),
        }
