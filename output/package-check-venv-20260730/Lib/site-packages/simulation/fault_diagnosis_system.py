"""
Phase 447: Fault Diagnosis System for Predictive Maintenance
"""

from dataclasses import dataclass


@dataclass
class FaultCode:
    """``FaultCode`` 관련 기능을 제공한다."""
    code: str
    severity: str
    description: str


@dataclass
class DiagnosticResult:
    """``DiagnosticResult`` 데이터를 표현한다."""
    drone_id: str
    fault_code: FaultCode | None
    health_score: float
    recommendations: list[str]


class FaultDiagnosisSystem:
    """``FaultDiagnosisSystem`` 역할을 담당한다."""
    def __init__(self):
        """인스턴스를 초기화한다."""
        self.fault_codes = {
            "E001": FaultCode("E001", "critical", "Motor failure"),
            "E002": FaultCode("E002", "high", "Battery malfunction"),
            "E003": FaultCode("E003", "medium", "GPS signal loss"),
            "E004": FaultCode("E004", "low", "Sensor calibration needed"),
        }
        self.diagnostic_history: list[DiagnosticResult] = []

    def diagnose(self, drone_id: str, telemetry: dict) -> DiagnosticResult:
        """``diagnose`` 동작을 수행한다."""
        health_score = 1.0

        if telemetry.get("motor_temp", 25) > 80:
            fault = self.fault_codes["E001"]
            health_score -= 0.5
        elif telemetry.get("battery_voltage", 22) < 20:
            fault = self.fault_codes["E002"]
            health_score -= 0.4
        elif telemetry.get("gps_satellites", 10) < 6:
            fault = self.fault_codes["E003"]
            health_score -= 0.2
        else:
            fault = None

        recommendations = []
        if fault:
            recommendations.append(f"Replace {fault.description}")

        result = DiagnosticResult(drone_id, fault, health_score, recommendations)
        self.diagnostic_history.append(result)

        return result

    def predict_failure(self, drone_id: str, history: list[dict]) -> float:
        """`failure` 결과를 계산하거나 판정한다."""
        if len(history) < 5:
            return 0.0

        health_trend = sum(h.get("health_score", 1.0) for h in history[-5:]) / 5

        risk = 1.0 - health_trend
        return risk
