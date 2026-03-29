"""Tests for Real-time Anomaly Detection (Phase 220).

Tests for anomaly detection, monitoring, and alerting.
"""

import json
import shutil
import tempfile
import time

import numpy as np
import pytest

from simulation.realtime_anomaly_detection import (
    Anomaly,
    AnomalyDetector,
    AnomalyType,
    DetectionThresholds,
    RealTimeAnomalyMonitor,
    SeverityLevel,
    StatisticalMonitor,
    anomaly_alert_handler,
)


class TestAnomalyType:
    """Test AnomalyType enum."""

    def test_all_anomaly_types_defined(self):
        """Test all anomaly types are defined."""
        assert len(AnomalyType) == 10
        assert AnomalyType.COLLISION_RISK in AnomalyType
        assert AnomalyType.BATTERY_CRITICAL in AnomalyType
        assert AnomalyType.WEATHER_SEVERE in AnomalyType

    def test_anomaly_type_values(self):
        """Test anomaly type values."""
        assert AnomalyType.COLLISION_RISK.value == "collision_risk"
        assert AnomalyType.BATTERY_CRITICAL.value == "battery_critical"


class TestSeverityLevel:
    """Test SeverityLevel enum."""

    def test_all_severity_levels_defined(self):
        """Test all severity levels are defined."""
        assert len(SeverityLevel) == 4
        assert SeverityLevel.LOW in SeverityLevel
        assert SeverityLevel.CRITICAL in SeverityLevel

    def test_severity_ordering(self):
        """Test severity levels have expected order."""
        levels = [
            SeverityLevel.LOW,
            SeverityLevel.MEDIUM,
            SeverityLevel.HIGH,
            SeverityLevel.CRITICAL,
        ]
        severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        for i in range(len(levels) - 1):
            assert severity_order[levels[i].value] < severity_order[levels[i + 1].value]


class TestAnomaly:
    """Test Anomaly dataclass."""

    def test_anomaly_creation(self):
        """Test anomaly creation."""
        anomaly = Anomaly(
            anomaly_type=AnomalyType.COLLISION_RISK,
            severity=SeverityLevel.HIGH,
            timestamp=time.time(),
            drone_ids=[1, 2],
            description="Test collision",
        )

        assert anomaly.anomaly_type == AnomalyType.COLLISION_RISK
        assert anomaly.severity == SeverityLevel.HIGH
        assert anomaly.drone_ids == [1, 2]
        assert not anomaly.resolved

    def test_anomaly_to_dict(self):
        """Test anomaly conversion to dictionary."""
        anomaly = Anomaly(
            anomaly_type=AnomalyType.BATTERY_CRITICAL,
            severity=SeverityLevel.CRITICAL,
            timestamp=1000.0,
            drone_ids=[5],
            description="Low battery",
            metrics={"battery": 5.0},
            recommended_action="Land immediately",
        )

        d = anomaly.to_dict()
        assert d["anomaly_type"] == "battery_critical"
        assert d["severity"] == "critical"
        assert d["metrics"]["battery"] == 5.0


class TestDetectionThresholds:
    """Test DetectionThresholds dataclass."""

    def test_default_thresholds(self):
        """Test default threshold values."""
        thresholds = DetectionThresholds()

        assert thresholds.collision_distance == 50.0
        assert thresholds.collision_probability == 0.7
        assert thresholds.battery_critical == 10.0

    def test_custom_thresholds(self):
        """Test custom threshold values."""
        thresholds = DetectionThresholds(
            collision_distance=30.0,
            battery_critical=20.0,
            speed_max=50.0,
        )

        assert thresholds.collision_distance == 30.0
        assert thresholds.battery_critical == 20.0
        assert thresholds.speed_max == 50.0


