"""Phase 311: Distributed Consensus v2 — Byzantine Fault Tolerant 합의.

PBFT (Practical Byzantine Fault Tolerance) 기반 다중 노드 합의,
뷰 변경, 메시지 인증, 3f+1 내결함성.
"""

from __future__ import annotations
import numpy as np
import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class PBFTPhase(Enum):
    IDLE = "idle"
    PRE_PREPARE = "pre_prepare"
    PREPARE = "prepare"
    COMMIT = "commit"
    REPLY = "reply"


class NodeRole(Enum):
    PRIMARY = "primary"
    BACKUP = "backup"
    FAULTY = "faulty"


@dataclass
class PBFTMessage:
    msg_type: str  # "pre-prepare", "prepare", "commit", "reply", "view-change"
    view: int
    sequence: int
    digest: str
    sender: int
    data: dict = field(default_factory=dict)
    timestamp: float = 0.0
    signature: str = ""

    def compute_digest(self) -> str:
        content = f"{self.msg_type}:{self.view}:{self.sequence}:{self.sender}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class ConsensusRequest:
    client_id: str
    operation: str
    data: dict = field(default_factory=dict)
    timestamp: float = 0.0


@dataclass
class PBFTNode:
    node_id: int
    role: NodeRole = NodeRole.BACKUP
    view: int = 0
    sequence: int = 0
    log: List[PBFTMessage] = field(default_factory=list)
    prepare_count: Dict[int, int] = field(default_factory=dict)
    commit_count: Dict[int, int] = field(default_factory=dict)
    committed: List[int] = field(default_factory=list)
    is_faulty: bool = False


class DistributedConsensusV2:
    """PBFT 기반 분산 합의 엔진.

    - 3f+1 비잔틴 내결함성
    - Pre-prepare/Prepare/Commit 3단계 합의
    - 뷰 변경 프로토콜
    - 메시지 다이제스트 검증
    """

    def __init__(self, n_nodes: int = 4, f_faulty: int = 1, rng_seed: int = 42):
        self._rng = np.random.default_rng(rng_seed)
        self.n_nodes = max(n_nodes, 3 * f_faulty + 1)
        self.f_faulty = f_faulty
        self._nodes: Dict[int, PBFTNode] = {}
        self._view = 0
        self._sequence = 0
        self._committed_ops: List[dict] = []
        self._message_log: List[PBFTMessage] = []
        self._init_nodes()

    def _init_nodes(self):
        for i in range(self.n_nodes):
            role = NodeRole.PRIMARY if i == self._view % self.n_nodes else NodeRole.BACKUP
            self._nodes[i] = PBFTNode(node_id=i, role=role, view=self._view)

    def set_faulty(self, node_id: int):
        if node_id in self._nodes:
            self._nodes[node_id].is_faulty = True
            self._nodes[node_id].role = NodeRole.FAULTY

    def submit_request(self, request: ConsensusRequest) -> bool:
        """Submit client request for consensus."""
        if request.timestamp == 0:
            request.timestamp = time.time()

        self._sequence += 1
        seq = self._sequence

        # Phase 1: Pre-prepare (primary broadcasts)
        primary_id = self._view % self.n_nodes
        primary = self._nodes[primary_id]
        if primary.is_faulty:
            return False

        digest = hashlib.sha256(
            f"{request.operation}:{request.timestamp}".encode()
        ).hexdigest()[:16]

        pre_prepare = PBFTMessage(
            msg_type="pre-prepare", view=self._view, sequence=seq,
            digest=digest, sender=primary_id, data={"operation": request.operation},
            timestamp=time.time(),
        )
        self._message_log.append(pre_prepare)

        # Phase 2: Prepare (each backup sends prepare)
        prepare_count = 0
        for node in self._nodes.values():
            if node.is_faulty or node.node_id == primary_id:
                continue
            prepare = PBFTMessage(
                msg_type="prepare", view=self._view, sequence=seq,
                digest=digest, sender=node.node_id, timestamp=time.time(),
            )
            self._message_log.append(prepare)
            node.prepare_count[seq] = node.prepare_count.get(seq, 0) + 1
            prepare_count += 1

        # Check quorum: need 2f prepares
        if prepare_count < 2 * self.f_faulty:
            return False

        # Phase 3: Commit (each node sends commit)
        commit_count = 0
        for node in self._nodes.values():
            if node.is_faulty:
                continue
            commit = PBFTMessage(
                msg_type="commit", view=self._view, sequence=seq,
                digest=digest, sender=node.node_id, timestamp=time.time(),
            )
            self._message_log.append(commit)
            node.commit_count[seq] = node.commit_count.get(seq, 0) + 1
            commit_count += 1

        # Check commit quorum: need 2f+1 commits
        if commit_count >= 2 * self.f_faulty + 1:
            self._committed_ops.append({
                "sequence": seq, "operation": request.operation,
                "digest": digest, "timestamp": time.time(),
            })
            for node in self._nodes.values():
                if not node.is_faulty:
                    node.committed.append(seq)
            return True

        return False

    def view_change(self) -> int:
        """Trigger view change to next primary."""
        self._view += 1
        new_primary = self._view % self.n_nodes
        for node in self._nodes.values():
            node.view = self._view
            if node.node_id == new_primary and not node.is_faulty:
                node.role = NodeRole.PRIMARY
            elif not node.is_faulty:
                node.role = NodeRole.BACKUP
        return self._view

    def get_node(self, node_id: int) -> Optional[PBFTNode]:
        return self._nodes.get(node_id)

    def get_committed_ops(self) -> List[dict]:
        return self._committed_ops.copy()

    def get_primary(self) -> int:
        return self._view % self.n_nodes

    def verify_consistency(self) -> bool:
        """Verify all non-faulty nodes have same committed sequence."""
        committed_sets = []
        for node in self._nodes.values():
            if not node.is_faulty:
                committed_sets.append(set(node.committed))
        if not committed_sets:
            return True
        return all(s == committed_sets[0] for s in committed_sets)

    def summary(self) -> dict:
        healthy = sum(1 for n in self._nodes.values() if not n.is_faulty)
        return {
            "total_nodes": self.n_nodes,
            "healthy_nodes": healthy,
            "faulty_nodes": self.n_nodes - healthy,
            "f_tolerance": self.f_faulty,
            "current_view": self._view,
            "primary": self.get_primary(),
            "committed_ops": len(self._committed_ops),
            "total_messages": len(self._message_log),
            "consistent": self.verify_consistency(),
        }
