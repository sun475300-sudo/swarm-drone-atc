"""
감사 추적 시스템
===============
불변 로그 체인 + 타임스탬프 검증 + 무결성 해시.

사용법:
    at = AuditTrail()
    at.log_event("d1", "TAKEOFF", details={"pad": "A1"})
    chain_valid = at.verify_chain()
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import hashlib


@dataclass
class AuditEntry:
    """감사 항목"""
    seq: int
    actor: str
    action: str
    details: dict[str, Any]
    t: float
    prev_hash: str
    entry_hash: str


class AuditTrail:
    """불변 감사 추적."""

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []
        self._seq = 0

    def _compute_hash(self, seq: int, actor: str, action: str, details: dict, t: float, prev_hash: str) -> str:
        data = f"{seq}:{actor}:{action}:{details}:{t}:{prev_hash}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]

    def log_event(self, actor: str, action: str, details: dict[str, Any] | None = None, t: float = 0.0) -> AuditEntry:
        self._seq += 1
        prev_hash = self._entries[-1].entry_hash if self._entries else "0" * 32

        entry_hash = self._compute_hash(self._seq, actor, action, details or {}, t, prev_hash)

        entry = AuditEntry(
            seq=self._seq, actor=actor, action=action,
            details=details or {}, t=t,
            prev_hash=prev_hash, entry_hash=entry_hash,
        )
        self._entries.append(entry)
        return entry

    def verify_chain(self) -> bool:
        """체인 무결성 검증"""
        if not self._entries:
            return True

        for i, entry in enumerate(self._entries):
            expected_prev = self._entries[i - 1].entry_hash if i > 0 else "0" * 32
            if entry.prev_hash != expected_prev:
                return False

            expected_hash = self._compute_hash(
                entry.seq, entry.actor, entry.action,
                entry.details, entry.t, entry.prev_hash,
            )
            if entry.entry_hash != expected_hash:
                return False

        return True

    def query(
        self, actor: str | None = None,
        action: str | None = None, n: int = 50,
    ) -> list[AuditEntry]:
        entries = self._entries
        if actor:
            entries = [e for e in entries if e.actor == actor]
        if action:
            entries = [e for e in entries if e.action == action]
        return entries[-n:]

    def actions_by_actor(self, actor: str) -> list[str]:
        return list(set(e.action for e in self._entries if e.actor == actor))

    def entry_count(self) -> int:
        return len(self._entries)

    def summary(self) -> dict[str, Any]:
        return {
            "entries": len(self._entries),
            "chain_valid": self.verify_chain(),
            "actors": len(set(e.actor for e in self._entries)),
            "actions": len(set(e.action for e in self._entries)),
        }
