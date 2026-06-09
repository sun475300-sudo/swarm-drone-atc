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

    def replicate(self, command: dict) -> bool:
        """리더만 호출. 명령을 복제 (quorum 합의)."""
        if not self.is_leader():
            return False
        entry = LogEntry(
            term=self.state.current_term,
            index=len(self.state.log),
            command=command,
        )
        self.state.log.append(entry)
        # NOTE: 단일노드 단순화 — 로컬 append 후 즉시 commit.
        #   실제 quorum 복제(AppendEntries RPC → 과반 commit)는
        #   `cluster.RaftCluster._replicate_to`가 next_index/match_index로 수행한다.
        self.state.commit_index = entry.index
        return True

    def start(self) -> None:
        """Raft 백그라운드 루프 시작."""
        self._running = True
        self.state.last_heartbeat_ts = time.monotonic()
        # NOTE: 단일노드는 running 플래그만 세운다.
        #   election timeout watchdog · heartbeat sender · RequestVote/AppendEntries
        #   RPC 루프는 `cluster.RaftCluster`가 결정론적 인프로세스 합의 루프로 구동한다.

    def stop(self) -> None:
        """노드 종료."""
        self._running = False

    def on_request_vote(self, candidate_id: str, term: int, last_log_index: int, last_log_term: int) -> bool:
        """RequestVote RPC handler."""
        # Raft §5.2: vote granted if (term ≥ self.term) ∧ (haven't voted) ∧ (log up-to-date)
        if term < self.state.current_term:
            return False
        # Raft §5.1: 더 높은 term 발견 시 term 갱신 + 투표 기록 초기화 + FOLLOWER 강등
        if term > self.state.current_term:
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
        return True

    def on_append_entries(
        self,
        leader_id: str,
        term: int,
        entries: list[LogEntry],
        commit_index: int,
        prev_log_index: int = -1,
        prev_log_term: int = 0,
    ) -> bool:
        """AppendEntries RPC handler — heartbeat + 로그 복제 (§5.3 log matching).

        ``prev_log_index``/``prev_log_term`` 은 ``entries`` 직전 엔트리의 위치·term
        으로, 리더와 팔로워 로그의 연속성을 보장한다 (기본값은 로그 선두 추가).
        """
        if term < self.state.current_term:
            return False
        # Raft §5.1: 새 term의 리더 발견 시 투표 기록 초기화
        if term > self.state.current_term:
            self.state.voted_for = None
        self.state.current_term = term
        self.state.leader_id = leader_id
        self.state.role = NodeRole.FOLLOWER
        self.state.last_heartbeat_ts = time.monotonic()
        # Raft §5.3: 직전 엔트리가 일치하지 않으면 거부 (리더가 next_index 감소 후 재시도).
        if prev_log_index >= 0:
            if prev_log_index >= len(self.state.log):
                return False
            if self.state.log[prev_log_index].term != prev_log_term:
                return False
        # 충돌 엔트리(같은 index·다른 term)는 잘라내고, 신규 엔트리만 추가 (idempotent).
        insert_at = prev_log_index + 1
        for offset, e in enumerate(entries):
            idx = insert_at + offset
            if idx < len(self.state.log):
                if self.state.log[idx].term != e.term:
                    del self.state.log[idx:]
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
