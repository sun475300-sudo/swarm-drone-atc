"""P741: 결정론적 인메모리 Raft 클러스터 오케스트레이터.

실제 소켓·스레드 없이 **논리 시계 tick** 으로 Raft 합의 루프를 구동한다.
- 선거 타임아웃 → CANDIDATE → RequestVote → 과반 득표 시 LEADER
- LEADER 의 주기적 AppendEntries(heartbeat) + 로그 복제
- 과반(match_index) 합의 시 ``commit_index`` 전진
- 리더 crash 시 잔여 노드가 새 리더 선출 (페일오버)

소켓/스레드를 배제해 단위 테스트에서 **재현 가능**(seeded RNG)하다.
프로덕션 배포는 이 상태 기계를 gRPC/asyncio 전송 계층에 연결하면 된다.
"""
from __future__ import annotations

import numpy as np

from src.raft.airspace_controller_ha import (
    AirspaceControllerHA,
    NodeRole,
    RaftConfig,
)


class RaftCluster:
    """인메모리 Raft 클러스터 — 논리 시계로 합의 루프 구동.

    Usage:
        cluster = RaftCluster(["ctrl-1", "ctrl-2", "ctrl-3"], seed=0)
        cluster.run_until_leader()
        idx = cluster.submit({"type": "advisory", "drone_id": "DR-001"})
        cluster.run_for(ms=300)          # 복제·커밋 진행
        cluster.crash(cluster.leader().node_id)
        cluster.run_until_leader()       # 페일오버
    """

    def __init__(
        self,
        node_ids: list[str],
        cfg: RaftConfig | None = None,
        seed: int = 0,
    ) -> None:
        """``__init__`` 동작을 수행한다."""
        if len(node_ids) < 1:
            raise ValueError("클러스터는 최소 1개 노드가 필요합니다")
        self.cfg = cfg or RaftConfig()
        self._rng = np.random.default_rng(seed)
        self.nodes: dict[str, AirspaceControllerHA] = {}
        self.alive: dict[str, bool] = {}
        for nid in node_ids:
            peers = [p for p in node_ids if p != nid]
            node = AirspaceControllerHA(nid, peers=peers, cfg=self.cfg)
            node.start()
            self.nodes[nid] = node
            self.alive[nid] = True
            self._reset_election_timeout(node)

    # ---- 타이밍 ----------------------------------------------------------

    def _reset_election_timeout(self, node: AirspaceControllerHA) -> None:
        """노드별 무작위 선거 타임아웃 설정 (split-vote 완화)."""
        lo, hi = self.cfg.election_timeout_ms
        node.state.election_timeout_ms = int(self._rng.integers(lo, hi + 1))
        node.state.election_elapsed_ms = 0.0

    # ---- 메인 루프 -------------------------------------------------------

    def tick(self, dt_ms: float) -> None:
        """논리 시계를 ``dt_ms`` 만큼 전진시키고 합의 루프를 한 스텝 구동."""
        for nid, node in self.nodes.items():
            if not self.alive[nid]:
                continue
            st = node.state
            if st.role == NodeRole.LEADER:
                st.heartbeat_elapsed_ms += dt_ms
                if st.heartbeat_elapsed_ms >= self.cfg.heartbeat_interval_ms:
                    st.heartbeat_elapsed_ms = 0.0
                    self._send_heartbeats(node)
            else:
                st.election_elapsed_ms += dt_ms
                if st.election_elapsed_ms >= st.election_timeout_ms:
                    self._start_election(node)

    def run_for(self, ms: float, dt_ms: float = 10.0) -> None:
        """``ms`` 밀리초 동안 ``dt_ms`` 간격으로 tick."""
        steps = int(ms / dt_ms)
        for _ in range(steps):
            self.tick(dt_ms)

    def run_until_leader(self, max_ms: float = 2000.0, dt_ms: float = 10.0) -> AirspaceControllerHA | None:
        """리더가 선출될 때까지(또는 ``max_ms`` 까지) tick. 리더 반환."""
        steps = int(max_ms / dt_ms)
        for _ in range(steps):
            self.tick(dt_ms)
            ldr = self.leader()
            if ldr is not None:
                return ldr
        return self.leader()

    # ---- 선거 -----------------------------------------------------------

    def _start_election(self, node: AirspaceControllerHA) -> None:
        """선거 타임아웃 → CANDIDATE 전환 + RequestVote 수집."""
        node.become_candidate()
        self._reset_election_timeout(node)
        last_idx = len(node.state.log) - 1
        last_term = node.state.log[-1].term if node.state.log else 0
        for peer_id in node.peers:
            if not self.alive[peer_id]:
                continue
            peer = self.nodes[peer_id]
            granted = peer.on_request_vote(
                node.node_id, node.state.current_term, last_idx, last_term,
            )
            if granted:
                node.state.votes_received.add(peer_id)
            elif peer.state.current_term > node.state.current_term:
                node.become_follower(peer.state.current_term)
                self._reset_election_timeout(node)
                return
        if len(node.state.votes_received) >= node.quorum:
            node.become_leader()
            self._send_heartbeats(node)

    # ---- 복제 -----------------------------------------------------------

    def _send_heartbeats(self, leader: AirspaceControllerHA) -> None:
        """리더 → 모든 alive peer 에 AppendEntries(전체 로그) 전송."""
        entries = list(leader.state.log)
        for peer_id in leader.peers:
            if not self.alive[peer_id]:
                continue
            peer = self.nodes[peer_id]
            ok = peer.on_append_entries(
                leader.node_id,
                leader.state.current_term,
                entries,
                leader.state.commit_index,
            )
            if ok:
                leader.state.match_index[peer_id] = len(peer.state.log) - 1
                leader.state.next_index[peer_id] = len(peer.state.log)
            elif peer.state.current_term > leader.state.current_term:
                leader.become_follower(peer.state.current_term)
                self._reset_election_timeout(leader)
                return
        self._advance_commit(leader)

    def _advance_commit(self, leader: AirspaceControllerHA) -> None:
        """과반(match_index) 합의된 최신 인덱스로 commit_index 전진.

        Raft §5.4.2: 현재 term 엔트리만 카운팅으로 커밋한다.
        """
        leader.state.match_index[leader.node_id] = len(leader.state.log) - 1
        for n in range(len(leader.state.log) - 1, leader.state.commit_index, -1):
            if leader.state.log[n].term != leader.state.current_term:
                continue
            # alive 노드의 ack 만 카운팅 — crash 노드의 stale match_index 배제.
            count = sum(
                1 for nid in self.nodes
                if self.alive[nid] and leader.state.match_index.get(nid, -1) >= n
            )
            if count >= leader.quorum:
                leader.state.commit_index = n
                break

    # ---- 조회·제어 ------------------------------------------------------

    def leader(self) -> AirspaceControllerHA | None:
        """현재 alive 리더 노드 (없으면 None)."""
        leaders = [
            node for nid, node in self.nodes.items()
            if self.alive[nid] and node.state.role == NodeRole.LEADER
        ]
        if not leaders:
            return None
        # 분할 상황 방어: 최고 term 리더를 정통 리더로 간주.
        return max(leaders, key=lambda n: n.state.current_term)

    def submit(self, command: dict) -> int | None:
        """리더에 명령 제출. 로그 인덱스 반환 (리더 없으면 None)."""
        ldr = self.leader()
        if ldr is None:
            return None
        if ldr.replicate(command):
            return ldr.state.log[-1].index
        return None

    def crash(self, node_id: str) -> None:
        """노드 장애 시뮬레이션 (네트워크 분리)."""
        self.alive[node_id] = False

    def recover(self, node_id: str) -> None:
        """장애 노드 복구 — FOLLOWER 로 재합류.

        인메모리(비영속) crash 모델: 복구 노드는 진행 중 선거의 ballot 을
        리셋하고, 다음 AppendEntries 수신 시 리더의 term·로그를 따라잡는다.
        리더의 stale ``next_index`` 는 다음 heartbeat 에서 재동기화된다.
        """
        self.alive[node_id] = True
        node = self.nodes[node_id]
        node.state.role = NodeRole.FOLLOWER
        node.state.leader_id = None
        node.state.voted_for = None
        node.state.votes_received = set()
        self._reset_election_timeout(node)

    def committed_commands(self, node_id: str) -> list[dict]:
        """노드가 커밋한 명령 리스트 (state machine 적용 대상)."""
        node = self.nodes[node_id]
        return [e.command for e in node.state.log[: node.state.commit_index + 1]]
