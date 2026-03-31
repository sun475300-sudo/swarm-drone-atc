# Phase 645: Swarm Consensus Raft — Distributed Decision Making
"""
Raft 합의 프로토콜 기반 군집 분산 의사결정.
리더 선출, 로그 복제, 다수결 기반 경로 합의.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum


class NodeRole(Enum):
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


@dataclass
class LogEntry:
    term: int
    command: str
    data: dict = field(default_factory=dict)
    committed: bool = False


@dataclass
class RaftNode:
    node_id: str
    role: NodeRole = NodeRole.FOLLOWER
    current_term: int = 0
    voted_for: str | None = None
    log: list[LogEntry] = field(default_factory=list)
    commit_index: int = 0
    votes_received: int = 0


class SwarmRaftConsensus:
    def __init__(self, n_nodes: int = 5, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.n_nodes = n_nodes
        self.nodes: dict[str, RaftNode] = {}
        self.leader_id: str | None = None
        self._term_history: list[dict] = []

        for i in range(n_nodes):
            nid = f"NODE-{i:03d}"
            self.nodes[nid] = RaftNode(node_id=nid)

    def _majority(self) -> int:
        return self.n_nodes // 2 + 1

    def start_election(self, candidate_id: str) -> bool:
        if candidate_id not in self.nodes:
            return False

        candidate = self.nodes[candidate_id]
        candidate.current_term += 1
        candidate.role = NodeRole.CANDIDATE
        candidate.voted_for = candidate_id
        candidate.votes_received = 1  # self-vote

        for nid, node in self.nodes.items():
            if nid == candidate_id:
                continue
            if node.voted_for is None or node.current_term < candidate.current_term:
                # Grant vote
                node.voted_for = candidate_id
                node.current_term = candidate.current_term
                candidate.votes_received += 1

        if candidate.votes_received >= self._majority():
            candidate.role = NodeRole.LEADER
            self.leader_id = candidate_id
            # Reset other nodes to follower
            for nid, node in self.nodes.items():
                if nid != candidate_id:
                    node.role = NodeRole.FOLLOWER
            self._term_history.append({
                "term": candidate.current_term,
                "leader": candidate_id,
                "votes": candidate.votes_received,
            })
            return True

        candidate.role = NodeRole.FOLLOWER
        return False

    def append_entry(self, command: str, data: dict | None = None) -> bool:
        if self.leader_id is None:
            return False

        leader = self.nodes[self.leader_id]
        entry = LogEntry(
            term=leader.current_term,
            command=command,
            data=data or {},
        )
        leader.log.append(entry)

        # Replicate to followers
        acks = 1  # leader already has it
        for nid, node in self.nodes.items():
            if nid == self.leader_id:
                continue
            # Simulate replication (with random network delay)
            if self.rng.random() > 0.1:  # 90% success rate
                node.log.append(LogEntry(
                    term=entry.term,
                    command=entry.command,
                    data=entry.data.copy(),
                ))
                acks += 1

        if acks >= self._majority():
            entry.committed = True
            leader.commit_index = len(leader.log)
            return True
        return False

    def propose_route(self, drone_id: str, route: list[np.ndarray]) -> bool:
        return self.append_entry("ROUTE_PROPOSAL", {
            "drone_id": drone_id,
            "waypoints": len(route),
        })

    def propose_avoidance(self, drone_a: str, drone_b: str, action: str) -> bool:
        return self.append_entry("AVOIDANCE_DECISION", {
            "drone_a": drone_a,
            "drone_b": drone_b,
            "action": action,
        })

    def get_committed_log(self) -> list[LogEntry]:
        if self.leader_id is None:
            return []
        return [e for e in self.nodes[self.leader_id].log if e.committed]

    def summary(self) -> dict:
        return {
            "n_nodes": self.n_nodes,
            "leader": self.leader_id,
            "current_term": max(n.current_term for n in self.nodes.values()),
            "total_entries": sum(len(n.log) for n in self.nodes.values()),
            "committed": len(self.get_committed_log()),
            "elections": len(self._term_history),
        }

    def run(self, n_rounds: int = 20) -> dict:
        # Elect leader
        candidates = list(self.nodes.keys())
        elected = False
        for cid in self.rng.permutation(candidates):
            if self.start_election(cid):
                elected = True
                break

        if not elected:
            return self.summary()

        # Run rounds of proposals
        for _ in range(n_rounds):
            action = self.rng.choice(["route", "avoid"])
            if action == "route":
                did = self.rng.choice(candidates)
                route = [self.rng.uniform(-1000, 1000, 3) for _ in range(5)]
                self.propose_route(did, route)
            else:
                a, b = self.rng.choice(candidates, 2, replace=False)
                self.propose_avoidance(a, b, "CLIMB")

        return self.summary()


if __name__ == "__main__":
    raft = SwarmRaftConsensus(7, 42)
    result = raft.run(30)
    for k, v in result.items():
        print(f"  {k}: {v}")
