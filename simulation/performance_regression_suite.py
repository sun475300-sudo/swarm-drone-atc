"""Phase 304: Performance Regression Suite — 성능 회귀 테스트 스위트.

핵심 성능 지표 벤치마킹, 회귀 감지, 임계값 모니터링,
히스토리 비교 및 자동 알림.
"""

from __future__ import annotations
import numpy as np
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Tuple


@dataclass
class BenchmarkResult:
    name: str
    metric: str
    value: float
    unit: str = ""
    timestamp: float = 0.0
    baseline: Optional[float] = None
    regression: bool = False
    delta_pct: float = 0.0


@dataclass
class BenchmarkConfig:
    name: str
    func: Callable
    metric: str
    unit: str = ""
    n_runs: int = 10
    baseline: Optional[float] = None
    threshold_pct: float = 10.0  # regression if >10% slower


class PerformanceRegressionSuite:
    """성능 회귀 테스트 스위트.

    - 벤치마크 등록 및 실행
    - 기준선 대비 회귀 감지
    - 히스토리 추적 및 추세 분석
    - 자동 알림 생성
    """

    def __init__(self):
        self._benchmarks: Dict[str, BenchmarkConfig] = {}
        self._history: Dict[str, List[BenchmarkResult]] = {}
        self._baselines: Dict[str, float] = {}
        self._alerts: List[str] = []

    def register(self, name: str, func: Callable, metric: str = "time_ms",
                 unit: str = "ms", n_runs: int = 10, baseline: Optional[float] = None,
                 threshold_pct: float = 10.0):
        config = BenchmarkConfig(
            name=name, func=func, metric=metric, unit=unit,
            n_runs=n_runs, baseline=baseline, threshold_pct=threshold_pct,
        )
        self._benchmarks[name] = config
        if baseline is not None:
            self._baselines[name] = baseline

    def run(self, name: str) -> Optional[BenchmarkResult]:
        config = self._benchmarks.get(name)
        if not config:
            return None
        measurements = []
        for _ in range(config.n_runs):
            start = time.perf_counter()
            result_value = config.func()
            elapsed = (time.perf_counter() - start) * 1000  # ms
            if config.metric == "time_ms":
                measurements.append(elapsed)
            elif isinstance(result_value, (int, float)):
                measurements.append(float(result_value))
            else:
                measurements.append(elapsed)
        median_value = float(np.median(measurements))
        baseline = self._baselines.get(name, config.baseline)
        regression = False
        delta_pct = 0.0
        if baseline is not None and baseline > 0:
            delta_pct = (median_value - baseline) / baseline * 100
            if config.metric == "time_ms":
                regression = delta_pct > config.threshold_pct
            else:
                regression = delta_pct < -config.threshold_pct
        result = BenchmarkResult(
            name=name, metric=config.metric, value=round(median_value, 4),
            unit=config.unit, timestamp=time.time(), baseline=baseline,
            regression=regression, delta_pct=round(delta_pct, 2),
        )
        self._history.setdefault(name, []).append(result)
        if regression:
            self._alerts.append(f"REGRESSION: {name} — {delta_pct:+.1f}% ({median_value:.2f} vs baseline {baseline:.2f})")
        return result

    def run_all(self) -> List[BenchmarkResult]:
        return [r for name in self._benchmarks if (r := self.run(name)) is not None]

    def set_baseline(self, name: str, value: float):
        self._baselines[name] = value

    def auto_baseline(self, name: str) -> Optional[float]:
        """최근 결과의 중앙값을 기준선으로 설정."""
        history = self._history.get(name, [])
        if not history:
            return None
        values = [h.value for h in history[-10:]]
        baseline = float(np.median(values))
        self._baselines[name] = baseline
        return baseline

    def get_trend(self, name: str) -> dict:
        history = self._history.get(name, [])
        if len(history) < 3:
            return {"trend": "insufficient_data"}
        values = [h.value for h in history]
        slope = np.polyfit(range(len(values)), values, 1)[0]
        direction = "degrading" if slope > 0.01 else "improving" if slope < -0.01 else "stable"
        return {
            "trend": direction,
            "slope": round(float(slope), 4),
            "latest": values[-1],
            "mean": round(float(np.mean(values)), 4),
        }

    def get_alerts(self) -> List[str]:
        return self._alerts.copy()

    def clear_alerts(self):
        self._alerts.clear()

    def summary(self) -> dict:
        regressions = sum(
            1 for history in self._history.values()
            if history and history[-1].regression
        )
        return {
            "total_benchmarks": len(self._benchmarks),
            "total_runs": sum(len(h) for h in self._history.values()),
            "baselines_set": len(self._baselines),
            "regressions_detected": regressions,
            "active_alerts": len(self._alerts),
        }
