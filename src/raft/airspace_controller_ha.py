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


class RaftTransport(Protocol):
    """peer 노드로 Raft RPC를 전달하는 전송 계층.

    인프로세스(`RaftCluster`)는 직접 메서드 호출로, 실 배포는 gRPC/HTTP로 구현.
    down 상태인 peer는 False를 반환(타임아웃 등가).
    """

    def request_vote(
        self, target: str, *, candidate_id: str, term: int, last_log_index: int, last_log_term: int,
    ) -> bool:
        """``request_vote`` RPC를 target 노드로 전달한다."""
        ...

    def append_entries(
        self, target: str, *, leader_id: str, term: int, entries: list[LogEntry], commit_index: int,
    ) -> bool:
        """``append_entries`` RPC를 target 노드로 전달한다."""
        ...


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
        self._transport: RaftTransport | None = None

    def set_transport(self, transport: RaftTransport) -> None:
        """peer RPC 전송 계층을 주입한다 (`RaftCluster`가 노드를 연결)."""
        self._transport = transport

    def is_leader(self) -> bool:
        """현재 노드가 리더인지."""
        return self.state.role == NodeRole.LEADER

    def _quorum(self) -> int:
        """과반 수 — self 포함 (peers + 1) 노드 중 majority."""
        return (len(self.peers) + 1) // 2 + 1

    def trigger_election(self) -> bool:
        """선거 시작 — 후보 전환 후 peer 투표 수집, 과반 시 리더 등극.

        반환: 리더가 되었으면 True.
        """
        self.state.role = NodeRole.CANDIDATE
        self.state.current_term += 1
        self.state.voted_for = self.node_id
        votes = 1  # 자기 자신
        last = self.state.log[-1] if self.state.log else None
        last_index = last.index if last else 0
        last_term = last.term if last else 0
        if self._transport is not None:
            for peer in self.peers:
                if self._transport.request_vote(
                    peer,
                    candidate_id=self.node_id,
                    term=self.state.current_term,
                    last_log_index=last_index,
                    last_log_term=last_term,
                ):
                    votes += 1
        if votes >= self._quorum():
            self.state.role = NodeRole.LEADER
            self.state.leader_id = self.node_id
            self._send_heartbeat()
            return True
        self.state.role = NodeRole.FOLLOWER
        return False

    def _send_heartbeat(self) -> None:
        """리더가 전체 peer에 빈 AppendEntries(하트비트)를 전송."""
        if self._transport is None:
            return
        for peer in self.peers:
            self._transport.append_entries(
                peer,
                leader_id=self.node_id,
                term=self.state.current_term,
                entries=[],
                commit_index=self.state.commit_index,
            )

    def replicate(self, command: dict) -> bool:
        """리더만 호출. 명령을 로그에 추가 후 peer 과반 ack 시 commit."""
        if not self.is_leader():
            return False
        entry = LogEntry(
            term=self.state.current_term,
            index=len(self.state.log),
            command=command,
        )
        self.state.log.append(entry)
        acks = 1  # 자기 자신
        if self._transport is not None:
            for peer in self.peers:
                if self._transport.append_entries(
                    peer,
                    leader_id=self.node_id,
                    term=self.state.current_term,
                    entries=[entry],
                    commit_index=self.state.commit_index,
                ):
                    acks += 1
        if acks >= self._quorum():
            self.state.commit_index = entry.index
            # 갱신된 commit_index를 follower에 전파 (Raft §5.3 leaderCommit).
            self._send_heartbeat()
            return True
        return False

    def start(self) -> None:
        """Raft 노드 활성화 + election deadline 초기화.

        분산 합의 루프는 `RaftCluster`(인프로세스 결정론적 오케스트레이션)가
        `trigger_election`/`replicate`로 구동한다. 실 배포 시 이 transport를
        asyncio/gRPC 구현으로 교체한다.
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
            # 더 높은 term 관측 → 강등 + 투표 초기화 (Raft §5.1). 페일오버 재선거 필수.
            self.state.voted_for = None
            self.state.role = NodeRole.FOLLOWER
        self.state.current_term = term
        if self.state.voted_for is not None and self.state.voted_for != candidate_id:
            return False
        my_last_log = self.state.log[-1] if self.state.log else None
        if my_last_log:
            if last_log_term < my_last_log.term:
                return False
            if last_log_term == my_last_log.term and last_log_index < my_last_log.index:
                return False
        self.state.voted_for = candidate_id
        return True

    def on_append_entries(self, leader_id: str, term: int, entries: list[LogEntry], commit_index: int) -> bool:
        """AppendEntries RPC handler — heartbeat + 로그 복제."""
        if term < self.state.current_term:
            return False
        self.state.current_term = term
        self.state.leader_id = leader_id
        self.state.role = NodeRole.FOLLOWER
        self.state.last_heartbeat_ts = time.monotonic()
        # TODO: 로그 일관성 검사 + entries 추가
        for e in entries:
            self.state.log.append(e)
        if commit_index > self.state.commit_index and self.state.log:
            # 빈 로그(-1) 방지: 보유 엔트리 범위 내로만 commit_index 전진.
            self.state.commit_index = min(commit_index, len(self.state.log) - 1)
        return True


class RaftCluster:
    """인프로세스 Raft 클러스터 — 결정론적 선거·복제·페일오버 오케스트레이션.

    실 네트워크(asyncio/socket) 없이 노드 간 RPC를 직접 호출하여 리더 선출·
    로그 복제·마스터 페일오버를 단위 테스트 가능하게 한다. 자신이 곧 transport.

    Usage:
        cluster = RaftCluster(["ctrl-1", "ctrl-2", "ctrl-3"])
        leader = cluster.elect_leader()
        leader.replicate({"type": "advisory"})
        cluster.fail(leader.node_id)        # 마스터 장애
        new_leader = cluster.elect_leader()  # <1s 재선출
    """

    def __init__(self, node_ids: list[str], cfg: RaftConfig | None = None) -> None:
        """노드들을 생성·상호 연결하고 활성화한다."""
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("node_ids에 중복이 있습니다")
        self.cfg = cfg or RaftConfig()
        self.nodes: dict[str, AirspaceControllerHA] = {}
        self._down: set[str] = set()
        for nid in node_ids:
            peers = [p for p in node_ids if p != nid]
            self.nodes[nid] = AirspaceControllerHA(nid, peers=peers, cfg=self.cfg)
        for node in self.nodes.values():
            node.set_transport(self)
            node.start()

    def request_vote(
        self, target: str, *, candidate_id: str, term: int, last_log_index: int, last_log_term: int,
    ) -> bool:
        """down이 아닌 target에게 RequestVote 전달."""
        if target in self._down:
            return False
        return self.nodes[target].on_request_vote(
            candidate_id=candidate_id, term=term,
            last_log_index=last_log_index, last_log_term=last_log_term,
        )

    def append_entries(
        self, target: str, *, leader_id: str, term: int, entries: list[LogEntry], commit_index: int,
    ) -> bool:
        """down이 아닌 target에게 AppendEntries 전달."""
        if target in self._down:
            return False
        return self.nodes[target].on_append_entries(
            leader_id=leader_id, term=term, entries=entries, commit_index=commit_index,
        )

    def elect_leader(self, preferred: str | None = None) -> AirspaceControllerHA | None:
        """선거를 구동하여 새 리더를 선출. 살아있는 노드 중 후보를 고른다."""
        candidate_id = preferred
        if candidate_id is None or candidate_id in self._down:
            alive = [n for n in self.nodes if n not in self._down]
            if not alive:
                return None
            candidate_id = alive[0]
        self.nodes[candidate_id].trigger_election()
        return self.leader()

    def leader(self) -> AirspaceControllerHA | None:
        """현재 살아있는 리더 노드 (없으면 None)."""
        for node in self.nodes.values():
            if node.node_id not in self._down and node.is_leader():
                return node
        return None

    def fail(self, node_id: str) -> None:
        """노드를 down 처리 (마스터 장애 시뮬레이션)."""
        self._down.add(node_id)
        node = self.nodes[node_id]
        node.stop()
        node.state.role = NodeRole.FOLLOWER
        node.state.leader_id = None

    def recover(self, node_id: str) -> None:
        """down 노드를 복구."""
        self._down.discard(node_id)
        self.nodes[node_id].start()


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
