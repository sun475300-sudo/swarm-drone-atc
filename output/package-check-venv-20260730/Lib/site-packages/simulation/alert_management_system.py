"""
Phase 454: Alert Management System for Real-Time Notifications
"""

import time
from dataclasses import dataclass


@dataclass
class Alert:
    """``Alert`` 데이터를 표현한다."""
    alert_id: str
    severity: str
    message: str
    drone_id: str
    timestamp: float
    acknowledged: bool = False


class AlertManagementSystem:
    """``AlertManagementSystem`` 역할을 담당한다."""
    def __init__(self):
        """인스턴스를 초기화한다."""
        self.alerts: list[Alert] = []
        self.handlers: dict[str, callable] = {}

    def create_alert(self, severity: str, message: str, drone_id: str = "") -> Alert:
        """`alert` 결과를 생성한다."""
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
        """``acknowledge_alert`` 동작을 수행한다."""
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return True
        return False

    def get_active_alerts(self, severity: str = None) -> list[Alert]:
        """`active alerts` 정보를 조회한다."""
        active = [a for a in self.alerts if not a.acknowledged]
        if severity:
            active = [a for a in active if a.severity == severity]
        return active
