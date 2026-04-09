"""
Phase 414: Blockchain Consensus Protocol
Consensus mechanisms for drone swarm blockchain: PoW, PoS, PBFT, Raft.
"""

import hashlib
import json
import time
import numpy as np
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Dict, Optional, Tuple, Any, Set
from collections import defaultdict


class ConsensusState(Enum):
    """Consensus protocol states."""

    IDLE = auto()
    PRE_PREPARE = auto()
    PREPARE = auto()
    COMMIT = auto()
    FINALIZED = auto()
    FAILED = auto()


class NodeRole(Enum):
    """Node roles in consensus."""

    LEADER = auto()
    FOLLOWER = auto()
    CANDIDATE = auto()
    VALIDATOR = auto()
    OBSERVER = auto()


@dataclass
class ConsensusMessage:
    """Consensus protocol message."""

    msg_type: str
    sender: str
    receiver: str
    data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    signature: str = ""
    sequence: int = 0


@dataclass
class Vote:
    """Consensus vote."""

    voter: str
    proposal_id: str
    decision: bool
    timestamp: float = field(default_factory=time.time)
    stake: float = 0.0


@dataclass
class ConsensusRound:
    """Single consensus round."""

    round_id: int
    leader: str
    proposal: Dict[str, Any]
    votes: List[Vote] = field(default_factory=list)
    state: ConsensusState = ConsensusState.IDLE
    start_time: float = field(default_factory=time.time)
    end_time: float = 0.0
    result: Optional[bool] = None


class PBFTConsensus:
    """Practical Byzantine Fault Tolerance consensus."""

    def __init__(self, node_id: str, seed: int = 42):
        self.node_id = node_id
        self.rng = np.random.default_rng(seed)
        self.view: int = 0
        self.sequence: int = 0
        self.peers: Dict[str, Dict[str, Any]] = {}
        self.message_log: List[ConsensusMessage] = []
        self.prepare_messages: Dict[int, List[ConsensusMessage]] = defaultdict(list)
        self.commit_messages: Dict[int, List[ConsensusMessage]] = defaultdict(list)
        self.state = ConsensusState.IDLE

    def add_peer(self, peer_id: str, address: Tuple[str, int]) -> None:
        self.peers[peer_id] = {
            "address": address,
            "is_active": True,
            "reputation": 1.0,
            "last_seen": time.time(),
        }

    def get_fault_tolerance(self) -> int:
        n = len(self.peers) + 1
        return (n - 1) // 3

    def propose(self, data: Dict[str, Any]) -> ConsensusMessage:
        self.sequence += 1
        msg = ConsensusMessage(
            msg_type="pre-prepare",
            sender=self.node_id,
            receiver="all",
            data=data,
            sequence=self.sequence,
        )
        self.message_log.append(msg)
        self.state = ConsensusState.PRE_PREPARE
        return msg

    def prepare(self, msg: ConsensusMessage) -> Optional[ConsensusMessage]:
        if msg.sequence not in self.prepare_messages:
            self.prepare_messages[msg.sequence] = []
        prepare_msg = ConsensusMessage(
            msg_type="prepare",
            sender=self.node_id,
            receiver="all",
            data=msg.data,
            sequence=msg.sequence,
        )
        self.prepare_messages[msg.sequence].append(prepare_msg)
        if len(self.prepare_messages[msg.sequence]) >= 2 * self.get_fault_tolerance():
            self.state = ConsensusState.PREPARE
            return prepare_msg
        return None

    def commit(self, sequence: int) -> Optional[ConsensusMessage]:
        if (
            len(self.prepare_messages.get(sequence, []))
            >= 2 * self.get_fault_tolerance()
        ):
            commit_msg = ConsensusMessage(
                msg_type="commit",
                sender=self.node_id,
                receiver="all",
                data={"sequence": sequence},
                sequence=sequence,
            )
            self.commit_messages[sequence].append(commit_msg)
            if (
                len(self.commit_messages[sequence])
                >= 2 * self.get_fault_tolerance() + 1
            ):
                self.state = ConsensusState.FINALIZED
                return commit_msg
        return None

    def is_finalized(self, sequence: int) -> bool:
        return (
            len(self.commit_messages.get(sequence, []))
            >= 2 * self.get_fault_tolerance() + 1
        )


