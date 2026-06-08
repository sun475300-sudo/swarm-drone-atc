"""P741: Raft 합의 기반 AirspaceController 다중 인스턴스 HA.

마스터 장애 시 <1s 내 새 리더 선출하여 무중단 운영.
NLB(Network Load Balancer) 뒤에 3-5 인스턴스 배치.

기존 `swarm_raft_consensus.py`(P641-650)를 controller-level로 격상.
"""
from __future__ import annotations

import time
from collections.abc import Callable
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

    def __init__(self, node_id: str, peers: list[str], cfg: RaftConfig | None = None) -> None:
        """``__init__`` 동작을 수행한다."""
        self.node_id = node_id
        self.peers = peers
        self.cfg = cfg or RaftConfig()
        self.state = RaftState(node_id=node_id)
        self._running = False
        # 인메모리 클러스터 배선 — 결정론적 테스트/단일 프로세스 HA 시뮬레이션용.
        # 실제 분산 배포 시 동일 인터페이스를 네트워크 RPC stub으로 교체.
        self._peer_nodes: dict[str, AirspaceControllerHA] = {}
        self._alive = True
        self._now: Callable[[], float] = time.monotonic
        # 재현성: random.random() 대신 노드별 시드된 RNG (CLAUDE.md §11).
        self._rng = np.random.default_rng(abs(hash(node_id)) % (2**32))
        self._election_timeout_ms: int = self.cfg.election_timeout_ms[0]
        self._last_heartbeat_sent: float = 0.0

    def is_leader(self) -> bool:
        """현재 노드가 리더인지."""
        return self.state.role == NodeRole.LEADER

    def _live_peers(self) -> list[AirspaceControllerHA]:
        """응답 가능한(살아있는) 피어 노드 목록."""
        return [p for p in self._peer_nodes.values() if p is not None and p._alive]

    def _cluster_size(self) -> int:
        """전체 클러스터 노드 수 (자신 포함, 장애 노드 포함)."""
        return len(self._peer_nodes) + 1

    def _is_majority(self, votes: int) -> bool:
        """Raft quorum — 전체 노드의 과반(자신 포함)."""
        return votes > self._cluster_size() // 2

    def _reset_election_timeout(self) -> None:
        """선거 타임아웃을 (min, max) 범위에서 랜덤 재설정 — split-vote 회피."""
        lo, hi = self.cfg.election_timeout_ms
        self._election_timeout_ms = int(self._rng.integers(lo, hi + 1))

    def replicate(self, command: dict) -> bool:
        """리더만 호출. 명령을 로그에 추가하고 quorum 복제 후 커밋."""
        if not self.is_leader():
            return False
        entry = LogEntry(
            term=self.state.current_term,
            index=len(self.state.log),
            command=command,
        )
        prev_index = entry.index - 1
        prev_term = self.state.log[prev_index].term if prev_index >= 0 else 0
        self.state.log.append(entry)
        acks = 1  # 리더 자신
        for peer in self._live_peers():
            ok = peer.on_append_entries(
                leader_id=self.node_id,
                term=self.state.current_term,
                entries=[entry],
                commit_index=self.state.commit_index,
                prev_log_index=prev_index,
                prev_log_term=prev_term,
            )
            if ok:
                acks += 1
        if self._is_majority(acks):
            self.state.commit_index = entry.index
            # 커밋 확정을 다음 AppendEntries(하트비트)로 팔로워에 즉시 전파.
            self._send_heartbeats(self._now())
            return True
        return False

    def start(self) -> None:
        """Raft 노드 시작 — 타이머 초기화. tick()으로 선거/하트비트 구동."""
        self._running = True
        self.state.last_heartbeat_ts = self._now()
        self._reset_election_timeout()

    def stop(self) -> None:
        """노드 종료."""
        self._running = False

    def tick(self, now: float) -> None:
        """단일 스텝 진행 — 선거 타임아웃 감시 + 리더 하트비트 송신.

        스레드/asyncio 대신 외부 클럭 구동(step) 방식 — CI에서 결정론적.
        """
        if not self._running or not self._alive:
            return
        if self.is_leader():
            interval = self.cfg.heartbeat_interval_ms / 1000.0
            if now - self._last_heartbeat_sent >= interval:
                self._send_heartbeats(now)
            return
        timeout = self._election_timeout_ms / 1000.0
        if now - self.state.last_heartbeat_ts >= timeout:
            self._run_election(now)

    def _run_election(self, now: float) -> None:
        """선거 시작 — term 증가, 자기 투표, RequestVote 송신, 과반 시 리더."""
        self.state.role = NodeRole.CANDIDATE
        self.state.current_term += 1
        self.state.voted_for = self.node_id
        self.state.leader_id = None
        self.state.last_heartbeat_ts = now
        self._reset_election_timeout()
        last_index = self.state.log[-1].index if self.state.log else -1
        last_term = self.state.log[-1].term if self.state.log else 0
        votes = 1  # 자기 자신
        for peer in self._live_peers():
            if peer.on_request_vote(
                candidate_id=self.node_id,
                term=self.state.current_term,
                last_log_index=last_index,
                last_log_term=last_term,
            ):
                votes += 1
        if self._is_majority(votes):
            self._become_leader(now)

    def _become_leader(self, now: float) -> None:
        """리더 승격 + 즉시 하트비트로 권위 확립."""
        self.state.role = NodeRole.LEADER
        self.state.leader_id = self.node_id
        self._send_heartbeats(now)

    def _send_heartbeats(self, now: float) -> None:
        """살아있는 피어에 빈 AppendEntries(하트비트) 송신 — 선거 타이머 리셋."""
        self._last_heartbeat_sent = now
        prev_index = len(self.state.log) - 1
        prev_term = self.state.log[prev_index].term if prev_index >= 0 else 0
        for peer in self._live_peers():
            peer.on_append_entries(
                leader_id=self.node_id,
                term=self.state.current_term,
                entries=[],
                commit_index=self.state.commit_index,
                prev_log_index=prev_index,
                prev_log_term=prev_term,
            )

    def on_request_vote(self, candidate_id: str, term: int, last_log_index: int, last_log_term: int) -> bool:
        """RequestVote RPC handler."""
        # Raft §5.1: 더 높은 term 발견 시 즉시 step-down + 투표 기록 초기화.
        if term > self.state.current_term:
            self.state.current_term = term
            self.state.voted_for = None
            self.state.role = NodeRole.FOLLOWER
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
        self.state.last_heartbeat_ts = self._now()  # 투표 후 선거 타이머 리셋
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
        """AppendEntries RPC handler — heartbeat + 로그 복제.

        ``prev_log_index < 0`` 이면 일관성 검사를 생략(초기 동기화/단순 append).
        """
        if term < self.state.current_term:
            return False
        if term > self.state.current_term:
            self.state.voted_for = None  # 새 term 진입 시에만 투표 기록 초기화
        self.state.current_term = term
        self.state.leader_id = leader_id
        self.state.role = NodeRole.FOLLOWER
        self.state.last_heartbeat_ts = self._now()
        # Raft §5.3: prev_log_index 위치의 term 일치 검사 후 충돌 절단.
        if prev_log_index >= 0:
            if prev_log_index >= len(self.state.log):
                return False
            if self.state.log[prev_log_index].term != prev_log_term:
                return False
            del self.state.log[prev_log_index + 1:]
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
