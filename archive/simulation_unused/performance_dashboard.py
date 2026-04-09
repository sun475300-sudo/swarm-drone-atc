"""
Performance Monitoring Dashboard
Phase 380 - Real-time Metrics, KPI Tracking, Alerting
"""

import numpy as np
from dataclasses import dataclass
from typing import Dict, List
from datetime import datetime


@dataclass
class KPIMetric:
    name: str
    value: float
    unit: str
    threshold: float
    status: str


class PerformanceMonitor:
    def __init__(self):
        self.metrics: Dict[str, List[float]] = {}
        self.thresholds = {
            "cpu_usage": 80.0,
            "memory_usage": 85.0,
            "latency_ms": 100.0,
            "packet_loss": 5.0,
        }

    def record(self, metric_name: str, value: float):
        if metric_name not in self.metrics:
            self.metrics[metric_name] = []
        self.metrics[metric_name].append(value)
        if len(self.metrics[metric_name]) > 1000:
            self.metrics[metric_name].pop(0)

    def get_kpis(self) -> List[KPIMetric]:
        kpis = []
        for name, values in self.metrics.items():
            if values:
                avg = np.mean(values[-100:])
                threshold = self.thresholds.get(name, 100)
                status = "ok" if avg < threshold else "warning"
                kpis.append(KPIMetric(name, avg, "%", threshold, status))
        return kpis

    def get_alerts(self) -> List[str]:
        alerts = []
        for kpi in self.get_kpis():
            if kpi.status == "warning":
                alerts.append(f"ALERT: {kpi.name} = {kpi.value:.1f} {kpi.unit}")
        return alerts


class DashboardPublisher:
    def __init__(self):
        self.subscribers = []

    def publish(self, data: Dict):
        for sub in self.subscribers:
            sub.send(data)


def simulate_dashboard():
    print("=== Performance Monitoring Dashboard ===")
    monitor = PerformanceMonitor()

    for _ in range(100):
        monitor.record("cpu_usage", np.random.uniform(30, 90))
        monitor.record("latency_ms", np.random.uniform(10, 150))
        monitor.record("packet_loss", np.random.uniform(0, 8))

    kpis = monitor.get_kpis()
    print("KPIs:")
    for kpi in kpis:
        print(f"  {kpi.name}: {kpi.value:.1f} {kpi.unit} ({kpi.status})")

    alerts = monitor.get_alerts()
    print(f"Alerts: {len(alerts)}")
    return {"kpis": len(kpis), "alerts": len(alerts)}


if __name__ == "__main__":
    simulate_dashboard()
