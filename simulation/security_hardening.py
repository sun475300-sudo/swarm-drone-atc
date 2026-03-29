"""Security Hardening Module for Phase 240-259.

Provides security enhancements for drone swarm ATC.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import numpy as np


class ThreatLevel(Enum):
    """Threat levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AttackType(Enum):
    """Types of security attacks."""

    SPOOFING = "spoofing"
    TAMPERING = "tampering"
    REPLAY = "replay"
    DOS = "denial_of_service"
    MITM = "man_in_the_middle"
    JAMMING = "jamming"


@dataclass
class SecurityEvent:
    """Security event record."""

    event_id: str
    attack_type: AttackType
    threat_level: ThreatLevel
    source_id: str
    timestamp: float = field(default_factory=time.time)
    blocked: bool = False


class SecurityManager:
    """Manages security hardening."""

    def __init__(self):
        self.events: list[SecurityEvent] = []
        self.blocked_ids: set = set()
        self.auth_tokens: dict = {}
        self.event_counter = 0

    def authenticate(self, entity_id: str, token: str) -> bool:
        """Authenticate an entity."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        self.auth_tokens[entity_id] = {
            "token": token_hash,
            "issued_at": time.time(),
        }
        return True

    def verify_signature(self, data: bytes, signature: str) -> bool:
        """Verify data signature."""
        expected = hashlib.sha256(data).hexdigest()
        return signature == expected

    def detect_threat(self, source_id: str, activity_type: str) -> ThreatLevel:
        """Detect potential threats."""
        if source_id in self.blocked_ids:
            return ThreatLevel.CRITICAL

        if activity_type == "rapid_reconnection":
            return ThreatLevel.HIGH

        return ThreatLevel.LOW

    def block_entity(self, entity_id: str) -> None:
        """Block a malicious entity."""
        self.blocked_ids.add(entity_id)
        self.event_counter += 1
        event = SecurityEvent(
            event_id=f"evt_{self.event_counter}",
            attack_type=AttackType.SPOOFING,
            threat_level=ThreatLevel.CRITICAL,
            source_id=entity_id,
            blocked=True,
        )
        self.events.append(event)

    def get_security_stats(self) -> dict:
        """Get security statistics."""
        return {
            "total_events": len(self.events),
            "blocked_count": len(self.blocked_ids),
            "critical_threats": sum(
                1 for e in self.events if e.threat_level == ThreatLevel.CRITICAL
            ),
        }


def create_secure_manager() -> SecurityManager:
    """Create security manager with defaults."""
    return SecurityManager()
