"""
드론 리더 선출
==============
분산 리더 선출 + 자동 페일오버 + 합의.

사용법:
    le = LeaderElection()
    le.add_candidate("d1", score=0.9)
    leader = le.elect()
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class Candidate:
    """리더 후보"""
    drone_id: str
    score: float  # 0~1, 높을수록 리더 적합
    battery_pct: float = 100.0
    comm_quality: float = 1.0
    is_leader: bool = False
    term: int = 0


class LeaderElection:
    """분산 리더 선출."""

    def __init__(self, min_score: float = 0.3, failover_timeout_s: float = 10.0) -> None:
        self._candidates: dict[str, Candidate] = {}
        self._current_leader: str | None = None
        self._min_score = min_score
        self._failover_timeout = failover_timeout_s
        self._term = 0
        self._history: list[dict[str, Any]] = []

    def add_candidate(
        self, drone_id: str, score: float = 0.5,
        battery_pct: float = 100.0, comm_quality: float = 1.0,
    ) -> Candidate:
        c = Candidate(drone_id=drone_id, score=score,
                       battery_pct=battery_pct, comm_quality=comm_quality)
        self._candidates[drone_id] = c
        return c

    def remove_candidate(self, drone_id: str) -> bool:
        if drone_id in self._candidates:
            was_leader = self._current_leader == drone_id
            del self._candidates[drone_id]
            if was_leader:
                self._current_leader = None
                self.elect()  # auto failover
            return True
        return False

    def update_score(self, drone_id: str, score: float, battery_pct: float | None = None) -> None:
        c = self._candidates.get(drone_id)
        if c:
            c.score = score
            if battery_pct is not None:
                c.battery_pct = battery_pct

    def elect(self) -> str | None:
        """리더 선출 (최고 점수 * 배터리 * 통신품질)"""
        eligible = [
            c for c in self._candidates.values()
            if c.score >= self._min_score and c.battery_pct > 10
        ]
        if not eligible:
            return self._current_leader

        # 복합 점수
        best = max(eligible, key=lambda c: c.score * (c.battery_pct / 100) * c.comm_quality)

        # 리더 교체
        if self._current_leader and self._current_leader in self._candidates:
            self._candidates[self._current_leader].is_leader = False

        self._term += 1
        best.is_leader = True
        best.term = self._term
        self._current_leader = best.drone_id

        self._history.append({
            "term": self._term,
            "leader": best.drone_id,
            "score": best.score,
        })
        return best.drone_id

    def get_leader(self) -> str | None:
        return self._current_leader

    def is_leader(self, drone_id: str) -> bool:
        return self._current_leader == drone_id

    def failover(self) -> str | None:
        """리더 장애 시 자동 선출"""
        if self._current_leader:
            self._candidates.pop(self._current_leader, None)
            self._current_leader = None
        return self.elect()

    def consensus_score(self) -> float:
        """합의 점수 (리더 점수 대비 평균 점수)"""
        if not self._candidates or not self._current_leader:
            return 0.0
        leader = self._candidates.get(self._current_leader)
        if not leader:
            return 0.0
        avg = np.mean([c.score for c in self._candidates.values()])
        return leader.score / max(avg, 0.01)

    def summary(self) -> dict[str, Any]:
        return {
            "candidates": len(self._candidates),
            "current_leader": self._current_leader,
            "term": self._term,
            "elections_held": len(self._history),
        }
