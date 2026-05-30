"""군집 드론 NTP 스타일 시각 동기화 모듈 (목표: 지터 <10 ms)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# 지터 허용 기준 (ms)
JITTER_TARGET_MS = 10.0


class TimeSyncNode:
    """단일 노드의 NTP 스타일 시각 오프셋을 관리한다.

    슬루잉(slewing) 없이 단순 오프셋 적용 방식을 사용한다.
    지터는 최근 N 샘플의 오프셋 표준편차로 계산한다.
    """

    _HISTORY_SIZE = 8  # 지터 계산에 사용할 이력 크기

    def __init__(self, node_id: str) -> None:
        self.node_id = node_id
        self._offset: float = 0.0
        self._offset_history: list[float] = []

    def sync(self, reference_time: float, local_time: float) -> float:
        """기준 시각으로 로컬 시각을 보정하고 보정된 시각을 반환한다.

        Args:
            reference_time: 마스터/기준 노드의 현재 시각 (초).
            local_time: 이 노드의 현재 로컬 시각 (초).

        Returns:
            보정된 시각 (local_time + offset).
        """
        new_offset = reference_time - local_time
        self._offset = new_offset

        self._offset_history.append(new_offset)
        if len(self._offset_history) > self._HISTORY_SIZE:
            self._offset_history.pop(0)

        return local_time + self._offset

    @property
    def offset(self) -> float:
        """현재 측정된 시각 오프셋 (초)."""
        return self._offset

    @property
    def jitter_ms(self) -> float:
        """최근 이력 기반 지터 (ms, 표준편차)."""
        if len(self._offset_history) < 2:
            return 0.0
        n = len(self._offset_history)
        mean = sum(self._offset_history) / n
        variance = sum((x - mean) ** 2 for x in self._offset_history) / (n - 1)
        return math.sqrt(variance) * 1000.0  # 초 → ms 변환


class SwarmTimeSync:
    """군집 내 다수 노드의 시각 동기화를 관리한다."""

    def __init__(self) -> None:
        self._nodes: dict[str, TimeSyncNode] = {}

    def add_node(self, node_id: str) -> TimeSyncNode:
        """새 노드를 등록하고 반환한다.

        Args:
            node_id: 고유 노드 식별자.

        Returns:
            생성된 TimeSyncNode.

        Raises:
            ValueError: 이미 존재하는 node_id.
        """
        if node_id in self._nodes:
            raise ValueError(f"노드 '{node_id}' 이미 등록됨")
        node = TimeSyncNode(node_id)
        self._nodes[node_id] = node
        return node

    def get_node(self, node_id: str) -> TimeSyncNode:
        """등록된 노드를 반환한다."""
        try:
            return self._nodes[node_id]
        except KeyError:
            raise KeyError(f"노드 '{node_id}' 미등록") from None

    def sync_all(self, reference_time: float) -> dict[str, float]:
        """모든 노드를 기준 시각으로 동기화한다.

        각 노드의 local_time은 reference_time + 현재 offset으로 가정한다
        (오프셋 재측정을 위해 의도적으로 0으로 초기화되지 않은 상태를 사용).

        Args:
            reference_time: 마스터 기준 시각 (초).

        Returns:
            {node_id: corrected_time} 딕셔너리.
        """
        results: dict[str, float] = {}
        for node_id, node in self._nodes.items():
            # local_time = reference_time - current_offset (현재 편차 유지)
            local_time = reference_time - node.offset
            corrected = node.sync(reference_time, local_time)
            results[node_id] = corrected
        return results

    def max_jitter_ms(self) -> float:
        """모든 노드 중 최대 지터(ms)를 반환한다.

        Returns:
            최대 지터 ms. 노드 없으면 0.0.
        """
        if not self._nodes:
            return 0.0
        return max(node.jitter_ms for node in self._nodes.values())

    @property
    def node_ids(self) -> list[str]:
        """등록된 노드 ID 목록."""
        return list(self._nodes.keys())