class TestStatisticalMonitor:
    """Test StatisticalMonitor."""

    def test_monitor_initialization(self):
        """Test monitor initialization."""
        monitor = StatisticalMonitor(window_size=50)
        assert monitor._window_size == 50

    def test_update_and_stats(self):
        """Test updating and getting statistics."""
        monitor = StatisticalMonitor(window_size=100)

        for i in range(20):
            monitor.update("test_metric", float(i))

        stats = monitor.get_stats("test_metric")
        assert stats["count"] == 20
        assert stats["mean"] == 9.5

    def test_anomaly_detection(self):
        """Test statistical anomaly detection."""
        monitor = StatisticalMonitor(window_size=100)

        for _ in range(50):
            monitor.update("test_metric", 10.0)

        is_anomaly = monitor.is_anomaly("test_metric", 50.0, n_std=2.0)
        assert is_anomaly

    def test_buffer_overflow(self):
        """Test buffer doesn't exceed window size."""
        monitor = StatisticalMonitor(window_size=10)

        for i in range(20):
            monitor.update("test_metric", float(i))

        stats = monitor.get_stats("test_metric")
        assert stats["count"] == 10


class TestAnomalyDetector:
    """Test AnomalyDetector."""

    def setup_method(self):
        """Setup test fixtures."""
        self.detector = AnomalyDetector()

    def test_collision_detection_close_drones(self):
        """Test collision detection for close drones."""
        positions = np.array([[0, 0, 0], [40, 0, 0], [100, 0, 0]])
        velocities = np.array([[10, 0, 0], [-10, 0, 0], [0, 0, 0]])
        drone_ids = [0, 1, 2]

        anomalies = self.detector.detect_collision_risk(
            positions, velocities, drone_ids
        )

        assert len(anomalies) >= 1
        assert any(a.anomaly_type == AnomalyType.COLLISION_RISK for a in anomalies)

    def test_collision_detection_far_drones(self):
        """Test no collision for far drones."""
        positions = np.array([[0, 0, 0], [500, 0, 0]])
        velocities = np.array([[0, 0, 0], [0, 0, 0]])
        drone_ids = [0, 1]

        anomalies = self.detector.detect_collision_risk(
            positions, velocities, drone_ids
        )

        assert len(anomalies) == 0

    def test_battery_detection_critical(self):
        """Test battery critical detection."""
        battery_levels = np.array([50.0, 5.0, 80.0])
        drone_ids = [0, 1, 2]

        anomalies = self.detector.detect_battery_anomalies(battery_levels, drone_ids)

        assert len(anomalies) == 1
        assert anomalies[0].anomaly_type == AnomalyType.BATTERY_CRITICAL
        assert anomalies[0].drone_ids == [1]

    def test_battery_detection_normal(self):
        """Test no battery anomaly for normal levels."""
        battery_levels = np.array([50.0, 80.0, 90.0])
        drone_ids = [0, 1, 2]

        anomalies = self.detector.detect_battery_anomalies(battery_levels, drone_ids)

        assert len(anomalies) == 0

    def test_speed_detection_anomaly(self):
        """Test speed anomaly detection."""
        speeds = np.array([10.0, 10.0, 50.0])
        drone_ids = [0, 1, 2]

        anomalies = self.detector.detect_speed_anomalies(speeds, drone_ids)

        assert len(anomalies) >= 1
        assert any(a.anomaly_type == AnomalyType.UNUSUAL_SPEED for a in anomalies)

    def test_weather_detection_severe(self):
        """Test severe weather detection."""
        anomalies = self.detector.detect_weather_anomalies(
            wind_speed=25.0, visibility=1000, precipitation=0.5
        )

        assert len(anomalies) >= 1
        assert any(a.anomaly_type == AnomalyType.WEATHER_SEVERE for a in anomalies)

    def test_zone_violation_detection(self):
        """Test zone violation detection."""
        positions = np.array([[0, 0, 0], [-400, 0, 0], [0, 400, 0]])
        boundaries = {"x": (-300, 300), "y": (-300, 300), "z": (0, 200)}
        drone_ids = [0, 1, 2]

        anomalies = self.detector.detect_zone_violations(
            positions, boundaries, drone_ids
        )

        assert len(anomalies) == 2

    def test_enable_disable_detectors(self):
        """Test enabling and disabling detectors."""
        self.detector.disable_detector("battery")

        battery_levels = np.array([5.0])
        anomalies = self.detector.detect_battery_anomalies(battery_levels, [0])

        assert len(anomalies) == 0

        self.detector.enable_detector("battery")
        anomalies = self.detector.detect_battery_anomalies(battery_levels, [0])

        assert len(anomalies) == 1


