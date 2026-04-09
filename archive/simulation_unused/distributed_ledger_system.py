"""
Phase 413: Distributed Ledger System
Distributed ledger for drone swarm data management and synchronization.
"""

import hashlib
import json
import time
import numpy as np
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Optional, Tuple, Any, Set
from collections import defaultdict


class LedgerType(Enum):
    """Ledger types."""

    PUBLIC = auto()
    PRIVATE = auto()
    CONSORTIUM = auto()
    PERMISSIONED = auto()


class SyncStatus(Enum):
    """Synchronization status."""

    SYNCED = auto()
    SYNCING = auto()
    OUT_OF_SYNC = auto()
    CONFLICT = auto()


@dataclass
class LedgerEntry:
    """Ledger entry."""

    entry_id: str
    data: Dict[str, Any]
    timestamp: float
    owner: str
    signature: str = ""
    version: int = 1
    hash: str = ""

    def compute_hash(self) -> str:
        content = json.dumps(
            {
                "entry_id": self.entry_id,
                "data": self.data,
                "timestamp": self.timestamp,
                "owner": self.owner,
                "version": self.version,
            },
            sort_keys=True,
        )
        return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class LedgerPage:
    """Ledger page containing multiple entries."""

    page_id: int
    entries: List[LedgerEntry]
    previous_hash: str
    timestamp: float = field(default_factory=time.time)
    hash: str = ""
    merkle_root: str = ""

    def compute_merkle_root(self) -> str:
        if not self.entries:
            return hashlib.sha256(b"empty").hexdigest()
        hashes = [e.compute_hash() for e in self.entries]
        while len(hashes) > 1:
            if len(hashes) % 2 != 0:
                hashes.append(hashes[-1])
            new_hashes = []
            for i in range(0, len(hashes), 2):
                combined = hashes[i] + hashes[i + 1]
                new_hashes.append(hashlib.sha256(combined.encode()).hexdigest())
            hashes = new_hashes
        return hashes[0]

    def compute_hash(self) -> str:
        content = json.dumps(
            {
                "page_id": self.page_id,
                "merkle_root": self.merkle_root,
                "previous_hash": self.previous_hash,
                "timestamp": self.timestamp,
            },
            sort_keys=True,
        )
        return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class PeerNode:
    """Peer node in distributed ledger."""

    node_id: str
    address: Tuple[str, int]
    is_active: bool = True
    last_sync: float = 0.0
    ledger_version: int = 0
    reputation: float = 1.0


class DistributedLedger:
    """Distributed ledger implementation."""

    def __init__(
        self,
        ledger_type: LedgerType = LedgerType.PERMISSIONED,
        page_size: int = 10,
        seed: int = 42,
    ):
        self.ledger_type = ledger_type
        self.page_size = page_size
        self.rng = np.random.default_rng(seed)
        self.pages: List[LedgerPage] = []
        self.pending_entries: List[LedgerEntry] = []
        self.peers: Dict[str, PeerNode] = {}
        self.index: Dict[str, int] = {}
        self._create_genesis_page()

    def _create_genesis_page(self) -> None:
        genesis = LedgerPage(page_id=0, entries=[], previous_hash="0" * 64)
        genesis.merkle_root = genesis.compute_merkle_root()
        genesis.hash = genesis.compute_hash()
        self.pages.append(genesis)

    def add_peer(self, node_id: str, address: Tuple[str, int]) -> None:
        self.peers[node_id] = PeerNode(node_id, address)

    def remove_peer(self, node_id: str) -> None:
        if node_id in self.peers:
            self.peers[node_id].is_active = False

    def add_entry(self, data: Dict[str, Any], owner: str) -> LedgerEntry:
        entry_id = hashlib.sha256(
            f"{json.dumps(data, sort_keys=True)}{owner}{time.time()}".encode()
        ).hexdigest()[:16]
        entry = LedgerEntry(
            entry_id=entry_id, data=data, timestamp=time.time(), owner=owner
        )
        entry.hash = entry.compute_hash()
        self.pending_entries.append(entry)
        self.index[entry_id] = len(self.pages)
        return entry

    def commit_page(self) -> Optional[LedgerPage]:
        if not self.pending_entries:
            return None
        entries = self.pending_entries[: self.page_size]
        self.pending_entries = self.pending_entries[self.page_size :]
        page = LedgerPage(
            page_id=len(self.pages), entries=entries, previous_hash=self.pages[-1].hash
        )
        page.merkle_root = page.compute_merkle_root()
        page.hash = page.compute_hash()
        self.pages.append(page)
        self._sync_peers()
        return page

    def _sync_peers(self) -> None:
        for peer in self.peers.values():
            if peer.is_active:
                peer.last_sync = time.time()
                peer.ledger_version = len(self.pages)

    def query_entries(
        self, filters: Optional[Dict[str, Any]] = None, owner: Optional[str] = None
    ) -> List[LedgerEntry]:
        results = []
        for page in self.pages:
            for entry in page.entries:
                if owner and entry.owner != owner:
                    continue
                if filters:
                    match = all(entry.data.get(k) == v for k, v in filters.items())
                    if not match:
                        continue
                results.append(entry)
        return results

    def get_entry_by_id(self, entry_id: str) -> Optional[LedgerEntry]:
        for page in self.pages:
            for entry in page.entries:
                if entry.entry_id == entry_id:
                    return entry
        return None

    def verify_integrity(self) -> bool:
        for i in range(1, len(self.pages)):
            current = self.pages[i]
            previous = self.pages[i - 1]
            if current.previous_hash != previous.hash:
                return False
            if current.compute_hash() != current.hash:
                return False
            if current.compute_merkle_root() != current.merkle_root:
                return False
        return True

    def get_stats(self) -> Dict[str, Any]:
        total_entries = sum(len(p.entries) for p in self.pages)
        return {
            "total_pages": len(self.pages),
            "total_entries": total_entries,
            "pending_entries": len(self.pending_entries),
            "active_peers": sum(1 for p in self.peers.values() if p.is_active),
            "is_valid": self.verify_integrity(),
        }


