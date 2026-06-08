"""P741: Raft 합의 기반 AirspaceController 다중 인스턴스 HA.

마스터 장애 시 <1s 내 새 리더 선출하여 무중단 운영.
NLB(Network Load Balancer) 뒤에 3-5 인스턴스 배치.

기존 `swarm_raft_consensus.py`(P641-650)를 controller-level로 격상.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum

import numpy as np


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

    def __init__(
        self,
        node_id: str,
        peers: list[str],
        cfg: RaftConfig | None = None,
        cluster: RaftCluster | None = None,
    ) -> None:
        """``__init__`` 동작을 수행한다."""
        self.node_id = node_id
        self.peers = peers
        self.cfg = cfg or RaftConfig()
        self.state = RaftState(node_id=node_id)
        self._running = False
        # 인메모리 클러스터 시뮬레이션용 (None이면 단독 RPC 핸들러로만 동작)
        self._cluster = cluster
        self._clock_ms: float = 0.0
        self._election_deadline_ms: float = 0.0
        self._last_heartbeat_sent_ms: float = 0.0

    def is_leader(self) -> bool:
        """현재 노드가 리더인지."""
        return self.state.role == NodeRole.LEADER

    def _quorum_size(self) -> int:
        """과반 정족수 = (전체 노드 수)//2 + 1 (자신 포함)."""
        return (len(self.peers) + 1) // 2 + 1

    def replicate(self, command: dict) -> bool:
        """리더만 호출. 명령을 복제하고 과반 ack 시 commit한다."""
        if not self.is_leader():
            return False
        entry = LogEntry(
            term=self.state.current_term,
            index=len(self.state.log),
            command=command,
        )
        self.state.log.append(entry)
        acks = 1  # 자신
        if self._cluster is not None:
            for peer in self.peers:
                ok = self._cluster.send_append_entries(
                    self.node_id,
                    peer,
                    term=self.state.current_term,
                    entries=[entry],
                    commit_index=entry.index,
                )
                if ok:
                    acks += 1
        if acks < self._quorum_size():
            # quorum 미달 — commit 보류 (로그는 남으나 미적용)
            return False
        self.state.commit_index = entry.index
        return True

    # ── 선거 루프 ────────────────────────────────────────────────
    def become_candidate(self) -> bool:
        """선거 시작 — term 증가·자기 투표·peer 투표 요청. 과반 시 리더 승격."""
        self.state.current_term += 1
        self.state.role = NodeRole.CANDIDATE
        self.state.voted_for = self.node_id
        self.state.leader_id = None
        votes = 1  # 자기 투표
        last = self.state.log[-1] if self.state.log else None
        last_index = last.index if last else 0
        last_term = last.term if last else 0
        if self._cluster is not None:
            for peer in self.peers:
                granted = self._cluster.send_request_vote(
                    self.node_id,
                    peer,
                    term=self.state.current_term,
                    last_log_index=last_index,
                    last_log_term=last_term,
                )
                if granted:
                    votes += 1
        if votes >= self._quorum_size():
            self._become_leader()
            return True
        return False

    def _become_leader(self) -> None:
        """리더 승격 후 즉시 하트비트 전파."""
        self.state.role = NodeRole.LEADER
        self.state.leader_id = self.node_id
        self._last_heartbeat_sent_ms = self._clock_ms
        self._send_heartbeats()

    def _send_heartbeats(self) -> None:
        """빈 AppendEntries로 권한 유지 + 팔로워 타이머 리셋."""
        if self._cluster is None:
            return
        for peer in self.peers:
            self._cluster.send_append_entries(
                self.node_id,
                peer,
                term=self.state.current_term,
                entries=[],
                commit_index=self.state.commit_index,
            )

    def start(self) -> None:
        """Raft 백그라운드 루프 시작 (단독 모드 플래그)."""
        self._running = True
        self.state.last_heartbeat_ts = time.monotonic()
        # 인메모리 시뮬레이션은 RaftCluster.tick()이 루프를 구동한다.

    def stop(self) -> None:
        """노드 종료."""
        self._running = False

    def on_request_vote(self, candidate_id: str, term: int, last_log_index: int, last_log_term: int) -> bool:
        """RequestVote RPC handler."""
        # Raft §5.2: vote granted if (term ≥ self.term) ∧ (haven't voted) ∧ (log up-to-date)
        if term < self.state.current_term:
            return False
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
        self._reset_election_deadline()
        return True

    def on_append_entries(self, leader_id: str, term: int, entries: list[LogEntry], commit_index: int) -> bool:
        """AppendEntries RPC handler — heartbeat + 로그 복제."""
        if term < self.state.current_term:
            return False
        self.state.current_term = term
        self.state.leader_id = leader_id
        self.state.role = NodeRole.FOLLOWER
        self.state.voted_for = None
        self.state.last_heartbeat_ts = time.monotonic()
        self._reset_election_deadline()
        for e in entries:
            self.state.log.append(e)
        if commit_index > self.state.commit_index:
            self.state.commit_index = min(commit_index, len(self.state.log) - 1)
        return True

    def _reset_election_deadline(self) -> None:
        """현재 클록 기준으로 무작위 선거 타임아웃을 재설정 (틱 모델)."""
        if self._cluster is not None:
            lo, hi = self.cfg.election_timeout_ms
            self._election_deadline_ms = self._clock_ms + float(self._cluster.rng.integers(lo, hi + 1))


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


