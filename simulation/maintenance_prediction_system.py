"""
Phase 459: Maintenance Prediction System
"""

import numpy as np
from typing import Dict, List
from dataclasses import dataclass
import time


@dataclass
class MaintenanceRecord:
    drone_id: str
    component: str
    hours_used: float
    last_maintenance: float


class MaintenancePredictionSystem:
    def __init__(self):
        self.records: Dict[str, List[MaintenanceRecord]] = {}
        self.thresholds = {"motor": 500, "battery": 300, "propeller": 200}

    def add_record(self, record: MaintenanceRecord):
        if record.drone_id not in self.records:
            self.records[record.drone_id] = []
        self.records[record.drone_id].append(record)

    def predict_maintenance(self, drone_id: str) -> Dict[str, str]:
        if drone_id not in self.records:
            return {"status": "unknown"}

        predictions = {}
        for record in self.records[drone_id]:
            threshold = self.thresholds.get(record.component, 100)

            if record.hours_used > threshold:
                predictions[record.component] = "overdue"
            elif record.hours_used > threshold * 0.8:
                predictions[record.component] = "soon"
            else:
                predictions[record.component] = "ok"

        return predictions
