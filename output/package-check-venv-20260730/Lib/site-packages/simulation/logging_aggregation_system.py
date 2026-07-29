"""
Phase 460: Logging Aggregation System for Centralized Logging
"""

import time
from dataclasses import dataclass


@dataclass
class LogEntry:
    """``LogEntry`` 데이터를 표현한다."""
    drone_id: str
    level: str
    message: str
    timestamp: float
    metadata: dict


class LoggingAggregationSystem:
    """``LoggingAggregationSystem`` 역할을 담당한다."""
    def __init__(self):
        """인스턴스를 초기화한다."""
        self.logs: list[LogEntry] = []
        self.log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    def log(self, drone_id: str, level: str, message: str, metadata: dict = None):
        """`대상` 정보를 기록한다."""
        entry = LogEntry(drone_id, level, message, time.time(), metadata or {})
        self.logs.append(entry)

    def get_logs(
        self, drone_id: str = None, level: str = None, limit: int = 100
    ) -> list[LogEntry]:
        """`logs` 정보를 조회한다."""
        filtered = self.logs

        if drone_id:
            filtered = [l for l in filtered if l.drone_id == drone_id]

        if level:
            filtered = [l for l in filtered if l.level == level]

        return filtered[-limit:]

    def get_error_count(self, drone_id: str = None) -> int:
        """`error count` 정보를 조회한다."""
        logs = self.get_logs(drone_id, "ERROR", 10000)
        return len(logs)
