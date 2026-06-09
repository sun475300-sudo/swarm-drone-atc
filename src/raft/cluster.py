"""P741: 결정론적 인프로세스 Raft 클러스터 시뮬레이터.

`AirspaceControllerHA` 노드들의 RPC 핸들러(``on_request_vote`` /
``on_append_entries``)를 네트워크 없이 인프로세스로 라우팅하여 **실제 선거 ·
하트비트 · quorum 복제 · 페일오버**를 구동한다.

기존 노드 구현은 RPC 핸들러만 제공할 뿐 이를 호출하는 합의 루프가 없었다
(``start()`` 가 스텁). 이 클러스터가 그 루프를 담당한다.

재현성(CLAUDE.md §11): wall-clock 대신 시뮬레이션 시계(``now_ms``)를 사용하고
election timeout 무작위화는 ``np.random.default_rng(seed)`` 로 고정한다.
스레드/asyncio 대신 tick 기반 단일 스레드 진행 → 결정론적·테스트 가능.

Usage:
    cluster = RaftCluster(["ctrl-1", "ctrl-2", "ctrl-3"], seed=42)
    leader = cluster.run_until_leader()
    cluster.propose({"type": "advisory", "drone_id": "DR-001"})
    cluster.kill(leader.node_id)          # 리더 장애 주입
    new_leader = cluster.run_until_leader()  # <1s 내 페일오버
"""
from __future__ import annotations

import numpy as np

from src.raft.airspace_controller_ha import (
    AirspaceControllerHA,
    LogEntry,
    NodeRole,
    RaftConfig,
)


