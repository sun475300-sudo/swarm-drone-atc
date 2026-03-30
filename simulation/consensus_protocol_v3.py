"""
Consensus Protocol v3
Phase 358 - Raft, HotStuff, DAG-based Consensus for Swarm Coordination
"""

import numpy as np
import heapq
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Set
from enum import Enum
import time
import hashlib


class NodeState(Enum):
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


class MessageType(Enum):
    REQUEST_VOTE = "request_vote"
    VOTE = "vote"
    APPEND_ENTRIES = "append_entries"
    APPEND_RESPONSE = "append_response"
    PREPARE = "prepare"
    COMMIT = "commit"


@dataclass
class LogEntry:
    term: int
    index: int
    command: str
    data: Dict = field(default_factory=dict)


@dataclass
class ConsensusMessage:
    msg_type: MessageType
    from_node: str
    to_node: str
    term: int
    data: Dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class RaftNode:
    def __init__(self, node_id: str, peers: List[str]):
        self.node_id = node_id
        self.peers = peers

        self.state = NodeState.FOLLOWER
        self.current_term = 0
        self.voted_for: Optional[str] = None

        self.log: List[LogEntry] = []
        self.commit_index = 0
        self.last_applied = 0

        self.election_timeout = np.random.uniform(1.5, 3.0)
        self.heartbeat_interval = 0.5

        self.leader_id: Optional[str] = None
        self.next_index: Dict[str, int] = {p: len(self.log) + 1 for p in peers}
        self.match_index: Dict[str, int] = {p: 0 for p in peers}

        self.last_election_time = time.time()
        self.last_heartbeat = time.time()

    def become_follower(self, term: int):
        self.state = NodeState.FOLLOWER
        self.current_term = term
        self.voted_for = None

    def become_candidate(self):
        self.state = NodeState.CANDIDATE
        self.current_term += 1
        self.voted_for = self.node_id
        self.last_election_time = time.time()

    def become_leader(self):
        self.state = NodeState.LEADER
        self.leader_id = self.node_id
        self.next_index = {p: len(self.log) + 1 for p in self.peers}
        self.match_index = {p: 0 for p in self.peers}

    def request_vote(
        self,
        candidate_id: str,
        candidate_term: int,
        last_log_index: int,
        last_log_term: int,
    ) -> bool:
        if candidate_term > self.current_term:
            self.become_follower(candidate_term)

        vote_granted = False

        if self.voted_for is None or self.voted_for == candidate_id:
            if last_log_term > (self.log[-1].term if self.log else 0):
                vote_granted = True
            elif last_log_term == (self.log[-1].term if self.log else 0):
                if last_log_index >= len(self.log):
                    vote_granted = True

        if vote_granted:
            self.voted_for = candidate_id
            self.last_election_time = time.time()

        return vote_granted

    def append_entries(
        self,
        leader_id: str,
        leader_term: int,
        prev_log_index: int,
        prev_log_term: int,
        entries: List[LogEntry],
    ) -> Tuple[bool, int]:
        if leader_term < self.current_term:
            return False, self.current_term

        if leader_term > self.current_term:
            self.become_follower(leader_term)

        self.last_election_time = time.time()
        self.leader_id = leader_id

        if prev_log_index > len(self.log):
            return False, len(self.log)

        if prev_log_index > 0:
            if (
                prev_log_index > len(self.log)
                or self.log[prev_log_index - 1].term != prev_log_term
            ):
                return False, len(self.log)

        self.log = self.log[:prev_log_index]
        self.log.extend(entries)

        self.commit_index = min(leader_term, len(self.log))

        return True, len(self.log)

    def start_election(self) -> List[ConsensusMessage]:
        self.become_candidate()

        votes = {self.node_id: True}

        for peer in self.peers:
            msg = ConsensusMessage(
                msg_type=MessageType.REQUEST_VOTE,
                from_node=self.node_id,
                to_node=peer,
                term=self.current_term,
                data={
                    "last_log_index": len(self.log),
                    "last_log_term": self.log[-1].term if self.log else 0,
                },
            )

        return votes

    def commit(self, command: str, data: Dict) -> bool:
        if self.state != NodeState.LEADER:
            return False

        entry = LogEntry(
            term=self.current_term, index=len(self.log) + 1, command=command, data=data
        )
        self.log.append(entry)

        return True

    def check_commit(self) -> bool:
        if self.state != NodeState.LEADER:
            return False

        for N in range(self.commit_index + 1, len(self.log) + 1):
            count = 1
            for peer in self.peers:
                if self.match_index.get(peer, 0) >= N:
                    count += 1

            if count > len(self.peers) / 2:
                self.commit_index = N

        return True


