"""
Phase 333: Digital Sovereignty Manager
데이터 주권 관리 — 지역별 데이터 라우팅 + 암호화 정책 적용.
GDPR/개인정보보호법 준수를 위한 데이터 분류 및 지역 제한.
"""

import hashlib
import time
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Set, Tuple


class DataClassification(Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    TOP_SECRET = "top_secret"


class EncryptionLevel(Enum):
    NONE = "none"
    AES128 = "aes128"
    AES256 = "aes256"
    POST_QUANTUM = "post_quantum"


class Region(Enum):
    KR = "kr"   # Korea
    US = "us"   # United States
    EU = "eu"   # European Union
    JP = "jp"   # Japan
    CN = "cn"   # China
    GLOBAL = "global"


@dataclass
class DataPolicy:
    classification: DataClassification
    allowed_regions: Set[Region]
    encryption: EncryptionLevel
    retention_days: int
    requires_consent: bool = False
    anonymize_pii: bool = False


@dataclass
class DataRecord:
    record_id: str
    source_region: Region
    classification: DataClassification
    payload_hash: str
    size_bytes: int
    timestamp: float
    encrypted: bool = False
    encryption_level: EncryptionLevel = EncryptionLevel.NONE
    routed_to: Optional[Region] = None


@dataclass
class ComplianceViolation:
    violation_id: str
    record_id: str
    rule: str
    severity: str  # warning, error, critical
    description: str
    timestamp: float


@dataclass
class AuditEntry:
    action: str
    record_id: str
    from_region: Region
    to_region: Optional[Region]
    timestamp: float
    compliant: bool


class DigitalSovereigntyManager:
    """Manages data sovereignty policies and compliance."""

    DEFAULT_POLICIES = {
        DataClassification.PUBLIC: DataPolicy(
            DataClassification.PUBLIC,
            {Region.GLOBAL}, EncryptionLevel.NONE, 365),
        DataClassification.INTERNAL: DataPolicy(
            DataClassification.INTERNAL,
            {Region.KR, Region.US, Region.EU, Region.JP},
            EncryptionLevel.AES128, 180),
        DataClassification.CONFIDENTIAL: DataPolicy(
            DataClassification.CONFIDENTIAL,
            {Region.KR}, EncryptionLevel.AES256, 90,
            requires_consent=True, anonymize_pii=True),
        DataClassification.RESTRICTED: DataPolicy(
            DataClassification.RESTRICTED,
            {Region.KR}, EncryptionLevel.AES256, 30,
            requires_consent=True, anonymize_pii=True),
        DataClassification.TOP_SECRET: DataPolicy(
            DataClassification.TOP_SECRET,
            {Region.KR}, EncryptionLevel.POST_QUANTUM, 7,
            requires_consent=True, anonymize_pii=True),
    }

    def __init__(self, home_region: Region = Region.KR, seed: int = 42):
        self.home_region = home_region
        self.rng = np.random.default_rng(seed)
        self.policies: Dict[DataClassification, DataPolicy] = dict(self.DEFAULT_POLICIES)
        self.records: Dict[str, DataRecord] = {}
        self.violations: List[ComplianceViolation] = []
        self.audit_log: List[AuditEntry] = []
        self._violation_counter = 0

    def set_policy(self, classification: DataClassification, policy: DataPolicy) -> None:
        self.policies[classification] = policy

    def ingest_data(self, record_id: str, source_region: Region,
                    classification: DataClassification,
                    payload: bytes, timestamp: Optional[float] = None) -> DataRecord:
        ts = timestamp or time.time()
        payload_hash = hashlib.sha256(payload).hexdigest()

        policy = self.policies[classification]
        enc_level = policy.encryption
        encrypted = enc_level != EncryptionLevel.NONE

        record = DataRecord(
            record_id=record_id,
            source_region=source_region,
            classification=classification,
            payload_hash=payload_hash,
            size_bytes=len(payload),
            timestamp=ts,
            encrypted=encrypted,
            encryption_level=enc_level,
        )
        self.records[record_id] = record

        self.audit_log.append(AuditEntry(
            action="ingest", record_id=record_id,
            from_region=source_region, to_region=None,
            timestamp=ts, compliant=True
        ))
        return record

    def route_data(self, record_id: str, target_region: Region) -> Tuple[bool, Optional[str]]:
        record = self.records.get(record_id)
        if not record:
            return False, "Record not found"

        policy = self.policies[record.classification]

        if Region.GLOBAL not in policy.allowed_regions and target_region not in policy.allowed_regions:
            self._add_violation(
                record_id, "region_restriction", "critical",
                f"Cannot route {record.classification.value} data to {target_region.value}"
            )
            self.audit_log.append(AuditEntry(
                action="route_denied", record_id=record_id,
                from_region=record.source_region, to_region=target_region,
                timestamp=time.time(), compliant=False
            ))
            return False, f"Region {target_region.value} not allowed"

        if policy.encryption != EncryptionLevel.NONE and not record.encrypted:
            self._add_violation(
                record_id, "encryption_required", "error",
                f"Data must be encrypted with {policy.encryption.value}"
            )
            return False, "Encryption required"

        record.routed_to = target_region
        self.audit_log.append(AuditEntry(
            action="route", record_id=record_id,
            from_region=record.source_region, to_region=target_region,
            timestamp=time.time(), compliant=True
        ))
        return True, None

    def check_compliance(self, record_id: str) -> List[str]:
        record = self.records.get(record_id)
        if not record:
            return ["Record not found"]

        issues = []
        policy = self.policies[record.classification]

        if policy.encryption != EncryptionLevel.NONE and not record.encrypted:
            issues.append(f"Missing encryption: {policy.encryption.value} required")

        if record.routed_to and record.routed_to not in policy.allowed_regions:
            if Region.GLOBAL not in policy.allowed_regions:
                issues.append(f"Region violation: {record.routed_to.value}")

        age_days = (time.time() - record.timestamp) / 86400
        if age_days > policy.retention_days:
            issues.append(f"Retention exceeded: {age_days:.0f} > {policy.retention_days} days")

        return issues

    def bulk_compliance_scan(self) -> Dict[str, List[str]]:
        results = {}
        for rid in self.records:
            issues = self.check_compliance(rid)
            if issues:
                results[rid] = issues
        return results

    def anonymize_record(self, record_id: str) -> bool:
        record = self.records.get(record_id)
        if not record:
            return False
        record.payload_hash = hashlib.sha256(
            record.payload_hash.encode() + b"_anonymized"
        ).hexdigest()
        self.audit_log.append(AuditEntry(
            action="anonymize", record_id=record_id,
            from_region=record.source_region, to_region=None,
            timestamp=time.time(), compliant=True
        ))
        return True

    def get_region_data_count(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for record in self.records.values():
            region = (record.routed_to or record.source_region).value
            counts[region] = counts.get(region, 0) + 1
        return counts

    def _add_violation(self, record_id: str, rule: str,
                       severity: str, description: str) -> None:
        self._violation_counter += 1
        self.violations.append(ComplianceViolation(
            violation_id=f"CV-{self._violation_counter:06d}",
            record_id=record_id, rule=rule,
            severity=severity, description=description,
            timestamp=time.time()
        ))

    def summary(self) -> Dict:
        return {
            "home_region": self.home_region.value,
            "total_records": len(self.records),
            "total_violations": len(self.violations),
            "audit_entries": len(self.audit_log),
            "encrypted_records": sum(1 for r in self.records.values() if r.encrypted),
            "region_distribution": self.get_region_data_count(),
        }


if __name__ == "__main__":
    mgr = DigitalSovereigntyManager(home_region=Region.KR)

    for i in range(10):
        cls = [DataClassification.PUBLIC, DataClassification.INTERNAL,
               DataClassification.CONFIDENTIAL][i % 3]
        mgr.ingest_data(f"rec_{i}", Region.KR, cls, f"data_{i}".encode(), timestamp=float(i))

    ok, err = mgr.route_data("rec_0", Region.US)
    print(f"Route public to US: {ok}")

    ok, err = mgr.route_data("rec_2", Region.US)
    print(f"Route confidential to US: {ok} ({err})")

    print(f"Summary: {mgr.summary()}")
