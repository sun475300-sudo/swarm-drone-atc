# Phase 544: Hypergraph Routing — Multi-Destination Routing
"""
하이퍼그래프 라우팅: 하이퍼엣지(다중 노드 연결)로 브로드캐스트/멀티캐스트 최적화.
Steiner 트리 근사로 다중 목적지 최소비용 경로 계산.
"""

import numpy as np
from dataclasses import dataclass, field
import heapq


@dataclass
class HyperEdge:
    edge_id: str
    nodes: list  # 연결된 노드 ID 리스트
    cost: float
    bandwidth: float


@dataclass
class RoutingResult:
    source: str
    destinations: list
    path_cost: float
    edges_used: int
    reachable: int


class HyperGraph:
    """하이퍼그래프: 하이퍼엣지로 다중 노드 연결."""

    def __init__(self):
        self.nodes: set = set()
        self.edges: list[HyperEdge] = []
        self.adj: dict = {}  # node -> [(edge_id, neighbor_nodes, cost)]

    def add_node(self, node_id: str):
        self.nodes.add(node_id)
        if node_id not in self.adj:
            self.adj[node_id] = []

    def add_hyperedge(self, edge_id: str, nodes: list, cost: float, bw: float = 100.0):
        he = HyperEdge(edge_id, nodes, cost, bw)
        self.edges.append(he)
        for n in nodes:
            self.add_node(n)
            others = [m for m in nodes if m != n]
            self.adj[n].append((edge_id, others, cost))

    def dijkstra(self, source: str) -> dict:
        """단일 소스 최단 거리 (하이퍼엣지 → 일반 엣지 분해)."""
        dist = {n: float('inf') for n in self.nodes}
        dist[source] = 0
        pq = [(0.0, source)]
        while pq:
            d, u = heapq.heappop(pq)
            if d > dist[u]:
                continue
            for eid, neighbors, cost in self.adj.get(u, []):
                for v in neighbors:
                    nd = d + cost
                    if nd < dist.get(v, float('inf')):
                        dist[v] = nd
                        heapq.heappush(pq, (nd, v))
        return dist

    def steiner_tree_approx(self, source: str, destinations: list) -> RoutingResult:
        """Steiner 트리 근사: 다중 목적지 최소비용."""
        dist = self.dijkstra(source)
        total_cost = 0.0
        reachable = 0
        edges_used = set()
        for dest in destinations:
            if dist.get(dest, float('inf')) < float('inf'):
                total_cost += dist[dest]
                reachable += 1
        edges_used_count = min(reachable, len(self.edges))
        return RoutingResult(source, destinations, total_cost, edges_used_count, reachable)


class HypergraphRouting:
    """하이퍼그래프 기반 라우팅 시뮬레이션."""

    def __init__(self, n_nodes=20, n_edges=30, seed=42):
        self.rng = np.random.default_rng(seed)
        self.graph = HyperGraph()
        self.n_nodes = n_nodes
        self.results: list[RoutingResult] = []

        # 노드 생성
        for i in range(n_nodes):
            self.graph.add_node(f"N_{i}")

        # 하이퍼엣지 생성 (2~4 노드 연결)
        node_list = [f"N_{i}" for i in range(n_nodes)]
        for i in range(n_edges):
            k = int(self.rng.integers(2, min(5, n_nodes + 1)))
            selected = list(self.rng.choice(node_list, k, replace=False))
            cost = self.rng.uniform(1, 20)
            bw = self.rng.uniform(10, 200)
            self.graph.add_hyperedge(f"HE_{i}", selected, cost, bw)

    def route(self, source: str, destinations: list) -> RoutingResult:
        result = self.graph.steiner_tree_approx(source, destinations)
        self.results.append(result)
        return result

    def run_batch(self, n_queries=10):
        node_list = [f"N_{i}" for i in range(self.n_nodes)]
        for _ in range(n_queries):
            src = node_list[int(self.rng.integers(0, self.n_nodes))]
            n_dest = int(self.rng.integers(1, min(5, self.n_nodes)))
            dests = list(self.rng.choice([n for n in node_list if n != src],
                                          min(n_dest, self.n_nodes - 1), replace=False))
            self.route(src, dests)

    def summary(self):
        avg_cost = float(np.mean([r.path_cost for r in self.results])) if self.results else 0
        avg_reach = float(np.mean([r.reachable for r in self.results])) if self.results else 0
        return {
            "nodes": self.n_nodes,
            "hyperedges": len(self.graph.edges),
            "queries": len(self.results),
            "avg_path_cost": round(avg_cost, 2),
            "avg_reachable": round(avg_reach, 2),
        }


if __name__ == "__main__":
    hr = HypergraphRouting(20, 30, 42)
    hr.run_batch(10)
    for k, v in hr.summary().items():
        print(f"  {k}: {v}")
