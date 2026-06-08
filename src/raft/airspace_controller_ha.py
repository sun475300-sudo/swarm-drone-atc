"""P741: Raft 합의 기반 AirspaceController 다중 인스턴스 HA.

마스터 장애 시 <1s 내 새 리더 선출하여 무중단 운영.
NLB(Network Load Balancer) 뒤에 3-5 인스턴스 배치.

기존 `swarm_raft_consensus.py`(P641-650)를 controller-level로 격상.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class NodeRole(Enum):
    """Raft 노드 역할."""

    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


@dataclass
class LogEntry:
    """Raft 로그 엔트리 — AirspaceController 명령."""

    term: int
    index: int
    command: dict


@dataclass
class RaftState:
    """노드별 Raft 상태."""

    node_id: str
    role: NodeRole = NodeRole.FOLLOWER
    current_term: int = 0
    voted_for: str | None = None
    log: list[LogEntry] = field(default_factory=list)
    commit_index: int = 0
    last_applied: int = 0
    leader_id: str | None = None
    last_heartbeat_ts: float = 0.0
    # 결정론적 논리 시계 기반 합의 루프 상태 (RaftCluster가 구동).
    election_elapsed_ms: float = 0.0
    heartbeat_elapsed_ms: float = 0.0
    election_timeout_ms: int = 0
    votes_received: set[str] = field(default_factory=set)
    # 리더 전용: 각 peer에 대한 복제 진행 인덱스.
    next_index: dict[str, int] = field(default_factory=dict)
    match_index: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class RaftConfig:
    """Raft 타이밍 설정."""

    election_timeout_ms: tuple[int, int] = (150, 300)  # randomized
    heartbeat_interval_ms: int = 50
    rpc_timeout_ms: int = 100


class AirspaceControllerHA:
    """HA AirspaceController — Raft 합의로 명령 복제.

    Usage:
        node = AirspaceControllerHA("ctrl-1", peers=["ctrl-2:8001", "ctrl-3:8002"])
        node.start()
        if node.is_leader():
            node.replicate(command={"type": "advisory", ...})
    """

    def __init__(self, node_id: str, peers: list[str], cfg: RaftConfig | None = None) -> None:
        """``__init__`` 동작을 수행한다."""
        self.node_id = node_id
        self.peers = peers
        self.cfg = cfg or RaftConfig()
        self.state = RaftState(node_id=node_id)
        self._running = False

    def is_leader(self) -> bool:
        """현재 노드가 리더인지."""
        return self.state.role == NodeRole.LEADER

    @property
    def cluster_size(self) -> int:
        """자신 포함 클러스터 노드 수."""
        return len(self.peers) + 1

    @property
    def quorum(self) -> int:
        """과반 합의에 필요한 노드 수."""
        return self.cluster_size // 2 + 1

    def replicate(self, command: dict) -> bool:
        """리더만 호출. 명령을 로컬 로그에 append.

        단일 노드(peer 없음)는 quorum=1 이므로 즉시 커밋한다.
        다중 노드는 :class:`RaftCluster` 가 AppendEntries 후 과반 ack
        시점에 ``commit_index`` 를 전진시킨다.
        """
        if not self.is_leader():
            return False
        entry = LogEntry(
            term=self.state.current_term,
            index=len(self.state.log),
            command=command,
        )
        self.state.log.append(entry)
        self.state.match_index[self.node_id] = entry.index
        if not self.peers:
            self.state.commit_index = entry.index
        return True

    def become_follower(self, term: int, leader_id: str | None = None) -> None:
        """상위 term 발견 시 FOLLOWER 로 강등."""
        self.state.role = NodeRole.FOLLOWER
        self.state.current_term = term
        self.state.voted_for = None
        self.state.leader_id = leader_id
        self.state.votes_received = set()

    def become_candidate(self) -> None:
        """선거 타임아웃 → CANDIDATE 전환 + 자기 투표."""
        self.state.role = NodeRole.CANDIDATE
        self.state.current_term += 1
        self.state.voted_for = self.node_id
        self.state.leader_id = None
        self.state.votes_received = {self.node_id}
        self.state.election_elapsed_ms = 0.0

    def become_leader(self) -> None:
        """과반 득표 → LEADER 전환 + 복제 인덱스 초기화."""
        self.state.role = NodeRole.LEADER
        self.state.leader_id = self.node_id
        self.state.heartbeat_elapsed_ms = 0.0
        next_idx = len(self.state.log)
        self.state.next_index = {p: next_idx for p in self.peers}
        self.state.match_index = {p: -1 for p in self.peers}
        self.state.match_index[self.node_id] = len(self.state.log) - 1

    def start(self) -> None:
        """노드를 활성화. 실제 구동은 :class:`RaftCluster.tick` 가 담당."""
        self._running = True
        self.state.last_heartbeat_ts = time.monotonic()

    def stop(self) -> None:
        """노드 종료."""
        self._running = False

    def on_request_vote(self, candidate_id: str, term: int, last_log_index: int, last_log_term: int) -> bool:
        """RequestVote RPC handler."""
        # Raft §5.2: vote granted if (term ≥ self.term) ∧ (haven't voted) ∧ (log up-to-date)
        if term < self.state.current_term:
            return False
        if term > self.state.current_term:
            # 상위 term 발견 → 강등 + 투표 기록 초기화.
            self.state.current_term = term
            self.state.voted_for = None
            self.state.role = NodeRole.FOLLOWER
        if self.state.voted_for is not None and self.state.voted_for != candidate_id:
            return False
        my_last_log = self.state.log[-1] if self.state.log else None
        if my_last_log:
            if last_log_term < my_last_log.term:
                return False
            if last_log_term == my_last_log.term and last_log_index < my_last_log.index:
                return False
        self.state.voted_for = candidate_id
        self.state.current_term = term
        self.state.election_elapsed_ms = 0.0
        return True

    def on_append_entries(self, leader_id: str, term: int, entries: list[LogEntry], commit_index: int) -> bool:
        """AppendEntries RPC handler — heartbeat + 로그 복제.

        ``entries`` 는 ``entry.index`` 위치에 배치되어 멱등하다.
        term 이 일치하지 않는 충돌 엔트리는 절단(truncate) 후 교체한다.
        """
        if term < self.state.current_term:
            return False
        if term > self.state.current_term:
            self.state.current_term = term
            self.state.voted_for = None
        self.state.leader_id = leader_id
        self.state.role = NodeRole.FOLLOWER
        self.state.votes_received = set()
        self.state.last_heartbeat_ts = time.monotonic()
        self.state.election_elapsed_ms = 0.0
        for e in entries:
            if e.index < len(self.state.log):
                if self.state.log[e.index].term != e.term:
                    del self.state.log[e.index:]
                    self.state.log.append(e)
            else:
                self.state.log.append(e)
        if commit_index > self.state.commit_index:
            self.state.commit_index = min(commit_index, len(self.state.log) - 1)
        return True


def health_check(node: AirspaceControllerHA) -> dict:
    """노드 헬스체크 — Kubernetes liveness probe 용."""
    return {
        "node_id": node.node_id,
        "role": node.state.role.value,
        "term": node.state.current_term,
        "log_size": len(node.state.log),
        "commit_index": node.state.commit_index,
        "leader_id": node.state.leader_id,
        "is_leader": node.is_leader(),
        "running": node._running,
    }