class DroneLedgerManager:
    """Ledger manager for drone operations."""

    def __init__(self, seed: int = 42):
        self.ledger = DistributedLedger(LedgerType.PERMISSIONED, seed=seed)
        self.drone_registry: Dict[str, Dict[str, Any]] = {}
        self.flight_logs: Dict[str, List[Dict]] = defaultdict(list)
        self.airspace_records: Dict[str, List[Dict]] = defaultdict(list)

    def register_drone(self, drone_id: str, owner: str, specs: Dict[str, Any]) -> str:
        data = {
            "type": "drone_registration",
            "drone_id": drone_id,
            "owner": owner,
            "specs": specs,
        }
        entry = self.ledger.add_entry(data, owner)
        self.drone_registry[drone_id] = {
            "owner": owner,
            "specs": specs,
            "registered_at": time.time(),
            "entry_id": entry.entry_id,
        }
        self.ledger.commit_page()
        return entry.entry_id

    def log_flight(
        self,
        drone_id: str,
        position: List[float],
        altitude: float,
        speed: float,
        battery: float,
    ) -> str:
        data = {
            "type": "flight_log",
            "drone_id": drone_id,
            "position": position,
            "altitude": altitude,
            "speed": speed,
            "battery": battery,
            "timestamp": time.time(),
        }
        owner = self.drone_registry.get(drone_id, {}).get("owner", "unknown")
        entry = self.ledger.add_entry(data, owner)
        self.flight_logs[drone_id].append(data)
        if len(self.ledger.pending_entries) >= self.ledger.page_size:
            self.ledger.commit_page()
        return entry.entry_id

    def record_airspace_usage(self, zone_id: str, drone_id: str, action: str) -> str:
        data = {
            "type": "airspace_usage",
            "zone_id": zone_id,
            "drone_id": drone_id,
            "action": action,
            "timestamp": time.time(),
        }
        owner = self.drone_registry.get(drone_id, {}).get("owner", "unknown")
        entry = self.ledger.add_entry(data, owner)
        self.airspace_records[zone_id].append(data)
        return entry.entry_id

    def get_drone_history(self, drone_id: str) -> List[Dict[str, Any]]:
        return self.ledger.query_entries({"drone_id": drone_id})

    def get_zone_history(self, zone_id: str) -> List[Dict[str, Any]]:
        return self.ledger.query_entries({"zone_id": zone_id})

    def get_ledger_stats(self) -> Dict[str, Any]:
        stats = self.ledger.get_stats()
        stats["registered_drones"] = len(self.drone_registry)
        stats["flight_logs"] = sum(len(v) for v in self.flight_logs.values())
        return stats


if __name__ == "__main__":
    manager = DroneLedgerManager(seed=42)
    manager.register_drone("D001", "owner1", {"type": "delivery", "max_speed": 20})
    manager.register_drone("D002", "owner2", {"type": "surveillance", "max_speed": 15})
    for i in range(15):
        manager.log_flight("D001", [100 + i, 200, 50], 50, 15, 85 - i)
    manager.record_airspace_usage("ZONE_A", "D001", "enter")
    print(f"Stats: {manager.get_ledger_stats()}")
    print(f"D001 history: {len(manager.get_drone_history('D001'))} entries")
