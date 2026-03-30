"""Phase 306: Blockchain Audit Trail — 블록체인 감사 추적.

이벤트 불변 로깅, 해시 체인 무결성 검증,
타임스탬프 증명, 감사 쿼리 인터페이스.
"""

from __future__ import annotations
import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Block:
    index: int
    timestamp: float
    data: dict
    previous_hash: str
    nonce: int = 0
    hash: str = ""

    def compute_hash(self) -> str:
        content = json.dumps({
            "index": self.index, "timestamp": self.timestamp,
            "data": self.data, "previous_hash": self.previous_hash,
            "nonce": self.nonce,
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class AuditEvent:
    event_type: str  # "command", "state_change", "alert", "decision", "config_change"
    actor: str
    description: str
    data: dict = field(default_factory=dict)
    timestamp: float = 0.0


class BlockchainAuditTrail:
    """블록체인 감사 추적 시스템.

    - 이벤트 불변 기록 (해시 체인)
    - 무결성 검증
    - 이벤트 타입/액터별 쿼리
    - Proof-of-Work (간이)
    """

    DIFFICULTY = 2  # Number of leading zeros

    def __init__(self):
        self._chain: List[Block] = []
        self._pending: List[AuditEvent] = []
        self._create_genesis()

    def _create_genesis(self):
        genesis = Block(index=0, timestamp=time.time(), data={"type": "genesis"}, previous_hash="0" * 64)
        genesis.hash = genesis.compute_hash()
        self._chain.append(genesis)

    def record_event(self, event: AuditEvent) -> str:
        if event.timestamp == 0:
            event.timestamp = time.time()
        self._pending.append(event)
        block = self._mine_block({"event": event.event_type, "actor": event.actor,
                                  "description": event.description, "data": event.data,
                                  "event_timestamp": event.timestamp})
        return block.hash

    def _mine_block(self, data: dict) -> Block:
        prev = self._chain[-1]
        block = Block(
            index=len(self._chain), timestamp=time.time(),
            data=data, previous_hash=prev.hash,
        )
        # Simple proof-of-work
        target = "0" * self.DIFFICULTY
        while True:
            block.hash = block.compute_hash()
            if block.hash.startswith(target):
                break
            block.nonce += 1
        self._chain.append(block)
        return block

    def verify_chain(self) -> bool:
        for i in range(1, len(self._chain)):
            current = self._chain[i]
            previous = self._chain[i - 1]
            if current.hash != current.compute_hash():
                return False
            if current.previous_hash != previous.hash:
                return False
        return True

    def query_by_type(self, event_type: str) -> List[Block]:
        return [b for b in self._chain[1:] if b.data.get("event") == event_type]

    def query_by_actor(self, actor: str) -> List[Block]:
        return [b for b in self._chain[1:] if b.data.get("actor") == actor]

    def query_by_time_range(self, start: float, end: float) -> List[Block]:
        return [b for b in self._chain[1:] if start <= b.timestamp <= end]

    def get_block(self, index: int) -> Optional[Block]:
        if 0 <= index < len(self._chain):
            return self._chain[index]
        return None

    def get_latest_block(self) -> Block:
        return self._chain[-1]

    @property
    def chain_length(self) -> int:
        return len(self._chain)

    def export_chain(self) -> List[dict]:
        return [{
            "index": b.index, "timestamp": b.timestamp, "hash": b.hash,
            "previous_hash": b.previous_hash, "data": b.data, "nonce": b.nonce,
        } for b in self._chain]

    def summary(self) -> dict:
        event_types = {}
        for b in self._chain[1:]:
            et = b.data.get("event", "unknown")
            event_types[et] = event_types.get(et, 0) + 1
        return {
            "chain_length": len(self._chain),
            "is_valid": self.verify_chain(),
            "event_types": event_types,
            "latest_hash": self._chain[-1].hash[:16] + "...",
            "pending_events": len(self._pending),
        }
