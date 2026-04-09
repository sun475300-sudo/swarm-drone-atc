"""Phase 292: Telemetry Stream Processor — 텔레메트리 스트림 처리기.

실시간 드론 텔레메트리 수집, 윈도우 집계, 이상치 필터링,
스트림 분석 및 대시보드 피드 생성.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Deque, Callable
from collections import deque


class TelemetryField(Enum):
    ALTITUDE = "altitude"
    SPEED = "speed"
    BATTERY = "battery"
    TEMPERATURE = "temperature"
    VIBRATION = "vibration"
    GPS_ACCURACY = "gps_accuracy"
    SIGNAL_STRENGTH = "signal_strength"
    MOTOR_RPM = "motor_rpm"


@dataclass
class TelemetryPoint:
    drone_id: str
    timestamp: float
    field: TelemetryField
    value: float
    unit: str = ""


@dataclass
class StreamWindow:
    field: TelemetryField
    values: Deque[float] = field(default_factory=lambda: deque(maxlen=100))
    timestamps: Deque[float] = field(default_factory=lambda: deque(maxlen=100))

    @property
    def mean(self) -> float:
        return float(np.mean(self.values)) if self.values else 0.0

    @property
    def std(self) -> float:
        return float(np.std(self.values)) if len(self.values) > 1 else 0.0

    @property
    def min_val(self) -> float:
        return float(min(self.values)) if self.values else 0.0

    @property
    def max_val(self) -> float:
        return float(max(self.values)) if self.values else 0.0


@dataclass
class AnomalyAlert:
    drone_id: str
    field: TelemetryField
    value: float
    expected_range: tuple
    severity: str
    timestamp: float


class TelemetryStreamProcessor:
    """텔레메트리 스트림 처리기.

    - 실시간 데이터 수집 및 윈도우 집계
    - Z-score 기반 이상치 탐지
    - 필드별 임계치 모니터링
    - 스트림 통계 및 알림 생성
    """

    THRESHOLDS = {
        TelemetryField.ALTITUDE: (0, 500),
        TelemetryField.SPEED: (0, 30),
        TelemetryField.BATTERY: (10, 100),
        TelemetryField.TEMPERATURE: (-20, 60),
        TelemetryField.VIBRATION: (0, 5),
        TelemetryField.GPS_ACCURACY: (0, 10),
        TelemetryField.SIGNAL_STRENGTH: (-100, 0),
        TelemetryField.MOTOR_RPM: (0, 12000),
    }

    def __init__(self, window_size: int = 100, z_threshold: float = 3.0):
        self._window_size = window_size
        self._z_threshold = z_threshold
        self._windows: Dict[str, Dict[TelemetryField, StreamWindow]] = {}
        self._alerts: List[AnomalyAlert] = []
        self._callbacks: List[Callable] = []
        self._total_points = 0
        self._total_anomalies = 0

    def register_callback(self, cb: Callable):
        self._callbacks.append(cb)

    def ingest(self, point: TelemetryPoint) -> Optional[AnomalyAlert]:
        self._total_points += 1
        if point.drone_id not in self._windows:
            self._windows[point.drone_id] = {}
        if point.field not in self._windows[point.drone_id]:
            self._windows[point.drone_id][point.field] = StreamWindow(
                field=point.field,
                values=deque(maxlen=self._window_size),
                timestamps=deque(maxlen=self._window_size),
            )
        window = self._windows[point.drone_id][point.field]
        window.values.append(point.value)
        window.timestamps.append(point.timestamp)
        # Check thresholds
        lo, hi = self.THRESHOLDS.get(point.field, (float("-inf"), float("inf")))
        alert = None
        if point.value < lo or point.value > hi:
            severity = "critical" if (point.value < lo * 0.5 or point.value > hi * 1.5) else "warning"
            alert = AnomalyAlert(
                drone_id=point.drone_id, field=point.field, value=point.value,
                expected_range=(lo, hi), severity=severity, timestamp=point.timestamp,
            )
        # Z-score check
        elif len(window.values) > 10:
            z = abs(point.value - window.mean) / max(window.std, 1e-6)
            if z > self._z_threshold:
                alert = AnomalyAlert(
                    drone_id=point.drone_id, field=point.field, value=point.value,
                    expected_range=(window.mean - 2 * window.std, window.mean + 2 * window.std),
                    severity="warning", timestamp=point.timestamp,
                )
        if alert:
            self._alerts.append(alert)
            self._total_anomalies += 1
            for cb in self._callbacks:
                try:
                    cb(alert)
                except Exception:
                    pass
        return alert

    def ingest_batch(self, points: List[TelemetryPoint]) -> List[AnomalyAlert]:
        return [a for p in points if (a := self.ingest(p)) is not None]

    def get_window_stats(self, drone_id: str, field: TelemetryField) -> Optional[dict]:
        windows = self._windows.get(drone_id, {})
        w = windows.get(field)
        if not w or not w.values:
            return None
        return {
            "field": field.value,
            "count": len(w.values),
            "mean": round(w.mean, 3),
            "std": round(w.std, 3),
            "min": round(w.min_val, 3),
            "max": round(w.max_val, 3),
            "latest": round(float(w.values[-1]), 3),
        }

    def get_drone_dashboard(self, drone_id: str) -> Dict[str, dict]:
        result = {}
        for field in TelemetryField:
            stats = self.get_window_stats(drone_id, field)
            if stats:
                result[field.value] = stats
        return result

    def get_alerts(self, drone_id: Optional[str] = None, severity: Optional[str] = None) -> List[AnomalyAlert]:
        alerts = self._alerts
        if drone_id:
            alerts = [a for a in alerts if a.drone_id == drone_id]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        return alerts

    def clear_alerts(self):
        self._alerts.clear()

    def summary(self) -> dict:
        severity_counts = {}
        for a in self._alerts:
            severity_counts[a.severity] = severity_counts.get(a.severity, 0) + 1
        return {
            "tracked_drones": len(self._windows),
            "total_points_ingested": self._total_points,
            "total_anomalies": self._total_anomalies,
            "active_alerts": len(self._alerts),
            "severity_counts": severity_counts,
        }
