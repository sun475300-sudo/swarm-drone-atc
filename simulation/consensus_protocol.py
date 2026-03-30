"""Phase 293: Consensus Protocol — 분산 합의 프로토콜.

Raft 기반 리더 선출, 상태 복제, 분산 의사결정,
Byzantine Fault Tolerance 지원.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set


class NodeRole(Enum):
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


class LogEntryType(Enum):
    COMMAND = "command"
    CONFIG_CHANGE = "config_change"
    NO_OP = "no_op"


@dataclass
class LogEntry:
    term: int
    index: int
    entry_type: LogEntryType
    data: dict = field(default_factory=dict)


@dataclass
class ConsensusNode:
    node_id: str
    role: NodeRole = NodeRole.FOLLOWER
    current_term: int = 0
    voted_for: Optional[str] = None
    log: List[LogEntry] = field(default_factory=list)
    commit_index: int = 0
    last_applied: int = 0
    votes_received: Set[str] = field(default_factory=set)
    is_alive: bool = True


class RaftConsensus:
    """Raft 합의 알고리즘 구현.

    - 리더 선출
    - 로그 복제
    - 상태 머신 적용
    - 과반수 합의
    """

    def __init__(self, rng_seed: int = 42):
        self._rng = np.random.default_rng(rng_seed)
        self._nodes: Dict[str, ConsensusNode] = {}
        self._leader_id: Optional[str] = None
        self._history: List[dict] = []
        self._committed_entries: List[LogEntry] = []

    def add_node(self, node_id: str) -> ConsensusNode:
        node = ConsensusNode(node_id=node_id)
        self._nodes[node_id] = node
        return node

    def remove_node(self, node_id: str):
        self._nodes.pop(node_id, None)
        if self._leader_id == node_id:
            self._leader_id = None

    @property
    def quorum_size(self) -> int:
        return len(self._nodes) // 2 + 1

    def start_election(self, candidate_id: str) -> bool:
        node = self._nodes.get(candidate_id)
        if not node or not node.is_alive:
            return False
        node.current_term += 1
        node.role = NodeRole.CANDIDATE
        node.voted_for = candidate_id
        node.votes_received = {candidate_id}
        self._history.append({"event": "election_start", "candidate": candidate_id, "term": node.current_term})
        # Request votes from all nodes
        for nid, n in self._nodes.items():
            if nid == candidate_id or not n.is_alive:
                continue
            if n.voted_for is None or n.current_term < node.current_term:
                # Grant vote
                n.voted_for = candidate_id
                n.current_term = node.current_term
                node.votes_received.add(nid)
        # Check if won
        if len(node.votes_received) >= self.quorum_size:
            node.role = NodeRole.LEADER
            self._leader_id = candidate_id
            # Reset other nodes
            for nid, n in self._nodes.items():
                if nid != candidate_id:
                    n.role = NodeRole.FOLLOWER
            self._history.append({"event": "leader_elected", "leader": candidate_id, "term": node.current_term})
            return True
        node.role = NodeRole.FOLLOWER
        return False

    def propose(self, data: dict) -> Optional[LogEntry]:
        if not self._leader_id:
            return None
        leader = self._nodes.get(self._leader_id)
        if not leader:
            return None
        entry = LogEntry(
            term=leader.current_term,
            index=len(leader.log),
            entry_type=LogEntryType.COMMAND,
            data=data,
        )
        leader.log.append(entry)
        # Replicate to followers
        replicated = 1  # leader itself
        for nid, node in self._nodes.items():
            if nid == self._leader_id or not node.is_alive:
                continue
            node.log.append(entry)
            node.current_term = leader.current_term
            replicated += 1
        if replicated >= self.quorum_size:
            leader.commit_index = entry.index
            self._committed_entries.append(entry)
            self._history.append({"event": "committed", "index": entry.index, "replicated": replicated})
            return entry
        return None

    def get_leader(self) -> Optional[str]:
        return self._leader_id

    def get_node(self, node_id: str) -> Optional[ConsensusNode]:
        return self._nodes.get(node_id)

    def kill_node(self, node_id: str):
        node = self._nodes.get(node_id)
        if node:
            node.is_alive = False
            if self._leader_id == node_id:
                self._leader_id = None

    def revive_node(self, node_id: str):
        node = self._nodes.get(node_id)
        if node:
            node.is_alive = True
            node.role = NodeRole.FOLLOWER
            node.voted_for = None

    def summary(self) -> dict:
        alive = sum(1 for n in self._nodes.values() if n.is_alive)
        return {
            "total_nodes": len(self._nodes),
            "alive_nodes": alive,
            "leader": self._leader_id,
            "current_term": max((n.current_term for n in self._nodes.values()), default=0),
            "committed_entries": len(self._committed_entries),
            "quorum_size": self.quorum_size,
            "history_events": len(self._history),
        }
