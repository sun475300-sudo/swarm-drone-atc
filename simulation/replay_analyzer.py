"""
자동 리플레이 분석기
===================
FDR 데이터에서 사고 시나리오를 자동으로 재구성하고
인과관계를 추적하여 사고 리포트를 생성.

사용법:
    analyzer = ReplayAnalyzer()
    analyzer.load_fdr_data(fdr_records)
    report = analyzer.analyze_incident(t_incident=42.3)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class IncidentEvent:
    """사고 이벤트"""
    time: float
    event_type: str  # COLLISION, NEAR_MISS, BREACH, FAILURE
    drone_ids: list[str]
    severity: str = "INFO"
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class CausalChain:
    """인과관계 체인"""
    root_cause: IncidentEvent
    chain: list[IncidentEvent] = field(default_factory=list)
    contributing_factors: list[str] = field(default_factory=list)

    @property
    def depth(self) -> int:
        return len(self.chain)


@dataclass
class IncidentReport:
    """사고 리포트"""
    incident_time: float
    incident_type: str
    involved_drones: list[str]
    causal_chain: CausalChain | None = None
    timeline: list[IncidentEvent] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    summary: str = ""


class ReplayAnalyzer:
    """
    FDR 기반 사고 리플레이 분석기.

    궤적 데이터를 역추적하여 사고 원인을 파악하고
    자동으로 리포트를 생성.
    """

    def __init__(
        self,
        collision_dist: float = 5.0,
        near_miss_dist: float = 15.0,
        lookback_s: float = 30.0,
    ) -> None:
        self.collision_dist = collision_dist
        self.near_miss_dist = near_miss_dist
        self.lookback_s = lookback_s

        self._records: list[dict] = []  # [{tick, drone_id, position, velocity, phase, ...}]
        self._incidents: list[IncidentEvent] = []
        self._reports: list[IncidentReport] = []

    def load_fdr_data(self, records: list[dict]) -> int:
        """FDR 데이터 로드"""
        self._records = sorted(records, key=lambda r: (r.get("tick", 0), r.get("drone_id", "")))
        return len(self._records)

    def detect_incidents(self, dt: float = 0.1) -> list[IncidentEvent]:
        """모든 사고 이벤트 자동 탐지"""
        self._incidents.clear()

        # 틱별로 그룹화
        ticks: dict[int, list[dict]] = {}
        for r in self._records:
            tick = r.get("tick", 0)
            ticks.setdefault(tick, []).append(r)

        for tick, records in sorted(ticks.items()):
            t = tick * dt
            # 근접/충돌 탐지
            for i in range(len(records)):
                for j in range(i + 1, len(records)):
                    pos_i = np.array(records[i].get("position", [0, 0, 0]))
                    pos_j = np.array(records[j].get("position", [0, 0, 0]))
                    dist = float(np.linalg.norm(pos_i - pos_j))

                    if dist < self.collision_dist:
                        self._incidents.append(IncidentEvent(
                            time=t,
                            event_type="COLLISION",
                            drone_ids=[records[i]["drone_id"], records[j]["drone_id"]],
                            severity="CRITICAL",
                            details={"distance": dist},
                        ))
                    elif dist < self.near_miss_dist:
                        self._incidents.append(IncidentEvent(
                            time=t,
                            event_type="NEAR_MISS",
                            drone_ids=[records[i]["drone_id"], records[j]["drone_id"]],
                            severity="WARNING",
                            details={"distance": dist},
                        ))

            # 장애 탐지
            for r in records:
                phase = r.get("phase", "")
                if phase == "FAILED":
                    self._incidents.append(IncidentEvent(
                        time=t,
                        event_type="FAILURE",
                        drone_ids=[r["drone_id"]],
                        severity="CRITICAL",
                        details={"failure_type": r.get("failure_type", "UNKNOWN")},
                    ))

        return self._incidents

    def trace_causal_chain(
        self, incident: IncidentEvent, dt: float = 0.1
    ) -> CausalChain:
        """사고 인과관계 역추적"""
        chain_events = []
        t_start = max(0, incident.time - self.lookback_s)

        # 관련 드론의 이전 이벤트 추적
        related_ids = set(incident.drone_ids)
        for ev in self._incidents:
            if ev.time < incident.time and ev.time >= t_start:
                if any(d in related_ids for d in ev.drone_ids):
                    chain_events.append(ev)
                    related_ids.update(ev.drone_ids)

        chain_events.sort(key=lambda e: e.time)

        contributing = []
        # 기여 요인 분석
        for ev in chain_events:
            if ev.event_type == "NEAR_MISS":
                contributing.append(f"T+{ev.time:.1f}s: 근접 경고 발생 ({', '.join(ev.drone_ids)})")
            elif ev.event_type == "FAILURE":
                contributing.append(f"T+{ev.time:.1f}s: 장애 발생 ({ev.drone_ids[0]})")

        root = chain_events[0] if chain_events else incident
        return CausalChain(
            root_cause=root,
            chain=chain_events,
            contributing_factors=contributing,
        )

    def analyze_incident(
        self, t_incident: float, dt: float = 0.1
    ) -> IncidentReport:
        """특정 시점 사고 분석"""
        if not self._incidents:
            self.detect_incidents(dt)

        # 해당 시점 ±1초 이내 사고 찾기
        nearby = [
            ev for ev in self._incidents
            if abs(ev.time - t_incident) <= 1.0
        ]

        if not nearby:
            return IncidentReport(
                incident_time=t_incident,
                incident_type="NONE",
                involved_drones=[],
                summary="해당 시점에 사고가 발견되지 않았습니다.",
            )

        # 가장 심각한 이벤트 선택
        primary = max(nearby, key=lambda e: (
            3 if e.severity == "CRITICAL" else 2 if e.severity == "WARNING" else 1
        ))

        causal = self.trace_causal_chain(primary, dt)

        # 타임라인 (사고 전후 5초)
        timeline = [
            ev for ev in self._incidents
            if primary.time - 5 <= ev.time <= primary.time + 2
        ]

        # 권장 사항
        recommendations = self._generate_recommendations(primary, causal)

        # 요약 생성
        summary = self._generate_summary(primary, causal)

        report = IncidentReport(
            incident_time=primary.time,
            incident_type=primary.event_type,
            involved_drones=primary.drone_ids,
            causal_chain=causal,
            timeline=timeline,
            recommendations=recommendations,
            summary=summary,
        )
        self._reports.append(report)
        return report

    def _generate_recommendations(
        self, incident: IncidentEvent, causal: CausalChain
    ) -> list[str]:
        """권장 사항 생성"""
        recs = []
        if incident.event_type == "COLLISION":
            recs.append("APF 척력 반경(d0) 확대 검토")
            recs.append("CPA 룩어헤드 시간 연장 (90s → 120s)")
        if incident.event_type == "NEAR_MISS":
            recs.append("동적 분리간격 증가")
        if any(ev.event_type == "FAILURE" for ev in causal.chain):
            recs.append("장애 드론 자동 격리 로직 강화")
        if causal.depth >= 3:
            recs.append("인과관계 체인이 길어 근본 원인 조사 필요")
        return recs

    def _generate_summary(
        self, incident: IncidentEvent, causal: CausalChain
    ) -> str:
        """사고 요약 텍스트 생성"""
        parts = [
            f"T+{incident.time:.1f}s에 {incident.event_type} 발생.",
            f"관련 드론: {', '.join(incident.drone_ids)}.",
        ]
        if causal.contributing_factors:
            parts.append(
                f"기여 요인 {len(causal.contributing_factors)}건: "
                + causal.contributing_factors[0]
            )
        if incident.details.get("distance") is not None:
            parts.append(f"최소 거리: {incident.details['distance']:.1f}m.")
        return " ".join(parts)

    def get_all_reports(self) -> list[IncidentReport]:
        return list(self._reports)

    def clear(self) -> None:
        self._records.clear()
        self._incidents.clear()
        self._reports.clear()
