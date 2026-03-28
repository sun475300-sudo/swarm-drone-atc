"""
침입 탐지 시스템
===============
이상 트래픽 패턴 탐지 + 블랙리스트 + 격리.

사용법:
    ids = IntrusionDetector()
    ids.record_traffic("d1", msg_count=100, error_count=5)
    threats = ids.detect()
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class TrafficRecord:
    """트래픽 기록"""
    node_id: str
    msg_count: int = 0
    error_count: int = 0
    auth_failures: int = 0
    anomaly_score: float = 0.0
    t: float = 0.0


@dataclass
class ThreatReport:
    """위협 보고"""
    node_id: str
    threat_type: str  # FLOOD, AUTH_BRUTE_FORCE, ANOMALY, ERROR_SPIKE
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    detail: str


class IntrusionDetector:
    """침입 탐지."""

    def __init__(
        self, flood_threshold: int = 200,
        auth_fail_threshold: int = 5,
        error_rate_threshold: float = 0.3,
    ) -> None:
        self.flood_threshold = flood_threshold
        self.auth_fail_threshold = auth_fail_threshold
        self.error_rate_threshold = error_rate_threshold
        self._traffic: dict[str, list[TrafficRecord]] = {}
        self._blacklist: set[str] = set()
        self._quarantine: set[str] = set()
        self._threats: list[ThreatReport] = []

    def record_traffic(
        self, node_id: str, msg_count: int = 0,
        error_count: int = 0, auth_failures: int = 0, t: float = 0.0,
    ) -> None:
        if node_id not in self._traffic:
            self._traffic[node_id] = []
        self._traffic[node_id].append(TrafficRecord(
            node_id=node_id, msg_count=msg_count,
            error_count=error_count, auth_failures=auth_failures, t=t,
        ))
        if len(self._traffic[node_id]) > 100:
            self._traffic[node_id] = self._traffic[node_id][-100:]

    def detect(self) -> list[ThreatReport]:
        threats = []

        for node_id, records in self._traffic.items():
            if not records:
                continue
            latest = records[-1]

            # 플러드 감지
            if latest.msg_count > self.flood_threshold:
                threats.append(ThreatReport(
                    node_id=node_id, threat_type="FLOOD",
                    severity="HIGH",
                    detail=f"메시지 {latest.msg_count} > 임계치 {self.flood_threshold}",
                ))

            # 인증 브루트포스
            if latest.auth_failures >= self.auth_fail_threshold:
                threats.append(ThreatReport(
                    node_id=node_id, threat_type="AUTH_BRUTE_FORCE",
                    severity="CRITICAL",
                    detail=f"인증 실패 {latest.auth_failures}회",
                ))

            # 에러율 급등
            if latest.msg_count > 0:
                error_rate = latest.error_count / latest.msg_count
                if error_rate > self.error_rate_threshold:
                    threats.append(ThreatReport(
                        node_id=node_id, threat_type="ERROR_SPIKE",
                        severity="MEDIUM",
                        detail=f"에러율 {error_rate:.1%} > {self.error_rate_threshold:.1%}",
                    ))

            # 이상 패턴 (트래픽 급증)
            if len(records) >= 5:
                counts = [r.msg_count for r in records[-10:]]
                mean = np.mean(counts)
                std = np.std(counts)
                if std > 0 and latest.msg_count > mean + 2 * std:
                    threats.append(ThreatReport(
                        node_id=node_id, threat_type="ANOMALY",
                        severity="MEDIUM",
                        detail=f"트래픽 이상 z-score={(latest.msg_count - mean) / std:.1f}",
                    ))

        self._threats.extend(threats)
        return threats

    def blacklist(self, node_id: str) -> None:
        self._blacklist.add(node_id)

    def quarantine(self, node_id: str) -> None:
        self._quarantine.add(node_id)

    def release(self, node_id: str) -> None:
        self._quarantine.discard(node_id)
        self._blacklist.discard(node_id)

    def is_blocked(self, node_id: str) -> bool:
        return node_id in self._blacklist or node_id in self._quarantine

    def summary(self) -> dict[str, Any]:
        return {
            "nodes_monitored": len(self._traffic),
            "total_threats": len(self._threats),
            "blacklisted": len(self._blacklist),
            "quarantined": len(self._quarantine),
        }
