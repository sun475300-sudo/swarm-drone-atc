"""
Phase 335: Mesh Network Optimizer
드론 메쉬 네트워크 최적화.
Dijkstra/Bellman-Ford 라우팅 + 자가치유 + 링크 품질 관리.
"""

import heapq
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple, Set


class LinkStatus(Enum):
    ACTIVE = "active"
    DEGRADED = "degraded"
    FAILED = "failed"


class RoutingProtocol(Enum):
    DIJKSTRA = "dijkstra"
    BELLMAN_FORD = "bellman_ford"
    AODV = "aodv"


@dataclass
class MeshNode:
    node_id: str
    x: float
    y: float
    z: float
    is_gateway: bool = False
    is_active: bool = True
    battery_level: float = 100.0
    tx_power_dbm: float = 20.0
    neighbors: Set[str] = field(default_factory=set)


@dataclass
class MeshLink:
    src: str
    dst: str
    rssi: float = -60.0   # dBm
    snr: float = 20.0     # dB
    bandwidth_mbps: float = 10.0
    latency_ms: float = 5.0
    packet_loss: float = 0.01
    status: LinkStatus = LinkStatus.ACTIVE

    @property
    def cost(self) -> float:
        if self.status == LinkStatus.FAILED:
            return float('inf')
        base = self.latency_ms + (1.0 / max(self.bandwidth_mbps, 0.1))
        loss_penalty = 1.0 + self.packet_loss * 10
        degraded_factor = 2.0 if self.status == LinkStatus.DEGRADED else 1.0
        return base * loss_penalty * degraded_factor


@dataclass
class RouteEntry:
    destination: str
    next_hop: str
    cost: float
    hop_count: int
    path: List[str]


