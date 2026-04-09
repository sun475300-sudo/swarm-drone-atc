"""
동적 우선순위 스케줄러
=====================
드론 임무 우선순위를 실시간으로 재조정하고
공역 혼잡도 기반 최적 출발 시간을 산출.

우선순위: EMERGENCY > MEDICAL > COMMERCIAL > SURVEILLANCE > RECREATIONAL

사용법:
    scheduler = PriorityScheduler()
    scheduler.add_mission(mission)
    queue = scheduler.get_launch_queue()
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any


class MissionPriority(IntEnum):
    EMERGENCY = 5
    MEDICAL = 4
    COMMERCIAL = 3
    SURVEILLANCE = 2
    RECREATIONAL = 1


@dataclass
class Mission:
    """드론 임무"""
    drone_id: str
    priority: MissionPriority
    estimated_duration_s: float = 300.0
    departure_time: float = 0.0
    destination: tuple[float, float, float] = (0.0, 0.0, 60.0)
    battery_required_pct: float = 30.0
    scheduled: bool = False
    completed: bool = False

    @property
    def priority_score(self) -> float:
        """우선순위 점수 (높을수록 먼저)"""
        return float(self.priority.value) * 10 + (100.0 - self.battery_required_pct) * 0.1


@dataclass
class CongestionInfo:
    """공역 혼잡도 정보"""
    active_drones: int = 0
    max_capacity: int = 100
    avg_conflict_rate: float = 0.0
    sector_densities: dict[str, float] = field(default_factory=dict)

    @property
    def congestion_level(self) -> float:
        """혼잡도 0.0~1.0"""
        return min(1.0, self.active_drones / max(self.max_capacity, 1))

    @property
    def is_congested(self) -> bool:
        return self.congestion_level > 0.7


class PriorityScheduler:
    """
    동적 우선순위 기반 임무 스케줄러.

    혼잡도를 고려하여 출발 시간을 동적 조정하고
    우선순위가 높은 임무를 먼저 배정.
    """

    def __init__(
        self,
        max_concurrent: int = 50,
        stagger_interval_s: float = 2.0,
    ) -> None:
        self.max_concurrent = max_concurrent
        self.stagger_interval_s = stagger_interval_s
        self._missions: list[Mission] = []
        self._congestion = CongestionInfo()

    def add_mission(self, mission: Mission) -> None:
        """임무 추가"""
        self._missions.append(mission)

    def remove_mission(self, drone_id: str) -> bool:
        """임무 제거"""
        before = len(self._missions)
        self._missions = [m for m in self._missions if m.drone_id != drone_id]
        return len(self._missions) < before

    def update_congestion(self, info: CongestionInfo) -> None:
        """혼잡도 정보 업데이트"""
        self._congestion = info

    def get_launch_queue(self) -> list[Mission]:
        """
        출발 큐 생성.

        우선순위순 정렬 후 혼잡도에 따라 출발 간격 조정.
        """
        pending = [m for m in self._missions if not m.scheduled and not m.completed]
        pending.sort(key=lambda m: m.priority_score, reverse=True)

        # 혼잡도 기반 출발 간격 조정
        congestion = self._congestion.congestion_level
        interval = self.stagger_interval_s * (1.0 + congestion * 2.0)

        launch_queue = []
        t = 0.0
        for mission in pending:
            # EMERGENCY는 즉시 출발
            if mission.priority == MissionPriority.EMERGENCY:
                mission.departure_time = 0.0
            else:
                mission.departure_time = t
                t += interval

            launch_queue.append(mission)
            if len(launch_queue) >= self.max_concurrent:
                break

        return launch_queue

    def schedule_next(self, current_time: float) -> list[Mission]:
        """현재 시각에 출발해야 할 임무 반환"""
        ready = []
        for m in self._missions:
            if not m.scheduled and not m.completed and m.departure_time <= current_time:
                m.scheduled = True
                ready.append(m)
        return ready

    def complete_mission(self, drone_id: str) -> None:
        """임무 완료 처리"""
        for m in self._missions:
            if m.drone_id == drone_id:
                m.completed = True
                break

    def estimate_wait_time(self, priority: MissionPriority) -> float:
        """예상 대기 시간 (초)"""
        pending_higher = sum(
            1 for m in self._missions
            if not m.completed and m.priority >= priority
        )
        congestion = self._congestion.congestion_level
        interval = self.stagger_interval_s * (1.0 + congestion * 2.0)
        return pending_higher * interval

    def rebalance(self) -> int:
        """
        혼잡도 변화에 따른 우선순위 재조정.

        혼잡도 높으면 저우선순위 임무 지연.
        Returns: 재조정된 임무 수
        """
        if not self._congestion.is_congested:
            return 0

        adjusted = 0
        congestion = self._congestion.congestion_level
        for m in self._missions:
            if not m.scheduled and m.priority <= MissionPriority.RECREATIONAL:
                m.departure_time += 30.0 * congestion
                adjusted += 1

        return adjusted

    def summary(self) -> dict[str, Any]:
        """스케줄러 요약"""
        by_priority = {}
        for m in self._missions:
            k = m.priority.name
            by_priority[k] = by_priority.get(k, 0) + 1

        return {
            "total_missions": len(self._missions),
            "pending": sum(1 for m in self._missions if not m.scheduled and not m.completed),
            "scheduled": sum(1 for m in self._missions if m.scheduled and not m.completed),
            "completed": sum(1 for m in self._missions if m.completed),
            "by_priority": by_priority,
            "congestion_level": self._congestion.congestion_level,
        }

    def clear(self) -> None:
        self._missions.clear()
        self._congestion = CongestionInfo()

    @property
    def missions(self) -> list[Mission]:
        return list(self._missions)
