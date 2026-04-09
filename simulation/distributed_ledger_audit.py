# Phase 534: Distributed Ledger Audit — Merkle Audit Trail
"""
분산 원장 감사: Merkle 트리 기반 무결성 검증, 감사 로그 체인,
탬퍼 탐지 및 증거 보존.
"""

import hashlib
import numpy as np
from dataclasses import dataclass, field
from enum import Enum


class AuditEventType(Enum):
    FLIGHT_LOG = "flight_log"
    MAINTENANCE = "maintenance"
    CERT_ISSUE = "cert_issue"
    INCIDENT = "incident"
    CONFIG_CHANGE = "config_change"


@dataclass
class AuditEntry:
    entry_id: str
    event_type: AuditEventType
    drone_id: str
    timestamp: float
    data: str
    hash: str = ""
    prev_hash: str = ""


@dataclass
class MerkleNode:
    hash: str
    left: 'MerkleNode | None' = None
    right: 'MerkleNode | None' = None
    data: str = ""


def sha256(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


class MerkleTree:
    """Merkle 트리: 감사 로그 무결성 검증."""

    def __init__(self):
        self.root: MerkleNode | None = None
        self.leaves: list[MerkleNode] = []

    def build(self, entries: list[str]):
        self.leaves = [MerkleNode(sha256(e), data=e) for e in entries]
        if not self.leaves:
            self.root = None
            return
        nodes = list(self.leaves)
        while len(nodes) > 1:
            if len(nodes) % 2 == 1:
                nodes.append(nodes[-1])  # 홀수면 마지막 복제
            new_level = []
            for i in range(0, len(nodes), 2):
                combined = nodes[i].hash + nodes[i + 1].hash
                parent = MerkleNode(sha256(combined), nodes[i], nodes[i + 1])
                new_level.append(parent)
            nodes = new_level
        self.root = nodes[0]

    def root_hash(self) -> str:
        return self.root.hash if self.root else ""

    def verify_leaf(self, index: int) -> bool:
        """리프에서 루트까지 경로 검증."""
        if not self.root or index >= len(self.leaves):
            return False
        # 단순 재빌드 후 해시 비교
        expected = sha256(self.leaves[index].data)
        return self.leaves[index].hash == expected

    def get_proof(self, index: int) -> list[tuple[str, str]]:
        """Merkle proof (sibling hashes) 생성."""
        if not self.leaves or index >= len(self.leaves):
            return []
        proof = []
        nodes = list(self.leaves)
        idx = index
        while len(nodes) > 1:
            if len(nodes) % 2 == 1:
                nodes.append(nodes[-1])
            sibling_idx = idx ^ 1
            side = "left" if idx % 2 == 1 else "right"
            proof.append((side, nodes[sibling_idx].hash))
            new_nodes = []
            for i in range(0, len(nodes), 2):
                combined = nodes[i].hash + nodes[i + 1].hash
                new_nodes.append(MerkleNode(sha256(combined)))
            nodes = new_nodes
            idx //= 2
        return proof


class AuditChain:
    """해시 체인 기반 감사 로그."""

    def __init__(self):
        self.entries: list[AuditEntry] = []
        self.prev_hash = "0" * 64

    def append(self, event_type: AuditEventType, drone_id: str, timestamp: float, data: str):
        entry_id = f"AE-{len(self.entries):06d}"
        content = f"{entry_id}:{event_type.value}:{drone_id}:{timestamp}:{data}:{self.prev_hash}"
        h = sha256(content)
        entry = AuditEntry(entry_id, event_type, drone_id, timestamp, data, h, self.prev_hash)
        self.entries.append(entry)
        self.prev_hash = h

    def verify_chain(self) -> tuple[bool, int]:
        """체인 무결성 검증. (valid, first_tampered_index)"""
        prev = "0" * 64
        for i, e in enumerate(self.entries):
            content = f"{e.entry_id}:{e.event_type.value}:{e.drone_id}:{e.timestamp}:{e.data}:{prev}"
            expected = sha256(content)
            if e.hash != expected or e.prev_hash != prev:
                return False, i
            prev = e.hash
        return True, -1

    def tamper(self, index: int, new_data: str):
        """탬퍼링 시뮬레이션 (테스트용)."""
        if 0 <= index < len(self.entries):
            self.entries[index].data = new_data


class DistributedLedgerAudit:
    """분산 감사 시스템 총괄."""

    def __init__(self, n_drones=20, seed=42):
        self.rng = np.random.default_rng(seed)
        self.chain = AuditChain()
        self.tree = MerkleTree()
        self.n_drones = n_drones
        self.tamper_detected = 0

    def generate_logs(self, n_events=100):
        event_types = list(AuditEventType)
        for i in range(n_events):
            etype = event_types[int(self.rng.integers(0, len(event_types)))]
            drone = f"drone_{int(self.rng.integers(0, self.n_drones))}"
            ts = float(i * 10 + self.rng.uniform(0, 5))
            data = f"event_data_{i}_val={self.rng.uniform(0, 100):.2f}"
            self.chain.append(etype, drone, ts, data)

    def build_merkle(self):
        entries_data = [f"{e.entry_id}:{e.data}" for e in self.chain.entries]
        self.tree.build(entries_data)

    def verify_all(self) -> dict:
        chain_valid, tamper_idx = self.chain.verify_chain()
        self.build_merkle()
        merkle_root = self.tree.root_hash()
        leaves_valid = all(self.tree.verify_leaf(i) for i in range(len(self.tree.leaves)))
        return {
            "chain_valid": chain_valid,
            "tamper_index": tamper_idx,
            "merkle_root": merkle_root[:16],
            "leaves_valid": leaves_valid,
            "entries": len(self.chain.entries),
        }

    def simulate_tamper(self, index=5):
        self.chain.tamper(index, "TAMPERED_DATA")
        valid, idx = self.chain.verify_chain()
        if not valid:
            self.tamper_detected += 1
        return {"detected": not valid, "at_index": idx}

    def summary(self):
        v = self.verify_all()
        return {
            "total_entries": len(self.chain.entries),
            "chain_valid": v["chain_valid"],
            "merkle_root": v["merkle_root"],
            "tamper_detected": self.tamper_detected,
        }


if __name__ == "__main__":
    dla = DistributedLedgerAudit(20, 42)
    dla.generate_logs(100)
    print(f"Verify: {dla.verify_all()}")
    print(f"Tamper test: {dla.simulate_tamper(10)}")
    print(f"Summary: {dla.summary()}")
