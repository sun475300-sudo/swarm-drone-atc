"""
Phase 460: Logging Aggregation System for Centralized Logging
"""

import numpy as np
from typing import Dict, List
from dataclasses import dataclass
import time


@dataclass
class LogEntry:
    drone_id: str
    level: str
    message: str
    timestamp: float
    metadata: Dict


class LoggingAggregationSystem:
    def __init__(self):
        self.logs: List[LogEntry] = []
        self.log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

    def log(self, drone_id: str, level: str, message: str, metadata: Dict = None):
        entry = LogEntry(drone_id, level, message, time.time(), metadata or {})
        self.logs.append(entry)

    def get_logs(
        self, drone_id: str = None, level: str = None, limit: int = 100
    ) -> List[LogEntry]:
        filtered = self.logs

        if drone_id:
            filtered = [l for l in filtered if l.drone_id == drone_id]

        if level:
            filtered = [l for l in filtered if l.level == level]

        return filtered[-limit:]

    def get_error_count(self, drone_id: str = None) -> int:
        logs = self.get_logs(drone_id, "ERROR", 10000)
        return len(logs)