class RaftCluster:
    """인메모리 결정론적 Raft 클러스터 — 선거·복제·페일오버 시뮬레이션.

    실제 네트워크 없이 노드 간 RPC를 직접 메서드 호출로 라우팅한다.
    `np.random.default_rng(seed)`로 선거 타임아웃을 무작위화하되 재현 가능.

    Usage:
        cluster = RaftCluster(["c1", "c2", "c3"], seed=0)
        cluster.run_until_leader()
        leader = cluster.leader()
        leader.replicate({"type": "advisory"})
    """

    def __init__(
        self,
        node_ids: list[str],
        cfg: RaftConfig | None = None,
        seed: int = 0,
        tick_ms: float = 10.0,
    ) -> None:
        """``__init__`` 동작을 수행한다."""
        self.cfg = cfg or RaftConfig()
        self.tick_ms = tick_ms
        self.rng = np.random.default_rng(seed)
        self.nodes: dict[str, AirspaceControllerHA] = {}
        self._alive: dict[str, bool] = {}
        for nid in node_ids:
            peers = [p for p in node_ids if p != nid]
            node = AirspaceControllerHA(nid, peers=peers, cfg=self.cfg, cluster=self)
            node._reset_election_deadline()
            self.nodes[nid] = node
            self._alive[nid] = True

    # ── 노드 생사 제어 ───────────────────────────────────────────
    def kill(self, node_id: str) -> None:
        """노드 다운 — 이후 RPC 무응답, 틱 미진행."""
        self._alive[node_id] = False

    def revive(self, node_id: str) -> None:
        """노드 복구 — 팔로워로 재시작."""
        node = self.nodes[node_id]
        node.state.role = NodeRole.FOLLOWER
        node.state.voted_for = None
        node._reset_election_deadline()
        self._alive[node_id] = True

    def is_alive(self, node_id: str) -> bool:
        """노드 생존 여부."""
        return self._alive.get(node_id, False)

    # ── RPC 라우팅 (다운 노드는 무응답) ──────────────────────────
    def send_request_vote(
        self, from_id: str, to_id: str, term: int, last_log_index: int, last_log_term: int,
    ) -> bool:
        """RequestVote RPC를 대상 노드로 전달한다."""
        if not self.is_alive(to_id):
            return False
        return self.nodes[to_id].on_request_vote(from_id, term, last_log_index, last_log_term)

    def send_append_entries(
        self, from_id: str, to_id: str, term: int, entries: list[LogEntry], commit_index: int,
    ) -> bool:
        """AppendEntries RPC를 대상 노드로 전달한다."""
        if not self.is_alive(to_id):
            return False
        return self.nodes[to_id].on_append_entries(from_id, term, entries, commit_index)

    # ── 시뮬레이션 루프 ──────────────────────────────────────────
    def tick(self) -> None:
        """모든 생존 노드의 클록을 1틱 전진시키고 선거/하트비트를 구동한다."""
        for nid, node in self.nodes.items():
            if not self._alive[nid]:
                continue
            node._clock_ms += self.tick_ms
            if node.is_leader():
                if node._clock_ms - node._last_heartbeat_sent_ms >= self.cfg.heartbeat_interval_ms:
                    node._last_heartbeat_sent_ms = node._clock_ms
                    node._send_heartbeats()
            elif node._clock_ms >= node._election_deadline_ms:
                node._reset_election_deadline()
                node.become_candidate()

    def tick_n(self, n: int) -> None:
        """``n``틱 진행한다."""
        for _ in range(n):
            self.tick()

    def run_until_leader(self, max_ticks: int = 200) -> AirspaceControllerHA | None:
        """리더가 선출될 때까지 (또는 ``max_ticks``까지) 진행한다."""
        for _ in range(max_ticks):
            self.tick()
            leader = self.leader()
            if leader is not None:
                return leader
        return self.leader()

    def leader(self) -> AirspaceControllerHA | None:
        """현재 생존한 리더 노드를 반환 (없으면 None)."""
        for nid, node in self.nodes.items():
            if self._alive[nid] and node.is_leader():
                return node
        return None
