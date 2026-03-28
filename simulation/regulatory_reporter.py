"""
규제 보고서 생성기
==================
K-UTM 준수 보고 + 감사 로그 + 시간대별 규정 준수율.

사용법:
    rr = RegulatoryReporter()
    rr.log_event("d1", "TAKEOFF", t=1.0)
    report = rr.generate_compliance_report()
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class AuditEntry:
    """감사 로그 항목"""
    t: float
    drone_id: str
    event_type: str
    details: str = ""
    compliant: bool = True
    regulation: str = ""


class RegulatoryReporter:
    """K-UTM 규제 보고서 생성."""

    def __init__(self) -> None:
        self._log: list[AuditEntry] = []
        self._violations: list[AuditEntry] = []

    def log_event(
        self,
        drone_id: str,
        event_type: str,
        t: float = 0.0,
        details: str = "",
        compliant: bool = True,
        regulation: str = "",
    ) -> None:
        entry = AuditEntry(
            t=t, drone_id=drone_id, event_type=event_type,
            details=details, compliant=compliant, regulation=regulation,
        )
        self._log.append(entry)
        if not compliant:
            self._violations.append(entry)

    def generate_compliance_report(self) -> str:
        """규제 준수 보고서 생성"""
        total = len(self._log)
        violations = len(self._violations)
        rate = (total - violations) / max(total, 1) * 100

        lines = [
            "=" * 50,
            "  K-UTM 규제 준수 보고서",
            "=" * 50,
            f"  생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"  총 이벤트: {total}건",
            f"  위반: {violations}건",
            f"  준수율: {rate:.1f}%",
            "",
        ]

        if self._violations:
            lines.append("  [ 위반 사항 ]")
            for v in self._violations[-20:]:
                lines.append(
                    f"  t={v.t:.1f}s | {v.drone_id} | {v.event_type} | "
                    f"{v.regulation} | {v.details}"
                )

        by_type: dict[str, int] = {}
        for v in self._violations:
            by_type[v.event_type] = by_type.get(v.event_type, 0) + 1

        if by_type:
            lines.append("")
            lines.append("  [ 유형별 위반 수 ]")
            for t, c in sorted(by_type.items(), key=lambda x: -x[1]):
                lines.append(f"    {t}: {c}건")

        return "\n".join(lines)

    def compliance_rate(self) -> float:
        total = len(self._log)
        if total == 0:
            return 100.0
        return (total - len(self._violations)) / total * 100

    def violations_by_drone(self) -> dict[str, int]:
        by_drone: dict[str, int] = {}
        for v in self._violations:
            by_drone[v.drone_id] = by_drone.get(v.drone_id, 0) + 1
        return by_drone

    def audit_trail(
        self, drone_id: str | None = None, limit: int = 50
    ) -> list[AuditEntry]:
        if drone_id:
            entries = [e for e in self._log if e.drone_id == drone_id]
        else:
            entries = list(self._log)
        return entries[-limit:]

    def summary(self) -> dict[str, Any]:
        return {
            "total_events": len(self._log),
            "total_violations": len(self._violations),
            "compliance_rate": round(self.compliance_rate(), 1),
            "violations_by_drone": self.violations_by_drone(),
        }

    def clear(self) -> None:
        self._log.clear()
        self._violations.clear()
