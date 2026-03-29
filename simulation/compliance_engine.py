"""Compliance engine for Phase 172.

Executes rule sets against flight snapshots and generates violation reports.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ComplianceRule:
    name: str
    metric: str
    min_value: float | None = None
    max_value: float | None = None
    severity: str = "MEDIUM"
    description: str = ""


@dataclass(frozen=True)
class ComplianceViolation:
    rule_name: str
    drone_id: str
    metric: str
    actual_value: float
    min_value: float | None
    max_value: float | None
    severity: str
    message: str


DEFAULT_RULESET: list[ComplianceRule] = [
    ComplianceRule("MAX_ALT", "altitude_m", max_value=120.0, severity="HIGH", description="K-UTM max altitude"),
    ComplianceRule("MIN_ALT", "altitude_m", min_value=30.0, severity="MEDIUM", description="Minimum safe altitude"),
    ComplianceRule("MAX_SPEED", "speed_mps", max_value=25.0, severity="MEDIUM", description="Speed limit"),
    ComplianceRule("MIN_BATTERY", "battery_pct", min_value=10.0, severity="HIGH", description="Battery safety floor"),
]


class ComplianceEngine:
    def __init__(self, ruleset: list[ComplianceRule] | None = None) -> None:
        self._ruleset = list(ruleset or DEFAULT_RULESET)
        self._violations: list[ComplianceViolation] = []
        self._evaluations = 0

    @property
    def ruleset(self) -> list[ComplianceRule]:
        return list(self._ruleset)

    def register_ruleset(self, ruleset: list[ComplianceRule]) -> None:
        self._ruleset = list(ruleset)

    def _check_rule(self, drone_id: str, rule: ComplianceRule, metrics: dict[str, float]) -> ComplianceViolation | None:
        if rule.metric not in metrics:
            return None

        value = float(metrics[rule.metric])
        violated = False
        reason = ""
        if rule.max_value is not None and value > rule.max_value:
            violated = True
            reason = f"{value:.2f} > {rule.max_value:.2f}"
        if rule.min_value is not None and value < rule.min_value:
            violated = True
            reason = f"{value:.2f} < {rule.min_value:.2f}"

        if not violated:
            return None

        return ComplianceViolation(
            rule_name=rule.name,
            drone_id=drone_id,
            metric=rule.metric,
            actual_value=value,
            min_value=rule.min_value,
            max_value=rule.max_value,
            severity=rule.severity,
            message=f"{rule.name} violation: {reason}",
        )

    def evaluate_flight(self, drone_id: str, **metrics: float) -> list[ComplianceViolation]:
        self._evaluations += 1
        out: list[ComplianceViolation] = []
        for rule in self._ruleset:
            v = self._check_rule(drone_id=drone_id, rule=rule, metrics=metrics)
            if v is not None:
                out.append(v)
                self._violations.append(v)
        return out

    def evaluate_batch(self, snapshots: list[dict[str, Any]]) -> dict[str, list[ComplianceViolation]]:
        by_drone: dict[str, list[ComplianceViolation]] = {}
        for item in snapshots:
            drone_id = str(item.get("drone_id", "UNKNOWN"))
            metrics = {k: v for k, v in item.items() if k != "drone_id"}
            violations = self.evaluate_flight(drone_id, **metrics)
            by_drone[drone_id] = violations
        return by_drone

    def violation_report(self) -> dict[str, Any]:
        by_severity: dict[str, int] = {}
        by_rule: dict[str, int] = {}
        for v in self._violations:
            by_severity[v.severity] = by_severity.get(v.severity, 0) + 1
            by_rule[v.rule_name] = by_rule.get(v.rule_name, 0) + 1
        return {
            "total_violations": len(self._violations),
            "by_severity": by_severity,
            "by_rule": by_rule,
        }

    def summary(self) -> dict[str, Any]:
        report = self.violation_report()
        return {
            "rules": len(self._ruleset),
            "evaluations": self._evaluations,
            "total_violations": report["total_violations"],
        }

    def clear(self) -> None:
        self._violations.clear()
        self._evaluations = 0
