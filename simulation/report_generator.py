"""
자동 보고서 생성기
==================
시뮬레이션 결과를 구조화된 텍스트 리포트로 변환.
KPI 분석, 이상치 탐지, 권장 사항 자동 생성.

사용법:
    gen = ReportGenerator()
    gen.add_section("overview", {"drones": 50, "duration": 120})
    report = gen.generate()
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np


@dataclass
class ReportSection:
    """보고서 섹션"""
    title: str
    content: str
    data: dict[str, Any] = field(default_factory=dict)
    severity: str = "INFO"  # INFO, WARNING, CRITICAL


@dataclass
class Recommendation:
    """권장 사항"""
    category: str  # SAFETY, PERFORMANCE, COMPLIANCE, EFFICIENCY
    priority: str  # LOW, MEDIUM, HIGH, CRITICAL
    title: str
    description: str
    metric_name: str = ""
    current_value: float = 0.0
    target_value: float = 0.0


class ReportGenerator:
    """
    시뮬레이션 결과 자동 보고서 생성기.

    KPI 분석 + 이상치 탐지 + 권장 사항.
    """

    def __init__(self, title: str = "SDACS 시뮬레이션 보고서") -> None:
        self.title = title
        self._sections: list[ReportSection] = []
        self._recommendations: list[Recommendation] = []
        self._raw_data: dict[str, Any] = {}
        self._generated_at: str = ""

    def add_section(
        self, key: str, data: dict[str, Any], title: str = ""
    ) -> None:
        """데이터 섹션 추가"""
        self._raw_data[key] = data

    def add_simulation_result(self, result: dict[str, Any]) -> None:
        """시뮬레이션 결과 데이터 일괄 추가"""
        self._raw_data["simulation"] = result

    def generate(self) -> str:
        """전체 보고서 생성"""
        self._generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._sections.clear()
        self._recommendations.clear()

        # 1. 헤더
        self._build_header()

        # 2. 개요 섹션
        self._build_overview()

        # 3. KPI 분석
        self._build_kpi_analysis()

        # 4. 안전 분석
        self._build_safety_analysis()

        # 5. 성능 분석
        self._build_performance_analysis()

        # 6. 권장 사항
        self._build_recommendations()

        # 조합
        lines = []
        for section in self._sections:
            severity_marker = ""
            if section.severity == "WARNING":
                severity_marker = " [WARNING]"
            elif section.severity == "CRITICAL":
                severity_marker = " [CRITICAL]"
            lines.append(f"{'='*60}")
            lines.append(f"  {section.title}{severity_marker}")
            lines.append(f"{'='*60}")
            lines.append(section.content)
            lines.append("")

        return "\n".join(lines)

    def generate_summary(self) -> dict[str, Any]:
        """요약 딕셔너리 반환"""
        sim = self._raw_data.get("simulation", {})
        overview = self._raw_data.get("overview", {})

        return {
            "generated_at": self._generated_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "title": self.title,
            "drone_count": overview.get("drones", sim.get("drone_count", 0)),
            "duration_s": overview.get("duration", sim.get("duration", 0)),
            "total_sections": len(self._sections),
            "total_recommendations": len(self._recommendations),
            "critical_recommendations": sum(
                1 for r in self._recommendations if r.priority == "CRITICAL"
            ),
            "raw_data_keys": list(self._raw_data.keys()),
        }

    def get_recommendations(
        self, min_priority: str = "LOW"
    ) -> list[Recommendation]:
        """권장 사항 필터링"""
        priority_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
        min_level = priority_order.get(min_priority, 0)
        return [
            r for r in self._recommendations
            if priority_order.get(r.priority, 0) >= min_level
        ]

    def _build_header(self) -> None:
        header = (
            f"보고서: {self.title}\n"
            f"생성 시각: {self._generated_at}\n"
            f"시스템: SDACS v1.0 (Swarm Drone Airspace Control System)"
        )
        self._sections.append(ReportSection(
            title="보고서 정보", content=header
        ))

    def _build_overview(self) -> None:
        overview = self._raw_data.get("overview", {})
        sim = self._raw_data.get("simulation", {})
        data = {**sim, **overview}

        lines = []
        if "drones" in data or "drone_count" in data:
            lines.append(f"  드론 수: {data.get('drones', data.get('drone_count', 'N/A'))}")
        if "duration" in data:
            lines.append(f"  시뮬레이션 시간: {data['duration']}초")
        if "collisions" in data:
            lines.append(f"  충돌 수: {data['collisions']}")
        if "conflicts" in data:
            lines.append(f"  충돌 위험 수: {data['conflicts']}")
        if "resolution_rate" in data:
            lines.append(f"  충돌 해결률: {data['resolution_rate']:.1%}")

        if not lines:
            lines.append("  데이터 없음")

        self._sections.append(ReportSection(
            title="시뮬레이션 개요",
            content="\n".join(lines),
            data=data,
        ))

    def _build_kpi_analysis(self) -> None:
        sim = self._raw_data.get("simulation", {})
        if not sim:
            return

        lines = []
        # 충돌 해결률
        res_rate = sim.get("resolution_rate", None)
        if res_rate is not None:
            status = "PASS" if res_rate >= 0.95 else "FAIL"
            lines.append(f"  충돌 해결률: {res_rate:.1%} [{status}] (목표: >=95%)")
            if res_rate < 0.95:
                self._recommendations.append(Recommendation(
                    category="SAFETY", priority="HIGH",
                    title="충돌 해결률 미달",
                    description="충돌 해결률이 95% 미만입니다. APF 파라미터 또는 분리 기준 조정이 필요합니다.",
                    metric_name="resolution_rate",
                    current_value=res_rate, target_value=0.95,
                ))

        # 평균 지연
        avg_latency = sim.get("avg_latency_ms", None)
        if avg_latency is not None:
            status = "PASS" if avg_latency < 100 else "FAIL"
            lines.append(f"  평균 관제 지연: {avg_latency:.1f}ms [{status}] (목표: <100ms)")

        # 처리량
        throughput = sim.get("throughput_ops_s", None)
        if throughput is not None:
            lines.append(f"  처리량: {throughput:.1f} ops/s")

        if lines:
            severity = "WARNING" if any("FAIL" in l for l in lines) else "INFO"
            self._sections.append(ReportSection(
                title="KPI 분석",
                content="\n".join(lines),
                severity=severity,
            ))

    def _build_safety_analysis(self) -> None:
        sim = self._raw_data.get("simulation", {})
        safety = self._raw_data.get("safety", {})
        data = {**sim, **safety}

        lines = []
        collisions = data.get("collisions", 0)
        near_misses = data.get("near_misses", data.get("conflicts", 0))

        lines.append(f"  충돌 발생: {collisions}건")
        lines.append(f"  근접 위험: {near_misses}건")

        if collisions > 0:
            self._recommendations.append(Recommendation(
                category="SAFETY", priority="CRITICAL",
                title="충돌 발생",
                description=f"{collisions}건의 충돌이 발생했습니다. 분리 기준 강화 및 CPA 룩어헤드 시간 증가를 권장합니다.",
                metric_name="collisions", current_value=collisions, target_value=0,
            ))

        nfz_violations = data.get("nfz_violations", 0)
        if nfz_violations > 0:
            lines.append(f"  NFZ 침범: {nfz_violations}건")
            self._recommendations.append(Recommendation(
                category="COMPLIANCE", priority="CRITICAL",
                title="비행금지구역 침범",
                description=f"{nfz_violations}건의 NFZ 침범 발생. 지오펜스 여유 거리 확대 필요.",
                metric_name="nfz_violations",
                current_value=nfz_violations, target_value=0,
            ))

        severity = "CRITICAL" if collisions > 0 else "INFO"
        self._sections.append(ReportSection(
            title="안전 분석", content="\n".join(lines), severity=severity,
        ))

    def _build_performance_analysis(self) -> None:
        perf = self._raw_data.get("performance", {})
        sim = self._raw_data.get("simulation", {})
        data = {**sim, **perf}

        lines = []
        tick_p95 = data.get("tick_p95_ms", None)
        if tick_p95 is not None:
            status = "PASS" if tick_p95 < 50 else "WARNING"
            lines.append(f"  틱 처리시간 P95: {tick_p95:.1f}ms [{status}]")
            if tick_p95 >= 50:
                self._recommendations.append(Recommendation(
                    category="PERFORMANCE", priority="MEDIUM",
                    title="틱 처리 시간 초과",
                    description="P95 처리시간이 50ms를 초과합니다. KDTree 공간 인덱스 또는 드론 수 감축을 고려하세요.",
                    metric_name="tick_p95_ms",
                    current_value=tick_p95, target_value=50.0,
                ))

        battery_min = data.get("min_battery_pct", None)
        if battery_min is not None:
            lines.append(f"  최소 배터리 잔량: {battery_min:.1f}%")

        energy_avg = data.get("avg_energy_wh_km", None)
        if energy_avg is not None:
            lines.append(f"  평균 에너지 효율: {energy_avg:.2f} Wh/km")

        if lines:
            self._sections.append(ReportSection(
                title="성능 분석", content="\n".join(lines),
            ))

    def _build_recommendations(self) -> None:
        if not self._recommendations:
            self._sections.append(ReportSection(
                title="권장 사항",
                content="  이상 없음. 모든 지표가 정상 범위입니다.",
            ))
            return

        # 우선순위별 정렬
        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        sorted_recs = sorted(
            self._recommendations,
            key=lambda r: priority_order.get(r.priority, 99),
        )

        lines = []
        for i, rec in enumerate(sorted_recs, 1):
            lines.append(f"  [{rec.priority}] {i}. {rec.title}")
            lines.append(f"    분류: {rec.category}")
            lines.append(f"    설명: {rec.description}")
            if rec.metric_name:
                lines.append(
                    f"    현재: {rec.current_value} → 목표: {rec.target_value}"
                )
            lines.append("")

        severity = "CRITICAL" if any(
            r.priority == "CRITICAL" for r in self._recommendations
        ) else "WARNING"
        self._sections.append(ReportSection(
            title=f"권장 사항 ({len(self._recommendations)}건)",
            content="\n".join(lines),
            severity=severity,
        ))

    def clear(self) -> None:
        self._sections.clear()
        self._recommendations.clear()
        self._raw_data.clear()
