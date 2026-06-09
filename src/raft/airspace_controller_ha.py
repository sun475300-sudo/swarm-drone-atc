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

from src.raft.transport import (
    AppendEntriesArgs,
    AppendEntriesReply,
    RaftTransport,
    RequestVoteArgs,
    RequestVoteReply,
)


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
    commit_index: int = -1  # -1 = 아무것도 커밋 안 됨 (Raft 센티넬)
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
        transport: RaftTransport | None = None,
        seed: int | None = None,
    ) -> None:
        """``__init__`` 동작을 수행한다.

        Args:
            node_id: 노드 식별자.
            peers: 동료 노드 id 목록 (자신 제외).
            cfg: Raft 타이밍 설정.
            transport: RPC 전송 계층 (None이면 단독 노드, RPC 비활성).
            seed: 선거 타임아웃 난수 시드 (재현성).
        """
        self.node_id = node_id
        self.peers = peers
        self.cfg = cfg or RaftConfig()
        self.transport = transport
        self.state = RaftState(node_id=node_id)
        self._running = False
        self._rng = np.random.default_rng(seed)
        # 리더 전용: 각 피어의 다음 전송 인덱스 / 복제 확인 인덱스
        self.next_index: dict[str, int] = {}
        self.match_index: dict[str, int] = {}
        # 타이밍 (monotonic 또는 가상 시계 기준)
        self._now: float = 0.0  # tick/start가 갱신하는 최신 시각 (RPC 핸들러가 참조)
        self._election_deadline: float = 0.0
        self._last_heartbeat_sent: float = 0.0

    # ------------------------------------------------------------------
    # 상태 조회
    # ------------------------------------------------------------------
    def is_leader(self) -> bool:
        """현재 노드가 리더인지."""
        return self.state.role == NodeRole.LEADER

    def _last_log_index(self) -> int:
        """마지막 로그 인덱스 (없으면 -1)."""
        return len(self.state.log) - 1

    def _last_log_term(self) -> int:
        """마지막 로그 term (없으면 0)."""
        return self.state.log[-1].term if self.state.log else 0

    # ------------------------------------------------------------------
    # 생명주기 + 틱 루프
    # ------------------------------------------------------------------
    def start(self, now: float | None = None) -> None:
        """Raft 루프 시작 — 팔로워로 출발하고 선거 타임아웃 무장."""
        now = time.monotonic() if now is None else now
        self._now = now
        self._running = True
        self.state.role = NodeRole.FOLLOWER
        self.state.last_heartbeat_ts = now
        self._reset_election_deadline(now)

    def stop(self) -> None:
        """노드 종료."""
        self._running = False

    def tick(self, now: float) -> None:
        """가상 시계 ``now`` 기준 1스텝 진행.

        리더: 하트비트 주기 도래 시 AppendEntries 전송.
        팔로워/후보: 선거 타임아웃 경과 시 새 선거 개시.
        """
        if not self._running:
            return
        self._now = now
        if self.is_leader():
            if now - self._last_heartbeat_sent >= self.cfg.heartbeat_interval_ms / 1000.0:
                self._send_heartbeats(now)
        elif now >= self._election_deadline:
            self._start_election(now)

    def _reset_election_deadline(self, now: float | None = None) -> None:
        """랜덤화된 선거 타임아웃으로 데드라인 재설정 (split vote 회피)."""
        now = self._now if now is None else now
        lo, hi = self.cfg.election_timeout_ms
        timeout = self._rng.uniform(lo, hi) / 1000.0
        self._election_deadline = now + timeout

    # ------------------------------------------------------------------
    # 선거 (Raft §5.2)
    # ------------------------------------------------------------------
    def _start_election(self, now: float) -> None:
        """후보로 전환하여 RequestVote 수집 → 과반이면 리더."""
        self.state.role = NodeRole.CANDIDATE
        self.state.current_term += 1
        self.state.voted_for = self.node_id
        self.state.leader_id = None
        self._reset_election_deadline(now)

        votes = 1  # 자기 자신
        if self.transport is not None:
            args = RequestVoteArgs(
                term=self.state.current_term,
                candidate_id=self.node_id,
                last_log_index=self._last_log_index(),
                last_log_term=self._last_log_term(),
            )
            for peer in self.peers:
                reply = self.transport.request_vote(peer, args)
                if reply.term > self.state.current_term:
                    self._step_down(reply.term)
                    return
                if reply.granted:
                    votes += 1

        if votes * 2 > len(self.peers) + 1:
            self._become_leader(now)

    def _become_leader(self, now: float) -> None:
        """리더 등극 — 리더 상태 초기화 후 즉시 하트비트."""
        self.state.role = NodeRole.LEADER
        self.state.leader_id = self.node_id
        next_idx = len(self.state.log)
        self.next_index = dict.fromkeys(self.peers, next_idx)
        self.match_index = dict.fromkeys(self.peers, -1)
        self._send_heartbeats(now)

    def _step_down(self, term: int) -> None:
        """더 높은 term 발견 시 팔로워로 강등."""
        self.state.current_term = term
        self.state.role = NodeRole.FOLLOWER
        self.state.voted_for = None
        self.state.leader_id = None
        self._reset_election_deadline()

    # ------------------------------------------------------------------
    # 로그 복제 (Raft §5.3)
    # ------------------------------------------------------------------
    def replicate(self, command: dict) -> bool:
        """리더만 호출. 명령을 로그에 추가하고 피어로 복제."""
        if not self.is_leader():
            return False
        entry = LogEntry(
            term=self.state.current_term,
            index=len(self.state.log),
            command=command,
        )
        self.state.log.append(entry)
        if self.transport is not None:
            for peer in self.peers:
                self._replicate_to_peer(peer)
            self._advance_commit_index()
        else:
            # 단독 노드: 즉시 커밋
            self.state.commit_index = entry.index
        return True

    def _send_heartbeats(self, now: float) -> None:
        """모든 피어로 AppendEntries(하트비트/로그) 전송 후 커밋 전진."""
        self._last_heartbeat_sent = now
        if self.transport is None:
            return
        for peer in self.peers:
            self._replicate_to_peer(peer)
        self._advance_commit_index()

    def _replicate_to_peer(self, peer: str) -> None:
        """단일 피어로 AppendEntries 전송 + next/match 인덱스 갱신."""
        assert self.transport is not None
        prev_index = self.next_index.get(peer, len(self.state.log)) - 1
        prev_term = self.state.log[prev_index].term if prev_index >= 0 else 0
        entries = self.state.log[prev_index + 1:]
        args = AppendEntriesArgs(
            term=self.state.current_term,
            leader_id=self.node_id,
            prev_log_index=prev_index,
            prev_log_term=prev_term,
            entries=list(entries),
            leader_commit=self.state.commit_index,
        )
        reply = self.transport.append_entries(peer, args)
        if reply.term > self.state.current_term:
            self._step_down(reply.term)
            return
        if reply.success:
            self.match_index[peer] = reply.match_index
            self.next_index[peer] = reply.match_index + 1
        else:
            # 로그 불일치 → backtrack
            self.next_index[peer] = max(0, self.next_index.get(peer, 1) - 1)

    def _advance_commit_index(self) -> None:
        """과반이 복제한 가장 높은 (현재 term) 인덱스로 commit_index 전진."""
        if not self.is_leader():
            return
        indices = sorted(
            [self._last_log_index()] + [self.match_index.get(p, -1) for p in self.peers],
            reverse=True,
        )
        majority_index = indices[len(indices) // 2]
        if (
            majority_index > self.state.commit_index
            and majority_index >= 0
            and self.state.log[majority_index].term == self.state.current_term
        ):
            self.state.commit_index = majority_index

    # ------------------------------------------------------------------
    # RPC 핸들러 (전송 계층이 호출)
    # ------------------------------------------------------------------
    def handle_request_vote(self, args: RequestVoteArgs) -> RequestVoteReply:
        """RequestVote RPC 핸들러 — 자격 충족 시 투표."""
        if args.term > self.state.current_term:
            self._step_down(args.term)  # leader_id 초기화 + 선거 데드라인 리셋 포함
        granted = self._is_vote_eligible(args)
        if granted:
            self.state.voted_for = args.candidate_id
            self.state.current_term = args.term
            self._reset_election_deadline()
        return RequestVoteReply(term=self.state.current_term, granted=granted)

    def _is_vote_eligible(self, args: RequestVoteArgs) -> bool:
        """Raft §5.2 투표 자격 판정."""
        if args.term < self.state.current_term:
            return False
        if self.state.voted_for is not None and self.state.voted_for != args.candidate_id:
            return False
        # 후보 로그가 최소한 나만큼 최신이어야 함
        if args.last_log_term < self._last_log_term():
            return False
        if args.last_log_term == self._last_log_term() and args.last_log_index < self._last_log_index():
            return False
        return True

    def handle_append_entries(self, args: AppendEntriesArgs) -> AppendEntriesReply:
        """AppendEntries RPC 핸들러 — 로그 일관성 검사 + 복제 + 커밋."""
        if args.term < self.state.current_term:
            return AppendEntriesReply(term=self.state.current_term, success=False)
        if args.term > self.state.current_term:
            self._step_down(args.term)
        self.state.current_term = args.term
        self.state.role = NodeRole.FOLLOWER
        self.state.leader_id = args.leader_id
        self.state.last_heartbeat_ts = self._now
        self._reset_election_deadline()

        # 로그 일관성: prev_log_index 위치의 term 일치 확인
        if args.prev_log_index >= 0 and (
            len(self.state.log) <= args.prev_log_index
            or self.state.log[args.prev_log_index].term != args.prev_log_term
        ):
            return AppendEntriesReply(term=self.state.current_term, success=False)

        # 일치하는 prefix는 보존하고 충돌 지점부터만 절단·추가 (Raft §5.3).
        # 빈 entries(순수 하트비트)는 기존 로그 꼬리를 지우지 않는다.
        insert_at = args.prev_log_index + 1
        for i, entry in enumerate(args.entries):
            pos = insert_at + i
            if pos >= len(self.state.log):
                self.state.log.extend(args.entries[i:])
                break
            if self.state.log[pos].term != entry.term:
                del self.state.log[pos:]
                self.state.log.extend(args.entries[i:])
                break
        if args.leader_commit > self.state.commit_index:
            self.state.commit_index = min(args.leader_commit, self._last_log_index())
        return AppendEntriesReply(
            term=self.state.current_term,
            success=True,
            match_index=self._last_log_index(),
        )

    # ------------------------------------------------------------------
    # 하위 호환 래퍼 (기존 단위 테스트 시그니처 유지)
    # ------------------------------------------------------------------
    def on_request_vote(self, candidate_id: str, term: int, last_log_index: int, last_log_term: int) -> bool:
        """RequestVote RPC handler (레거시 시그니처)."""
        reply = self.handle_request_vote(
            RequestVoteArgs(
                term=term,
                candidate_id=candidate_id,
                last_log_index=last_log_index,
                last_log_term=last_log_term,
            )
        )
        return reply.granted

    def on_append_entries(self, leader_id: str, term: int, entries: list[LogEntry], commit_index: int) -> bool:
        """AppendEntries RPC handler (레거시 시그니처 — 일관성 검사 생략 append)."""
        if term < self.state.current_term:
            return False
        self.state.current_term = term
        self.state.leader_id = leader_id
        self.state.role = NodeRole.FOLLOWER
        self.state.last_heartbeat_ts = time.monotonic()
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
