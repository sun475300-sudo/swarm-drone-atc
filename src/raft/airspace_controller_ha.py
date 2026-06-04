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


class Transport(Protocol):
    """피어로의 Raft RPC 전달 추상화.

    실제 배포에서는 gRPC/HTTP로 구현하고, 단위 테스트에서는
    `InMemoryTransport`로 결정론적 검증한다. 합의 로직(quorum 커밋·로그
    일관성·리더 선출)을 네트워킹과 분리해 전송 계층 없이도 검증 가능하게 한다.
    """

    def send_append_entries(
        self,
        peer: str,
        leader_id: str,
        term: int,
        prev_log_index: int,
        prev_log_term: int,
        entries: list[LogEntry],
        commit_index: int,
    ) -> bool:
        """AppendEntries RPC를 ``peer``에 전달하고 ack(성공) 여부를 반환."""
        ...

    def send_request_vote(
        self,
        peer: str,
        candidate_id: str,
        term: int,
        last_log_index: int,
        last_log_term: int,
    ) -> bool:
        """RequestVote RPC를 ``peer``에 전달하고 vote granted 여부를 반환."""
        ...


class InMemoryTransport:
    """단위 테스트용 인-메모리 전송 — 피어 노드 핸들러를 직접 호출.

    `register(node)`로 등록된 노드들 사이에서 RPC를 동기 호출한다.
    """

    def __init__(self) -> None:
        """``__init__`` 동작을 수행한다."""
        self._nodes: dict[str, AirspaceControllerHA] = {}

    def register(self, node: AirspaceControllerHA) -> None:
        """클러스터에 노드를 등록한다."""
        self._nodes[node.node_id] = node

    def send_append_entries(
        self,
        peer: str,
        leader_id: str,
        term: int,
        prev_log_index: int,
        prev_log_term: int,
        entries: list[LogEntry],
        commit_index: int,
    ) -> bool:
        """등록된 ``peer`` 노드의 핸들러를 직접 호출한다."""
        node = self._nodes.get(peer)
        if node is None:
            return False
        return node.on_append_entries(
            leader_id=leader_id,
            term=term,
            entries=list(entries),
            commit_index=commit_index,
            prev_log_index=prev_log_index,
            prev_log_term=prev_log_term,
        )

    def send_request_vote(
        self,
        peer: str,
        candidate_id: str,
        term: int,
        last_log_index: int,
        last_log_term: int,
    ) -> bool:
        """등록된 ``peer`` 노드의 핸들러를 직접 호출한다."""
        node = self._nodes.get(peer)
        if node is None:
            return False
        return node.on_request_vote(
            candidate_id=candidate_id,
            term=term,
            last_log_index=last_log_index,
            last_log_term=last_log_term,
        )


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
        transport: Transport | None = None,
    ) -> None:
        """``__init__`` 동작을 수행한다."""
        self.node_id = node_id
        self.peers = peers
        self.cfg = cfg or RaftConfig()
        self.transport = transport
        self.state = RaftState(node_id=node_id)
        self._running = False

    def is_leader(self) -> bool:
        """현재 노드가 리더인지."""
        return self.state.role == NodeRole.LEADER

    def _majority(self) -> int:
        """과반(quorum) 정족수 — 자신 포함 클러스터 크기 기준."""
        cluster_size = len(self.peers) + 1
        return cluster_size // 2 + 1

    def replicate(self, command: dict) -> bool:
        """리더만 호출. 명령을 로그에 추가하고 quorum ack 시 커밋한다.

        피어 ack 수가 과반 미만이면 엔트리는 로그에 남되 커밋하지 않는다
        (Raft §5.3 — 다음 AppendEntries에서 재시도). 트랜스포트가 없으면
        단일 노드로 간주해 즉시 커밋한다.
        """
        if not self.is_leader():
            return False
        entry = LogEntry(
            term=self.state.current_term,
            index=len(self.state.log),
            command=command,
        )
        prev_log_index = entry.index - 1
        prev_log_term = self.state.log[prev_log_index].term if prev_log_index >= 0 else 0
        self.state.log.append(entry)

        acks = 1  # 자신의 로그 기록은 1표
        if self.peers and self.transport is not None:
            for peer in self.peers:
                granted = self.transport.send_append_entries(
                    peer=peer,
                    leader_id=self.node_id,
                    term=self.state.current_term,
                    prev_log_index=prev_log_index,
                    prev_log_term=prev_log_term,
                    entries=[entry],
                    commit_index=self.state.commit_index,
                )
                if granted:
                    acks += 1

        if acks >= self._majority():
            self.state.commit_index = entry.index
            return True
        return False

    def trigger_election(self) -> bool:
        """선거 타임아웃 만료 시 후보로 전환해 RequestVote를 모은다.

        과반 득표 시 리더로 승격하고 True를 반환한다. 결정론적 검증을 위해
        타이머가 아닌 명시 호출로 노출한다 (배포 시 watchdog가 호출).

        전제: 실제 선거 타임아웃 만료 시에만 호출해야 한다. term을 증가시키며
        새 term에서 자신에게 투표하므로, 동일 term 내 임의 재호출은 분할투표를
        유발할 수 있다 (watchdog가 타임아웃 게이트를 책임진다).
        """
        self.state.role = NodeRole.CANDIDATE
        self.state.current_term += 1
        self.state.voted_for = self.node_id
        last_log_index = self.state.log[-1].index if self.state.log else -1
        last_log_term = self.state.log[-1].term if self.state.log else 0

        votes = 1  # 자기 자신에게 투표
        if self.transport is not None:
            for peer in self.peers:
                granted = self.transport.send_request_vote(
                    peer=peer,
                    candidate_id=self.node_id,
                    term=self.state.current_term,
                    last_log_index=last_log_index,
                    last_log_term=last_log_term,
                )
                if granted:
                    votes += 1

        if votes >= self._majority():
            self.state.role = NodeRole.LEADER
            self.state.leader_id = self.node_id
            return True
        self.state.role = NodeRole.FOLLOWER
        return False

    def start(self) -> None:
        """Raft 노드 활성화 — 마지막 하트비트 시각 초기화.

        합의 로직(선거·복제·로그 일관성)은 트랜스포트 주입으로 동기 검증
        가능하며(``trigger_election``/``replicate``), 실제 배포의 백그라운드
        선거 watchdog·하트비트 송신·RPC 서버는 전송 계층(gRPC/HTTP)에 위임한다.
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
        # Raft §5.1: 상위 term 관측 시 즉시 term 갱신 + 이전 vote 무효화
        # (새 term에서는 한 번도 투표하지 않은 상태가 되어야 적법한 후보를 막지 않음)
        if term > self.state.current_term:
            self.state.current_term = term
            self.state.voted_for = None
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
        """AppendEntries RPC handler — heartbeat + 로그 복제.

        Raft §5.3 로그 일관성: ``prev_log_index``가 가리키는 엔트리의 term이
        ``prev_log_term``과 일치하지 않으면 거부한다. 충돌하는 기존 엔트리는
        잘라내고 새 엔트리를 이어 붙인다.
        """
        if term < self.state.current_term:
            return False
        self.state.current_term = term
        self.state.leader_id = leader_id
        self.state.role = NodeRole.FOLLOWER
        self.state.last_heartbeat_ts = time.monotonic()

        # 로그 일관성 검사 (prev_log_index >= 0 일 때만 — 첫 엔트리는 검사 생략)
        if prev_log_index >= 0:
            if prev_log_index >= len(self.state.log):
                return False
            if self.state.log[prev_log_index].term != prev_log_term:
                return False

        # 충돌 엔트리 절단 후 append (idempotent — 동일 term 엔트리는 보존)
        for offset, entry in enumerate(entries):
            idx = prev_log_index + 1 + offset
            if idx < len(self.state.log):
                if self.state.log[idx].term != entry.term:
                    del self.state.log[idx:]
                    self.state.log.append(entry)
            else:
                self.state.log.append(entry)

        # leaderCommit 반영 — 빈 로그에서 -1로 퇴행하지 않도록 가드
        if self.state.log and commit_index > self.state.commit_index:
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