class HotStuffNode:
    def __init__(self, node_id: str, peers: List[str]):
        self.node_id = node_id
        self.peers = peers

        self.view_number = 0
        self.high_qc = None
        self.locked_qc = None

        self.pending_proposals: List[Dict] = []
        self.committed_blocks: List[Dict] = []

        self.prepared_statements: Dict[str, Dict] = {}

    def create_proposal(self, command: str, data: Dict) -> Dict:
        proposal = {
            "command": command,
            "data": data,
            "view": self.view_number,
            "node_id": self.node_id,
            "timestamp": time.time(),
        }

        self.pending_proposals.append(proposal)

        return self._create_qc(proposal)

    def _create_qc(self, proposal: Dict) -> Dict:
        qc = {
            "proposal": proposal,
            "view": self.view_number,
            "signatures": {self.node_id: self._sign(proposal)},
            "validator_set": self.peers + [self.node_id],
        }

        return qc

    def _sign(self, data: Dict) -> str:
        data_str = str(data)
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]

    def prepare(self, qc: Dict) -> Dict:
        prepare_msg = {
            "type": "prepare",
            "qc": qc,
            "node_id": self.node_id,
            "view": self.view_number,
        }

        self.prepared_statements[qc["proposal"]["command"]] = prepare_msg

        return prepare_msg

    def pre_commit(self, prepare_messages: List[Dict]) -> Dict:
        if len(prepare_messages) > len(self.peers) / 2:
            return self._create_qc({"status": "pre-committed", "node_id": self.node_id})
        return None

    def commit(self, qc: Dict) -> bool:
        if qc:
            self.committed_blocks.append(qc["proposal"])
            self.locked_qc = qc
            return True
        return False

    def decide(self, commit_qc: Dict) -> bool:
        self.high_qc = commit_qc
        return True


class DAGConsensus:
    def __init__(self, num_nodes: int):
        self.num_nodes = num_nodes
        self.dag: Dict[int, List[int]] = {}
        self.vertex_data: Dict[int, Dict] = {}
        self.tip_hashes: Set[int] = set()

        self.genesis = 0
        self.dag[0] = []
        self.vertex_data[0] = {"hash": "genesis", "validated": True}
        self.tip_hashes.add(0)

    def add_vertex(self, parent_hashes: List[int], data: Dict) -> int:
        vertex_id = len(self.vertex_data)

        hash_input = f"{vertex_id}{data}{parent_hashes}"
        vertex_hash = int(hashlib.sha256(hash_input.encode()).hexdigest(), 16) % 1000000

        self.dag[vertex_id] = parent_hashes
        self.vertex_data[vertex_id] = {
            "hash": vertex_hash,
            "data": data,
            "validated": False,
            "parents": parent_hashes,
        }

        for parent in parent_hashes:
            if parent in self.tip_hashes:
                self.tip_hashes.remove(parent)

        self.tip_hashes.add(vertex_id)

        return vertex_id

    def validate_vertex(self, vertex_id: int) -> bool:
        if (
            vertex_id in self.vertex_data
            and not self.vertex_data[vertex_id]["validated"]
        ):
            parents = self.dag[vertex_id]

            all_validated = all(
                self.vertex_data.get(p, {}).get("validated", False) for p in parents
            )

            if all_validated:
                self.vertex_data[vertex_id]["validated"] = True
                return True

        return False

    def get_consensus_order(self) -> List[int]:
        ordered = []
        validated = {v for v, data in self.vertex_data.items() if data["validated"]}

        while validated:
            for tip in self.tip_hashes:
                if tip in validated:
                    ordered.append(tip)
                    validated.remove(tip)

                    for vertex, parents in self.dag.items():
                        if tip in parents:
                            parents.remove(tip)

                    self.tip_hashes.remove(tip)
                    break

        return ordered


