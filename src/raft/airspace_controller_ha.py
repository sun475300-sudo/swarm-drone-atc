"""P741: Raft 합의 기반 AirspaceController 다중 인스턴스 HA.

마스터 장애 시 <1s 내 새 리더 선출하여 무중단 운영.
NLB(Network Load Balancer) 뒤에 3-5 인스턴스 배치.

기존 `swarm_raft_consensus.py`(P641-650)를 controller-level로 격상.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

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
    next_index: dict[str, int] = field(default_factory=dict)
    match_index: dict[str, int] = field(default_factory=dict)
    votes_received: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class RaftConfig:
    """Raft 타이밍 설정."""

    election_timeout_ms: tuple[int, int] = (150, 300)  # randomized
    heartbeat_interval_ms: int = 50
    rpc_timeout_ms: int = 100


class RaftTransport(Protocol):
    """노드 간 RPC 전송 추상화 — 테스트는 in-process, 운영은 gRPC/HTTP 주입."""

    def request_vote(
        self, peer: str, candidate_id: str, term: int, last_log_index: int, last_log_term: int
    ) -> tuple[int, bool]:
        """RequestVote RPC. (peer_term, granted) 반환. 도달 불가 시 (term, False)."""
        ...

    def append_entries(
        self,
        peer: str,
        leader_id: str,
        term: int,
        entries: list[LogEntry],
        commit_index: int,
        prev_log_index: int,
        prev_log_term: int,
    ) -> tuple[int, bool]:
        """AppendEntries RPC. (peer_term, success) 반환. 도달 불가 시 (term, False)."""
        ...


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
        transport: RaftTransport | None = None,
        seed: int = 0,
    ) -> None:
        """``__init__`` 동작을 수행한다."""
        self.node_id = node_id
        self.peers = peers
        self.cfg = cfg or RaftConfig()
        self.state = RaftState(node_id=node_id)
        self.transport = transport
        self._rng = np.random.default_rng(seed)
        self._running = False
        self._now_ms: float = 0.0
        self._election_deadline: float = 0.0
        self._last_heartbeat_sent: float = 0.0
        self._heard_from_leader: bool = False

    @property
    def _quorum(self) -> int:
        """과반 정족수 (자기 자신 포함)."""
        return (len(self.peers) + 1) // 2 + 1

    def is_leader(self) -> bool:
        """현재 노드가 리더인지."""
        return self.state.role == NodeRole.LEADER

    def _reset_election_deadline(self, now_ms: float) -> None:
        """randomized election timeout 으로 다음 선거 마감 시각 갱신."""
        lo, hi = self.cfg.election_timeout_ms
        self._election_deadline = now_ms + float(self._rng.uniform(lo, hi))

    def replicate(self, command: dict) -> bool:
        """리더만 호출. 명령을 로그에 추가하고 quorum 합의로 commit 시도."""
        if not self.is_leader():
            return False
        entry = LogEntry(
            term=self.state.current_term,
            index=len(self.state.log),
            command=command,
        )
        self.state.log.append(entry)
        self.send_heartbeats(self._now_ms)
        self._advance_commit_index()
        return True

    def start(self) -> None:
        """Raft 노드 활성화 — election timeout watchdog 가동."""
        self._running = True
        self.state.last_heartbeat_ts = time.monotonic()
        self._reset_election_deadline(self._now_ms)

    def stop(self) -> None:
        """노드 종료 — tick 무시."""
        self._running = False

    def tick(self, now_ms: float) -> None:
        """논리 시계 1스텝. 리더는 heartbeat, 그 외는 election timeout 감시."""
        if not self._running:
            return
        self._now_ms = now_ms
        if self.is_leader():
            if now_ms - self._last_heartbeat_sent >= self.cfg.heartbeat_interval_ms:
                self.send_heartbeats(now_ms)
            return
        if self._heard_from_leader:  # 직전 tick 이후 유효 리더 RPC 수신 → 선거 연기
            self._heard_from_leader = False
            self._reset_election_deadline(now_ms)
            return
        if now_ms >= self._election_deadline:
            self.start_election(now_ms)

    def start_election(self, now_ms: float) -> None:
        """CANDIDATE 로 전환하여 term 을 올리고 동료에게 투표 요청."""
        self.state.role = NodeRole.CANDIDATE
        self.state.current_term += 1
        self.state.voted_for = self.node_id
        self.state.votes_received = {self.node_id}
        self._reset_election_deadline(now_ms)

        last_index = len(self.state.log) - 1
        last_term = self.state.log[-1].term if self.state.log else 0
        if self.transport is not None:
            for peer in self.peers:
                peer_term, granted = self.transport.request_vote(
                    peer, self.node_id, self.state.current_term, last_index, last_term,
                )
                if peer_term > self.state.current_term:
                    self._step_down(peer_term)
                    return
                if granted:
                    self.state.votes_received.add(peer)
        if len(self.state.votes_received) >= self._quorum:
            self.become_leader(now_ms)

    def become_leader(self, now_ms: float) -> None:
        """LEADER 로 승격하고 nextIndex/matchIndex 초기화 후 즉시 heartbeat."""
        self.state.role = NodeRole.LEADER
        self.state.leader_id = self.node_id
        next_idx = len(self.state.log)
        self.state.next_index = dict.fromkeys(self.peers, next_idx)
        self.state.match_index = dict.fromkeys(self.peers, -1)
        self.send_heartbeats(now_ms)

    def send_heartbeats(self, now_ms: float) -> None:
        """리더가 모든 동료에게 AppendEntries(로그 미동기 구간 포함) 전송."""
        if not self.is_leader() or self.transport is None:
            self._last_heartbeat_sent = now_ms
            return
        for peer in self.peers:
            next_idx = self.state.next_index.get(peer, len(self.state.log))
            prev_index = next_idx - 1
            prev_term = self.state.log[prev_index].term if 0 <= prev_index < len(self.state.log) else 0
            entries = self.state.log[next_idx:]
            peer_term, ok = self.transport.append_entries(
                peer,
                self.node_id,
                self.state.current_term,
                entries,
                self.state.commit_index,
                prev_index,
                prev_term,
            )
            if peer_term > self.state.current_term:
                self._step_down(peer_term)
                return
            if ok:
                self.state.match_index[peer] = len(self.state.log) - 1
                self.state.next_index[peer] = len(self.state.log)
            elif next_idx > 0:
                self.state.next_index[peer] = next_idx - 1  # 로그 불일치 → 후퇴
        self._last_heartbeat_sent = now_ms
        self._advance_commit_index()

    def _advance_commit_index(self) -> None:
        """match_index 과반이 도달한 최대 인덱스를 commit (현재 term 한정)."""
        if not self.is_leader():
            return
        for idx in range(len(self.state.log) - 1, self.state.commit_index, -1):
            if self.state.log[idx].term != self.state.current_term:
                continue
            replicas = 1 + sum(1 for m in self.state.match_index.values() if m >= idx)
            if replicas >= self._quorum:
                self.state.commit_index = idx
                break

    def _step_down(self, term: int) -> None:
        """더 높은 term 관측 시 FOLLOWER 로 강등."""
        self.state.current_term = term
        self.state.role = NodeRole.FOLLOWER
        self.state.voted_for = None
        self.state.votes_received = set()

    def on_request_vote(self, candidate_id: str, term: int, last_log_index: int, last_log_term: int) -> bool:
        """RequestVote RPC handler."""
        # Raft §5.2: vote granted if (term ≥ self.term) ∧ (haven't voted) ∧ (log up-to-date)
        if term < self.state.current_term:
            return False
        if term > self.state.current_term:  # 새 term 관측 → 강등 후 투표 가능
            self._step_down(term)
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
        self._heard_from_leader = True  # 투표 부여 → 선거 연기
        return True

    def on_append_entries(
        self,
        leader_id: str,
        term: int,
        entries: list[LogEntry],
        commit_index: int,
        prev_log_index: int | None = None,
        prev_log_term: int = 0,
    ) -> bool:
        """AppendEntries RPC handler — heartbeat + 로그 복제.

        ``prev_log_index`` 지정 시 Raft §5.3 로그 일관성 검사를 수행한다
        (불일치 시 거부 → 리더가 nextIndex 를 후퇴). 미지정 시 단순 append.
        """
        if term < self.state.current_term:
            return False
        if term > self.state.current_term:
            self.state.voted_for = None
        self.state.current_term = term
        self.state.leader_id = leader_id
        self.state.role = NodeRole.FOLLOWER
        self.state.last_heartbeat_ts = time.monotonic()
        self._heard_from_leader = True  # 유효 리더 heartbeat → 선거 연기

        if prev_log_index is not None and prev_log_index >= 0:
            if prev_log_index >= len(self.state.log):
                return False  # 누락 구간 존재
            if self.state.log[prev_log_index].term != prev_log_term:
                return False  # 충돌 → 후퇴 요청
            self.state.log = self.state.log[: prev_log_index + 1]  # 충돌 tail 절단
        for e in entries:
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


class InProcessTransport:
    """동일 프로세스 내 노드들을 직접 호출로 연결하는 RaftTransport 구현.

    테스트·단일 호스트 다중 인스턴스 시뮬레이션용. 정지(`failed`)된 노드는
    도달 불가로 처리한다(RPC 타임아웃 모사).
    """

    def __init__(self) -> None:
        """``__init__`` 동작을 수행한다."""
        self._nodes: dict[str, AirspaceControllerHA] = {}
        self.failed: set[str] = set()

    def register(self, node: AirspaceControllerHA) -> None:
        """노드를 라우팅 테이블에 등록."""
        self._nodes[node.node_id] = node

    def request_vote(
        self, peer: str, candidate_id: str, term: int, last_log_index: int, last_log_term: int
    ) -> tuple[int, bool]:
        """대상 노드의 on_request_vote 직접 호출. 정지 노드는 (term, False)."""
        node = self._nodes.get(peer)
        if node is None or peer in self.failed:
            return term, False
        granted = node.on_request_vote(candidate_id, term, last_log_index, last_log_term)
        return node.state.current_term, granted

    def append_entries(
        self,
        peer: str,
        leader_id: str,
        term: int,
        entries: list[LogEntry],
        commit_index: int,
        prev_log_index: int,
        prev_log_term: int,
    ) -> tuple[int, bool]:
        """대상 노드의 on_append_entries 직접 호출. 정지 노드는 (term, False)."""
        node = self._nodes.get(peer)
        if node is None or peer in self.failed:
            return term, False
        ok = node.on_append_entries(
            leader_id, term, list(entries), commit_index, prev_log_index, prev_log_term,
        )
        return node.state.current_term, ok


class RaftCluster:
    """결정론적 in-process Raft 클러스터 — 선거·복제·페일오버 시뮬레이션.

    Usage:
        cluster = RaftCluster(["a", "b", "c"], seed=7)
        for now in range(0, 5000, 10):
            cluster.tick(now)
        leader = cluster.leader()
    """

    def __init__(self, node_ids: list[str], cfg: RaftConfig | None = None, seed: int = 0) -> None:
        """``__init__`` 동작을 수행한다."""
        self.transport = InProcessTransport()
        self.nodes: list[AirspaceControllerHA] = []
        for i, nid in enumerate(node_ids):
            peers = [p for p in node_ids if p != nid]
            node = AirspaceControllerHA(nid, peers, cfg=cfg, transport=self.transport, seed=seed + i)
            self.transport.register(node)
            self.nodes.append(node)
        for node in self.nodes:
            node.start()

    def tick(self, now_ms: float) -> None:
        """모든 살아있는 노드를 1스텝 진행."""
        for node in self.nodes:
            if node.node_id not in self.transport.failed:
                node.tick(now_ms)

    def leader(self) -> AirspaceControllerHA | None:
        """현재 살아있는 리더(없으면 None)."""
        for node in self.nodes:
            if node.is_leader() and node.node_id not in self.transport.failed:
                return node
        return None

    def fail(self, node_id: str) -> None:
        """노드 정지(네트워크 분리/크래시 모사)."""
        self.transport.failed.add(node_id)

    def recover(self, node_id: str) -> None:
        """정지 노드 복구."""
        self.transport.failed.discard(node_id)
