"""P741: 인메모리 Raft 클러스터 하니스.

여러 ``AirspaceControllerHA`` 노드를 단일 프로세스에서 배선하고
가상 클럭(step) 으로 선거·복제·페일오버를 결정론적으로 구동한다.

스레드/asyncio 없이 ``tick()`` 으로 시간을 전진시키므로 CI에서 재현 가능.
실제 분산 배포 시 노드 간 호출(``on_request_vote``/``on_append_entries``)을
네트워크 RPC stub으로 교체하면 동일 로직이 그대로 동작한다.
"""
from __future__ import annotations

import numpy as np

from src.raft.airspace_controller_ha import (
    AirspaceControllerHA,
    NodeRole,
    RaftConfig,
)


class RaftCluster:
    """N개 노드를 배선한 결정론적 Raft 클러스터.

    Usage:
        cluster = RaftCluster(["ctrl-1", "ctrl-2", "ctrl-3"], seed=0)
        cluster.run_until_leader()
        leader = cluster.leader()
        cluster.propose({"type": "advisory", "drone_id": "DR-001"})
        cluster.kill(leader.node_id)
        cluster.run_until_leader()   # 새 리더 선출
    """

    def __init__(
        self,
        node_ids: list[str],
        cfg: RaftConfig | None = None,
        seed: int = 0,
        dt: float = 0.01,
    ) -> None:
        """노드 생성 + 상호 배선 + 가상 클럭 주입 후 start()."""
        if len(node_ids) < 1:
            raise ValueError("node_ids는 최소 1개 필요")
        self.cfg = cfg or RaftConfig()
        self._t = 0.0
        self._dt = dt
        self.nodes: dict[str, AirspaceControllerHA] = {}
        for i, nid in enumerate(node_ids):
            node = AirspaceControllerHA(
                nid, peers=[x for x in node_ids if x != nid], cfg=self.cfg
            )
            # 노드별 구별되는 시드 → 선거 타임아웃 분산(split-vote 회피).
            node._rng = np.random.default_rng(seed + i)
            node._now = self._clock
            self.nodes[nid] = node
        for nid, node in self.nodes.items():
            node._peer_nodes = {
                pid: self.nodes[pid] for pid in node_ids if pid != nid
            }
            node.start()

    def _clock(self) -> float:
        """노드에 주입되는 가상 클럭 — 현재 클러스터 시각."""
        return self._t

    def tick(self) -> None:
        """가상 시간을 dt 만큼 전진시키고 모든 노드를 1스텝 진행."""
        self._t += self._dt
        for node in self.nodes.values():
            node.tick(self._t)

    def run(self, steps: int) -> None:
        """``steps`` 만큼 tick 반복."""
        for _ in range(steps):
            self.tick()

    def leaders(self) -> list[AirspaceControllerHA]:
        """현재 살아있는 리더 노드 목록 (정상 시 1개)."""
        return [
            n
            for n in self.nodes.values()
            if n._alive and n.state.role == NodeRole.LEADER
        ]

    def leader(self) -> AirspaceControllerHA | None:
        """단일 리더 반환 — 없으면 None, 2개 이상이면 안전성 위반(에러)."""
        ls = self.leaders()
        if len(ls) > 1:
            raise RuntimeError(
                f"Raft 안전성 위반: 동시 리더 {len(ls)}개 — {[n.node_id for n in ls]}"
            )
        return ls[0] if ls else None

    def run_until_leader(self, max_steps: int = 2000) -> AirspaceControllerHA | None:
        """리더가 선출될 때까지 tick — 선출된 리더 반환(타임아웃 시 None)."""
        for _ in range(max_steps):
            self.tick()
            if self.leaders():
                return self.leader()
        return None

    def propose(self, command: dict) -> bool:
        """현재 리더를 통해 명령 복제. 리더 부재 시 False."""
        leader = self.leader()
        if leader is None:
            return False
        return leader.replicate(command)

    def kill(self, node_id: str) -> None:
        """노드 장애 시뮬레이션 — 투표/복제에 응답하지 않음."""
        self.nodes[node_id]._alive = False

    def revive(self, node_id: str) -> None:
        """장애 노드 복귀 — FOLLOWER로 재합류."""
        node = self.nodes[node_id]
        node._alive = True
        node.state.role = NodeRole.FOLLOWER
        node.state.voted_for = None  # 구 term의 stale 투표 기록 제거
        node.state.leader_id = None  # 하트비트로 현 리더 재인지
        node.state.last_heartbeat_ts = self._t
        node._reset_election_timeout()
