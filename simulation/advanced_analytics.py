"""Advanced Analytics Dashboard for Phase 200-219.

Provides detailed performance analysis and visualization capabilities
using Plotly Dash for interactive dashboards.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np


@dataclass
class MetricSnapshot:
    """Single metric snapshot at a point in time."""

    timestamp: float
    name: str
    value: float
    unit: str = ""
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class PerformanceReport:
    """Complete performance report for analysis."""

    report_id: str
    created_at: str
    metrics: list[MetricSnapshot]
    summary: dict[str, float]
    recommendations: list[str] = field(default_factory=list)


class AnalyticsAggregator:
    """Aggregates and analyzes performance metrics."""

    def __init__(self) -> None:
        self._snapshots: list[MetricSnapshot] = []
        self._metric_names: set[str] = set()

    def add_snapshot(self, snapshot: MetricSnapshot) -> None:
        """Add a metric snapshot."""
        self._snapshots.append(snapshot)
        self._metric_names.add(snapshot.name)

    def add_snapshots(self, snapshots: list[MetricSnapshot]) -> None:
        """Add multiple snapshots."""
        for s in snapshots:
            self.add_snapshot(s)

    def get_metric_series(self, name: str) -> list[MetricSnapshot]:
        """Get all snapshots for a specific metric."""
        return [s for s in self._snapshots if s.name == name]

    def compute_statistics(self, name: str) -> dict[str, float]:
        """Compute statistics for a metric."""
        values = [s.value for s in self.get_metric_series(name)]
        if not values:
            return {}
        return {
            "count": len(values),
            "mean": float(np.mean(values)),
            "std": float(np.std(values)),
            "min": float(np.min(values)),
            "max": float(np.max(values)),
            "p50": float(np.percentile(values, 50)),
            "p95": float(np.percentile(values, 95)),
            "p99": float(np.percentile(values, 99)),
        }

    def detect_anomalies(
        self,
        name: str,
        threshold_std: float = 3.0,
    ) -> list[MetricSnapshot]:
        """Detect anomalous values using z-score method."""
        values = [s.value for s in self.get_metric_series(name)]
        if len(values) < 3:
            return []
        mean = np.mean(values)
        std = np.std(values)
        anomalies = []
        for s in self.get_metric_series(name):
            z_score = abs((s.value - mean) / (std + 1e-9))
            if z_score > threshold_std:
                anomalies.append(s)
        return anomalies

    def compute_correlation(
        self,
        metric_a: str,
        metric_b: str,
    ) -> float:
        """Compute correlation between two metrics."""
        series_a = self.get_metric_series(metric_a)
        series_b = self.get_metric_series(metric_b)
        if len(series_a) != len(series_b) or len(series_a) < 2:
            return 0.0
        values_a = [s.value for s in series_a]
        values_b = [s.value for s in series_b]
        return float(np.corrcoef(values_a, values_b)[0, 1])

    def generate_report(self) -> PerformanceReport:
        """Generate comprehensive performance report."""
        report_id = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        summary: dict[str, float] = {}
        recommendations: list[str] = []

        for name in self._metric_names:
            stats = self.compute_statistics(name)
            summary[name] = stats.get("mean", 0.0)
            anomalies = self.detect_anomalies(name)
            if anomalies:
                recommendations.append(
                    f"Detected {len(anomalies)} anomalies in '{name}'"
                )

        return PerformanceReport(
            report_id=report_id,
            created_at=datetime.now().isoformat(),
            metrics=self._snapshots,
            summary=summary,
            recommendations=recommendations,
        )

    def export_to_json(self, filepath: str | Path) -> None:
        """Export analytics data to JSON."""
        report = self.generate_report()
        data = {
            "report_id": report.report_id,
            "created_at": report.created_at,
            "summary": report.summary,
            "recommendations": report.recommendations,
            "metrics": [
                {
                    "timestamp": m.timestamp,
                    "name": m.name,
                    "value": m.value,
                    "unit": m.unit,
                    "tags": m.tags,
                }
                for m in report.metrics
            ],
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def get_all_metric_names(self) -> list[str]:
        """Get list of all unique metric names."""
        return sorted(list(self._metric_names))


class PerformanceComparator:
    """Compare performance across different runs or configurations."""

    def __init__(self) -> None:
        self._reports: dict[str, PerformanceReport] = {}

    def add_report(self, name: str, report: PerformanceReport) -> None:
        """Add a performance report."""
        self._reports[name] = report

    def compare_metric(
        self,
        metric_name: str,
        baseline: str,
    ) -> dict[str, dict[str, float]]:
        """Compare a metric across all reports against baseline."""
        if baseline not in self._reports:
            return {}
        baseline_report = self._reports[baseline]
        baseline_value = baseline_report.summary.get(metric_name, 0.0)
        comparison = {}

        for name, report in self._reports.items():
            value = report.summary.get(metric_name, 0.0)
            change_pct = ((value - baseline_value) / (baseline_value + 1e-9)) * 100
            comparison[name] = {
                "value": value,
                "change_pct": change_pct,
                "vs_baseline": value - baseline_value,
            }
        return comparison

    def find_best_performer(
        self,
        metric_name: str,
        higher_is_better: bool = True,
    ) -> str | None:
        """Find the best performing configuration."""
        if not self._reports:
            return None
        values = {
            name: report.summary.get(metric_name, 0.0)
            for name, report in self._reports.items()
        }
        if not values:
            return None
        return (
            max(values, key=values.get)
            if higher_is_better
            else min(values, key=values.get)
        )


class TrendAnalyzer:
    """Analyze trends in performance metrics over time."""

    def __init__(self, window_size: int = 10) -> None:
        self._window_size = window_size

    def compute_moving_average(
        self,
        values: list[float],
        window: int | None = None,
    ) -> list[float]:
        """Compute moving average."""
        window = window or self._window_size
        if len(values) < window:
            return values
        result = []
        for i in range(len(values)):
            start = max(0, i - window + 1)
            result.append(float(np.mean(values[start : i + 1])))
        return result

    def detect_trend(
        self,
        values: list[float],
    ) -> str:
        """Detect overall trend direction."""
        if len(values) < 2:
            return "stable"
        x = np.arange(len(values))
        slope = np.polyfit(x, values, 1)[0]
        if abs(slope) < 0.01 * np.mean(values):
            return "stable"
        return "increasing" if slope > 0 else "decreasing"

    def predict_next_value(
        self,
        values: list[float],
        n_steps: int = 1,
    ) -> list[float]:
        """Predict next values using linear regression."""
        if len(values) < 2:
            return values[-1:] * n_steps
        x = np.arange(len(values))
        coeffs = np.polyfit(x, values, 1)
        predictions = []
        for i in range(n_steps):
            pred = np.polyval(coeffs, len(values) + i)
            predictions.append(float(pred))
        return predictions


class DashboardExporter:
    """Export dashboard data for various formats."""

    def __init__(self, aggregator: AnalyticsAggregator) -> None:
        self._aggregator = aggregator

    def export_plotly_config(
        self,
        metric_names: list[str],
    ) -> dict[str, Any]:
        """Export Plotly configuration for dashboard."""
        traces = []
        colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]
        for i, name in enumerate(metric_names):
            series = self._aggregator.get_metric_series(name)
            if not series:
                continue
            traces.append(
                {
                    "name": name,
                    "x": [s.timestamp for s in series],
                    "y": [s.value for s in series],
                    "type": "scatter",
                    "mode": "lines+markers",
                    "line": {"color": colors[i % len(colors)]},
                }
            )
        return {
            "data": traces,
            "layout": {
                "title": "Performance Metrics",
                "xaxis": {"title": "Time"},
                "yaxis": {"title": "Value"},
                "hovermode": "closest",
            },
        }

    def generate_html_dashboard(
        self,
        output_path: str | Path,
        title: str = "SDACS Performance Dashboard",
    ) -> None:
        """Generate standalone HTML dashboard."""
        metric_names = self._aggregator.get_all_metric_names()
        stats_html = ""
        for name in metric_names:
            stats = self._aggregator.compute_statistics(name)
            stats_html += f"""
            <div class="metric-card">
                <h3>{name}</h3>
                <ul>
                    <li>Mean: {stats.get("mean", 0):.2f}</li>
                    <li>Std: {stats.get("std", 0):.2f}</li>
                    <li>Min: {stats.get("min", 0):.2f}</li>
                    <li>Max: {stats.get("max", 0):.2f}</li>
                    <li>P95: {stats.get("p95", 0):.2f}</li>
                </ul>
            </div>
            """

        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .metric-card {{ border: 1px solid #ddd; padding: 15px; margin: 10px; display: inline-block; }}
        h2 {{ color: #333; }}
        ul {{ list-style: none; padding: 0; }}
        li {{ padding: 5px; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p>Generated: {datetime.now().isoformat()}</p>
    <h2>Metrics Summary</h2>
    {stats_html}
</body>
</html>"""
        with open(output_path, "w") as f:
            f.write(html_content)
