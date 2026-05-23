"""Phase 700: 후-비행(Post-flight) 보고서 통합기."""

from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np

# 분류 임계값 상수
_DEGRADED_DEVIATION_THRESHOLD: int = 3
_DEGRADED_CONFLICT_THRESHOLD: int = 5
_DEGRADED_FUEL_THRESHOLD: float = 85.0

# 단어 경계 기반 ABORT 감지 — "PRE_ABORT_CHECK" 등의 부분 문자열 오탐 방지
# \bABORT\b 는 _ 로 붙은 경우 일치하지 않음 (e.g. PRE_ABORT → 불일치)
_ABORT_RE = re.compile(r"\bABORT\b", re.IGNORECASE)


class ReportOutcome(Enum):
    SUCCESS = "success"
    DEGRADED = "degraded"
    INCIDENT = "incident"
    ABORTED = "aborted"


@dataclass
class FlightMetrics:
    duration_s: float
    distance_m: float
    avg_speed_mps: float
    max_speed_mps: float
    fuel_used_pct: float
    max_altitude_m: float
    conflicts_detected: int = 0
    collisions: int = 0
    deviation_alerts: int = 0


@dataclass
class PostFlightReport:
    report_id: str
    callsign: str
    plan_id: str
    outcome: ReportOutcome
    metrics: FlightMetrics
    events: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    generated_at: float = field(default_factory=time.time)


class PostFlightReporter:
    """경로/이벤트/메트릭을 수집해 운영 보고서를 생성."""

    def __init__(self, max_reports: int = 10_000) -> None:
        if max_reports <= 0:
            raise ValueError("max_reports must be positive")
        self.reports: dict[str, PostFlightReport] = {}
        self.max_reports = max_reports
        self._next_id = 0

    def _gen_id(self) -> str:
        self._next_id += 1
        return f"RPT-{self._next_id:06d}"

    def build_report(
        self,
        callsign: str,
        plan_id: str,
        track_points: list[tuple[float, tuple[float, float, float], float]],
        events: list[str] | None = None,
        conflicts_detected: int = 0,
        collisions: int = 0,
        deviation_alerts: int = 0,
    ) -> PostFlightReport:
        if len(track_points) < 2:
            raise ValueError("need at least 2 track points")
        for i, pt in enumerate(track_points):
            if len(pt[1]) != 3:
                raise ValueError(
                    f"track_points[{i}] position must be a 3-element (lat, lon, alt) tuple, "
                    f"got {len(pt[1])} elements"
                )
            if not all(math.isfinite(v) for v in pt[1]):
                raise ValueError(
                    f"track_points[{i}] position components must be finite, got {pt[1]!r}"
                )
        ts_seq = [p[0] for p in track_points]
        if any(t2 < t1 for t1, t2 in zip(ts_seq, ts_seq[1:])):
            raise ValueError("track_points timestamps must not decrease (no backward steps)")
        if collisions < 0 or conflicts_detected < 0 or deviation_alerts < 0:
            raise ValueError("collision/conflict/deviation counts must be non-negative")
        metrics = self._compute_metrics(track_points, conflicts_detected, collisions, deviation_alerts)
        events_list = list(events or [])
        if not all(isinstance(e, str) for e in events_list):
            raise ValueError("all events must be strings")
        outcome, issues = self._classify_outcome(metrics, events_list)
        report = PostFlightReport(
            report_id=self._gen_id(),
            callsign=callsign,
            plan_id=plan_id,
            outcome=outcome,
            metrics=metrics,
            events=events_list,
            issues=issues,
        )
        self.reports[report.report_id] = report
        # FIFO 방식으로 오래된 보고서 제거 — reports dict 무한 증가 방어
        # dict 삽입 순서는 CPython 3.7+ 에서 보장됨
        if len(self.reports) > self.max_reports:
            oldest_key = next(iter(self.reports))
            del self.reports[oldest_key]
        return report

    @staticmethod
    def _compute_metrics(
        track_points: list[tuple[float, tuple[float, float, float], float]],
        conflicts: int,
        collisions: int,
        deviations: int,
    ) -> FlightMetrics:
        times = np.array([p[0] for p in track_points], dtype=float)
        positions = np.array([p[1] for p in track_points], dtype=float)
        fuels = np.array([p[2] for p in track_points], dtype=float)
        duration = float(times[-1] - times[0])
        deltas = np.diff(positions, axis=0)
        segment_dists = np.linalg.norm(deltas, axis=1)
        distance = float(np.sum(segment_dists))
        dt = np.diff(times)
        # dt == 0 인 세그먼트는 속도 계산에서 제외 (1.0 대체 시 속도 과대 계산됨)
        valid = dt > 0
        if valid.any():
            speeds = segment_dists[valid] / dt[valid]
            avg_speed = float(np.mean(speeds))
            max_speed = float(np.max(speeds))
        else:
            avg_speed = max_speed = 0.0
        fuel_used = float(max(0.0, fuels[0] - fuels[-1]))
        max_alt = float(np.max(positions[:, 2]))
        return FlightMetrics(
            duration_s=duration,
            distance_m=distance,
            avg_speed_mps=avg_speed,
            max_speed_mps=max_speed,
            fuel_used_pct=fuel_used,
            max_altitude_m=max_alt,
            conflicts_detected=conflicts,
            collisions=collisions,
            deviation_alerts=deviations,
        )

    @staticmethod
    def _classify_outcome(
        metrics: FlightMetrics, events: list[str]
    ) -> tuple[ReportOutcome, list[str]]:
        issues: list[str] = []
        if metrics.collisions > 0:
            issues.append(f"{metrics.collisions} collision(s)")
            return ReportOutcome.INCIDENT, issues
        if any(_ABORT_RE.search(e) for e in events):
            issues.append("mission aborted")
            return ReportOutcome.ABORTED, issues
        if (metrics.deviation_alerts > _DEGRADED_DEVIATION_THRESHOLD
                or metrics.conflicts_detected > _DEGRADED_CONFLICT_THRESHOLD):
            issues.append("excessive deviation or conflicts")
            return ReportOutcome.DEGRADED, issues
        if metrics.fuel_used_pct > _DEGRADED_FUEL_THRESHOLD:
            issues.append("high fuel usage")
            return ReportOutcome.DEGRADED, issues
        return ReportOutcome.SUCCESS, issues

    def export_summary(self, report_id: str) -> dict[str, Any] | None:
        r = self.reports.get(report_id)
        if r is None:
            return None
        return {
            "report_id": r.report_id,
            "callsign": r.callsign,
            "plan_id": r.plan_id,
            "outcome": r.outcome.value,
            "duration_s": r.metrics.duration_s,
            "distance_m": r.metrics.distance_m,
            "avg_speed_mps": r.metrics.avg_speed_mps,
            "max_speed_mps": r.metrics.max_speed_mps,
            "fuel_used_pct": r.metrics.fuel_used_pct,
            "max_altitude_m": r.metrics.max_altitude_m,
            "conflicts": r.metrics.conflicts_detected,
            "collisions": r.metrics.collisions,
            "deviations": r.metrics.deviation_alerts,
            # 리스트 복사본 반환 — 호출자 수정이 저장된 보고서에 영향 미치지 않도록
            "events": list(r.events),
            "issues": list(r.issues),
        }

    def outcome_distribution(self) -> dict[str, int]:
        dist: dict[str, int] = {}
        for r in self.reports.values():
            dist[r.outcome.value] = dist.get(r.outcome.value, 0) + 1
        return dist

    def stats(self) -> dict[str, Any]:
        return {
            "total_reports": len(self.reports),
            "outcomes": self.outcome_distribution(),
        }
