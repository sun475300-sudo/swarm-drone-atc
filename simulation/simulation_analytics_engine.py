"""Phase 299: Simulation Analytics Engine — 시뮬레이션 분석 엔진.

대규모 시뮬레이션 결과 분석, KPI 대시보드, 비교 분석,
통계적 유의성 검정, 자동 보고서 생성.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any


class KPICategory(Enum):
    SAFETY = "safety"
    EFFICIENCY = "efficiency"
    PERFORMANCE = "performance"
    RELIABILITY = "reliability"
    SCALABILITY = "scalability"


@dataclass
class KPI:
    name: str
    category: KPICategory
    value: float
    unit: str = ""
    target: Optional[float] = None
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None

    @property
    def status(self) -> str:
        if self.target is not None:
            if abs(self.value - self.target) / max(abs(self.target), 1e-6) < 0.05:
                return "on_target"
        if self.threshold_critical is not None and self.value > self.threshold_critical:
            return "critical"
        if self.threshold_warning is not None and self.value > self.threshold_warning:
            return "warning"
        return "ok"


@dataclass
class SimulationRun:
    run_id: str
    config: dict = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    duration_sec: float = 0.0
    timestamp: float = 0.0


@dataclass
class ComparisonResult:
    metric: str
    baseline_mean: float
    experiment_mean: float
    difference_pct: float
    p_value: float
    significant: bool


class StatisticalTests:
    """통계 검정 도구."""

    @staticmethod
    def welch_t_test(a: List[float], b: List[float]) -> Tuple[float, float]:
        """Welch's t-test (unequal variance)."""
        na, nb = len(a), len(b)
        if na < 2 or nb < 2:
            return 0.0, 1.0
        ma, mb = np.mean(a), np.mean(b)
        va, vb = np.var(a, ddof=1), np.var(b, ddof=1)
        se = np.sqrt(va / na + vb / nb)
        if se < 1e-10:
            return 0.0, 1.0
        t_stat = (ma - mb) / se
        # Approximate p-value using normal distribution for large samples
        p_value = 2 * (1 - min(1.0, 0.5 + 0.5 * np.tanh(abs(t_stat) * 0.7)))
        return float(t_stat), float(p_value)

    @staticmethod
    def effect_size(a: List[float], b: List[float]) -> float:
        """Cohen's d effect size."""
        ma, mb = np.mean(a), np.mean(b)
        pooled_std = np.sqrt((np.var(a, ddof=1) + np.var(b, ddof=1)) / 2)
        if pooled_std < 1e-10:
            return 0.0
        return float((ma - mb) / pooled_std)

    @staticmethod
    def confidence_interval(data: List[float], confidence: float = 0.95) -> Tuple[float, float]:
        n = len(data)
        if n < 2:
            return (np.mean(data), np.mean(data)) if data else (0.0, 0.0)
        mean = np.mean(data)
        se = np.std(data, ddof=1) / np.sqrt(n)
        z = 1.96 if confidence == 0.95 else 2.576
        return (float(mean - z * se), float(mean + z * se))