class MeshNetworkOptimizer:
    """Mesh network with multi-hop routing and self-healing."""

    def __init__(self, protocol: RoutingProtocol = RoutingProtocol.DIJKSTRA,
                 seed: int = 42):
        self.protocol = protocol
        self.rng = np.random.default_rng(seed)
        self.nodes: Dict[str, MeshNode] = {}
        self.links: Dict[Tuple[str, str], MeshLink] = {}
        self.routing_tables: Dict[str, Dict[str, RouteEntry]] = {}
        self.heal_count = 0
        self.route_updates = 0

    def add_node(self, node_id: str, x: float, y: float, z: float,
                 is_gateway: bool = False) -> MeshNode:
        node = MeshNode(node_id, x, y, z, is_gateway=is_gateway)
        self.nodes[node_id] = node
        return node

    def add_link(self, src: str, dst: str, rssi: float = -60.0,
                 bandwidth: float = 10.0) -> MeshLink:
        link = MeshLink(src, dst, rssi=rssi, bandwidth_mbps=bandwidth,
                        latency_ms=self._estimate_latency(src, dst))
        self.links[(src, dst)] = link
        self.links[(dst, src)] = MeshLink(dst, src, rssi=rssi,
                                           bandwidth_mbps=bandwidth,
                                           latency_ms=link.latency_ms)
        self.nodes[src].neighbors.add(dst)
        self.nodes[dst].neighbors.add(src)
        return link

    def _estimate_latency(self, src: str, dst: str) -> float:
        a, b = self.nodes[src], self.nodes[dst]
        dist = np.sqrt((a.x - b.x)**2 + (a.y - b.y)**2 + (a.z - b.z)**2)
        return dist / 300.0 + 1.0  # propagation + processing

    def auto_connect(self, max_range: float = 200.0) -> int:
        connected = 0
        ids = list(self.nodes.keys())
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = self.nodes[ids[i]], self.nodes[ids[j]]
                dist = np.sqrt((a.x - b.x)**2 + (a.y - b.y)**2 + (a.z - b.z)**2)
                if dist <= max_range:
                    rssi = -30 - 20 * np.log10(max(dist, 1))
                    bw = max(1.0, 54.0 * (1.0 - dist / max_range))
                    self.add_link(ids[i], ids[j], rssi=rssi, bandwidth=bw)
                    connected += 1
        return connected

    def compute_routes(self, source: Optional[str] = None) -> None:
        sources = [source] if source else list(self.nodes.keys())
        for src in sources:
            if self.protocol == RoutingProtocol.DIJKSTRA:
                self.routing_tables[src] = self._dijkstra(src)
            elif self.protocol == RoutingProtocol.BELLMAN_FORD:
                self.routing_tables[src] = self._bellman_ford(src)
            else:
                self.routing_tables[src] = self._dijkstra(src)
            self.route_updates += 1

    def _dijkstra(self, source: str) -> Dict[str, RouteEntry]:
        dist: Dict[str, float] = {nid: float('inf') for nid in self.nodes}
        prev: Dict[str, Optional[str]] = {nid: None for nid in self.nodes}
        dist[source] = 0
        heap = [(0.0, source)]
        visited: Set[str] = set()

        while heap:
            d, u = heapq.heappop(heap)
            if u in visited:
                continue
            visited.add(u)
            node = self.nodes[u]
            if not node.is_active:
                continue

            for neighbor in node.neighbors:
                link = self.links.get((u, neighbor))
                if not link or link.status == LinkStatus.FAILED:
                    continue
                alt = d + link.cost
                if alt < dist[neighbor]:
                    dist[neighbor] = alt
                    prev[neighbor] = u
                    heapq.heappush(heap, (alt, neighbor))

        routes = {}
        for dst in self.nodes:
            if dst == source or dist[dst] == float('inf'):
                continue
            path = []
            node = dst
            while node is not None:
                path.append(node)
                node = prev[node]
            path.reverse()
            next_hop = path[1] if len(path) > 1 else dst
            routes[dst] = RouteEntry(dst, next_hop, dist[dst],
                                     len(path) - 1, path)
        return routes

    def _bellman_ford(self, source: str) -> Dict[str, RouteEntry]:
        dist = {nid: float('inf') for nid in self.nodes}
        prev: Dict[str, Optional[str]] = {nid: None for nid in self.nodes}
        dist[source] = 0

        for _ in range(len(self.nodes) - 1):
            for (u, v), link in self.links.items():
                if link.status == LinkStatus.FAILED:
                    continue
                if not self.nodes[u].is_active:
                    continue
                if dist[u] + link.cost < dist[v]:
                    dist[v] = dist[u] + link.cost
                    prev[v] = u

        routes = {}
        for dst in self.nodes:
            if dst == source or dist[dst] == float('inf'):
                continue
            path = []
            node = dst
            while node is not None:
                path.append(node)
                node = prev[node]
            path.reverse()
            next_hop = path[1] if len(path) > 1 else dst
            routes[dst] = RouteEntry(dst, next_hop, dist[dst],
                                     len(path) - 1, path)
        return routes

    def get_route(self, src: str, dst: str) -> Optional[RouteEntry]:
        table = self.routing_tables.get(src)
        if not table:
            return None
        return table.get(dst)

    def fail_link(self, src: str, dst: str) -> None:
        if (src, dst) in self.links:
            self.links[(src, dst)].status = LinkStatus.FAILED
        if (dst, src) in self.links:
            self.links[(dst, src)].status = LinkStatus.FAILED

    def fail_node(self, node_id: str) -> None:
        self.nodes[node_id].is_active = False
        for neighbor in self.nodes[node_id].neighbors:
            self.fail_link(node_id, neighbor)

    def self_heal(self) -> int:
        healed = 0
        for (src, dst), link in self.links.items():
            if link.status == LinkStatus.FAILED:
                if self.nodes[src].is_active and self.nodes[dst].is_active:
                    if self.rng.random() < 0.3:
                        link.status = LinkStatus.DEGRADED
                        healed += 1
            elif link.status == LinkStatus.DEGRADED:
                if self.rng.random() < 0.5:
                    link.status = LinkStatus.ACTIVE
                    healed += 1

        if healed > 0:
            self.compute_routes()
            self.heal_count += healed
        return healed

    def get_network_stats(self) -> Dict:
        active_links = sum(1 for l in self.links.values()
                          if l.status == LinkStatus.ACTIVE)
        degraded = sum(1 for l in self.links.values()
                      if l.status == LinkStatus.DEGRADED)
        failed = sum(1 for l in self.links.values()
                    if l.status == LinkStatus.FAILED)
        avg_cost = np.mean([l.cost for l in self.links.values()
                           if l.status != LinkStatus.FAILED]) if active_links else 0

        return {
            "nodes": len(self.nodes),
            "active_nodes": sum(1 for n in self.nodes.values() if n.is_active),
            "gateways": sum(1 for n in self.nodes.values() if n.is_gateway),
            "links_active": active_links // 2,
            "links_degraded": degraded // 2,
            "links_failed": failed // 2,
            "avg_link_cost": round(float(avg_cost), 4),
            "route_updates": self.route_updates,
            "healed": self.heal_count,
        }

    def summary(self) -> Dict:
        return self.get_network_stats()


if __name__ == "__main__":
    opt = MeshNetworkOptimizer(protocol=RoutingProtocol.DIJKSTRA)
    for i in range(8):
        angle = 2 * np.pi * i / 8
        opt.add_node(f"drone_{i}", np.cos(angle) * 100, np.sin(angle) * 100, 50,
                     is_gateway=(i == 0))
    opt.auto_connect(max_range=150)
    opt.compute_routes()

    route = opt.get_route("drone_0", "drone_4")
    if route:
        print(f"Route: {route.path}, cost={route.cost:.2f}, hops={route.hop_count}")

    opt.fail_node("drone_2")
    opt.compute_routes()
    route2 = opt.get_route("drone_0", "drone_4")
    if route2:
        print(f"After failure: {route2.path}")

    print(f"Stats: {opt.summary()}")
