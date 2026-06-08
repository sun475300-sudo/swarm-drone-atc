"""P741: Raft 합의 기반 AirspaceController 다중 인스턴스 HA.

마스터 장애 시 <1s 내 새 리더 선출하여 무중단 운영.
NLB(Network Load Balancer) 뒤에 3-5 인스턴스 배치.

기존 `swarm_raft_consensus.py`(P641-650)를 controller-level로 격상.

합의 루프는 결정론적 in-process 모델로 구현한다. `connect()`로 같은
호스트의 노드를 직접 연결하면 RPC가 동기 메서드 호출이 되어 단위 테스트에서
선거·quorum 복제·페일오버를 타이밍 의존 없이 검증할 수 있다. FSM 진행은
백그라운드 스레드 대신 `tick(now)`가 구동한다(테스트 결정성 + 운영 시
이벤트 루프에서 호출).
"""
from __future__ import annotations

import copy
import hashlib
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
    commit_index: int = -1  # -1 = 아무것도 커밋 안 됨 (index 0 커밋과 구분)
    last_applied: int = 0
    leader_id: str | None = None
    last_heartbeat_ts: float = 0.0


@dataclass(frozen=True)
class RaftConfig:
    """Raft 타이밍 설정."""

    election_timeout_ms: tuple[int, int] = (150, 300)  # randomized
    heartbeat_interval_ms: int = 50
    rpc_timeout_ms: int = 100


def _stable_timeout_ms(node_id: str, bounds: tuple[int, int]) -> float:
    """node_id로 결정론적 election timeout 산출.

    프로세스 간 안정적(해시 시드 무관)이며 노드마다 서로 다른 값을 줘
    split-vote 확률을 낮춘다. `random.random()` 대신 SHA-256 기반 결정론 사용.
    """
    lo, hi = bounds
    digest = int(hashlib.sha256(node_id.encode()).hexdigest(), 16)
    span = max(1, hi - lo)
    return float(lo + (digest % span))


