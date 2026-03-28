"""
충돌 포렌식
===========
충돌 근본원인 분석 + 기여도 + 재현 시퀀스.

사용법:
    cf = CollisionForensics()
    cf.record_event("d1", (500, 500, 50), (5, 0, 0), t=10.0)
    report = cf.analyze_collision("d1", "d2", t=15.0)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class ForensicEvent:
    """포렌식 이벤트"""
    drone_id: str
    position: tuple[float, float, float]
    velocity: tuple[float, float, float]
    t: float
    event_type: str = "POSITION"  # POSITION, ADVISORY, COMMAND, FAILURE


@dataclass
class CollisionReport:
    """충돌 분석 보고서"""
    drone_a: str
    drone_b: str
    collision_time: float
    collision_point: tuple[float, float, float]
    closing_speed: float
    root_cause: str
    contributing_factors: list[str]
    timeline: list[ForensicEvent]
    severity: str  # MINOR, MODERATE, SEVERE


class CollisionForensics:
    """충돌 근본원인 분석."""

    def __init__(self, lookback_s: float = 30.0) -> None:
        self._events: dict[str, list[ForensicEvent]] = {}
        self._lookback = lookback_s
        self._reports: list[CollisionReport] = []

    def record_event(
        self,
        drone_id: str,
        position: tuple[float, float, float],
        velocity: tuple[float, float, float] = (0, 0, 0),
        t: float = 0.0,
        event_type: str = "POSITION",
    ) -> None:
        if drone_id not in self._events:
            self._events[drone_id] = []
        self._events[drone_id].append(ForensicEvent(
            drone_id=drone_id, position=position,
            velocity=velocity, t=t, event_type=event_type,
        ))
        # 메모리 제한
        if len(self._events[drone_id]) > 1000:
            self._events[drone_id] = self._events[drone_id][-1000:]

    def analyze_collision(
        self,
        drone_a: str,
        drone_b: str,
        collision_time: float,
    ) -> CollisionReport:
        """충돌 분석"""
        events_a = self._get_lookback(drone_a, collision_time)
        events_b = self._get_lookback(drone_b, collision_time)

        # 충돌 지점 추정
        pos_a = events_a[-1].position if events_a else (0, 0, 0)
        pos_b = events_b[-1].position if events_b else (0, 0, 0)
        collision_point = tuple(
            (np.array(pos_a) + np.array(pos_b)) / 2
        )

        # 접근 속도
        vel_a = events_a[-1].velocity if events_a else (0, 0, 0)
        vel_b = events_b[-1].velocity if events_b else (0, 0, 0)
        closing_speed = float(np.linalg.norm(
            np.array(vel_a) - np.array(vel_b)
        ))

        # 근본원인 분석
        root_cause, factors = self._determine_cause(events_a, events_b)

        # 심각도
        if closing_speed > 20:
            severity = "SEVERE"
        elif closing_speed > 10:
            severity = "MODERATE"
        else:
            severity = "MINOR"

        timeline = sorted(events_a + events_b, key=lambda e: e.t)

        report = CollisionReport(
            drone_a=drone_a,
            drone_b=drone_b,
            collision_time=collision_time,
            collision_point=collision_point,
            closing_speed=closing_speed,
            root_cause=root_cause,
            contributing_factors=factors,
            timeline=timeline,
            severity=severity,
        )
        self._reports.append(report)
        return report

    def _get_lookback(
        self, drone_id: str, t: float,
    ) -> list[ForensicEvent]:
        events = self._events.get(drone_id, [])
        return [e for e in events if t - self._lookback <= e.t <= t]

    def _determine_cause(
        self,
        events_a: list[ForensicEvent],
        events_b: list[ForensicEvent],
    ) -> tuple[str, list[str]]:
        factors = []

        # 어드바이저리 무시 여부
        advisories_a = [e for e in events_a if e.event_type == "ADVISORY"]
        advisories_b = [e for e in events_b if e.event_type == "ADVISORY"]

        if not advisories_a and not advisories_b:
            factors.append("어드바이저리 미발령 — 탐지 실패 가능성")

        # 장애 이벤트
        failures_a = [e for e in events_a if e.event_type == "FAILURE"]
        failures_b = [e for e in events_b if e.event_type == "FAILURE"]

        if failures_a or failures_b:
            factors.append("드론 장애 발생")
            return "장비 고장으로 인한 회피 실패", factors

        # 속도 분석
        if events_a and events_b:
            speeds_a = [np.linalg.norm(e.velocity) for e in events_a]
            speeds_b = [np.linalg.norm(e.velocity) for e in events_b]
            if max(speeds_a, default=0) > 15:
                factors.append(f"드론 A 과속 ({max(speeds_a):.1f} m/s)")
            if max(speeds_b, default=0) > 15:
                factors.append(f"드론 B 과속 ({max(speeds_b):.1f} m/s)")

        if not factors:
            factors.append("경로 충돌 — 분리 간격 부족")

        root_cause = factors[0] if factors else "원인 불명"
        return root_cause, factors

    def get_reports(self) -> list[CollisionReport]:
        return list(self._reports)

    def summary(self) -> dict[str, Any]:
        severity_count: dict[str, int] = {}
        for r in self._reports:
            severity_count[r.severity] = severity_count.get(r.severity, 0) + 1
        return {
            "total_collisions_analyzed": len(self._reports),
            "tracked_drones": len(self._events),
            "by_severity": severity_count,
        }
