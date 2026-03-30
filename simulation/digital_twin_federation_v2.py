"""
Phase 476: Digital Twin Federation v2
분산 디지털 트윈 연합 — 동기화, 충돌 해소, 연합 쿼리.
"""

import hashlib
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Set


class SyncStatus(Enum):
    SYNCED = "synced"
    PENDING = "pending"
    CONFLICTED = "conflicted"
    STALE = "stale"


class ConflictResolution(Enum):
    LAST_WRITE_WINS = "lww"
    MERGE = "merge"
    PRIORITY = "priority"


@dataclass
class TwinState:
    twin_id: str
    version: int
    data: Dict
    timestamp: float
    node_id: str
    checksum: str = ""

    def compute_checksum(self) -> str:
        content = f"{self.twin_id}:{self.version}:{sorted(self.data.items())}"
        self.checksum = hashlib.sha256(content.encode()).hexdigest()[:16]
        return self.checksum


@dataclass
class FederationNode:
    node_id: str
    twins: Dict[str, TwinState] = field(default_factory=dict)
    peers: Set[str] = field(default_factory=set)
    is_leader: bool = False
    sync_count: int = 0


@dataclass
class SyncEvent:
    source: str
    target: str
    twin_id: str
    version: int
    status: SyncStatus
    timestamp: float


class DigitalTwinFederationV2:
    """Federated digital twin management across distributed nodes."""

    def __init__(self, conflict_resolution: ConflictResolution = ConflictResolution.LAST_WRITE_WINS,
                 seed: int = 42):
        self.cr = conflict_resolution
        self.rng = np.random.default_rng(seed)
        self.nodes: Dict[str, FederationNode] = {}
        self.sync_log: List[SyncEvent] = []
        self.conflicts_resolved = 0

    def add_node(self, node_id: str, is_leader: bool = False) -> FederationNode:
        node = FederationNode(node_id, is_leader=is_leader)
        self.nodes[node_id] = node
        for existing in self.nodes.values():
            if existing.node_id != node_id:
                existing.peers.add(node_id)
                node.peers.add(existing.node_id)
        return node

    def create_twin(self, node_id: str, twin_id: str, data: Dict, timestamp: float = 0) -> Optional[TwinState]:
        node = self.nodes.get(node_id)
        if not node:
            return None
        state = TwinState(twin_id, 1, data, timestamp, node_id)
        state.compute_checksum()
        node.twins[twin_id] = state
        return state

    def update_twin(self, node_id: str, twin_id: str, data: Dict, timestamp: float = 0) -> Optional[TwinState]:
        node = self.nodes.get(node_id)
        if not node or twin_id not in node.twins:
            return None
        old = node.twins[twin_id]
        new_state = TwinState(twin_id, old.version + 1, {**old.data, **data}, timestamp, node_id)
        new_state.compute_checksum()
        node.twins[twin_id] = new_state
        return new_state

    def sync_twin(self, source_id: str, target_id: str, twin_id: str) -> SyncStatus:
        source = self.nodes.get(source_id)
        target = self.nodes.get(target_id)
        if not source or not target:
            return SyncStatus.STALE

        src_twin = source.twins.get(twin_id)
        if not src_twin:
            return SyncStatus.STALE

        tgt_twin = target.twins.get(twin_id)
        if not tgt_twin:
            target.twins[twin_id] = TwinState(
                src_twin.twin_id, src_twin.version,
                dict(src_twin.data), src_twin.timestamp, target_id)
            target.twins[twin_id].compute_checksum()
            status = SyncStatus.SYNCED
        elif src_twin.checksum == tgt_twin.checksum:
            status = SyncStatus.SYNCED
        elif src_twin.version > tgt_twin.version:
            target.twins[twin_id] = TwinState(
                src_twin.twin_id, src_twin.version,
                dict(src_twin.data), src_twin.timestamp, target_id)
            target.twins[twin_id].compute_checksum()
            status = SyncStatus.SYNCED
        elif src_twin.version == tgt_twin.version:
            status = self._resolve_conflict(source, target, twin_id)
        else:
            status = SyncStatus.STALE

        source.sync_count += 1
        self.sync_log.append(SyncEvent(
            source_id, target_id, twin_id, src_twin.version, status, src_twin.timestamp))
        return status

    def _resolve_conflict(self, source: FederationNode, target: FederationNode,
                          twin_id: str) -> SyncStatus:
        self.conflicts_resolved += 1
        src = source.twins[twin_id]
        tgt = target.twins[twin_id]

        if self.cr == ConflictResolution.LAST_WRITE_WINS:
            if src.timestamp >= tgt.timestamp:
                target.twins[twin_id] = TwinState(
                    src.twin_id, src.version + 1, dict(src.data), src.timestamp, target.node_id)
            else:
                source.twins[twin_id] = TwinState(
                    tgt.twin_id, tgt.version + 1, dict(tgt.data), tgt.timestamp, source.node_id)
        elif self.cr == ConflictResolution.MERGE:
            merged = {**tgt.data, **src.data}
            new_version = max(src.version, tgt.version) + 1
            ts = max(src.timestamp, tgt.timestamp)
            for node in [source, target]:
                node.twins[twin_id] = TwinState(twin_id, new_version, merged, ts, node.node_id)
                node.twins[twin_id].compute_checksum()
        elif self.cr == ConflictResolution.PRIORITY:
            leader = source if source.is_leader else target
            follower = target if source.is_leader else source
            follower.twins[twin_id] = TwinState(
                leader.twins[twin_id].twin_id, leader.twins[twin_id].version + 1,
                dict(leader.twins[twin_id].data), leader.twins[twin_id].timestamp, follower.node_id)

        return SyncStatus.SYNCED

    def sync_all(self) -> Dict[str, int]:
        synced = 0
        conflicts = 0
        node_ids = list(self.nodes.keys())
        for i in range(len(node_ids)):
            for j in range(i + 1, len(node_ids)):
                src, tgt = node_ids[i], node_ids[j]
                all_twins = set(self.nodes[src].twins.keys()) | set(self.nodes[tgt].twins.keys())
                for twin_id in all_twins:
                    if twin_id in self.nodes[src].twins:
                        status = self.sync_twin(src, tgt, twin_id)
                        if status == SyncStatus.SYNCED:
                            synced += 1
                        elif status == SyncStatus.CONFLICTED:
                            conflicts += 1
        return {"synced": synced, "conflicts": conflicts}

    def query_federation(self, twin_id: str) -> List[Tuple]:
        results = []
        for node in self.nodes.values():
            twin = node.twins.get(twin_id)
            if twin:
                results.append((node.node_id, twin.version, twin.checksum))
        return results

    def summary(self) -> Dict:
        total_twins = sum(len(n.twins) for n in self.nodes.values())
        return {
            "nodes": len(self.nodes),
            "total_twin_instances": total_twins,
            "unique_twins": len(set(t for n in self.nodes.values() for t in n.twins)),
            "sync_events": len(self.sync_log),
            "conflicts_resolved": self.conflicts_resolved,
            "resolution_policy": self.cr.value,
        }


Tuple = tuple  # fix typing import
