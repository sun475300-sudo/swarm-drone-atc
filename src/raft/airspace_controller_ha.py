"""P741: Raft 합의 기반 AirspaceController 다중 인스턴스 HA.

마스터 장애 시 새 리더를 선출하여 무중단 운영.
NLB(Network Load Balancer) 뒤에 3-5 인스턴스 배치.

합의 루프는 논리 시계(`tick`) 기반으로 구현되어 실제 스레드/네트워크 없이
결정론적으로 재현·검증 가능하다. 노드 간 통신은 주입형 `transport` 콜러블로
추상화되며, 인메모리 클러스터(`raft_cluster.py`)가 이를 동기적으로 연결한다.

기존 `swarm_raft_consensus.py`(P641-650)를 controller-level로 격상.
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional


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


# transport(peer_id, rpc_type, payload) -> 응답 dict | None (None = 타임아웃/도달 불가)
Transport = Callable[[str, str, dict], Optional[dict]]


class AirspaceControllerHA:
    """HA AirspaceController — Raft 합의로 명령 복제.

    Usage:
        node = AirspaceControllerHA("ctrl-1", peers=["ctrl-2", "ctrl-3"])
        node.transport = my_transport          # 피어 RPC 라우팅
        node.start()
        node.tick()                            # 논리 시계 1틱 (선거/하트비트)
        if node.is_leader():
            node.replicate(command={"type": "advisory", ...})
    """

    def __init__(
        self,
        node_id: str,
        peers: list[str],
        cfg: RaftConfig | None = None,
        *,
        transport: Transport | None = None,
        seed: int | None = None,
    ) -> None:
        """``__init__`` 동작을 수행한다."""
        self.node_id = node_id
        self.peers = peers
        self.cfg = cfg or RaftConfig()
        self.state = RaftState(node_id=node_id)
        self._running = False
        self.transport: Transport | None = transport
        # 노드별로 다른(그러나 재현 가능한) 선거 타임아웃 지터 — split vote 완화
        base = seed if seed is not None else (hash(node_id) & 0xFFFFFFFF)
        self._rng = random.Random(base)
        self._ticks_since_heartbeat = 0
        self._election_timeout_ticks = self._random_election_timeout()

    # ── 타이밍 / 정족수 헬퍼 ────────────────────────────────────────────
    def _random_election_timeout(self) -> int:
        """선거 타임아웃을 틱 수로 변환 (heartbeat 간격 기준 지터)."""
        hb = max(1, self.cfg.heartbeat_interval_ms)
        lo = max(1, self.cfg.election_timeout_ms[0] // hb)
        hi = max(lo + 1, self.cfg.election_timeout_ms[1] // hb)
        return self._rng.randint(lo, hi)

    def _cluster_size(self) -> int:
        """설정된 클러스터 크기 (자신 포함). 정족수는 항상 이 값 기준."""
        return len(self.peers) + 1

    def _has_majority(self, count: int) -> bool:
        """정족수(과반) 도달 여부 — 살아있는 노드가 아닌 설정 크기 기준."""
        return count >= (self._cluster_size() // 2) + 1

    # ── 공개 API ────────────────────────────────────────────────────────
    def is_leader(self) -> bool:
        """현재 노드가 리더인지."""
        return self.state.role == NodeRole.LEADER

    def start(self) -> None:
        """Raft 노드 활성화. 이후 `tick()`으로 합의 루프를 구동한다."""
        self._running = True
        self.state.last_heartbeat_ts = time.monotonic()
        self._ticks_since_heartbeat = 0
        self._election_timeout_ticks = self._random_election_timeout()

    def stop(self) -> None:
        """노드 종료."""
        self._running = False

    def tick(self) -> None:
        """논리 시계 1틱 진행.

        본 모델에서 1틱 = heartbeat 간격(`heartbeat_interval_ms`)이다.
        선거 타임아웃(`_election_timeout_ticks`)도 heartbeat 간격 단위로 환산되므로
        (예: 150~300ms / 50ms = 3~6틱), 리더가 매 틱 하트비트를 보내는 것은
        의도된 동작이다. 그 외 노드는 선거 타임아웃을 감시하여 만료 시 선거를 시작한다.
        """
        if not self._running:
            return
        if self.is_leader():
            self._append_entries_to_peers([])  # heartbeat
            return
        self._ticks_since_heartbeat += 1
        if self._ticks_since_heartbeat >= self._election_timeout_ticks:
            self._start_election()

    def replicate(self, command: dict) -> bool:
        """리더만 호출. 명령을 로그에 추가하고 과반 복제 시 커밋."""
        if not self.is_leader():
            return False
        entry = LogEntry(
            term=self.state.current_term,
            index=len(self.state.log),
            command=command,
        )
        self.state.log.append(entry)
        acks = 1 + self._append_entries_to_peers([entry])  # 자신 포함
        if self._has_majority(acks):
            self.state.commit_index = entry.index
            return True
        return False

    # ── 선거 ────────────────────────────────────────────────────────────
    def _start_election(self) -> None:
        """CANDIDATE 전환 후 RequestVote를 피어에 전파, 과반 시 리더 승격."""
        self.state.role = NodeRole.CANDIDATE
        self.state.current_term += 1
        self.state.voted_for = self.node_id
        self._ticks_since_heartbeat = 0
        self._election_timeout_ticks = self._random_election_timeout()
        last = self.state.log[-1] if self.state.log else None
        payload = {
            "candidate_id": self.node_id,
            "term": self.state.current_term,
            "last_log_index": last.index if last else -1,
            "last_log_term": last.term if last else 0,
        }
        votes = 1  # self
        for peer in self.peers:
            resp = self._rpc(peer, "request_vote", payload)
            if resp is None:
                continue
            if resp.get("term", 0) > self.state.current_term:
                self._step_down(resp["term"])
                return
            if resp.get("vote_granted") and resp.get("term") == self.state.current_term:
                votes += 1
        # step-down으로 CANDIDATE가 아니게 됐을 수 있으므로 불변식 재확인
        if self.state.role == NodeRole.CANDIDATE and self._has_majority(votes):
            self._become_leader()

    def _become_leader(self) -> None:
        """리더 승격 후 즉시 하트비트로 권위 확립."""
        self.state.role = NodeRole.LEADER
        self.state.leader_id = self.node_id
        self._append_entries_to_peers([])

    def _step_down(self, term: int) -> None:
        """더 높은 term 발견 시 FOLLOWER로 강등."""
        self.state.current_term = term
        self.state.role = NodeRole.FOLLOWER
        self.state.voted_for = None
        self._ticks_since_heartbeat = 0

    # ── 복제 / 하트비트 (단일 경로) ─────────────────────────────────────
    def _append_entries_to_peers(self, entries: list[LogEntry]) -> int:
        """피어에 AppendEntries 송신 (빈 entries = 하트비트). ack 수 반환."""
        acks = 0
        for peer in self.peers:
            payload = {
                "leader_id": self.node_id,
                "term": self.state.current_term,
                "entries": list(entries),
                "commit_index": self.state.commit_index,
            }
            resp = self._rpc(peer, "append_entries", payload)
            if resp is None:
                continue
            if resp.get("term", 0) > self.state.current_term:
                self._step_down(resp["term"])
                return acks
            if resp.get("success"):
                acks += 1
        return acks

    def _rpc(self, peer: str, rpc_type: str, payload: dict) -> Optional[dict]:
        """transport를 통해 RPC 송신. transport 미설정 시 None."""
        if self.transport is None:
            return None
        return self.transport(peer, rpc_type, payload)

    # ── RPC 핸들러 (bool 반환 — 기존 단위 테스트 API 고정) ─────────────
    def on_request_vote(self, candidate_id: str, term: int, last_log_index: int, last_log_term: int) -> bool:
        """RequestVote RPC handler."""
        # Raft §5.1: 더 높은 term 발견 시 먼저 step-down (voted_for 초기화).
        # 누락 시 한 번 투표한 노드가 이후 임기에서 영구 거부 → 페일오버 데드락.
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
        self._ticks_since_heartbeat = 0  # 투표 부여 시 선거 타이머 리셋
        return True

    def on_append_entries(self, leader_id: str, term: int, entries: list[LogEntry], commit_index: int) -> bool:
        """AppendEntries RPC handler — heartbeat + 로그 복제."""
        if term < self.state.current_term:
            return False
        self.state.current_term = term
        self.state.leader_id = leader_id
        self.state.role = NodeRole.FOLLOWER
        self.state.last_heartbeat_ts = time.monotonic()
        self._ticks_since_heartbeat = 0
        for e in entries:
            if e.index >= len(self.state.log):  # 멱등 — 중복 하트비트 재전송 방지
                self.state.log.append(e)
        # commit_index는 로그에 엔트리가 있을 때만 전진 (빈 로그 하트비트로 오커밋 방지)
        if commit_index > self.state.commit_index and self.state.log:
            self.state.commit_index = min(commit_index, len(self.state.log) - 1)
        return True

    # ── RPC 래퍼 (transport용 dict 응답: 호출자가 term을 보고 step-down) ─
    def handle_request_vote_rpc(self, payload: dict) -> dict:
        """RequestVote를 처리하고 {vote_granted, term} 응답."""
        granted = self.on_request_vote(
            payload["candidate_id"],
            payload["term"],
            payload["last_log_index"],
            payload["last_log_term"],
        )
        return {"vote_granted": granted, "term": self.state.current_term}

    def handle_append_entries_rpc(self, payload: dict) -> dict:
        """AppendEntries를 처리하고 {success, term} 응답."""
        ok = self.on_append_entries(
            payload["leader_id"],
            payload["term"],
            payload["entries"],
            payload["commit_index"],
        )
        return {"success": ok, "term": self.state.current_term}


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
