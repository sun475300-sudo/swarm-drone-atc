"""궤적 리플레이를 위한 드론 궤적 기록 모듈.

메모리 효율을 위해 드론당 최대 ``max_snapshots`` 개의 스냅샷만 유지한다.
"""

from __future__ import annotations

import json
from collections import defaultdict, deque
from typing import Any, Dict, List, Sequence, Tuple


class TrajectoryRecorder:
    """드론 궤적을 시간순으로 기록하고 내보내는 레코더.

    Args:
        max_snapshots: 드론당 유지할 최대 스냅샷 수.
    """

    def __init__(self, max_snapshots: int = 1000) -> None:
        self._max = max_snapshots
        # drone_id → deque[(t, (x, y, z))]
        self._data: Dict[str, deque[Tuple[float, Tuple[float, ...]]]] = defaultdict(
            lambda: deque(maxlen=self._max)
        )

    def record(self, t: float, drone_id: str, position: Sequence[float]) -> None:
        """시각 ``t`` 에 드론 위치를 기록한다.

        Args:
            t: 시뮬레이션 시각(초).
            drone_id: 드론 식별자.
            position: ``(x, y, z)`` 좌표.
        """
        self._data[drone_id].append((float(t), tuple(float(v) for v in position)))

    def get_trajectory(self, drone_id: str) -> List[Tuple[float, Tuple[float, ...]]]:
        """특정 드론의 궤적을 ``[(t, (x, y, z)), ...]`` 형태로 반환한다."""
        return list(self._data.get(drone_id, []))

    @property
    def drone_ids(self) -> List[str]:
        """기록된 드론 ID 목록."""
        return list(self._data.keys())

    def export_json(self, filepath: str) -> None:
        """전체 궤적 데이터를 JSON 파일로 저장한다.

        Args:
            filepath: 저장할 파일 경로.
        """
        payload: Dict[str, Any] = {}
        for drone_id, records in self._data.items():
            payload[drone_id] = [
                {"t": t, "position": list(pos)} for t, pos in records
            ]
        with open(filepath, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
