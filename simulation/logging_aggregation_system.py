"""
Phase 460: Logging Aggregation System for Centralized Logging
"""

import time
from dataclasses import dataclass


@dataclass
class LogEntry:
    drone_id: str
    level: str
    message: str
    timestamp: float
    metadata: dict


class LoggingAggregationSystem:
    def __init__(self):
        self.logs: list[LogEntry] = []
        self.log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    def log(self, drone_id: str, level: str, message: str, metadata: dict = None):
        entry = LogEntry(drone_id, level, message, time.time(), metadata or {})
        self.logs.append(entry)

    def get_logs(
        self, drone_id: str = None, level: str = None, limit: int = 100
    ) -> list[LogEntry]:
        filtered = self.logs

        if drone_id:
            filtered = [l for l in filtered if l.drone_id == drone_id]

        if level:
            filtered = [l for l in filtered if l.level == level]

        return filtered[-limit:]

    def get_error_count(self, drone_id: str = None) -> int:
        logs = self.get_logs(drone_id, "ERROR", 10000)
        return len(logs)
