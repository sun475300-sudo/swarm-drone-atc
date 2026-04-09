"""
드론 건강 모니터
================
센서 상태 추적 + 진동 분석 + 예방 정비 스케줄.
이상 징후 사전 탐지 + 잔여 수명 예측.

사용법:
    dhm = DroneHealthMonitor()
    dhm.update("drone_1", motor_rpm=5000, vibration=0.3, temp=45)
    health = dhm.get_health("drone_1")
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class SensorReading:
    """센서 측정값"""
    t: float
    motor_rpm: float = 5000.0
    vibration_g: float = 0.1  # 진동 (g)
    motor_temp_c: float = 40.0
    esc_temp_c: float = 35.0
    bearing_noise_db: float = 30.0
    flight_hours: float = 0.0


@dataclass
class HealthStatus:
    """건강 상태"""
    drone_id: str
    health_score: float  # 0~100
    status: str  # HEALTHY, CAUTION, WARNING, CRITICAL
    remaining_life_hours: float
    next_maintenance_hours: float
    issues: list[str] = field(default_factory=list)


@dataclass
class MaintenanceSchedule:
    """정비 스케줄"""
    drone_id: str
    maintenance_type: str  # ROUTINE, MOTOR, BEARING, ESC
    due_hours: float
    priority: str  # LOW, MEDIUM, HIGH, URGENT
    description: str = ""


class DroneHealthMonitor:
    """
    드론 건강 모니터.

    센서 데이터 기반 건강 점수 + 예방 정비.
    """

    def __init__(
        self,
        maintenance_interval_hours: float = 50.0,
        motor_life_hours: float = 500.0,
    ) -> None:
        self._maintenance_interval = maintenance_interval_hours
        self._motor_life = motor_life_hours
        self._readings: dict[str, list[SensorReading]] = {}
        self._max_history = 500

        # 정상 범위
        self._limits = {
            "motor_rpm": (3000, 8000),
            "vibration_g": (0, 1.5),
            "motor_temp_c": (0, 80),
            "esc_temp_c": (0, 70),
            "bearing_noise_db": (0, 60),
        }

    def update(
        self,
        drone_id: str,
        t: float = 0.0,
        motor_rpm: float = 5000.0,
        vibration: float = 0.1,
        motor_temp: float = 40.0,
        esc_temp: float = 35.0,
        bearing_noise: float = 30.0,
        flight_hours: float = 0.0,
    ) -> HealthStatus:
        """센서 데이터 업데이트"""
        reading = SensorReading(
            t=t, motor_rpm=motor_rpm, vibration_g=vibration,
            motor_temp_c=motor_temp, esc_temp_c=esc_temp,
            bearing_noise_db=bearing_noise, flight_hours=flight_hours,
        )

        if drone_id not in self._readings:
            self._readings[drone_id] = []
        self._readings[drone_id].append(reading)

        if len(self._readings[drone_id]) > self._max_history:
            self._readings[drone_id] = self._readings[drone_id][-self._max_history:]

        return self.get_health(drone_id)

    def get_health(self, drone_id: str) -> HealthStatus:
        """건강 상태 평가"""
        readings = self._readings.get(drone_id, [])
        if not readings:
            return HealthStatus(
                drone_id=drone_id, health_score=100, status="HEALTHY",
                remaining_life_hours=self._motor_life,
                next_maintenance_hours=self._maintenance_interval,
            )

        latest = readings[-1]
        issues = []
        score = 100.0

        # 모터 RPM 검사
        rpm_min, rpm_max = self._limits["motor_rpm"]
        if latest.motor_rpm < rpm_min or latest.motor_rpm > rpm_max:
            score -= 20
            issues.append(f"모터 RPM 이상: {latest.motor_rpm:.0f}")

        # 진동 검사
        vib_max = self._limits["vibration_g"][1]
        if latest.vibration_g > vib_max * 0.8:
            deduct = min(30, (latest.vibration_g / vib_max) * 30)
            score -= deduct
            issues.append(f"진동 높음: {latest.vibration_g:.2f}g")

        # 모터 온도 검사
        temp_max = self._limits["motor_temp_c"][1]
        if latest.motor_temp_c > temp_max * 0.85:
            deduct = min(20, (latest.motor_temp_c / temp_max) * 20)
            score -= deduct
            issues.append(f"모터 과열: {latest.motor_temp_c:.1f}°C")

        # ESC 온도 검사
        esc_max = self._limits["esc_temp_c"][1]
        if latest.esc_temp_c > esc_max * 0.85:
            score -= 15
            issues.append(f"ESC 과열: {latest.esc_temp_c:.1f}°C")

        # 베어링 소음
        noise_max = self._limits["bearing_noise_db"][1]
        if latest.bearing_noise_db > noise_max * 0.7:
            score -= 15
            issues.append(f"베어링 소음: {latest.bearing_noise_db:.0f}dB")

        # 진동 트렌드 (증가 추세면 감점)
        if len(readings) >= 5:
            recent_vibs = [r.vibration_g for r in readings[-10:]]
            if len(recent_vibs) >= 3:
                trend = np.polyfit(range(len(recent_vibs)), recent_vibs, 1)[0]
                if trend > 0.01:
                    score -= 10
                    issues.append(f"진동 증가 추세: +{trend:.3f}g/sample")

        score = max(0, min(100, score))

        # 잔여 수명
        remaining = max(0, self._motor_life - latest.flight_hours)
        # 건강 점수가 낮으면 잔여 수명 감소
        remaining *= score / 100

        # 다음 정비
        next_maint = self._maintenance_interval - (
            latest.flight_hours % self._maintenance_interval
        )

        status = self._status_from_score(score)

        return HealthStatus(
            drone_id=drone_id,
            health_score=round(score, 1),
            status=status,
            remaining_life_hours=round(remaining, 1),
            next_maintenance_hours=round(next_maint, 1),
            issues=issues,
        )

    def get_maintenance_schedule(
        self, drone_id: str
    ) -> list[MaintenanceSchedule]:
        """정비 스케줄 생성"""
        health = self.get_health(drone_id)
        readings = self._readings.get(drone_id, [])
        schedules = []

        # 정기 정비
        schedules.append(MaintenanceSchedule(
            drone_id=drone_id,
            maintenance_type="ROUTINE",
            due_hours=health.next_maintenance_hours,
            priority="MEDIUM",
            description="정기 점검 (모터, 프롭, ESC, 배터리)",
        ))

        if not readings:
            return schedules

        latest = readings[-1]

        # 베어링 정비
        if latest.bearing_noise_db > 45:
            schedules.append(MaintenanceSchedule(
                drone_id=drone_id,
                maintenance_type="BEARING",
                due_hours=max(0, 10 - latest.flight_hours % 10),
                priority="HIGH",
                description=f"베어링 교체 (소음 {latest.bearing_noise_db:.0f}dB)",
            ))

        # 모터 정비
        if latest.vibration_g > 1.0:
            schedules.append(MaintenanceSchedule(
                drone_id=drone_id,
                maintenance_type="MOTOR",
                due_hours=0,
                priority="URGENT",
                description=f"모터 점검 필요 (진동 {latest.vibration_g:.2f}g)",
            ))

        return sorted(schedules, key=lambda s: {"URGENT": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}[s.priority])

    def fleet_health(self) -> dict[str, Any]:
        """전체 함대 건강 요약"""
        if not self._readings:
            return {"total_drones": 0}

        healths = {did: self.get_health(did) for did in self._readings}
        scores = [h.health_score for h in healths.values()]
        by_status: dict[str, int] = {}
        for h in healths.values():
            by_status[h.status] = by_status.get(h.status, 0) + 1

        return {
            "total_drones": len(healths),
            "avg_health": round(float(np.mean(scores)), 1),
            "min_health": round(min(scores), 1),
            "by_status": by_status,
            "urgent_maintenance": sum(
                1 for h in healths.values()
                if h.status in ("WARNING", "CRITICAL")
            ),
        }

    def _status_from_score(self, score: float) -> str:
        if score >= 80:
            return "HEALTHY"
        if score >= 60:
            return "CAUTION"
        if score >= 30:
            return "WARNING"
        return "CRITICAL"

    def clear(self) -> None:
        self._readings.clear()