class AirspaceControllerHA:
    """HA AirspaceController — Raft 합의로 명령 복제.

    Usage:
        n1 = AirspaceControllerHA("ctrl-1", peers=["ctrl-2", "ctrl-3"])
        n2 = AirspaceControllerHA("ctrl-2", peers=["ctrl-1", "ctrl-3"])
        n3 = AirspaceControllerHA("ctrl-3", peers=["ctrl-1", "ctrl-2"])
        cluster = {n.node_id: n for n in (n1, n2, n3)}
        for n in cluster.values():
            n.connect(cluster)
            n.start()
        n1.start_election()
        if n1.is_leader():
            n1.replicate(command={"type": "advisory", ...})
    """

    def __init__(self, node_id: str, peers: list[str], cfg: RaftConfig | None = None) -> None:
        """``__init__`` 동작을 수행한다."""
        self.node_id = node_id
        self.peers = peers
        self.cfg = cfg or RaftConfig()
        self.state = RaftState(node_id=node_id)
        self._running = False
        # in-process 피어 레지스트리 (node_id -> 노드). connect()로 채운다.
        self._peer_nodes: dict[str, AirspaceControllerHA] = {}
        self._election_timeout_ms = _stable_timeout_ms(node_id, self.cfg.election_timeout_ms)
        self._last_heartbeat_sent_ts = 0.0

    # ── 클러스터 연결 ────────────────────────────────────────────────
    def connect(self, nodes: dict[str, AirspaceControllerHA]) -> None:
        """같은 호스트의 다른 노드를 in-process 피어로 등록.

        RPC가 동기 메서드 호출이 되어 결정론적 합의 검증이 가능하다.
        """
        self._peer_nodes = {nid: n for nid, n in nodes.items() if nid != self.node_id}

    @property
    def cluster_size(self) -> int:
        """전체 클러스터 노드 수 (self 포함)."""
        return len(self.peers) + 1

    def _majority(self) -> int:
        """commit/선거에 필요한 최소 표 수 (과반)."""
        return self.cluster_size // 2 + 1

    def is_leader(self) -> bool:
        """현재 노드가 리더인지."""
        return self.state.role == NodeRole.LEADER

    # ── 명령 복제 ────────────────────────────────────────────────────
    def replicate(self, command: dict) -> bool:
        """리더만 호출. 명령을 AppendEntries로 팬아웃하여 quorum 합의 시 commit."""
        if not self.is_leader():
            return False
        entry = LogEntry(
            term=self.state.current_term,
            index=len(self.state.log),
            command=command,
        )
        self.state.log.append(entry)

        prev_index = entry.index - 1
        prev_term = self.state.log[prev_index].term if prev_index >= 0 else 0
        acks = 1  # self
        for node in self._peer_nodes.values():
            ok = node.on_append_entries(
                leader_id=self.node_id,
                term=self.state.current_term,
                entries=[entry],
                commit_index=self.state.commit_index,
                prev_log_index=prev_index,
                prev_log_term=prev_term,
            )
            if ok:
                acks += 1

        if acks >= self._majority():
            self.state.commit_index = entry.index
            # 팔로워에 commit_index 전파 (다음 heartbeat가 반영)
            self._advance_followers_commit()
            return True
        return False

    def _advance_followers_commit(self) -> None:
        """커밋 후 빈 AppendEntries(heartbeat)로 commit_index 전파."""
        for node in self._peer_nodes.values():
            node.on_append_entries(
                leader_id=self.node_id,
                term=self.state.current_term,
                entries=[],
                commit_index=self.state.commit_index,
            )

    # ── 선거 ─────────────────────────────────────────────────────────
    def start_election(self) -> None:
        """election timeout 만료 시 호출. 새 term으로 후보가 되어 표를 모은다."""
        if self.is_leader():
            return  # 리더는 선거를 시작하지 않는다 (Raft §5.2)
        self.state.current_term += 1
        self.state.role = NodeRole.CANDIDATE
        self.state.voted_for = self.node_id
        self.state.leader_id = None
        self.state.last_heartbeat_ts = time.monotonic()

        last = self.state.log[-1] if self.state.log else None
        last_index = last.index if last else -1
        last_term = last.term if last else 0

        votes = 1  # self
        for node in self._peer_nodes.values():
            granted = node.on_request_vote(
                candidate_id=self.node_id,
                term=self.state.current_term,
                last_log_index=last_index,
                last_log_term=last_term,
            )
            if granted:
                votes += 1

        if votes >= self._majority():
            self._become_leader()

    def _become_leader(self) -> None:
        """리더 승격 + 초기 heartbeat 송신."""
        self.state.role = NodeRole.LEADER
        self.state.leader_id = self.node_id
        self._send_heartbeats()

    def _send_heartbeats(self) -> None:
        """팔로워 election timeout 리셋용 빈 AppendEntries 송신."""
        for node in self._peer_nodes.values():
            node.on_append_entries(
                leader_id=self.node_id,
                term=self.state.current_term,
                entries=[],
                commit_index=self.state.commit_index,
            )

    # ── 결정론적 FSM 진행 ───────────────────────────────────────────
    def tick(self, now: float | None = None) -> None:
        """FSM 1스텝. 리더면 heartbeat, 그 외엔 election timeout 검사.

        백그라운드 스레드 대신 운영 이벤트 루프/테스트가 주기적으로 호출한다.
        """
        if not self._running:
            return
        clock = now if now is not None else time.monotonic()
        if self.state.role == NodeRole.LEADER:
            # heartbeat_interval_ms 주기로만 송신 (과도한 RPC 방지)
            if (clock - self._last_heartbeat_sent_ts) * 1000.0 >= self.cfg.heartbeat_interval_ms:
                self._send_heartbeats()
                self._last_heartbeat_sent_ts = clock
            return
        elapsed_ms = (clock - self.state.last_heartbeat_ts) * 1000.0
        if elapsed_ms >= self._election_timeout_ms:
            self.start_election()

    def start(self) -> None:
        """Raft FSM 활성화. 이후 진행은 `tick()`이 구동한다."""
        self._running = True
        self.state.last_heartbeat_ts = time.monotonic()

    def stop(self) -> None:
        """노드 종료."""
        self._running = False

    # ── RPC 핸들러 ───────────────────────────────────────────────────
    def on_request_vote(self, candidate_id: str, term: int, last_log_index: int, last_log_term: int) -> bool:
        """RequestVote RPC handler."""
        # Raft §5.2: vote granted if (term ≥ self.term) ∧ (haven't voted) ∧ (log up-to-date)
        if term < self.state.current_term:
            return False
        # 더 높은 term을 보면 step-down하고 vote 가능 상태로 리셋
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
        """AppendEntries RPC handler — heartbeat + 로그 복제.

        `prev_log_index < 0`이면 일관성 검사를 건너뛴다(heartbeat / 초기 복제).
        """
        if term < self.state.current_term:
            return False
        if term > self.state.current_term:
            self.state.voted_for = None
        self.state.current_term = term
        self.state.leader_id = leader_id
        self.state.role = NodeRole.FOLLOWER
        self.state.last_heartbeat_ts = time.monotonic()

        # Raft §5.3: entries를 실어 나르면 항상 일관성 검사 (heartbeat=빈 entries는 skip).
        # prev_log_index < 0 → entries가 index 0부터 시작함을 의미.
        if entries:
            if prev_log_index >= len(self.state.log):
                return False  # gap: 선행 엔트리 누락
            if prev_log_index >= 0 and self.state.log[prev_log_index].term != prev_log_term:
                return False  # prev 위치 term 불일치
            # 충돌 tail 절단 + 새 엔트리 추가 (불변 재구성, deepcopy로 leader와 객체 분리)
            self.state.log = (
                self.state.log[: prev_log_index + 1] + [copy.deepcopy(e) for e in entries]
            )

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
