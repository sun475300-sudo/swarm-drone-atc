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
    commit_index: int = -1  # 0-based 로그 인덱스. -1 = 아직 커밋된 엔트리 없음
    last_applied: int = -1
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
        # 인메모리 클러스터(`RaftCluster`)가 설정. 없으면 단독 노드로 동작.
        self._cluster: "RaftCluster | None" = None

    def is_leader(self) -> bool:
        """현재 노드가 리더인지."""
        return self.state.role == NodeRole.LEADER

    # ── 클러스터 멤버십 헬퍼 ────────────────────────────────────────────
    def _cluster_size(self) -> int:
        """전체 클러스터 노드 수 (자신 포함). quorum 계산 기준."""
        return len(self.peers) + 1

    def _live_peers(self) -> "list[AirspaceControllerHA]":
        """현재 살아있는 peer 노드 객체 목록."""
        if self._cluster is None:
            return []
        return self._cluster.live_peer_nodes(self.node_id)

    def _last_log_meta(self) -> tuple[int, int]:
        """(마지막 로그 인덱스, term). 비어있으면 (-1, 0)."""
        if not self.state.log:
            return -1, 0
        last = self.state.log[-1]
        return last.index, last.term

    # ── 선거 (Raft §5.2) ────────────────────────────────────────────────
    def become_candidate(self) -> bool:
        """선거 시작 — term 증가·자기투표·RequestVote 브로드캐스트.

        과반 득표 시 리더로 승격하고 ``True`` 반환.
        """
        self.state.role = NodeRole.CANDIDATE
        self.state.current_term += 1
        self.state.voted_for = self.node_id
        self.state.leader_id = None
        votes = 1  # self-vote
        last_index, last_term = self._last_log_meta()
        for peer in self._live_peers():
            if peer.on_request_vote(
                self.node_id, self.state.current_term, last_index, last_term,
            ):
                votes += 1
        if votes > self._cluster_size() // 2:
            self._become_leader()
        else:
            self.state.role = NodeRole.FOLLOWER
        return self.is_leader()

    def _become_leader(self) -> None:
        """리더 승격 + 즉시 heartbeat로 권위 확립."""
        self.state.role = NodeRole.LEADER
        self.state.leader_id = self.node_id
        self._send_heartbeat()

    def _send_heartbeat(self) -> None:
        """살아있는 peer에 빈 AppendEntries(heartbeat) 전송."""
        prev_index, prev_term = self._last_log_meta()
        for peer in self._live_peers():
            peer.on_append_entries(
                self.node_id, self.state.current_term, [], self.state.commit_index,
                prev_log_index=prev_index, prev_log_term=prev_term,
            )

    def replicate(self, command: dict) -> bool:
        """리더만 호출. 명령을 로그에 append 후 quorum 복제.

        과반 ack 시 ``commit_index`` 전진 + ``True``, 미달 시 ``False``.
        """
        if not self.is_leader():
            return False
        prev_index, prev_term = self._last_log_meta()
        entry = LogEntry(
            term=self.state.current_term,
            index=len(self.state.log),
            command=command,
        )
        self.state.log.append(entry)
        acks = 1  # self
        for peer in self._live_peers():
            if peer.on_append_entries(
                self.node_id, self.state.current_term, [entry], self.state.commit_index,
                prev_log_index=prev_index, prev_log_term=prev_term,
            ):
                acks += 1
        if acks > self._cluster_size() // 2:
            self.state.commit_index = entry.index
            return True
        return False

    def start(self) -> None:
        """노드를 running 상태로 표시.

        합의(선거·heartbeat·복제)는 결정적 인메모리 ``RaftCluster``가
        in-process로 구동한다. 실제 네트워크 RPC 전송 계층은 본 시뮬레이션
        범위 밖이며, 운영 배포 시 gRPC/HTTP 어댑터로 대체한다.
        """
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
            # 더 높은 term 발견 → 갱신하고 이전 투표 초기화
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
        *,
        prev_log_index: int = -1,
        prev_log_term: int = 0,
    ) -> bool:
        """AppendEntries RPC handler — heartbeat + 로그 복제 (Raft §5.3).

        ``commit_index`` 는 리더의 commit_index(leaderCommit)이며, -1 은
        "아직 커밋된 엔트리 없음"을 뜻하는 0-based sentinel이다.
        """
        if term < self.state.current_term:
            return False
        # Raft §5.1: 더 높은(또는 같은) term의 합법적 리더는 무조건 인식한다.
        # 로그 불일치로 엔트리를 거부하더라도 term 갱신·리더 인식·타이머 리셋은
        # prev_log 검사보다 먼저 수행해야 한다 (그래야 stale 후보/리더가 강등됨).
        if term > self.state.current_term:
            self.state.voted_for = None
        self.state.current_term = term
        self.state.leader_id = leader_id
        self.state.role = NodeRole.FOLLOWER
        self.state.last_heartbeat_ts = time.monotonic()
        # 로그 일관성 검사 (Raft §5.3): prev_log 엔트리가 일치해야 엔트리 수용
        if prev_log_index >= 0:
            if prev_log_index >= len(self.state.log):
                return False
            if self.state.log[prev_log_index].term != prev_log_term:
                return False
        for e in entries:
            if e.index < len(self.state.log):
                self.state.log[e.index] = e  # 충돌 엔트리 덮어쓰기
            else:
                self.state.log.append(e)
        if commit_index > self.state.commit_index:
            self.state.commit_index = min(commit_index, len(self.state.log) - 1)
        return True


class RaftCluster:
    """결정적 인메모리 Raft 클러스터.

    노드 간 RPC를 네트워크 대신 직접 메서드 호출로 전달해 선거·복제·
    페일오버를 타이밍 플레이키니스 없이 재현한다. 테스트·시뮬레이션용.
    """

    def __init__(self, node_ids: list[str], cfg: RaftConfig | None = None) -> None:
        """``node_ids`` 로 노드를 생성하고 서로 peer로 연결한다."""
        self.nodes: dict[str, AirspaceControllerHA] = {}
        self._failed: set[str] = set()
        for nid in node_ids:
            peers = [p for p in node_ids if p != nid]
            node = AirspaceControllerHA(nid, peers, cfg)
            node._cluster = self
            self.nodes[nid] = node

    def live_peer_nodes(self, node_id: str) -> list[AirspaceControllerHA]:
        """``node_id`` 의 살아있는 peer 노드 객체."""
        node = self.nodes[node_id]
        return [
            self.nodes[p]
            for p in node.peers
            if p in self.nodes and p not in self._failed
        ]

    def fail(self, node_id: str) -> None:
        """노드를 장애 상태로 표시 (RPC 응답 중단)."""
        self._failed.add(node_id)
        node = self.nodes.get(node_id)
        if node is not None:
            node.state.role = NodeRole.FOLLOWER

    def recover(self, node_id: str) -> None:
        """장애 노드를 복구."""
        self._failed.discard(node_id)

    def leader(self) -> AirspaceControllerHA | None:
        """현재 살아있는 리더 노드 (없으면 None)."""
        for nid, node in self.nodes.items():
            if nid not in self._failed and node.is_leader():
                return node
        return None

    def elect_leader(self) -> AirspaceControllerHA | None:
        """살아있는 노드를 결정적 순서로 후보로 세워 리더 선출.

        이미 살아있는 리더가 있으면 불필요한 term 인플레이션을 막기 위해
        그대로 반환한다.
        """
        existing = self.leader()
        if existing is not None:
            return existing
        for nid, node in self.nodes.items():
            if nid in self._failed:
                continue
            if node.become_candidate():
                return node
        return None


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
