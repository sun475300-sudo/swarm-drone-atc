"""
통신 중계 드론 자동 배치
========================
통신 음영 지역 탐지 + 중계 드론 최적 배치 + 커버리지 분석.
메쉬 네트워크 기반 다중 홉 중계 경로 탐색.

사용법:
    relay = CommRelayPlanner(base_station=(0, 0, 0))
    relay.update_drones(positions)
    plan = relay.compute_relay_plan()
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class RelayNode:
    """중계 노드"""
    node_id: str
    position: np.ndarray
    is_relay: bool = False
    is_base: bool = False
    connected: bool = True
    hop_count: int = 0  # 기지국까지 홉 수
    signal_quality: float = 100.0


@dataclass
class RelayPlan:
    """중계 배치 계획"""
    relay_positions: list[np.ndarray]
    coverage_before: float  # 0~1
    coverage_after: float  # 0~1
    disconnected_drones: list[str]
    relay_count: int = 0
    total_cost: float = 0.0  # 중계 거리 합


class CommRelayPlanner:
    """
    통신 중계 드론 배치 최적화.

    커버리지 분석 + 그리디 중계 배치 + 다중 홉 경로.
    """

    def __init__(
        self,
        base_station: tuple[float, float, float] = (0.0, 0.0, 0.0),
        comm_range: float = 500.0,
        relay_range: float = 300.0,
        min_coverage: float = 0.95,
    ) -> None:
        self.base_pos = np.array(base_station, dtype=float)
        self.comm_range = comm_range
        self.relay_range = relay_range
        self.min_coverage = min_coverage

        self._nodes: dict[str, RelayNode] = {}
        # 기지국 노드
        self._nodes["BASE"] = RelayNode(
            node_id="BASE", position=self.base_pos,
            is_base=True, hop_count=0,
        )

    def update_drones(
        self,
        drone_positions: dict[str, tuple[float, float, float]],
    ) -> None:
        """드론 위치 갱신"""
        for did, pos in drone_positions.items():
            if did in self._nodes and self._nodes[did].is_relay:
                continue  # 중계 드론은 유지
            self._nodes[did] = RelayNode(
                node_id=did,
                position=np.array(pos, dtype=float),
            )
        self._update_connectivity()

    def get_coverage(self) -> float:
        """현재 커버리지 비율 (기지국 연결 가능 비율)"""
        drones = [n for n in self._nodes.values()
                  if not n.is_base and not n.is_relay]
        if not drones:
            return 1.0
        connected = sum(1 for d in drones if d.connected)
        return connected / len(drones)

    def get_disconnected(self) -> list[str]:
        """연결 불가 드론 목록"""
        return [
            n.node_id for n in self._nodes.values()
            if not n.is_base and not n.is_relay and not n.connected
        ]

    def compute_relay_plan(self, max_relays: int = 5) -> RelayPlan:
        """중계 드론 최적 배치 계획 (그리디)"""
        coverage_before = self.get_coverage()
        disconnected = self.get_disconnected()

        if coverage_before >= self.min_coverage:
            return RelayPlan(
                relay_positions=[],
                coverage_before=coverage_before,
                coverage_after=coverage_before,
                disconnected_drones=[],
                relay_count=0,
            )

        relay_positions = []
        total_cost = 0.0

        for _ in range(max_relays):
            disc = self.get_disconnected()
            if not disc:
                break

            # 연결 불가 드론의 중심점 찾기
            best_pos = self._find_best_relay_position(disc)
            if best_pos is None:
                break

            relay_id = f"RELAY_{len(relay_positions)}"
            self._nodes[relay_id] = RelayNode(
                node_id=relay_id,
                position=best_pos,
                is_relay=True,
            )
            relay_positions.append(best_pos)

            # 기지국까지 거리
            total_cost += float(np.linalg.norm(best_pos - self.base_pos))

            self._update_connectivity()

        coverage_after = self.get_coverage()
        still_disconnected = self.get_disconnected()

        return RelayPlan(
            relay_positions=relay_positions,
            coverage_before=coverage_before,
            coverage_after=coverage_after,
            disconnected_drones=still_disconnected,
            relay_count=len(relay_positions),
            total_cost=total_cost,
        )

    def find_path(self, drone_id: str) -> list[str]:
        """드론에서 기지국까지 통신 경로 (노드 ID 리스트)"""
        if drone_id not in self._nodes:
            return []

        # BFS
        visited = {drone_id}
        queue = [(drone_id, [drone_id])]

        while queue:
            current, path = queue.pop(0)
            node = self._nodes[current]

            if node.is_base:
                return path

            for nid, other in self._nodes.items():
                if nid in visited:
                    continue
                dist = float(np.linalg.norm(node.position - other.position))
                max_r = self.relay_range if (node.is_relay or other.is_relay) else self.comm_range
                if dist <= max_r:
                    visited.add(nid)
                    queue.append((nid, path + [nid]))

        return []  # 경로 없음

    def hop_count(self, drone_id: str) -> int:
        """기지국까지 홉 수 (-1 = 연결 불가)"""
        path = self.find_path(drone_id)
        return len(path) - 1 if path else -1

    def _find_best_relay_position(
        self, disconnected_ids: list[str]
    ) -> np.ndarray | None:
        """연결 불가 드론들을 최대한 커버하는 중계 위치"""
        if not disconnected_ids:
            return None

        disc_positions = np.array([
            self._nodes[did].position for did in disconnected_ids
            if did in self._nodes
        ])
        if len(disc_positions) == 0:
            return None

        # 연결 가능한 노드들 (기지국 + 연결된 드론 + 기존 중계)
        connected_nodes = [
            n for n in self._nodes.values()
            if n.connected or n.is_base
        ]
        if not connected_nodes:
            # 기지국 방향으로
            center = np.mean(disc_positions, axis=0)
            direction = self.base_pos - center
            dist = float(np.linalg.norm(direction))
            if dist > 0:
                direction = direction / dist
            return center + direction * min(self.relay_range * 0.5, dist * 0.5)

        # 연결된 노드와 연결 불가 노드의 중간점 중 최적
        best_pos = None
        best_score = -1

        for cn in connected_nodes:
            for dp in disc_positions:
                mid = (cn.position + dp) / 2.0
                # 이 위치에서 커버 가능한 연결 불가 드론 수
                score = sum(
                    1 for p in disc_positions
                    if float(np.linalg.norm(mid - p)) <= self.relay_range
                )
                # 연결된 노드와도 통신 가능해야 함
                can_connect = float(np.linalg.norm(mid - cn.position)) <= self.relay_range
                if can_connect and score > best_score:
                    best_score = score
                    best_pos = mid

        return best_pos

    def _update_connectivity(self) -> None:
        """BFS로 연결성 갱신"""
        for n in self._nodes.values():
            n.connected = n.is_base
            n.hop_count = 0 if n.is_base else -1

        # BFS from base
        visited = {"BASE"}
        queue = [("BASE", 0)]

        while queue:
            current_id, hops = queue.pop(0)
            current = self._nodes[current_id]

            for nid, other in self._nodes.items():
                if nid in visited:
                    continue
                dist = float(np.linalg.norm(current.position - other.position))
                max_r = self.relay_range if (current.is_relay or other.is_relay) else self.comm_range
                if dist <= max_r:
                    visited.add(nid)
                    other.connected = True
                    other.hop_count = hops + 1
                    queue.append((nid, hops + 1))

    def remove_relays(self) -> None:
        """모든 중계 드론 제거"""
        relay_ids = [nid for nid, n in self._nodes.items() if n.is_relay]
        for rid in relay_ids:
            del self._nodes[rid]
        self._update_connectivity()

    def summary(self) -> dict[str, Any]:
        drones = [n for n in self._nodes.values()
                  if not n.is_base and not n.is_relay]
        relays = [n for n in self._nodes.values() if n.is_relay]
        return {
            "total_drones": len(drones),
            "relay_count": len(relays),
            "coverage": round(self.get_coverage(), 3),
            "disconnected": len(self.get_disconnected()),
            "max_hops": max((n.hop_count for n in drones), default=0),
        }
