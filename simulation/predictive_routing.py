"""
Phase 518: Predictive Routing
트래픽 예측 기반 경로 최적화, 시공간 네트워크, 동적 가중치.
"""

import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple
import heapq


class CongestionLevel(Enum):
    FREE = 0
    LIGHT = 1
    MODERATE = 2
    HEAVY = 3
    BLOCKED = 4


@dataclass
class Waypoint:
    wp_id: str
    position: np.ndarray
    congestion: CongestionLevel = CongestionLevel.FREE
    capacity: int = 10
    current_load: int = 0


@dataclass
class RouteSegment:
    from_wp: str
    to_wp: str
    distance_m: float
    base_time_s: float
    predicted_delay_s: float = 0.0
    risk_score: float = 0.0


@dataclass
class Route:
    route_id: str
    waypoints: List[str]
    total_distance_m: float
    total_time_s: float
    risk: float
    predicted_congestion: float


class TrafficPredictor:
    """Predict airspace traffic density using temporal patterns."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.history: Dict[str, List[float]] = {}

    def record(self, wp_id: str, load: float):
        if wp_id not in self.history:
            self.history[wp_id] = []
        self.history[wp_id].append(load)
        if len(self.history[wp_id]) > 100:
            self.history[wp_id].pop(0)

    def predict(self, wp_id: str, horizon_s: float = 300) -> float:
        hist = self.history.get(wp_id, [])
        if len(hist) < 3:
            return self.rng.uniform(0, 0.5)
        recent = hist[-10:]
        trend = (recent[-1] - recent[0]) / len(recent) if len(recent) > 1 else 0
        predicted = recent[-1] + trend * (horizon_s / 60)
        return max(0, min(1.0, predicted + self.rng.standard_normal() * 0.05))


class SpatioTemporalGraph:
    """Space-time network for route planning."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.waypoints: Dict[str, Waypoint] = {}
        self.edges: Dict[str, List[RouteSegment]] = {}

    def add_waypoint(self, wp: Waypoint):
        self.waypoints[wp.wp_id] = wp
        if wp.wp_id not in self.edges:
            self.edges[wp.wp_id] = []

    def add_edge(self, from_wp: str, to_wp: str):
        if from_wp not in self.waypoints or to_wp not in self.waypoints:
            return
        p1 = self.waypoints[from_wp].position
        p2 = self.waypoints[to_wp].position
        dist = float(np.linalg.norm(p1 - p2))
        speed = 10.0  # m/s base
        seg = RouteSegment(from_wp, to_wp, round(dist, 1), round(dist / speed, 1))
        self.edges.setdefault(from_wp, []).append(seg)

    def dijkstra(self, start: str, end: str, weight_fn=None) -> Optional[Route]:
        if start not in self.waypoints or end not in self.waypoints:
            return None
        if weight_fn is None:
            weight_fn = lambda seg: seg.base_time_s + seg.predicted_delay_s

        dist_map = {start: 0}
        prev = {}
        pq = [(0, start)]
        visited = set()

        while pq:
            d, u = heapq.heappop(pq)
            if u in visited:
                continue
            visited.add(u)
            if u == end:
                break
            for seg in self.edges.get(u, []):
                v = seg.to_wp
                w = weight_fn(seg)
                nd = d + w
                if nd < dist_map.get(v, float('inf')):
                    dist_map[v] = nd
                    prev[v] = (u, seg)
                    heapq.heappush(pq, (nd, v))

        if end not in prev and start != end:
            return None

        path = [end]
        total_dist = 0
        total_time = 0
        total_risk = 0
        node = end
        while node in prev:
            parent, seg = prev[node]
            path.append(parent)
            total_dist += seg.distance_m
            total_time += seg.base_time_s + seg.predicted_delay_s
            total_risk += seg.risk_score
            node = parent
        path.reverse()
        return Route(f"R-{start}-{end}", path, round(total_dist, 1),
                    round(total_time, 1), round(total_risk, 3),
                    round(total_risk / max(len(path), 1), 3))


class PredictiveRouting:
    """Predictive routing system for drone swarms."""

    def __init__(self, n_waypoints: int = 30, seed: int = 42):
        self.rng = np.random.default_rng(seed)
        self.predictor = TrafficPredictor(seed)
        self.graph = SpatioTemporalGraph(seed)
        self.routes: List[Route] = []

        for i in range(n_waypoints):
            pos = self.rng.uniform(-500, 500, 3)
            pos[2] = self.rng.uniform(30, 150)
            wp = Waypoint(f"WP-{i:03d}", pos, capacity=self.rng.integers(5, 20))
            self.graph.add_waypoint(wp)

        wp_ids = list(self.graph.waypoints.keys())
        for i, wid in enumerate(wp_ids):
            neighbors = self.rng.choice(
                [w for w in wp_ids if w != wid],
                size=min(4, len(wp_ids) - 1), replace=False)
            for nid in neighbors:
                self.graph.add_edge(wid, nid)

    def update_traffic(self):
        for wid, wp in self.graph.waypoints.items():
            wp.current_load = int(self.rng.integers(0, wp.capacity + 3))
            load_ratio = wp.current_load / max(wp.capacity, 1)
            self.predictor.record(wid, load_ratio)
            if load_ratio > 0.8:
                wp.congestion = CongestionLevel.HEAVY
            elif load_ratio > 0.5:
                wp.congestion = CongestionLevel.MODERATE
            else:
                wp.congestion = CongestionLevel.FREE

        for edges in self.graph.edges.values():
            for seg in edges:
                pred = self.predictor.predict(seg.to_wp)
                seg.predicted_delay_s = round(pred * 30, 1)
                seg.risk_score = round(pred * 0.5, 3)

    def find_route(self, start: str, end: str) -> Optional[Route]:
        self.update_traffic()
        route = self.graph.dijkstra(start, end)
        if route:
            self.routes.append(route)
        return route

    def summary(self) -> Dict:
        return {
            "waypoints": len(self.graph.waypoints),
            "edges": sum(len(e) for e in self.graph.edges.values()),
            "routes_planned": len(self.routes),
            "avg_route_time": round(
                np.mean([r.total_time_s for r in self.routes]) if self.routes else 0, 1),
        }
