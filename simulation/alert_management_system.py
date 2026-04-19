"""
Phase 454: Alert Management System for Real-Time Notifications
"""

import numpy as np
from typing import Dict, List
from dataclasses import dataclass
import time


@dataclass
class Alert:
    alert_id: str
    severity: str
    message: str
    drone_id: str
    timestamp: float
    acknowledged: bool = False


class AlertManagementSystem:
    def __init__(self):
        self.alerts: List[Alert] = []
        self.handlers: Dict[str, callable] = {}

    def create_alert(self, severity: str, message: str, drone_id: str = "") -> Alert:
        alert = Alert(
            alert_id=f"alert_{int(time.time() * 1000)}",
            severity=severity,
            message=message,
            drone_id=drone_id,
            timestamp=time.time(),
        )
        self.alerts.append(alert)
        return alert

    def acknowledge_alert(self, alert_id: str) -> bool:
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return True
        return False

    def get_active_alerts(self, severity: str = None) -> List[Alert]:
        active = [a for a in self.alerts if not a.acknowledged]
        if severity:
            active = [a for a in active if a.severity == severity]
        return active
