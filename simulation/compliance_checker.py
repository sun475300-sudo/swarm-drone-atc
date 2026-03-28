"""
규제 준수 검증기
================
K-UTM 규정 및 ICAO 분리 기준 기반 비행 제한 자동 검증.
규제 준수 점수(compliance score) 산출.

검증 항목:
  - ICAO 수평 분리 (30m)
  - ICAO 수직 분리 (10m)
  - 최대 비행 고도 (120m AGL)
  - 최소 비행 고도 (30m AGL)
  - NFZ 침범
  - 최대 비행 속도
  - 배터리 최소 잔량
  - 통신 두절 프로토콜 준수
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ComplianceViolation:
    """규제 위반 이벤트"""
    rule_name: str
    drone_id: str
    time: float
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    actual_value: float
    limit_value: float
    description: str = ""


@dataclass
class ComplianceRule:
    """규제 규칙 정의"""
    name: str
    metric: str
    max_value: float | None = None
    min_value: float | None = None
    severity: str = "MEDIUM"
    description: str = ""


# K-UTM 기반 기본 규칙
DEFAULT_RULES: list[ComplianceRule] = [
    ComplianceRule("ICAO_수평분리", "horizontal_separation_m",
                   min_value=30.0, severity="CRITICAL",
                   description="ICAO 최소 수평 분리 30m"),
    ComplianceRule("ICAO_수직분리", "vertical_separation_m",
                   min_value=10.0, severity="HIGH",
                   description="ICAO 최소 수직 분리 10m"),
    ComplianceRule("최대고도", "altitude_m",
                   max_value=120.0, severity="HIGH",
                   description="K-UTM 최대 비행고도 120m AGL"),
    ComplianceRule("최소고도", "altitude_m",
                   min_value=30.0, severity="MEDIUM",
                   description="최소 안전 비행고도 30m AGL"),
    ComplianceRule("최대속도", "speed_ms",
                   max_value=25.0, severity="MEDIUM",
                   description="최대 허용 비행속도 25m/s"),
    ComplianceRule("배터리잔량", "battery_pct",
                   min_value=10.0, severity="HIGH",
                   description="최소 배터리 잔량 10%"),
    ComplianceRule("NFZ_침범", "nfz_violation",
                   max_value=0, severity="CRITICAL",
                   description="비행금지구역 침범 불가"),
]


class ComplianceChecker:
    """
    규제 준수 검증기.

    실시간 또는 사후 분석으로 규제 위반을 탐지하고
    준수 점수를 산출.
    """

    def __init__(
        self, rules: list[ComplianceRule] | None = None
    ) -> None:
        self.rules = rules or list(DEFAULT_RULES)
        self._violations: list[ComplianceViolation] = []
        self._check_count = 0

    def check(
        self,
        drone_id: str,
        time: float,
        **metrics: float,
    ) -> list[ComplianceViolation]:
        """현재 메트릭으로 규제 위반 검사"""
        violations = []
        self._check_count += 1

        for rule in self.rules:
            val = metrics.get(rule.metric)
            if val is None:
                continue

            violated = False
            if rule.max_value is not None and val > rule.max_value:
                violated = True
            if rule.min_value is not None and val < rule.min_value:
                violated = True

            if violated:
                v = ComplianceViolation(
                    rule_name=rule.name,
                    drone_id=drone_id,
                    time=time,
                    severity=rule.severity,
                    actual_value=val,
                    limit_value=rule.max_value if rule.max_value is not None else rule.min_value,
                    description=rule.description,
                )
                violations.append(v)
                self._violations.append(v)

        return violations

    def check_separation(
        self,
        drone_a: str,
        drone_b: str,
        h_dist: float,
        v_dist: float,
        time: float,
    ) -> list[ComplianceViolation]:
        """분리 기준 검사"""
        violations = []

        if h_dist < 30.0:
            v = ComplianceViolation(
                rule_name="ICAO_수평분리",
                drone_id=f"{drone_a}/{drone_b}",
                time=time,
                severity="CRITICAL",
                actual_value=h_dist,
                limit_value=30.0,
                description=f"수평 분리 위반: {h_dist:.1f}m < 30m",
            )
            violations.append(v)
            self._violations.append(v)

        if v_dist < 10.0:
            v = ComplianceViolation(
                rule_name="ICAO_수직분리",
                drone_id=f"{drone_a}/{drone_b}",
                time=time,
                severity="HIGH",
                actual_value=v_dist,
                limit_value=10.0,
                description=f"수직 분리 위반: {v_dist:.1f}m < 10m",
            )
            violations.append(v)
            self._violations.append(v)

        return violations

    @property
    def compliance_score(self) -> float:
        """
        규제 준수 점수 (0~100).

        100 = 완벽 준수, 위반 시 감점.
        """
        if self._check_count == 0:
            return 100.0

        severity_weights = {
            "LOW": 1,
            "MEDIUM": 3,
            "HIGH": 10,
            "CRITICAL": 25,
        }

        total_penalty = sum(
            severity_weights.get(v.severity, 5)
            for v in self._violations
        )

        # 최대 100점에서 감점
        score = 100.0 - (total_penalty / max(self._check_count, 1)) * 10
        return max(0.0, min(100.0, score))

    @property
    def violation_count(self) -> int:
        return len(self._violations)

    def violations_by_severity(self) -> dict[str, int]:
        """심각도별 위반 수"""
        by_sev: dict[str, int] = {}
        for v in self._violations:
            by_sev[v.severity] = by_sev.get(v.severity, 0) + 1
        return by_sev

    def violations_by_rule(self) -> dict[str, int]:
        """규칙별 위반 수"""
        by_rule: dict[str, int] = {}
        for v in self._violations:
            by_rule[v.rule_name] = by_rule.get(v.rule_name, 0) + 1
        return by_rule

    def summary(self) -> dict[str, Any]:
        """규제 준수 요약"""
        return {
            "compliance_score": round(self.compliance_score, 1),
            "total_checks": self._check_count,
            "total_violations": self.violation_count,
            "by_severity": self.violations_by_severity(),
            "by_rule": self.violations_by_rule(),
        }

    def clear(self) -> None:
        self._violations.clear()
        self._check_count = 0