class SwarmConsensusManager:
    def __init__(self, num_drones: int = 5):
        self.num_drones = num_drones
        self.drone_ids = [f"drone_{i}" for i in range(num_drones)]

        self.raft_nodes = {d: RaftNode(d, self.drone_ids) for d in self.drone_ids}
        self.hotstuff_nodes = {
            d: HotStuffNode(d, self.drone_ids) for d in self.drone_ids
        }
        self.dag = DAGConsensus(num_drones)

        self.leader: Optional[str] = None
        self.consensus_results: List[Dict] = []

    def elect_leader(self) -> str:
        for node_id in self.drone_ids:
            node = self.raft_nodes[node_id]
            votes = node.start_election()

            if sum(votes.values()) > self.num_drones / 2:
                self.leader = node_id
                return node_id

        return self.leader or self.drone_ids[0]

    def propose_mission(self, mission_data: Dict) -> bool:
        if not self.leader:
            self.elect_leader()

        leader_node = self.raft_nodes[self.leader]

        if leader_node.commit("mission", mission_data):
            entry = leader_node.log[-1]

            parent_hashes = list(self.dag.tip_hashes)[:3]
            self.dag.add_vertex(parent_hashes, entry.__dict__)

            self.consensus_results.append(
                {
                    "mission": mission_data,
                    "leader": self.leader,
                    "entry_index": entry.index,
                    "timestamp": time.time(),
                }
            )

            return True

        return False

    def run_consensus_round(self, command: str, data: Dict) -> Dict:
        result = {
            "command": command,
            "status": "proposed",
            "participants": self.drone_ids,
        }

        qc = self.hotstuff_nodes[self.drone_ids[0]].create_proposal(command, data)

        prepares = []
        for node_id in self.drone_ids:
            prepare = self.hotstuff_nodes[node_id].prepare(qc)
            prepares.append(prepare)

        pre_commit_qc = self.hotstuff_nodes[self.drone_ids[0]].pre_commit(prepares)

        if pre_commit_qc:
            for node_id in self.drone_ids:
                self.hotstuff_nodes[node_id].commit(pre_commit_qc)
            result["status"] = "committed"

        return result


def simulate_swarm_consensus():
    manager = SwarmConsensusManager(num_drones=5)

    print("=== Swarm Consensus Simulation (Raft + HotStuff + DAG) ===")

    leader = manager.elect_leader()
    print(f"Leader elected: {leader}")

    missions = [
        {"type": "formation", "target": (100, 100, 50), "drones": [0, 1, 2]},
        {"type": "search", "area": "zone_a", "drones": [3, 4]},
        {"type": "delivery", "payload": "medical", "destination": "hospital"},
    ]

    for mission in missions:
        result = manager.propose_mission(mission)
        print(f"Mission proposed: {mission['type']}, committed: {result}")

    print("\n--- HotStuff Consensus ---")
    for i in range(3):
        result = manager.run_consensus_round(f"command_{i}", {"data": i})
        print(f"Round {i}: {result['status']}")

    print(f"\n--- DAG State ---")
    print(f"Total vertices: {len(manager.dag.vertex_data)}")
    print(f"Tips: {manager.dag.tip_hashes}")

    return manager.consensus_results


if __name__ == "__main__":
    simulate_swarm_consensus()
