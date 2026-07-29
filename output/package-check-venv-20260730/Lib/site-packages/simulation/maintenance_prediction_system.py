"""
Phase 459: Maintenance Prediction System
"""

from dataclasses import dataclass


@dataclass
class MaintenanceRecord:
    """``MaintenanceRecord`` 데이터를 표현한다."""
    drone_id: str
    component: str
    hours_used: float
    last_maintenance: float


class MaintenancePredictionSystem:
    """``MaintenancePredictionSystem`` 역할을 담당한다."""
    def __init__(self):
        """인스턴스를 초기화한다."""
        self.records: dict[str, list[MaintenanceRecord]] = {}
        self.thresholds = {"motor": 500, "battery": 300, "propeller": 200}

    def add_record(self, record: MaintenanceRecord):
        """`record` 항목을 추가한다."""
        if record.drone_id not in self.records:
            self.records[record.drone_id] = []
        self.records[record.drone_id].append(record)

    def predict_maintenance(self, drone_id: str) -> dict[str, str]:
        """`maintenance` 결과를 계산하거나 판정한다."""
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
