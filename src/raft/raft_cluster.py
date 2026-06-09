"""P741: 결정론적 인메모리 Raft 클러스터.

각 노드의 `transport`를 동기 클로저로 연결하여 선거·로그 복제·페일오버를
실제 스레드/네트워크 없이 논리 시계(`tick`) 기반으로 재현한다.
테스트·데모·로컬 검증 전용 (운영 배포는 실제 RPC transport 주입).
"""
from __future__ import annotations

from typing import Optional

from src.raft.airspace_controller_ha import (
    AirspaceControllerHA,
    NodeRole,
    RaftConfig,
)


class InMemoryRaftCluster:
    """동기 인메모리 transport로 묶인 Raft 노드 집합.

    Usage:
        cluster = InMemoryRaftCluster(["n1", "n2", "n3"], seed=0)
        cluster.start()
        leader = cluster.run_until_leader()
        leader.replicate({"type": "advisory"})
        cluster.kill(leader.node_id)
        new_leader = cluster.run_until_leader()
    """

    def __init__(
        self,
        node_ids: list[str],
        cfg: RaftConfig | None = None,
        seed: int = 0,
    ) -> None:
        """노드 생성 + transport 배선."""
        self._partitioned: set[str] = set()
        self.nodes: dict[str, AirspaceControllerHA] = {}
        for i, nid in enumerate(node_ids):
            peers = [x for x in node_ids if x != nid]
            self.nodes[nid] = AirspaceControllerHA(
                nid,
                peers,
                cfg,
                transport=self._make_transport(nid),
                seed=seed + i,
            )

    def _make_transport(self, sender_id: str):
        """발신자 기준 transport 클로저 — 파티션된 노드는 도달 불가(None)."""

        def transport(peer_id: str, rpc_type: str, payload: dict) -> Optional[dict]:
            if sender_id in self._partitioned or peer_id in self._partitioned:
                return None
            peer = self.nodes.get(peer_id)
            if peer is None:
                return None
            if rpc_type == "request_vote":
                return peer.handle_request_vote_rpc(payload)
            if rpc_type == "append_entries":
                return peer.handle_append_entries_rpc(payload)
            return None

        return transport

    # ── 구동 ────────────────────────────────────────────────────────────
    def start(self) -> None:
        """모든 노드 활성화."""
        for node in self.nodes.values():
            node.start()

    def tick(self, n: int = 1) -> None:
        """논리 시계를 n틱 진행 (파티션된 노드는 건너뜀)."""
        for _ in range(n):
            for nid, node in self.nodes.items():
                if nid in self._partitioned:
                    continue
                node.tick()

    def run_until_leader(self, max_ticks: int = 50) -> Optional[AirspaceControllerHA]:
        """단일 리더가 나타날 때까지 틱 진행. 실패 시 None."""
        for _ in range(max_ticks):
            self.tick()
            leader = self.leader()
            if leader is not None:
                return leader
        return None

    # ── 조회 ────────────────────────────────────────────────────────────
    def leaders(self) -> list[AirspaceControllerHA]:
        """현재 살아있는 리더 목록 (정상 시 0 또는 1개)."""
        return [
            n
            for nid, n in self.nodes.items()
            if nid not in self._partitioned and n.is_leader()
        ]

    def leader(self) -> Optional[AirspaceControllerHA]:
        """단일 리더 반환 — 0개거나 2개 이상이면 None."""
        ls = self.leaders()
        return ls[0] if len(ls) == 1 else None

    # ── 장애 주입 ───────────────────────────────────────────────────────
    def kill(self, node_id: str) -> None:
        """노드를 파티션 — 도달 불가 + 틱 제외 (장애 시뮬레이션)."""
        self._partitioned.add(node_id)

    def revive(self, node_id: str) -> None:
        """노드 복구 — FOLLOWER로 재합류."""
        self._partitioned.discard(node_id)
        node = self.nodes.get(node_id)
        if node is not None:
            node._running = True  # kill() 강화 시에도 틱 재개 보장 (대칭성)
            node.state.role = NodeRole.FOLLOWER
            node._ticks_since_heartbeat = 0