class TestRealTimeAnomalyMonitor:
    """Test RealTimeAnomalyMonitor."""

    def setup_method(self):
        """Setup test fixtures."""
        self.monitor = RealTimeAnomalyMonitor()

    def test_monitor_initialization(self):
        """Test monitor initialization."""
        assert len(self.monitor._anomalies) == 0
        assert len(self.monitor._alert_callbacks) == 0

    def test_add_alert_callback(self):
        """Test adding alert callback."""
        alerts = []

        def callback(anomaly):
            alerts.append(anomaly)

        self.monitor.add_alert_callback(callback)
        assert len(self.monitor._alert_callbacks) == 1

    def test_detect_all_basic(self):
        """Test basic anomaly detection."""
        positions = np.array([[0, 0, 0], [40, 0, 0]])
        velocities = np.array([[10, 0, 0], [-10, 0, 0]])
        speeds = np.array([10.0, 10.0])
        battery_levels = np.array([50.0, 50.0])
        drone_ids = [0, 1]

        anomalies = self.monitor.detect_all(
            positions=positions,
            velocities=velocities,
            speeds=speeds,
            battery_levels=battery_levels,
            drone_ids=drone_ids,
        )

        assert len(anomalies) > 0

    def test_detect_all_with_weather(self):
        """Test detection with weather data."""
        positions = np.array([[0, 0, 0], [100, 0, 0]])
        velocities = np.array([[0, 0, 0], [0, 0, 0]])
        speeds = np.array([10.0, 10.0])
        battery_levels = np.array([50.0, 50.0])
        drone_ids = [0, 1]

        weather = {"wind_speed": 35.0, "visibility": 500, "precipitation": 0.9}

        anomalies = self.monitor.detect_all(
            positions=positions,
            velocities=velocities,
            speeds=speeds,
            battery_levels=battery_levels,
            drone_ids=drone_ids,
            weather=weather,
        )

        assert any(a.anomaly_type == AnomalyType.WEATHER_SEVERE for a in anomalies)

    def test_get_active_anomalies(self):
        """Test getting active anomalies."""
        positions = np.array([[0, 0, 0], [40, 0, 0]])
        velocities = np.array([[10, 0, 0], [-10, 0, 0]])
        drone_ids = [0, 1]

        self.monitor.detect_all(
            positions=positions,
            velocities=velocities,
            speeds=np.array([10.0, 10.0]),
            battery_levels=np.array([50.0, 50.0]),
            drone_ids=drone_ids,
        )

        active = self.monitor.get_active_anomalies()
        assert len(active) > 0

    def test_resolve_anomaly(self):
        """Test resolving an anomaly."""
        positions = np.array([[0, 0, 0], [40, 0, 0]])
        velocities = np.array([[10, 0, 0], [-10, 0, 0]])
        drone_ids = [0, 1]

        anomalies = self.monitor.detect_all(
            positions=positions,
            velocities=velocities,
            speeds=np.array([10.0, 10.0]),
            battery_levels=np.array([50.0, 50.0]),
            drone_ids=drone_ids,
        )

        if anomalies:
            self.monitor.resolve_anomaly(anomalies[0])
            assert anomalies[0].resolved

    def test_anomaly_summary(self):
        """Test anomaly summary generation."""
        positions = np.array([[0, 0, 0], [40, 0, 0]])
        velocities = np.array([[10, 0, 0], [-10, 0, 0]])
        drone_ids = [0, 1]

        self.monitor.detect_all(
            positions=positions,
            velocities=velocities,
            speeds=np.array([10.0, 10.0]),
            battery_levels=np.array([5.0, 50.0]),
            drone_ids=drone_ids,
        )

        summary = self.monitor.get_anomaly_summary()
        assert "total_anomalies" in summary
        assert "active_anomalies" in summary
        assert summary["total_anomalies"] > 0

    def test_export_anomalies(self):
        """Test exporting anomalies to file."""
        temp_dir = tempfile.mkdtemp()
        filepath = f"{temp_dir}/anomalies.json"

        try:
            positions = np.array([[0, 0, 0], [40, 0, 0]])
            velocities = np.array([[10, 0, 0], [-10, 0, 0]])
            drone_ids = [0, 1]

            self.monitor.detect_all(
                positions=positions,
                velocities=velocities,
                speeds=np.array([10.0, 10.0]),
                battery_levels=np.array([50.0, 50.0]),
                drone_ids=drone_ids,
            )

            self.monitor.export_anomalies(filepath)

            with open(filepath) as f:
                data = json.load(f)
                assert "anomalies" in data
                assert "summary" in data

        finally:
            shutil.rmtree(temp_dir)

    def test_clear_resolved(self):
        """Test clearing resolved anomalies."""
        positions = np.array([[0, 0, 0], [40, 0, 0]])
        velocities = np.array([[10, 0, 0], [-10, 0, 0]])
        drone_ids = [0, 1]

        self.monitor.detect_all(
            positions=positions,
            velocities=velocities,
            speeds=np.array([10.0, 10.0]),
            battery_levels=np.array([50.0, 50.0]),
            drone_ids=drone_ids,
        )

        active_before = len(self.monitor.get_active_anomalies())
        cleared = self.monitor.clear_resolved()
        assert cleared == 0


