"""P741 인메모리 Raft 클러스터 하니스 — 결정론적 합의 시뮬레이션.

가상 시계를 ``dt_ms`` 단위로 진행하며 살아있는 노드의 ``tick()``을 호출한다.
RPC는 `InMemoryTransport`로 동기 라우팅되어 네트워크 없이 선거·복제·
페일오버를 재현 가능하게 검증한다. 테스트와 SITL 데모 양쪽에서 사용한다.
"""
from __future__ import annotations

from src.raft.airspace_controller_ha import AirspaceControllerHA, RaftConfig
from src.raft.transport import InMemoryTransport


class RaftCluster:
    """다중 `AirspaceControllerHA` 노드를 묶는 인메모리 클러스터."""

    def __init__(
        self,
        node_ids: list[str],
        seed: int = 0,
        cfg: RaftConfig | None = None,
        dt_ms: int = 10,
    ) -> None:
        """노드들을 생성·기동하고 가상 시계를 초기화한다.

        Args:
            node_ids: 클러스터 노드 id 목록.
            seed: 기준 시드 (노드별 seed+i로 선거 타임아웃 분산).
            cfg: Raft 타이밍 설정.
            dt_ms: 틱당 가상 시간 진행량(ms).
        """
        self.cfg = cfg or RaftConfig()
        self.dt = dt_ms / 1000.0
        self.now = 0.0
        transport = InMemoryTransport(self)
        self.nodes: dict[str, AirspaceControllerHA] = {}
        for i, nid in enumerate(node_ids):
            peers = [p for p in node_ids if p != nid]
            self.nodes[nid] = AirspaceControllerHA(
                nid, peers=peers, cfg=self.cfg, transport=transport, seed=seed + i,
            )
        self.alive: set[str] = set(node_ids)
        for nid in node_ids:
            self.nodes[nid].start(self.now)

    def reachable(self, node_id: str) -> AirspaceControllerHA | None:
        """살아있는 노드면 인스턴스 반환, 아니면 None (전송 계층용)."""
        return self.nodes.get(node_id) if node_id in self.alive else None

    def step(self) -> None:
        """가상 시계를 1틱 진행하고 살아있는 노드를 tick."""
        self.now += self.dt
        for nid in list(self.alive):
            self.nodes[nid].tick(self.now)

    def run(self, ticks: int) -> None:
        """``ticks``회 step 실행."""
        for _ in range(ticks):
            self.step()

    def leader(self, exclude: set[str] | None = None) -> AirspaceControllerHA | None:
        """현재 리더 노드 반환 (없으면 None)."""
        exclude = exclude or set()
        for nid, node in self.nodes.items():
            if nid in self.alive and nid not in exclude and node.is_leader():
                return node
        return None

    def run_until_leader(
        self, max_ticks: int = 2000, exclude: set[str] | None = None,
    ) -> AirspaceControllerHA | None:
        """리더가 선출될 때까지 진행 후 리더 반환 (실패 시 None)."""
        for _ in range(max_ticks):
            leader = self.leader(exclude=exclude)
            if leader is not None:
                return leader
            self.step()
        return self.leader(exclude=exclude)

    def stop(self, node_id: str) -> None:
        """노드 정지 (페일오버 시뮬레이션)."""
        self.alive.discard(node_id)
        self.nodes[node_id].stop()

    def start(self, node_id: str) -> None:
        """정지된 노드 재가동."""
        self.alive.add(node_id)
        self.nodes[node_id].start(self.now)
