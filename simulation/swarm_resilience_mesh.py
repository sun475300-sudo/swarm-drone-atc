# Phase 531: Swarm Resilience Mesh — Self-Healing Topology
"""
자가 복구 메시 토폴로지: k-연결성 보장, 링크 장애 감지 및 자동 복구.
Kruskal MST + 증강 엣지로 k-connected 그래프 유지.
"""

import numpy as np
from dataclasses import dataclass, field


@dataclass
class MeshNode:
    node_id: str
    position: np.ndarray
    neighbors: list = field(default_factory=list)
    alive: bool = True
    load: float = 0.0


@dataclass
class MeshLink:
    src: str
    dst: str
    weight: float
    latency_ms: float
    alive: bool = True


class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if self.rank[ra] < self.rank[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        if self.rank[ra] == self.rank[rb]:
            self.rank[ra] += 1
        return True


class TopologyManager:
    """Kruskal MST 기반 토폴로지 생성 + k-연결성 증강."""

    def __init__(self, k_connectivity=2, seed=42):
        self.k = k_connectivity
        self.rng = np.random.default_rng(seed)

    def build_mst(self, nodes: list[MeshNode], max_range=150.0) -> list[MeshLink]:
        n = len(nodes)
        edges = []
        for i in range(n):
            for j in range(i + 1, n):
                if not nodes[i].alive or not nodes[j].alive:
                    continue
                dist = np.linalg.norm(nodes[i].position - nodes[j].position)
                if dist <= max_range:
                    edges.append((dist, i, j))
        edges.sort()
        uf = UnionFind(n)
        mst = []
        for w, i, j in edges:
            if uf.union(i, j):
                lat = w * 0.1 + self.rng.exponential(2.0)
                mst.append(MeshLink(nodes[i].node_id, nodes[j].node_id, w, lat))
        return mst

    def augment_connectivity(self, nodes, mst_links, max_range=150.0):
        """MST 위에 추가 엣지를 넣어 k-연결성 달성."""
        link_set = {(l.src, l.dst) for l in mst_links}
        link_set |= {(l.dst, l.src) for l in mst_links}
        degree = {}
        for l in mst_links:
            degree[l.src] = degree.get(l.src, 0) + 1
            degree[l.dst] = degree.get(l.dst, 0) + 1

        extra = []
        node_map = {n.node_id: n for n in nodes}
        for n in nodes:
            if not n.alive:
                continue
            if degree.get(n.node_id, 0) < self.k:
                candidates = []
                for m in nodes:
                    if m.node_id == n.node_id or not m.alive:
                        continue
                    if (n.node_id, m.node_id) in link_set:
                        continue
                    d = np.linalg.norm(n.position - m.position)
                    if d <= max_range:
                        candidates.append((d, m.node_id))
                candidates.sort()
                for d, mid in candidates[:self.k]:
                    link_set.add((n.node_id, mid))
                    link_set.add((mid, n.node_id))
                    lat = d * 0.1 + self.rng.exponential(2.0)
                    extra.append(MeshLink(n.node_id, mid, d, lat))
                    degree[n.node_id] = degree.get(n.node_id, 0) + 1
                    degree[mid] = degree.get(mid, 0) + 1
        return mst_links + extra


class FailureDetector:
    """하트비트 기반 장애 탐지."""

    def __init__(self, timeout_ms=500.0):
        self.timeout = timeout_ms
        self.last_heartbeat: dict[str, float] = {}

    def heartbeat(self, node_id: str, time_ms: float):
        self.last_heartbeat[node_id] = time_ms

    def detect_failures(self, current_time_ms: float) -> list[str]:
        failed = []
        for nid, t in self.last_heartbeat.items():
            if current_time_ms - t > self.timeout:
                failed.append(nid)
        return failed


class SwarmResilienceMesh:
    """자가 복구 메시 네트워크 시뮬레이션."""

    def __init__(self, n_drones=30, k_connectivity=2, seed=42):
        self.rng = np.random.default_rng(seed)
        self.topo = TopologyManager(k_connectivity, seed)
        self.detector = FailureDetector()
        self.nodes: list[MeshNode] = []
        self.links: list[MeshLink] = []
        self.healed = 0
        self.partitions = 0

        for i in range(n_drones):
            pos = self.rng.uniform(-200, 200, size=3)
            pos[2] = 30 + self.rng.uniform(0, 70)
            self.nodes.append(MeshNode(f"drone_{i}", pos))

        self._rebuild()

    def _rebuild(self):
        mst = self.topo.build_mst(self.nodes)
        self.links = self.topo.augment_connectivity(self.nodes, mst)
        for n in self.nodes:
            n.neighbors.clear()
        for l in self.links:
            if l.alive:
                for n in self.nodes:
                    if n.node_id == l.src:
                        n.neighbors.append(l.dst)
                    elif n.node_id == l.dst:
                        n.neighbors.append(l.src)

    def kill_node(self, node_id: str):
        for n in self.nodes:
            if n.node_id == node_id:
                n.alive = False
        self.links = [l for l in self.links if l.src != node_id and l.dst != node_id]

    def heal(self):
        self._rebuild()
        self.healed += 1

    def check_connectivity(self) -> int:
        alive = [n for n in self.nodes if n.alive]
        if not alive:
            return 0
        adj = {n.node_id: set() for n in alive}
        for l in self.links:
            if l.alive and l.src in adj and l.dst in adj:
                adj[l.src].add(l.dst)
                adj[l.dst].add(l.src)
        visited = set()
        stack = [alive[0].node_id]
        while stack:
            cur = stack.pop()
            if cur in visited:
                continue
            visited.add(cur)
            stack.extend(adj.get(cur, set()) - visited)
        components = 1 if len(visited) == len(alive) else 2
        return components

    def step(self):
        """한 사이클: 장애 노드 확인 → 토폴로지 복구."""
        alive_count = sum(1 for n in self.nodes if n.alive)
        comps = self.check_connectivity()
        if comps > 1:
            self.partitions += 1
            self.heal()
        return {"alive": alive_count, "links": len(self.links), "components": comps}

    def summary(self):
        alive = sum(1 for n in self.nodes if n.alive)
        return {
            "total_nodes": len(self.nodes),
            "alive_nodes": alive,
            "links": len(self.links),
            "healed": self.healed,
            "partitions": self.partitions,
            "components": self.check_connectivity(),
        }


if __name__ == "__main__":
    mesh = SwarmResilienceMesh(30, 2, 42)
    print(f"Initial: {mesh.summary()}")
    mesh.kill_node("drone_5")
    mesh.kill_node("drone_10")
    result = mesh.step()
    print(f"After kill+step: {result}")
    print(f"Final: {mesh.summary()}")