class TestAnomalyAlertHandler:
    """Test anomaly alert handler."""

    def test_handler_runs_without_error(self):
        """Test handler runs without error."""
        anomaly = Anomaly(
            anomaly_type=AnomalyType.COLLISION_RISK,
            severity=SeverityLevel.HIGH,
            timestamp=time.time(),
            drone_ids=[0, 1],
            description="Test collision",
        )

        anomaly_alert_handler(anomaly)


class TestIntegration:
    """Integration tests."""

    def test_full_detection_pipeline(self):
        """Test complete detection pipeline."""
        monitor = RealTimeAnomalyMonitor()
        alerts = []

        def capture_alert(anomaly):
            alerts.append(anomaly)

        monitor.add_alert_callback(capture_alert)

        n_drones = 10
        np.random.seed(42)

        positions = np.random.uniform(-200, 200, (n_drones, 3))
        positions[0] = positions[1] + np.array([30, 0, 0])

        velocities = np.random.uniform(-5, 5, (n_drones, 3))
        speeds = np.linalg.norm(velocities, axis=1)
        battery_levels = np.random.uniform(20, 100, n_drones)
        battery_levels[5] = 5
        drone_ids = list(range(n_drones))

        anomalies = monitor.detect_all(
            positions=positions,
            velocities=velocities,
            speeds=speeds,
            battery_levels=battery_levels,
            drone_ids=drone_ids,
            weather={"wind_speed": 15.0, "visibility": 5000, "precipitation": 0.1},
            boundaries={"x": (-250, 250), "y": (-250, 250), "z": (0, 150)},
        )

        assert len(alerts) == len(anomalies)
        assert monitor.get_anomaly_summary()["total_anomalies"] > 0

    def test_multiple_detection_rounds(self):
        """Test multiple rounds of detection."""
        monitor = RealTimeAnomalyMonitor()

        for round_num in range(3):
            positions = np.random.uniform(-100, 100, (5, 3))
            velocities = np.random.uniform(-5, 5, (5, 3))

            monitor.detect_all(
                positions=positions,
                velocities=velocities,
                speeds=np.linalg.norm(velocities, axis=1),
                battery_levels=np.array([50.0, 60.0, 70.0, 80.0, 90.0]),
                drone_ids=[0, 1, 2, 3, 4],
            )

        summary = monitor.get_anomaly_summary()
        assert summary["total_anomalies"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