class RaftConsensus:
    """Raft consensus protocol."""

    def __init__(self, node_id: str, seed: int = 42):
        self.node_id = node_id
        self.rng = np.random.default_rng(seed)
        self.current_term: int = 0
        self.voted_for: Optional[str] = None
        self.log: List[Dict[str, Any]] = []
        self.commit_index: int = 0
        self.last_applied: int = 0
        self.role = NodeRole.FOLLOWER
        self.leader_id: Optional[str] = None
        self.peers: Dict[str, Dict[str, Any]] = {}
        self.votes_received: Set[str] = set()
        self.election_timeout = self.rng.uniform(0.15, 0.3)
        self.last_heartbeat = time.time()

    def add_peer(self, peer_id: str) -> None:
        self.peers[peer_id] = {"match_index": 0, "next_index": 0}

    def start_election(self) -> bool:
        self.current_term += 1
        self.role = NodeRole.CANDIDATE
        self.voted_for = self.node_id
        self.votes_received = {self.node_id}
        self.last_heartbeat = time.time()
        return len(self.votes_received) > (len(self.peers) + 1) / 2

    def request_vote(self, candidate_id: str, term: int, last_log_index: int) -> bool:
        if term < self.current_term:
            return False
        if term > self.current_term:
            self.current_term = term
            self.voted_for = None
            self.role = NodeRole.FOLLOWER
        if self.voted_for is None or self.voted_for == candidate_id:
            self.voted_for = candidate_id
            self.current_term = term
            return True
        return False

    def append_entries(
        self, leader_id: str, term: int, entries: List[Dict[str, Any]]
    ) -> bool:
        if term < self.current_term:
            return False
        self.current_term = term
        self.leader_id = leader_id
        self.role = NodeRole.FOLLOWER
        self.last_heartbeat = time.time()
        self.log.extend(entries)
        return True

    def become_leader(self) -> None:
        self.role = NodeRole.LEADER
        self.leader_id = self.node_id
        for peer_id in self.peers:
            self.peers[peer_id]["next_index"] = len(self.log) + 1
            self.peers[peer_id]["match_index"] = 0

    def add_log_entry(self, data: Dict[str, Any]) -> int:
        entry = {
            "term": self.current_term,
            "index": len(self.log) + 1,
            "data": data,
            "timestamp": time.time(),
        }
        self.log.append(entry)
        return entry["index"]

    def check_election_timeout(self) -> bool:
        if self.role == NodeRole.LEADER:
            return False
        return time.time() - self.last_heartbeat > self.election_timeout


class ConsensusManager:
    """Consensus manager for drone swarm."""

    def __init__(self, consensus_type: str = "pbft", seed: int = 42):
        self.consensus_type = consensus_type
        self.rng = np.random.default_rng(seed)
        self.pbft: Optional[PBFTConsensus] = None
        self.raft: Optional[RaftConsensus] = None
        self.rounds: List[ConsensusRound] = []
        self.current_round = 0
        self._init_consensus()

    def _init_consensus(self) -> None:
        if self.consensus_type == "pbft":
            self.pbft = PBFTConsensus("node_0", seed=self.rng.integers(10000))
        elif self.consensus_type == "raft":
            self.raft = RaftConsensus("node_0", seed=self.rng.integers(10000))

    def add_node(self, node_id: str) -> None:
        if self.pbft:
            self.pbft.add_peer(node_id, ("localhost", 8000))
        if self.raft:
            self.raft.add_peer(node_id)

    def run_consensus_round(self, proposal: Dict[str, Any]) -> ConsensusRound:
        self.current_round += 1
        round_obj = ConsensusRound(
            round_id=self.current_round, leader="node_0", proposal=proposal
        )
        if self.consensus_type == "pbft" and self.pbft:
            msg = self.pbft.propose(proposal)
            prepare_msg = self.pbft.prepare(msg)
            if prepare_msg:
                commit_msg = self.pbft.commit(msg.sequence)
                round_obj.state = (
                    ConsensusState.FINALIZED if commit_msg else ConsensusState.FAILED
                )
                round_obj.result = commit_msg is not None
        elif self.consensus_type == "raft" and self.raft:
            if self.raft.role != NodeRole.LEADER:
                self.raft.start_election()
                if len(self.raft.votes_received) > len(self.raft.peers) / 2:
                    self.raft.become_leader()
            if self.raft.role == NodeRole.LEADER:
                self.raft.add_log_entry(proposal)
                round_obj.state = ConsensusState.FINALIZED
                round_obj.result = True
        round_obj.end_time = time.time()
        self.rounds.append(round_obj)
        return round_obj

    def get_consensus_stats(self) -> Dict[str, Any]:
        successful = sum(1 for r in self.rounds if r.result is True)
        return {
            "total_rounds": len(self.rounds),
            "successful": successful,
            "failed": len(self.rounds) - successful,
            "success_rate": successful / len(self.rounds) if self.rounds else 0,
            "consensus_type": self.consensus_type,
        }


class DroneConsensusNetwork:
    """Consensus network for drone swarm decisions."""

    def __init__(self, n_drones: int, seed: int = 42):
        self.n_drones = n_drones
        self.rng = np.random.default_rng(seed)
        self.consensus = ConsensusManager("pbft", seed)
        for i in range(n_drones):
            self.consensus.add_node(f"drone_{i}")

    def vote_on_mission(self, mission: Dict[str, Any]) -> bool:
        round_result = self.consensus.run_consensus_round(
            {"type": "mission_approval", "mission": mission}
        )
        return round_result.result is True

    def vote_on_airspace_change(self, zone_id: str, action: str) -> bool:
        round_result = self.consensus.run_consensus_round(
            {"type": "airspace_change", "zone_id": zone_id, "action": action}
        )
        return round_result.result is True

    def get_network_stats(self) -> Dict[str, Any]:
        return self.consensus.get_consensus_stats()


if __name__ == "__main__":
    network = DroneConsensusNetwork(n_drones=5, seed=42)
    result = network.vote_on_mission(
        {"type": "delivery", "waypoints": [[0, 0, 50], [100, 100, 50]]}
    )
    print(f"Mission approved: {result}")
    result = network.vote_on_airspace_change("ZONE_A", "open")
    print(f"Airspace change approved: {result}")
    print(f"Stats: {network.get_network_stats()}")