class RaftCluster:
    """인프로세스 Raft 노드 집합의 결정론적 합의 드라이버."""

    def __init__(
        self,
        node_ids: list[str],
        seed: int = 0,
        cfg: RaftConfig | None = None,
    ) -> None:
        """``node_ids`` 멤버십으로 클러스터를 구성한다.

        Args:
            node_ids: 노드 식별자 목록 (최소 1개).
            seed: election timeout 무작위화 시드 (재현성).
            cfg: Raft 타이밍 설정 (election/heartbeat 간격).
        """
        if not node_ids:
            raise ValueError("RaftCluster requires at least one node")
        if len(set(node_ids)) != len(node_ids):
            raise ValueError("node_ids must be unique")
        self.cfg = cfg or RaftConfig()
        self._rng = np.random.default_rng(seed)
        self.nodes: dict[str, AirspaceControllerHA] = {
            nid: AirspaceControllerHA(
                nid, peers=[p for p in node_ids if p != nid], cfg=self.cfg
            )
            for nid in node_ids
        }
        self._alive: dict[str, bool] = {nid: True for nid in node_ids}
        self.now_ms: float = 0.0
        self._election_deadline: dict[str, float] = {}
        self._last_heartbeat_ms: float = -1e9
        for nid in node_ids:
            node = self.nodes[nid]
            node.start()
            self._reset_election_timer(nid)

    # ── 멤버십 / 조회 ────────────────────────────────────────────────

    @property
    def majority(self) -> int:
        """전체 멤버십 기준 과반 정족수."""
        return len(self.nodes) // 2 + 1

    def leader(self) -> AirspaceControllerHA | None:
        """현재 살아있는 리더 노드 (없으면 None)."""
        for nid, node in self.nodes.items():
            if self._alive[nid] and node.is_leader():
                return node
        return None

    def alive_node_ids(self) -> list[str]:
        """살아있는 노드 ID 목록."""
        return [nid for nid, ok in self._alive.items() if ok]

    # ── 장애 주입 ────────────────────────────────────────────────────

    def kill(self, node_id: str) -> None:
        """노드를 정지(파티션/크래시)시킨다 — 페일오버 유발."""
        self._validate(node_id)
        self._alive[node_id] = False
        self.nodes[node_id].stop()

    def revive(self, node_id: str) -> None:
        """정지된 노드를 FOLLOWER로 복귀시킨다."""
        self._validate(node_id)
        self._alive[node_id] = True
        node = self.nodes[node_id]
        node.state.role = NodeRole.FOLLOWER
        node.start()
        self._reset_election_timer(node_id)

    # ── 합의 루프 구동 ───────────────────────────────────────────────

    def tick(self, dt_ms: float | None = None) -> None:
        """시뮬레이션 시계를 ``dt_ms`` 만큼 진행하고 합의 이벤트를 처리한다.

        1. 리더가 있으면 heartbeat 주기마다 AppendEntries(빈 엔트리) 방송.
        2. heartbeat를 받지 못한 follower/candidate는 election timeout 시 선거 개시.
        """
        if dt_ms is None:
            dt_ms = float(self.cfg.heartbeat_interval_ms)
        self.now_ms += dt_ms

        leader = self.leader()
        if leader is not None:
            if self.now_ms - self._last_heartbeat_ms >= self.cfg.heartbeat_interval_ms:
                self._send_heartbeats(leader)
                self._last_heartbeat_ms = self.now_ms

        # election timeout 검사 (리더 제외, 데드라인이 빠른 순으로 결정론적 처리)
        candidates = [
            nid
            for nid in sorted(
                self.alive_node_ids(), key=lambda n: self._election_deadline[n]
            )
            if not self.nodes[nid].is_leader()
            and self.now_ms >= self._election_deadline[nid]
        ]
        for nid in candidates:
            if self.leader() is None:
                self._start_election(nid)
            else:
                # 이번 tick에 이미 새 리더가 섰으면 타이머만 갱신
                self._reset_election_timer(nid)

    def run_until_leader(
        self, max_ticks: int = 1000, dt_ms: float | None = None
    ) -> AirspaceControllerHA:
        """리더가 선출될 때까지 tick을 반복한다.

        Returns:
            선출된 리더 노드.

        Raises:
            RuntimeError: ``max_ticks`` 안에 리더가 서지 않으면.
        """
        for _ in range(max_ticks):
            if self.leader() is not None:
                return self.leader()  # type: ignore[return-value]
            self.tick(dt_ms)
        leader = self.leader()
        if leader is None:
            raise RuntimeError(
                f"no leader elected within {max_ticks} ticks "
                f"(alive={self.alive_node_ids()})"
            )
        return leader

    def propose(self, command: dict) -> bool:
        """리더를 통해 명령을 quorum 복제한다.

        과반 노드가 복제를 ack하면 커밋하고 ``True``, 아니면 ``False``.
        """
        leader = self.leader()
        if leader is None:
            return False
        entry = LogEntry(
            term=leader.state.current_term,
            index=len(leader.state.log),
            command=command,
        )
        leader.state.log.append(entry)
        acks = 1  # 리더 자신
        for nid in self.alive_node_ids():
            if nid == leader.node_id:
                continue
            ok = self.nodes[nid].on_append_entries(
                leader_id=leader.node_id,
                term=leader.state.current_term,
                entries=[entry],
                commit_index=entry.index,
            )
            if ok:
                acks += 1
        if acks >= self.majority:
            leader.state.commit_index = entry.index
            return True
        return False

    # ── 내부 구현 ────────────────────────────────────────────────────

    def _start_election(self, candidate_id: str) -> None:
        """후보 노드의 선거: term 증가 → 자기 투표 → 과반 득표 시 리더 등극."""
        candidate = self.nodes[candidate_id]
        candidate.state.role = NodeRole.CANDIDATE
        candidate.state.current_term += 1
        candidate.state.voted_for = candidate_id
        candidate.state.leader_id = None
        term = candidate.state.current_term
        last = candidate.state.log[-1] if candidate.state.log else None
        last_index = last.index if last else -1
        last_term = last.term if last else 0

        votes = 1  # 자기 자신
        for nid in self.alive_node_ids():
            if nid == candidate_id:
                continue
            granted = self.nodes[nid].on_request_vote(
                candidate_id=candidate_id,
                term=term,
                last_log_index=last_index,
                last_log_term=last_term,
            )
            if granted:
                votes += 1

        if votes >= self.majority:
            candidate.state.role = NodeRole.LEADER
            candidate.state.leader_id = candidate_id
            self._send_heartbeats(candidate)
            self._last_heartbeat_ms = self.now_ms
        # 승리하지 못했으면 데드라인을 새로 잡아 split vote 후 재시도
        self._reset_election_timer(candidate_id)

    def _send_heartbeats(self, leader: AirspaceControllerHA) -> None:
        """리더 → 살아있는 follower에게 빈 AppendEntries(하트비트) 방송."""
        for nid in self.alive_node_ids():
            if nid == leader.node_id:
                continue
            self.nodes[nid].on_append_entries(
                leader_id=leader.node_id,
                term=leader.state.current_term,
                entries=[],
                commit_index=leader.state.commit_index,
            )
            self._reset_election_timer(nid)

    def _reset_election_timer(self, node_id: str) -> None:
        """election timeout을 ``[lo, hi)`` 범위에서 무작위(seeded) 재설정."""
        lo, hi = self.cfg.election_timeout_ms
        self._election_deadline[node_id] = self.now_ms + float(
            self._rng.uniform(lo, hi)
        )

    def _validate(self, node_id: str) -> None:
        """``node_id`` 가 클러스터 멤버인지 검증한다."""
        if node_id not in self.nodes:
            raise KeyError(f"unknown node_id: {node_id}")