class SimulationAnalyticsEngine:
    """시뮬레이션 분석 엔진.

    - 다중 실행 결과 수집 및 분석
    - KPI 계산 및 상태 평가
    - A/B 비교 분석 (통계 검정)
    - 추세 분석 및 보고서 생성
    """

    def __init__(self):
        self._runs: Dict[str, SimulationRun] = {}
        self._kpis: Dict[str, KPI] = {}
        self._groups: Dict[str, List[str]] = {}  # group_name -> [run_ids]
        self._stats = StatisticalTests()

    def record_run(self, run: SimulationRun):
        self._runs[run.run_id] = run

    def add_to_group(self, group_name: str, run_id: str):
        self._groups.setdefault(group_name, []).append(run_id)

    def compute_kpi(self, name: str, category: KPICategory, metric_key: str,
                    aggregation: str = "mean", **kwargs) -> Optional[KPI]:
        values = [r.metrics.get(metric_key, 0) for r in self._runs.values() if metric_key in r.metrics]
        if not values:
            return None
        if aggregation == "mean":
            val = float(np.mean(values))
        elif aggregation == "max":
            val = float(np.max(values))
        elif aggregation == "min":
            val = float(np.min(values))
        elif aggregation == "p95":
            val = float(np.percentile(values, 95))
        else:
            val = float(np.mean(values))
        kpi = KPI(name=name, category=category, value=round(val, 4), **kwargs)
        self._kpis[name] = kpi
        return kpi

    def compare_groups(self, group_a: str, group_b: str, metric_key: str) -> Optional[ComparisonResult]:
        runs_a = [self._runs[rid] for rid in self._groups.get(group_a, []) if rid in self._runs]
        runs_b = [self._runs[rid] for rid in self._groups.get(group_b, []) if rid in self._runs]
        vals_a = [r.metrics.get(metric_key, 0) for r in runs_a if metric_key in r.metrics]
        vals_b = [r.metrics.get(metric_key, 0) for r in runs_b if metric_key in r.metrics]
        if len(vals_a) < 2 or len(vals_b) < 2:
            return None
        t_stat, p_value = self._stats.welch_t_test(vals_a, vals_b)
        mean_a, mean_b = np.mean(vals_a), np.mean(vals_b)
        diff_pct = (mean_b - mean_a) / max(abs(mean_a), 1e-6) * 100
        return ComparisonResult(
            metric=metric_key, baseline_mean=round(float(mean_a), 4),
            experiment_mean=round(float(mean_b), 4), difference_pct=round(float(diff_pct), 2),
            p_value=round(p_value, 4), significant=p_value < 0.05,
        )

    def trend_analysis(self, metric_key: str) -> dict:
        """시간순 추세 분석."""
        sorted_runs = sorted(self._runs.values(), key=lambda r: r.timestamp)
        values = [r.metrics.get(metric_key) for r in sorted_runs if metric_key in r.metrics]
        if len(values) < 3:
            return {"trend": "insufficient_data"}
        # Simple linear regression
        x = np.arange(len(values), dtype=float)
        y = np.array(values)
        slope = np.polyfit(x, y, 1)[0]
        direction = "improving" if slope > 0.01 else "degrading" if slope < -0.01 else "stable"
        return {
            "trend": direction,
            "slope": round(float(slope), 4),
            "latest": round(float(values[-1]), 4),
            "mean": round(float(np.mean(values)), 4),
            "std": round(float(np.std(values)), 4),
        }

    def get_kpi_dashboard(self) -> Dict[str, dict]:
        dashboard = {}
        for name, kpi in self._kpis.items():
            dashboard[name] = {
                "value": kpi.value,
                "unit": kpi.unit,
                "status": kpi.status,
                "category": kpi.category.value,
            }
        return dashboard

    def generate_report(self) -> dict:
        """분석 보고서 생성."""
        return {
            "total_runs": len(self._runs),
            "groups": {g: len(rids) for g, rids in self._groups.items()},
            "kpis": self.get_kpi_dashboard(),
            "summary_metrics": {
                k: {"mean": round(float(np.mean(v)), 4), "std": round(float(np.std(v)), 4)}
                for k, v in self._aggregate_metrics().items() if len(v) > 0
            },
        }

    def _aggregate_metrics(self) -> Dict[str, List[float]]:
        agg: Dict[str, List[float]] = {}
        for run in self._runs.values():
            for k, v in run.metrics.items():
                agg.setdefault(k, []).append(v)
        return agg

    def summary(self) -> dict:
        kpi_statuses = {}
        for kpi in self._kpis.values():
            kpi_statuses[kpi.status] = kpi_statuses.get(kpi.status, 0) + 1
        return {
            "total_runs": len(self._runs),
            "total_groups": len(self._groups),
            "total_kpis": len(self._kpis),
            "kpi_statuses": kpi_statuses,
        }
